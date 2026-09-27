# Rebuilding a VM

A rebuild installs a host again from its configuration and keeps the host's data. It is how a host gets a clean operating system.

The VM stays as it is: the install wipes the root disk and the Docker disk, and it leaves the persistent disk alone. See [Three disks](../concepts/host-layout.md#disks).

| Part | Done by |
| --- | --- |
| Stopping the containers and taking the snapshot | You, on the host and on the Proxmox host |
| Sending the host back to the installer | You, with `reset-host` in a shell |
| Installing NixOS and deploying the host's configuration | The run |
| Deploying the host's Stacks | The run, through Komodo |

km01 and ci01 each need more. Read [Rebuilding km01](#km01) or [Rebuilding ci01](#ci01) before step 1 for those two. When the VM itself is what is broken, see [Replacing the VM](#replace-vm).

Status: written, not yet run.

## Prerequisites

- The control shell, with the fleet's SSH key in the SSH agent. `reset-host` has no Template in Semaphore. See [The control shell](../foundation/control-shell.md).
- The host's files in the private repo are generated, committed and pushed. See [After a change](../concepts/fleet-private.md#after-a-change).
- A run of the host with *Dry Run* ticked in Semaphore, or with `--check` on the command line, ends with `failed=0`. It stops at files that are out of date and at a configuration that does not evaluate, while the host is still up, and does not reach the host.
- The host is healthy and has a recent backup.
- No container version changes in the same session. A newer version that has already written to the data can stop a rollback from being clean.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host being rebuilt, such as `id01` |
| `<address>` | The host's address, `ansible_host` in the inventory |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |
| `<volume>` | The storage and volume name of the VM's `scsi2` disk, found in [step 1](#snapshot) |
| `<dataset>` | The ZFS dataset behind that volume, found in [step 1](#snapshot) |
| `<admin>` | The admin account, `<abbr_name>admin` |

## 1. Snapshot the persistent disk {#snapshot}

The snapshot is the point a rollback can return to. Stop the host's containers first, so that the data is at rest when the snapshot is taken and when the host goes down. Log in to the host as the admin account:

```bash
ssh <admin>@<address>
```

```bash
docker ps -q | xargs -r docker stop
sync
docker ps
```

The last list is empty. Periphery is a service of the host and not a container, so Komodo still shows the Server as connected.

On the Proxmox host, find the disk's volume, then its dataset:

```bash
qm config <vmid> | grep '^scsi2'
pvesm path <volume>
```

`<volume>` is the storage and volume name at the start of the `scsi2` line, such as `local-zfs:vm-7013-disk-2`. The second command prints `/dev/zvol/<dataset>`.

```bash
zfs snapshot <dataset>@pre-rebuild
zfs list -t snapshot <dataset>
```

The list shows `<dataset>@pre-rebuild`.

## 2. Send the host back to the installer {#reset}

> [!WARNING]
> The command ends the host's operating system. From here the host is down until the run in [step 3](#run) finishes, and everything on its root disk and its Docker disk is lost.

From `~/src/ansible`:

```bash
nix run ../nixos-fleet#reset-host -- --yes-wipe <host> <address>
```

The command reads the name the host gives itself in `/etc/fleet-host`, and wipes nothing when it is not `<host>`. Then it overwrites the start of the root disk and restarts the VM, which finds nothing to boot on that disk and boots the installer ISO. The last line reads:

```text
reset-host: wiped the start of the OS disk of <host>, which now reboots into the installer
```

Ask the VM what it runs, and repeat the command until it prints `installer`:

```bash
nix run ../nixos-fleet#host-state -- <address>
```

## 3. Run the host {#run}

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

| Stage | What it does on a host that was reset |
| --- | --- |
| Create the VM | Nothing. The VM is the one OpenTofu knows |
| Wait | Finds the installer's SSH port open |
| NixOS | Finds the installer, and installs. The install makes the root disk and the Docker disk anew, keeps the filesystem on the persistent disk, installs NixOS, and restarts the VM. Then the stage deploys the host's configuration |
| Deploy the stacks | Has Komodo deploy each of the host's Stacks. The Docker disk is empty, so every image is pulled again |

The host keeps its identity. Its SSH host keys come from the private repo's secrets and sit on the persistent disk, so the host answers with the keys it had. Periphery's key is on the same disk, so Komodo sees the Server it knew.

## 4. Verify {#verify}

--8<-- "verify-run.md"

Log in to the host and check that the data is where it was:

```bash
ssh <admin>@<address>
```

```bash
findmnt /srv/persist
sudo ls /opt/docker/volumes /opt/docker/logs
sudo ls /srv/persist/host/komodo /srv/persist/host/ssh
```

The disk is mounted, both folders hold the project folders the host had, and the last command lists `periphery.key` and the SSH host keys.

In Komodo, the host is the Server it was before, with the same Stacks. If the Server stays down, read Periphery's log on the host:

```bash
sudo journalctl -u komodo-periphery -n 50
```

Check each service the way its stack's page does. See [Stacks](../stacks/index.md).

## 5. Remove the snapshot {#remove}

Wait until you trust the host. A few days is reasonable. Then, on the Proxmox host:

```bash
zfs destroy <dataset>@pre-rebuild
```

The snapshot holds every block it covers on the pool until it is destroyed, so do not leave it there.

## Rolling back {#rollback}

A rebuild has no old operating system to return to. The host's system is whatever its configuration builds, so a rollback is about the data and about the configuration.

To have the data as it was before the rebuild, return the persistent disk to the snapshot. The command discards everything written to the disk since. On the Proxmox host:

```bash
qm shutdown <vmid>
zfs rollback <dataset>@pre-rebuild
qm start <vmid>
```

Then run the host again as in [step 3](#run), so that Komodo deploys the Stacks on the data that came back.

When the rebuilt host is wrong because of a change to its configuration, undo the change where it was made: revert the commit in the private repo or in nixos-fleet, generate the host's files again, and run the host. See [Rolling back](update-the-fleet.md#rollback).

### A host that does not answer {#no-answer}

`reset-host` needs a host that answers over SSH. For one that does not, do from the Proxmox host what the command does from inside. Find the volume of the root disk and stop the VM:

```bash
qm config <vmid> | grep '^scsi0'
qm stop <vmid>
```

> [!WARNING]
> The next command destroys the start of a disk. Run it against the volume on the `scsi0` line of this VM and no other.

```bash
dd if=/dev/zero of=$(pvesm path <os-volume>) bs=1M count=16 conv=fsync
qm start <vmid>
```

`<os-volume>` is the storage and volume name at the start of the `scsi0` line. The VM boots the installer, and [step 3](#run) installs it. `qm stop` is a power cut for the containers, so expect each database to recover as it would from one.

## Replacing the VM {#replace-vm}

This section is for a VM whose hardware definition is what is broken, where an install on the same VM would not help. OpenTofu creates a new VM under the host's name, the persistent disk moves to it, and the run installs it. The steps in between are by hand, because OpenTofu refuses to destroy a VM and knows nothing about moving a disk.

It needs a shell prepared for runs after the handover, with the tunnel to the state database open, and a free VMID for the new VM. See [Running from a shell again](../foundation/handover.md#shell-runs). `<old-vmid>` and `<new-vmid>` stand for the two VMs.

### Read the state {#shell}

Make a fresh checkout of the opentofu repo, give it the tfvars file, and list what the state holds:

```bash
rm -rf /tmp/ansible-opentofu-checkout
git clone --depth 1 https://github.com/myah-mitchell/opentofu \
  /tmp/ansible-opentofu-checkout
cd /tmp/ansible-opentofu-checkout/envs/prod
cp ~/src/fleet-private/opentofu/prod.tfvars private.auto.tfvars
tofu init
tofu state list
```

The list has one line for each VM, and the host's is among them:

```text
module.vm["<host>"].proxmox_virtual_environment_vm.this
```

### Shut the old VM down {#shutdown}

On the Proxmox host:

```bash
qm shutdown <old-vmid>
qm set <old-vmid> --name <host>-old --onboot 0
qm status <old-vmid>
```

The answer is `status: stopped`. The containers stop with the VM and the persistent disk unmounts cleanly, which is what makes it safe to move. Take the snapshot now, with the commands [step 1](#snapshot) runs on the Proxmox host and `<old-vmid>` as the VM.

The new name keeps the two VMs apart, because OpenTofu looks up where a VM runs by its name. Turning off the start at boot keeps a restart of the Proxmox host from starting the old VM on the address the new one uses.

### Take the old VM out of the state {#state}

While the state holds the old VM, OpenTofu sees the host as built and creates nothing.

Removing the entry changes nothing in Proxmox. It only makes OpenTofu forget the VM. In the shell, in the folder of the checkout:

```bash
tofu state rm 'module.vm["<host>"].proxmox_virtual_environment_vm.this'
tofu state list
```

The host's line is gone from the list, and every other VM's line is still there.

### Describe the new VM {#describe}

In the private repo's `opentofu/prod.tfvars`, change two lines of the host's entry. Set `vm_id` to the new VMID, and add `started = false`:

```hcl
  id01 = {
    server       = "vh01"
    vm_id        = 7113
    started      = false
    cores        = 4
```

Leave the rest as it is, and correct whatever was wrong with the old VM's definition. `started = false` has OpenTofu create the VM and leave it off, so the disk can be swapped before the first boot.

From `~/src/ansible`, commit and push, then give the new file to the OpenTofu checkout:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Replace the VM of <host>"
git -C ../fleet-private push
cp ../fleet-private/opentofu/prod.tfvars \
  /tmp/ansible-opentofu-checkout/envs/prod/private.auto.tfvars
```

### Create the new VM {#create}

In the shell, in the folder of the checkout, read the plan for this one VM:

```bash
tofu plan -target='module.vm["<host>"]'
```

The plan ends with `1 to add, 0 to change, 0 to destroy`. Anything else means the state or the tfvars file is not what this page expects, so stop and read the plan. Then apply it, and answer `yes`:

```bash
tofu apply -target='module.vm["<host>"]'
```

On the Proxmox host, check the result:

```bash
qm status <new-vmid>
qm config <new-vmid> | grep -E '^(name|scsi2)'
```

The VM is stopped, its name is the host's, and it has a `scsi2` disk. That disk is new and blank.

### Move the persistent disk {#move-disk}

On the Proxmox host, take the blank disk off the new VM:

```bash
qm set <new-vmid> --delete scsi2
qm config <new-vmid> | grep '^unused'
```

The second command shows the detached disk, as `unused0` on a VM with no other unused disk. Delete it under the name that line gives:

```bash
qm set <new-vmid> --delete unused0
```

> [!WARNING]
> The second delete destroys a volume. Check the VMID in both commands before running them. The old VM's disk is the only copy of the data outside the backup and the snapshot.

Move the old VM's disk across:

```bash
qm disk move <old-vmid> scsi2 --target-vmid <new-vmid> --target-disk scsi2
qm config <new-vmid> | grep '^scsi2'
```

The line carries `discard=on`, `iothread=1`, and `ssd=1`. If the move dropped them, set them again with the volume name that line prints:

```bash
qm set <new-vmid> --scsi2 <volume>,discard=on,ssd=1,iothread=1
```

### Start the new VM and run the host {#replace-run}

In `opentofu/prod.tfvars`, remove the `started = false` line. Commit and push, and copy the file into the OpenTofu checkout as before. Read the plan once more:

```bash
cd /tmp/ansible-opentofu-checkout/envs/prod
tofu plan -target='module.vm["<host>"]'
```

The plan ends with `0 to add, 1 to change, 0 to destroy`, and the change is `started`. A plan that wants to change or add a disk has noticed the swap. Stop there, and see [Not yet confirmed](#unconfirmed).

Then run the host from the **Command line** tab of [step 3](#run), and verify it as in [step 4](#verify). The new VM's root disk is blank, so it boots the installer, and the run installs it as it does any new host.

### Remove the old VM {#replace-remove}

Wait until you trust the new VM. Then, on the Proxmox host:

```bash
qm config <old-vmid> | grep '^scsi2' || echo "safe to destroy"
```

> [!WARNING]
> Go on only if the answer is `safe to destroy`. `qm destroy` deletes every disk the VM owns, and an old VM that still has a `scsi2` line owns the data.

```bash
qm destroy <old-vmid>
zfs destroy <dataset>@pre-rebuild
```

After the move the disk may be under another name, so find the dataset again as in [step 1](#snapshot), with `<new-vmid>` as the VM.

To give up on the new VM before that, shut it down, move the disk back with the two VMIDs swapped in the `qm disk move` command, and give the old VM its name and its start at boot again. Do not run the host while OpenTofu's state describes the new VM.

### Replacing ci01's VM {#replace-ci01}

The state database is on ci01, so it goes down with the old VM. Copy the state into a file in the shell first. After [Read the state](#shell), with the tunnel open:

```bash
mkdir -p ~/.local/state/ansible-opentofu
cat > backend_override.tf <<EOF
terraform {
  backend "local" {
    path = "$HOME/.local/state/ansible-opentofu/prod.tfstate"
  }
}
EOF
tofu init -migrate-state -force-copy
tofu state list
```

The list is the same as before, read from the file this time. Close the tunnel, and add `-e vms_backend=local` to the `ansible-playbook` command, which keeps the run on the file the `tofu` commands use.

When ci01's Stacks run again, put the state back. Open the tunnel as [The handover](../foundation/handover.md#tunnel) does, reading the container's address again since it may have changed. Then:

```bash
cd /tmp/ansible-opentofu-checkout/envs/prod
rm backend_override.tf
tofu init -migrate-state -force-copy
tofu state list
```

The list shows every VM. Until the state is back, do not run ci01 from Semaphore, which reads the old state.

## Rebuilding km01 {#km01}

Komodo Core runs on km01, so nothing in the fleet can be deployed while km01 is down. Every other host keeps running its containers. Their Periphery agents reconnect when Core is back.

Follow steps 1 and 2 as written. Then:

1. Run km01 from the shell with the last stage left out, because that stage asks Core to deploy and Core is not running yet. The command is the one in [step 3](#run) with `--skip-tags komodo` added.
2. Start Core by hand, as [The first run](../foundation/first-run.md#start-core) does. The file with Core's database credentials is on the persistent disk, so leave its values as they are. Core starts with the credentials its database already has.
3. Run km01 again with no option added. Komodo takes over Core's containers as it did on the first build, and deploys the rest of km01's Stacks.
4. Remove your checkout of docker-stacks from km01.

Skip [Setting up Komodo](../foundation/komodo-setup.md). The admin account, the keys, the Resource Sync, and every Variable and Secret are in Core's database, on the persistent disk.

Core's own keypair is under `komodo-keys` on the same disk, so every host still trusts it. See [What to keep safe](../hosts/km01-komodo.md#keep).

## Rebuilding ci01 {#ci01}

ci01 holds Semaphore and the database with OpenTofu's state. Both are down from the reset until ci01's Stacks run again, so the run comes from a shell and leaves OpenTofu out.

### Before the reset {#ci01-before}

Prepare the shell while ci01 is up. It needs the fleet's SSH key, the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`, and `KOMODO_API_KEY` and `KOMODO_API_SECRET`. It needs neither the tunnel nor anything OpenTofu reads.

Do the run with `--check` from this shell, with the tags below, before step 1.

### The run {#ci01-during}

Follow steps 1 and 2 as written. In [step 3](#run), name the stages to run:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ci01 \
  --tags wait,nixos,komodo
```

The first stage is left out. The VM has not changed, so OpenTofu has nothing to do, and its state stays in the database on the persistent disk.

### After the run {#ci01-after}

Verify ci01 as in [step 4](#verify). Then prove Semaphore with a run against km01 and one against ci01, as in [Prove Semaphore](../foundation/handover.md#prove). The second one is the first run since the rebuild that reads the state.

Semaphore's Project, its Template, and the secrets in its Variable Group are in its database, so they are there as before.

## Order and pacing {#order}

Rebuild one host at a time. Start with the host that costs least to lose, and finish with ci01 and then km01. A rebuild that goes wrong on a small host shows what to fix before it happens on Semaphore or on Core.

## What's next

Clean the shell when the work is done. See [Clean the shell](../foundation/handover.md#clean).

## Not yet confirmed {#unconfirmed}

No host has been rebuilt by these steps. Each point below came from the code and from the tools' documentation. Confirm them on the first real rebuild and correct this page.

- `reset-host`. That overwriting the start of the root disk and the restart that follows leave the VM in the installer has not been tried.
- The restart that `reset-host` asks for is the kernel's own, which unmounts nothing. The page stops the containers and runs `sync` first for that reason. Whether the persistent disk then mounts without a repair has not been tried.
- A snapshot of the persistent disk while the VM runs. The filesystem is mounted when the snapshot is taken, so a rollback returns to a filesystem that replays its journal at the next mount.
- That the install leaves a persistent disk with a filesystem alone. `install-host` formats the disk only when `blkid` finds nothing on it.
- That Periphery reconnects with its saved key, and that Core accepts the onboarding key from a Server name it already knows.
- The device names the host's configuration mounts by, `drive-scsi1` and `drive-scsi2`. Compare them with `ls -l /dev/disk/by-id` on a real VM.
- [A host that does not answer](#no-answer). The `dd` command does what `reset-host` does, from the Proxmox host, and has not been run.
- Replacing the VM. The state records the blank disk OpenTofu created, and the VM then carries another volume under the same `scsi2`. The plan in [Start the new VM and run the host](#replace-run) shows whether the provider reads that as a change. If it does, the likely fix is a run of `tofu apply -refresh-only` for the VM, which has not been tried.
- `started = false` on a new VM, the change to started in a later apply, and `tofu state rm` against the real state database.
- Whether `qm disk move` with a target VM renames the volume without copying it, and whether it keeps `discard`, `ssd`, and `iothread`.
- Rebuilding km01. Starting Core by hand against an existing database, and Komodo taking the containers over afterwards, follow the first build and have not been done on a rebuilt host.
- Rebuilding ci01. A run with `--tags wait,nixos,komodo` has not been tried, and neither has Semaphore's first start on a rebuilt ci01.
- Replacing ci01's VM. Copying the state out of the database, and `-force-copy` replacing a state the database already holds, have not been tried.
