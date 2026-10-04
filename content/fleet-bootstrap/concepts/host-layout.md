# Host layout

Every Docker VM in the fleet has the same disks, the same folders, the same file ownership rules, and the same accounts. This page describes them, so a host page can say "the persistent disk" or "owned by 101000" without explaining it again.

Status: written, not yet run. See [Not yet confirmed](#unconfirmed).

All of it comes from the host's NixOS configuration. Nothing here is set up by hand, and a change made by hand to something the configuration owns is undone by the next deploy or reboot. See [The NixOS flake](nixos-flake.md#configuration).

## Three disks {#disks}

| Disk | Mounted at | Holds | On a rebuild |
| --- | --- | --- | --- |
| `scsi0`, 20 GB | `/` | The operating system, with `/boot` and `/nix/store` | Wiped and installed again |
| `scsi1`, 40 GB | `/var/lib/docker` | Images and container layers | Wiped |
| `scsi2`, sized per host | `/srv/persist` | Everything worth keeping | Kept |

OpenTofu creates all three, blank, from the host's entry in the tfvars file. The sizes of the first two are the defaults, and `os_disk_gb` and `docker_disk_gb` change them. The third comes from the host's `extra_disks` entry.

An install partitions the first two disks every time. It formats the persistent disk only when the disk is blank, so a rebuild finds the host's data where it was. See [Rebuilding a VM](../procedures/rebuild-a-vm.md).

The host finds each disk by its slot on the VM, not by the order the kernel meets them in. A disk added later cannot take another's place.

Docker does not start unless all of its mounts are present. A missing data disk would otherwise send every container's data to the OS disk with no error.

The persistent disk is mounted early in the boot, before any service starts, because sshd and the host's secrets both need the keys on it. A host whose persistent disk is detached does not finish booting. Its console in Proxmox is the way in.

## The persistent disk {#persist}

`/srv/persist` is ext4 on the whole disk, with the label `persist`. It has three folders.

| Folder | Bind mounted onto | Holds |
| --- | --- | --- |
| `volumes` | `/opt/docker/volumes` | Every stack's data, config, and secrets |
| `logs` | `/opt/docker/logs` | Every stack's log files |
| `host` | Nothing | What makes this VM itself |

| Under `host` | Holds | Made by |
| --- | --- | --- |
| `ssh` | The SSH host keys, ed25519 and RSA | `install-host`, from the private repo's secrets |
| `komodo/periphery.key` | Periphery's private key | Periphery, at its first start |
| `node-exporter` | Node Exporter's password, certificate, and key | The host, at its first boot |

sshd reads its host keys straight from `host/ssh`, so a rebuilt host answers with the same keys from its first boot. The host's own age key follows from the ed25519 key there, and it is what decrypts the host's secrets. See [Secrets with sops](secrets-with-sops.md#host-keys).

The disk is thin provisioned with discard on, and the host trims its filesystems on a weekly timer, so space freed inside the VM goes back to the Proxmox pool. It grows while the VM runs and never shrinks. See [Growing a disk](../procedures/grow-a-disk.md).

## Stack folders {#stack-folders}

A stack's folders are named for its project, which is `PROJECT_NAME` in its `komodo.env`. Several stacks can share one project: every Traefik stack uses `traefik`.

```text
/opt/docker/volumes/<project>/<container>-<purpose>
/opt/docker/logs/<project>/<container>
```

| Purpose | Holds |
| --- | --- |
| `data` | The container's own state |
| `config` | Config files you may edit |
| `secrets` | Files that hold credentials, mode `0700` on the folder |

Neither Compose nor Periphery creates a bind-mount folder with the right owner, so the folders exist before the first deploy of the stack. Each stack declares its folders, seed files, and ports in its `setup.yaml`, which fleet-stacks generates from its container definitions. `nixos-sync.yml` copies them into the host's file, `nixos/hosts/<host>.json`, and the host's configuration makes them when the host is deployed.

A seed file is a config file the stack needs before its first start. It is copied into place only when nothing is there, so a file you have edited on the host is never put back.

Folders and files under `/opt/docker/volumes` belong to the stacks. Edit them on the host as a stack's page tells you to. Each stack's page lists its folders, under [Stacks](../stacks/index.md).

## Why 100000 and 101000 {#uid-offsets}

Docker runs with `"userns-remap": "default"`, so a container's user IDs are offset by 100000 on the host.

| In the container | On the host | Seen on |
| --- | --- | --- |
| UID 0, root | `100000` | Folders written by a container that runs as root, such as Postgres |
| UID 1000, `PUID` | `101000` | Most folders |
| UID 1001 | `101001` | Semaphore and Bulwark |
| UID 2000 | `102000` | Stalwart |

A container that breaks out as root is an unprivileged user on the host. That is the reason for the remap, and the cost is that every folder has to be owned by the offset ID, not the one in the image's documentation.

A project's two root folders are owned by the admin account with group `101000` and mode `0750`, so you can list them without sudo and containers can traverse them.

## The proxy network {#proxy-network}

Every deployable stack declares the Docker network `proxy` as external, and Compose never creates an external network. A systemd unit on the host, `docker-proxy-network`, creates it after Docker starts and leaves it alone when it is already there. Traefik reaches each published container over it.

## The firewall {#firewall}

The firewall is NixOS's own, built on iptables. It refuses every inbound connection that no rule admits, and logs what it refuses.

| Open | To | Comes from |
| --- | --- | --- |
| Port 22, SSH | Anywhere, rate limited | The host's configuration |
| Port 9100, Node Exporter | Anywhere | The `NODE_EXPORTER` flag |
| UDP ports 60000 to 61000, mosh | Anywhere | The `MOSH` flag |
| A stack's port marked `any` | Anywhere | The stack's `setup.yaml` |
| A stack's port marked `internal` | `docker_stacks_internal_subnet` only | The stack's `setup.yaml` |
| The same port, for a host outside that subnet | The addresses for that port in `docker_stacks_port_sources` | The host's entry in `hosts.yml` |

The rate limit refuses the tenth new SSH connection from one address within thirty seconds. fail2ban bans an address that keeps failing to sign in. SSH takes keys only: the accounts' password works for sudo and at the Proxmox console, and never over SSH.

A port that a container publishes is a special case. Docker passes those connections straight to the container, past the rules above, so on a Docker host the flake also closes each `internal` port to every address outside `docker_stacks_internal_subnet` and that port's `docker_stacks_port_sources` in Docker's own `DOCKER-USER` chain. A port that a container publishes and the stack's `setup.yaml` does not list is open to anyone who can reach the host. List every port a stack publishes.

No command on the host opens a port for good. A rule added by hand is lost at the next deploy or reboot. A port is open because the host's file lists it, so the way to open one is the way a stack gets onto a host: add the stack to the host's `docker_stacks`, generate the host's files again, commit, and run the host. See [After a change](fleet-private.md#after-a-change).

To see the rules a host has:

```bash
sudo iptables -S nixos-fw
```

## Accounts {#accounts}

| Account | Signs in with | Over SSH | sudo |
| --- | --- | --- | --- |
| root | The fleet's password, at the console only | No | Not needed |
| The admin, `<abbr_name>admin` | The keys in `admin_ssh_public_keys` over SSH, or the fleet's password at the console | Yes | Without a password |
| The client, `client_account` | The keys in `client_ssh_public_keys` over SSH, or the fleet's password at the console | Yes | Without a password |
| The deploy account, `ansible` | The keys in `ansible_ssh_public_keys` only. It has no password | Yes | Without a password |

`<abbr_name>` is the identity value of that name, so a fleet whose `abbr_name` is `mm` has the admin `mmadmin`. See [identity values](fleet-private.md#identity).

The fleet's password is one secret, `server-password-hash`, shared by root, the admin, and the client. The deploy account is what the run and `deploy-host` sign in as. The admin and the client are in the `docker` group.

The accounts are fixed by the host's configuration. A password changed with `passwd`, an account added with `useradd`, and a key added to an `authorized_keys` file are all put back by the next deploy. Change the key in `group_vars/all/private.yml`, or the password in `secrets/fleet.yaml`, and run the host. See [Changing a secret](secrets-with-sops.md#edit).

The admin and deploy keys are also inside the installer ISO, so the ISO is built again after either list changes. See [The installer](nixos-flake.md#installer).

## What to back up {#backups}

The persistent disk is the whole answer for a host. Within it, three places cost the most to lose.

| Path | Losing it means |
| --- | --- |
| `/opt/docker/volumes/komodo/komodo-keys` on km01 | Every host's Periphery has to be onboarded again |
| `/opt/docker/volumes/traefik/traefik-certs` on tf01 | Let's Encrypt re-registration and re-issue, both rate limited |
| `/opt/docker/volumes/step-ca` on pk01 | The certificate authority's keys, under `step-ca-data`, and the password that unlocks them, under `step-ca-secrets` |

The operating system needs no backup. It is built again from the fleet-nixos repo and the private repo, so those two repos and the admin age key are what to keep safe off the hosts. See [A lost key](secrets-with-sops.md#lost-key).

## Not yet confirmed {#unconfirmed}

The layout was read from the flake's modules and from an evaluation of the example host. No host has been built.

- A host booting with its persistent disk mounted early, and what the console shows when that disk is missing.
- Docker with `userns-remap` on NixOS. Run `cat /etc/subuid` on a host if the offset ever looks wrong: the line for `dockremap` starts at 100000.
- The folders and seed files as the host makes them, with the owners and modes the stacks expect.
- The firewall rules on a host: the SSH rate limit, the rules that admit the internal subnet only, and the `DOCKER-USER` rules for internal ports that a container publishes. Check them with `sudo iptables -S DOCKER-USER` on a Docker host.
- Signing in as root at the Proxmox console with the fleet's password.
- Node Exporter starting with the password and certificate made at first boot.
