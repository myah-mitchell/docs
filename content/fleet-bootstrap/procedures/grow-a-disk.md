# Growing a disk

A VM has three disks, and each one is declared in the tfvars file. A disk grows through a run, which makes it larger in Proxmox, and its filesystem grows by hand on the host afterwards. See [Three disks](../concepts/host-layout.md#disks) for what each one holds.

A disk only grows. Proxmox does not shrink one, and a run fails on a size that was lowered in the tfvars file.

Status: written, not yet run.

## Prerequisites

- The host was built by the run, so its VM is in `opentofu/prod.tfvars` and in OpenTofu's state.
- The Proxmox storage has room. The disks are thin provisioned, so the pool needs the space as the VM fills it, not on the day the disk grows.
- A recent backup of the VM.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host whose disk grows, such as `id01` |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |
| `<address>` | The host's address, `ansible_host` in the inventory |

## 1. Raise the size in the tfvars file {#tfvars}

Each disk has its own key in the host's entry, in the private repo's `opentofu/prod.tfvars`.

| Disk | Mounted at | Key | Size when the key is not set |
| --- | --- | --- | --- |
| `scsi0`, the root disk | `/` | `os_disk_gb` | 20 GB |
| `scsi1`, the Docker disk | `/var/lib/docker` | `docker_disk_gb` | 40 GB |
| `scsi2`, the persistent disk | `/srv/persist` | `size_gb` of the `persist` entry | None. The entry sets it |

Before growing the Docker disk, check on the host whether pruning is enough. It holds images and container layers and nothing worth keeping:

```bash
docker system df
```

This example takes id01's persistent disk from 20 GB to 40 GB:

```hcl
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 40 }
    }
```

Change nothing else in the entry. From `~/src/fleet-ansible`, commit and push:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Grow the persistent disk of <host>"
git -C ../fleet-private push
```

The host's NixOS file and its Komodo file hold no disk size, so there is nothing to generate.

## 2. Run the host {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

To see the plan before anything changes, tick *Dry Run* in Semaphore or add `--check` to the command. OpenTofu then stops at its plan, which shows the disk's size as the one change to the VM.

The first stage has OpenTofu grow the disk in Proxmox. The later stages find nothing to change. Nothing in the host's configuration grows a filesystem, so the filesystem keeps its size until [step 3](#filesystem).

The run ends with `failed=0` and `unreachable=0` for the host. On the Proxmox host, confirm the new size:

```bash
qm config <vmid> | grep '^scsi2'
```

The line ends with `size=40G`, or the size you set. For the root disk the line starts with `scsi0`, and for the Docker disk with `scsi1`.

## 3. Grow the filesystem {#filesystem}

Log in to the host as the admin account:

```bash
ssh <admin>@<address>
```

Each filesystem is ext4 and grows while mounted, with the stacks running. Follow the part for the disk that grew.

### The persistent disk {#persistent-disk}

Check that the VM sees the new size:

```bash
lsblk /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi2
```

The *SIZE* column shows the new size. The disk has no partition table, so the filesystem sits on the device itself and grows in one command:

```bash
sudo resize2fs /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi2
df -h /srv/persist
```

The *Size* column shows the new size, less the little that ext4 keeps for itself. `/opt/docker/volumes` and `/opt/docker/logs` are folders on the same filesystem, so they show the same figure.

### The Docker disk {#docker-disk}

The Docker disk has no partition table either:

```bash
lsblk /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1
sudo resize2fs /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1
df -h /var/lib/docker
```

### The root disk {#root-disk}

The root disk has a partition table. Partition 1 is a small one for GRUB, and partition 2 holds the root filesystem, so the partition has to grow before the filesystem can. Find the partition mounted at `/`:

```bash
findmnt -n -o SOURCE /
```

With `/dev/sda2` as the answer, grow partition 2 of `/dev/sda`, then the filesystem:

```bash
sudo nix shell nixpkgs#cloud-utils.guest -c growpart /dev/sda 2
sudo resize2fs /dev/sda2
df -h /
```

A host does not have `growpart` installed, so `nix shell` fetches it for the one command. The host needs to reach `cache.nixos.org` for that.

## What's next

Nothing follows from this page. If the disk filled because of one stack, that stack's page lists what it keeps under *Data worth keeping*. See [Stacks](../stacks/index.md).

A rebuilt host keeps the sizes in its entry. The install makes the filesystems of the root disk and the Docker disk anew, at the full size of each disk, and the persistent disk keeps the filesystem it has. See [Rebuilding a VM](rebuild-a-vm.md).

## Not yet confirmed {#unconfirmed}

No disk in the fleet has been grown by these steps.

- Whether the Proxmox provider grows a disk while the VM runs, or restarts the VM to do it. Plan for the host's stacks to stop for a minute.
- Whether the VM sees the new size at once. If `lsblk` still shows the old size, restart the VM from Proxmox and look again.
- Growing the root partition. `growpart` was run from the pinned nixpkgs on the control node and printed its help. It has not grown a partition on a host, and the device name `/dev/sda` has not been read from one.
- The device names, `drive-scsi1` and `drive-scsi2`. They are the ones the host's configuration mounts by, and they have not been compared with `ls -l /dev/disk/by-id` on a real VM.
