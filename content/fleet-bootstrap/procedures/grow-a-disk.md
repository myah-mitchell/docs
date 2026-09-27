# Growing a disk

A VM has three disks, and they grow in two different ways. The persistent disk is declared in the tfvars file, so it grows through a run, with one command by hand inside the VM afterwards. The root disk and the Docker disk come from the template, so they grow by hand on the Proxmox host. See [Three disks](../concepts/host-layout.md#disks) for what each one holds.

A disk only grows. Proxmox does not shrink one, so never lower a size in the tfvars file.

Status: written, not yet run.

## Prerequisites

- The host was built by the run, so its VM is in `opentofu/prod.tfvars` and in OpenTofu's state.
- The Proxmox storage has room. The disks are thin provisioned, so the pool needs the space as the VM fills it, not on the day the disk grows.
- A recent backup of the VM.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host whose disk grows, such as `id01` |
| `<admin>` | The admin account, `<abbr_name>admin` |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |
| `<address>` | The host's address, `ansible_host` in the inventory |

## 1. Raise the size in the tfvars file {#tfvars}

In the private repo's `opentofu/prod.tfvars`, raise `size_gb` in the host's `persist` entry. This example takes id01 from 20 GB to 40 GB:

```hcl
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 40 }
    }
```

Change nothing else in the entry. From the ansible checkout, commit and push:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Grow the persistent disk of <host>"
git -C ../fleet-private push
```

The Komodo files do not change, so there is nothing to generate.

## 2. Run the host {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

To see the plan before anything changes, tick *Dry Run* in Semaphore or add `--check` to the command. OpenTofu then stops at its plan, which shows the disk's size as the one change to the VM.

The first stage has OpenTofu grow the disk in Proxmox. The later stages find nothing to change. The provision stage creates a filesystem on a disk that has none and leaves an existing one as it is, so it does not grow the filesystem.

The run ends with `failed=0` and `unreachable=0` for the host. On the Proxmox host, confirm the new size:

```bash
qm config <vmid> | grep '^scsi2'
```

The line ends with `size=40G`, or the size you set.

## 3. Grow the filesystem {#filesystem}

Log in to the host as the admin account:

```bash
ssh <admin>@<address>
```

Check that the VM sees the new size:

```bash
lsblk /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi2
```

The *SIZE* column shows the new size. The disk has no partition table, so the filesystem sits on the device itself and grows in one command, while mounted and with the stacks running:

```bash
sudo resize2fs /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi2
```

Then check the mount:

```bash
df -h /srv/persist
```

The *Size* column shows the new size, less the little that ext4 keeps for itself. `/opt/docker/volumes` and `/opt/docker/logs` are folders on the same filesystem, so they show the same figure.

## The disks from the template {#template-disks}

The root disk and the Docker disk are copied from the template when the VM is cloned. The tfvars file has no entry for either, so OpenTofu cannot grow them, and both steps are by hand.

| Disk | Device in the VM | Partition table |
| --- | --- | --- |
| `scsi0`, the root disk | Found in [the root disk](#root-disk) below | Yes, from the Ubuntu cloud image |
| `scsi1`, the Docker disk | `/dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1` | None |

Before growing the Docker disk, check whether pruning is enough. It holds images and container layers and nothing worth keeping:

```bash
docker system df
```

### The Docker disk {#docker-disk}

On the Proxmox host, add to the disk. This adds 20 GB:

```bash
qm resize <vmid> scsi1 +20G
```

On the VM, grow the filesystem and check it:

```bash
sudo resize2fs /dev/disk/by-id/scsi-0QEMU_QEMU_HARDDISK_drive-scsi1
df -h /var/lib/docker
```

### The root disk {#root-disk}

On the Proxmox host:

```bash
qm resize <vmid> scsi0 +10G
```

The root filesystem is in a partition, so the partition has to grow before the filesystem can. On the VM, find the partition mounted at `/`:

```bash
findmnt -n -o SOURCE /
```

With `/dev/sda1` as the answer, grow partition 1 of `/dev/sda`, then the filesystem:

```bash
sudo growpart /dev/sda 1
sudo resize2fs /dev/sda1
df -h /
```

### What a rebuild does to them {#rebuild}

A rebuilt VM is a new clone, so it gets the template's sizes again: 20 GB and 40 GB. To change the size every new VM starts with, set `pve_template_root_disk_size` or `pve_template_docker_disk_size` for the Proxmox host and build the template again. See [Proxmox and the template](../foundation/proxmox-and-template.md#template).

The persistent disk keeps its size through a rebuild, because the disk itself moves to the new VM. See [Rebuilding a VM](rebuild-a-vm.md).

## What's next

Nothing follows from this page. If the disk filled because of one stack, that stack's page lists what it keeps under *Data worth keeping*. See [Stacks](../stacks/index.md).

## Not yet confirmed {#unconfirmed}

No disk in the fleet has been grown by these steps.

- Whether the Proxmox provider grows a disk while the VM runs, or restarts the VM to do it. Plan for the host's stacks to stop for a minute.
- Whether the VM sees the new size at once. If `lsblk` still shows the old size, restart the VM from Proxmox and look again.
- Whether OpenTofu reports a root disk or Docker disk grown with `qm resize` as a change it wants to undo. Neither disk is declared in the VM's resource, so it should not. Run the host with `--check` after growing one, and read the plan.
- Growing the root partition by hand. The commands assume the cloud image has `growpart` installed. cloud-init may also grow the partition by itself at the next boot, in which case a restart of the VM replaces both commands.
- The device names, `drive-scsi1` and `drive-scsi2`. Compare them with `ls -l /dev/disk/by-id` on a real VM.
