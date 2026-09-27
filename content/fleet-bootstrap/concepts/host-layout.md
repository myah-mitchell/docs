# Host layout

Every Docker VM in the fleet has the same disks, the same folders, and the same file ownership rules. This page describes them, so a host page can say "the persistent disk" or "owned by 101000" without explaining it again.

## Three disks {#disks}

| Disk | Mounted at | Holds | On a rebuild |
| --- | --- | --- | --- |
| `scsi0`, 20 GB, from the template | `/` | The operating system | Thrown away |
| `scsi1`, 40 GB, from the template | `/var/lib/docker` | Images and container layers | Thrown away |
| `scsi2`, sized per host | `/srv/persist` | Everything worth keeping | Moved to the new VM |

The template carries the first two. OpenTofu adds the third from the host's `extra_disks` entry, before the first boot.

Docker does not start unless all of its mounts are present. The docker role installs a systemd drop-in that requires them, because a missing data disk would otherwise send every container's data to the root disk with no error. SSH is not held back the same way, so a detached disk cannot lock you out.

## The persistent disk {#persist}

`/srv/persist` has three folders.

| Folder | Bind mounted onto | Holds |
| --- | --- | --- |
| `volumes` | `/opt/docker/volumes` | Every stack's data, config, and secrets |
| `logs` | `/opt/docker/logs` | Every stack's log files |
| `host` | Nothing | What makes this VM itself: its SSH host keys and Periphery's private key |

The docker role keeps a copy of the SSH host keys in `host/ssh` and restores them into `/etc/ssh` on a rebuilt VM, so the host keeps its identity once the run has finished. During a rebuild the control node meets the new VM's first keys before the old ones are restored. See [Rebuilding a VM](../procedures/rebuild-a-vm.md). Periphery reads its key straight from `host/komodo`.

The disk is thin provisioned, with discard on and `fstrim.timer` enabled, so space freed inside the VM goes back to the Proxmox pool. It grows while the VM runs and never shrinks. See [Growing a disk](../procedures/grow-a-disk.md).

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

Neither Compose nor Periphery creates a bind-mount folder with the right owner, so the folders exist before the first deploy. The stacks role creates them from the stack's `setup.yaml`, which docker-stacks generates from its container definitions. Each stack's page lists its folders, under [Stacks](../stacks/index.md).

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

Run `cat /etc/subuid` on the host if the offset ever looks wrong.

## The proxy network {#proxy-network}

Every deployable stack declares the Docker network `proxy` as external, and Compose never creates an external network. The docker role creates it during provisioning. Traefik reaches each published container over it.

## What to back up {#backups}

The persistent disk is the whole answer. Within it, three places cost the most to lose.

| Path | Losing it means |
| --- | --- |
| `/opt/docker/volumes/komodo/komodo-keys` on km01 | Every host's Periphery has to be onboarded again |
| `/opt/docker/volumes/traefik/traefik-certs` on tf01 | Let's Encrypt re-registration and re-issue, both rate limited |
| `/opt/docker/volumes/step-ca` on pk01 | The certificate authority's keys, under `step-ca-data`, and the password that unlocks them, under `step-ca-secrets` |
