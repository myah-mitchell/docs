# The NixOS flake

Every VM in the fleet runs NixOS, and one flake in the nixos-fleet repo builds all of them. This page explains what the flake holds, how a host's configuration comes out of it, and what its seven commands do. Read it before the first host, and come back when a run stops in its NixOS stage.

Status: written, not yet run. The flake evaluates and builds on a workstation. See [Not yet confirmed](#unconfirmed).

## Placeholders {#placeholders}

| Placeholder | Value |
| --- | --- |
| `<flake>` | Path of a checkout of [nixos-fleet](https://github.com/myah-mitchell/nixos-fleet), such as `$HOME/src/nixos-fleet` |
| `<fleet-dir>` | Absolute path of the private repo's checkout, such as `$HOME/src/fleet-private` |
| `<host>` | The host's name in the inventory, which is also the name of its file in `nixos/hosts/` |
| `<address>` | The host's IPv4 address |

## What the flake is {#what}

A flake is a git repo with a `flake.nix` that names its inputs, and a `flake.lock` that pins each input to one commit. The same flake and the same lock file build the same system on any machine, which is why a host rebuilt next year comes out as it did today.

| Input | Gives |
| --- | --- |
| `nixpkgs` | Every package and NixOS itself, from the `nixos-26.05` branch |
| `sops-nix` | Decrypting the fleet's secrets on a host |
| `disko` | Partitioning a host's disks at install |
| `fleet` | What the fleet is: its hosts and its secrets |
| `installer-key` | The installer ISO's SSH host key. `build-installer` sets it from the fleet, and the default is the example fleet's key |

The flake is public and holds no host of yours. The `fleet` input is a plain folder, and its default is the example fleet inside the repo. Every command on these pages puts the private repo in its place, so the hosts come from `nixos/` and the secrets from `secrets/` in that repo. See [The private repo](fleet-private.md#generated).

The override reads the private repo through git and takes only the files git tracks. A file you have generated and not yet added does not exist as far as a build is concerned.

## A host's configuration {#configuration}

Each file `nixos/hosts/<host>.json` in the private repo becomes one NixOS configuration, named for the host. The flake's modules are the same for every host. The file's values, together with those in `nixos/fleet.json`, are what make one host differ from the next.

Every host gets the base modules: packages, accounts, CA certificates, time, the network with its static address, sshd and its banner, logging, the swap file, the guest agent, GRUB, and the serial console. The `features` object in the host's file turns on the rest.

| Feature | Inventory flag | Adds |
| --- | --- | --- |
| `firewall` | `FIREWALL` | The firewall, the SSH rate limit, and the ports the host's stacks need |
| `docker` | `DOCKER` | Docker, the Docker disk, the persistent disk, and the folders and seed files of the host's stacks |
| `komodo` | `KOMODO` | Komodo Periphery as a systemd service. It needs `docker` |
| `nodeExporter` | `NODE_EXPORTER` | Node Exporter on port 9100, with TLS and a password |
| `fail2ban` | `FAIL2BAN` | fail2ban with its sshd jail |
| `auditd` | `AUDITD` | The Linux audit system with the fleet's rules |
| `mail` | `MAIL` | Postfix, which sends root's mail to the admin list |
| `mosh` | `MOSH` | mosh and its UDP ports |

[Host layout](host-layout.md) describes what those modules leave on a host: the disks, the folders, the firewall, and the accounts.

A value missing from either file stops the build with a message that names the file and the key. To check that a host builds without touching it, run this from `<flake>`:

```bash
nix build .#nixosConfigurations.<host>.config.system.build.toplevel \
  --override-input fleet git+file://<fleet-dir> \
  --no-write-lock-file --dry-run
```

## The commands {#commands}

The flake carries its own commands, and each brings the tools it calls from the pinned `nixpkgs`. The run calls them for you. Run one by hand when a page says to, or to find out why the run stopped.

```text
nix run <flake>#new-host-key      -- --fleet <fleet-dir> <host>
nix run <flake>#new-installer-key -- --fleet <fleet-dir>
nix run <flake>#build-installer   -- --fleet <fleet-dir> [--flake <flake>]
nix run <flake>#host-state   -- [--user <user>] <address>
nix run <flake>#install-host -- --fleet <fleet-dir> [--flake <flake>] [--build-on local|remote] <host> <address>
nix run <flake>#deploy-host  -- --fleet <fleet-dir> [--flake <flake>] [--user <user>] [--build-on local|remote] [--action switch|boot|test|dry-activate|dry-build] <host> <address>
nix run <flake>#reset-host   -- [--user <user>] --yes-wipe <host> <address>
```

| Command | What it does | Changes |
| --- | --- | --- |
| `new-host-key` | Makes a host's SSH host keys before the host exists and lets the host read the fleet's secrets. See [The host's SSH keys](secrets-with-sops.md#host-keys) | Files in the private repo |
| `new-installer-key` | Makes the installer ISO's SSH host key, once per fleet. See [The installer](#installer) | Files in the private repo |
| `build-installer` | Builds the installer ISO with that key, and prints the ISO's path | The Nix store of the machine that builds |
| `host-state` | Prints `installer`, `installed`, or `unreachable` for an address | Nothing |
| `install-host` | Installs NixOS on a VM that runs the installer, and reboots it | The VM's OS disk and Docker disk, and a blank persistent disk |
| `deploy-host` | Builds a host's configuration and activates it on the host | The host's running system |
| `reset-host` | Wipes the start of the OS disk and reboots, so the VM boots the installer again | The VM's OS disk |

| Option | Default | Meaning |
| --- | --- | --- |
| `--flake` | The flake the command came from | The flake to build the host from |
| `--build-on` | `remote` | `remote` builds on the host. `local` builds on the control node and copies the result |
| `--user` | `ansible` | The account to sign in to an installed host as |
| `--action` | `switch` | What happens to the built system. See [What a deploy does](#deploys) |

Every command prints its options with `--help`. It exits with 0 on success. On failure it prints one line that says what stopped it, and exits with another code.

Five of the commands read the private repo's secrets: `new-host-key`, `new-installer-key`, `build-installer`, `install-host`, and `deploy-host`. Each needs the deploy key or the admin key in its environment. See [Secrets with sops](secrets-with-sops.md#keys).

`host-state` exits with 0 whichever word it prints, and gives up on an address that does not answer after about five seconds. It tells the installer from a built host by a marker file: the installer has `/etc/fleet-installer`, and a built host has `/etc/fleet-host` with its own name in it.

## The installer {#installer}

The installer is a small NixOS on an ISO, built from the same flake. A VM whose OS disk is empty boots it from the CD drive.

| The installer | Detail |
| --- | --- |
| Runs from memory | It writes to no disk until `install-host` tells it to |
| Takes its address from the cloud-init drive | Address, gateway, and nameservers. With no drive attached it asks DHCP |
| Accepts root over SSH, with keys only | The keys are `adminSshKeys` and `deploySshKeys` from `nixos/fleet.json`, as they were when the ISO was built |
| Answers with the fleet's installer key | One SSH host key, the same at every boot, from `secrets/installer.yaml` in the private repo |
| Runs the guest agent | OpenTofu learns the VM's address from it |

The keys are inside the ISO, so the ISO is built again whenever the admin or deploy SSH keys change. The ansible pve role builds it on the control node with `build-installer` and copies it to every Proxmox host.

The installer's host key is how `install-host` knows it talks to the fleet's installer and not to some other machine at the same address, before it sends that machine a host's private keys. `new-installer-key` makes the key once, and it stays encrypted in the private repo for the admin and deploy keys only. The private key is inside the ISO and in the Nix store of the machine that built it. Whoever has it can pass for the installer, and nothing more. See [The installer ISO](../foundation/proxmox-and-installer.md#installer-iso).

> [!WARNING]
> The ISO stays in the CD drive of every VM made from it, so root on any installed host can read the installer's private key. A machine with that key, and a way to take the address of a VM that is being installed, could receive that VM's host keys. Taking the ISO out of each VM after its install would close this, and nothing does that yet. Keep this in mind for any host that runs code you do not trust.

`install-host` works in this order, and stops at the first step that fails.

1. It decrypts the host's SSH host keys and the installer's public key, so a missing key stops the install before anything is touched.
2. It checks that the machine at the address is the installer and answers with the installer's host key, and refuses any other.
3. It partitions and formats the OS disk and the Docker disk.
4. It formats the persistent disk only when the disk is blank. A disk that holds an ext4 filesystem is mounted as it is, and a disk that holds anything else stops the install.
5. It writes the host's SSH host keys to `/srv/persist/host/ssh`.
6. It installs the host's configuration and reboots.

Every connection `install-host` opens itself checks the installer's host key, and those are the ones that carry the host's keys. Steps 3 and 6 run nixos-anywhere, whose own connections check no host key. They carry the system and the disk layout, and no secret in the clear.

> [!WARNING]
> An install wipes the OS disk and the Docker disk of whatever installer answers at `<address>`. Check the address before you run `install-host` by hand.

## What a deploy does {#deploys}

`deploy-host` is how a built host changes, and nothing else changes one. No host updates itself.

A deploy first takes the host's ed25519 host key from the private repo's secrets, and refuses to go on when the machine at the address answers with another key. It then works out the host's configuration on the control node, builds it on the host, and activates it. The host downloads what it lacks from the public NixOS cache.

Activation restarts the services whose configuration changed and leaves the rest running. A deploy that changes nothing restarts nothing. Secrets are decrypted into `/run/secrets` at activation, so a changed secret reaches a host with its next deploy.

| `--action` | Builds | Activates | Boots into it next time |
| --- | --- | --- | --- |
| `switch` | Yes | Yes | Yes |
| `boot` | Yes | No | Yes |
| `test` | Yes | Yes | No |
| `dry-activate` | Yes | No. It lists what a switch would restart | No |
| `dry-build` | No. It lists what would be built, and never reaches the host | No | No |

The run uses `switch`, and `dry-build` in check mode, so that a check run changes nothing on the host. A new kernel takes effect at the next reboot, whichever action brought it. See [Updating the fleet](../procedures/update-the-fleet.md#reboot).

No command changes `flake.lock`. The versions a host is built from move only when the lock file is updated in nixos-fleet and committed. See [Updating the fleet](../procedures/update-the-fleet.md#lock).

## Generations and rollback {#rollback}

Each system a host has activated is kept as a generation. The boot menu lists them, and the host boots the newest unless you pick another at the console.

There are three ways back to an earlier system.

| Way | Use it when |
| --- | --- |
| Put the private repo or nixos-fleet back to the earlier commit and run the host again | You can. It is the only way that leaves the repos and the host in agreement |
| Run `sudo nixos-rebuild switch --rollback` on the host | The host answers over SSH and the fix has to come first |
| Pick the earlier generation in the boot menu, from the VM's console in Proxmox | The host does not come up far enough to answer |

The last two leave the host behind what the repos describe, and the next run brings it forward again. Fix the repos before that run. See [Updating the fleet](../procedures/update-the-fleet.md#rollback).

A rollback covers the operating system only. It does not touch the persistent disk, a stack's data, or what Komodo has deployed.

Generations older than 30 days are deleted by a weekly job on the host, along with whatever in the store nothing else uses. The generation the host runs is always kept.

## Limits {#limits}

- The flake builds `x86_64-linux` hosts on Proxmox, with the three disks OpenTofu gives them. It describes no other hardware.
- One lock file serves every host. Two hosts deployed from the same commit run the same versions, and a host that has not been deployed since the lock file moved runs the older ones.
- Working out one host's configuration took about 1 GiB of memory on the workstation it was measured on. Semaphore's container is limited to 2 GiB, so a run against several hosts at once can run out. See [The Semaphore project](../foundation/semaphore-project.md#nix).
- A host builds its own system by default, which needs memory and a route to the internet on the host.
- Komodo Periphery comes from the flake's own package, pinned to release v2.3.3. The `nixos-26.05` branch carries Komodo 1, which cannot connect out to a version 2 Core.
- The flake has no test that boots a VM. Its checks prove that every host evaluates and that every secret a host asks for exists.

## Not yet confirmed {#unconfirmed}

The flake's checks pass, the example hosts and the installer ISO build, and the commands stop as described when nothing answers. Nothing has run on a VM.

- The ISO booting on a Proxmox VM, taking its address from the cloud-init drive, and its guest agent reporting the address.
- `install-host` from start to end, with the build done on an installer that runs from memory.
- A built host booting from its OS disk, mounting the persistent disk early in the boot, and sshd finding the host keys there.
- An install keeping a persistent disk that already holds a filesystem.
- `deploy-host` against a host as the deploy account.
- `reset-host` leaving the VM in the installer.
- `sudo nixos-rebuild switch --rollback` on a host, and picking a generation in the boot menu. The boot menu waits two seconds.
- How much memory a build takes on a host of the smallest size these pages use.
