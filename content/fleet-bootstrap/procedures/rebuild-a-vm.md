# Rebuilding a VM

A rebuild replaces a host's VM with a fresh clone of the template and keeps the host's data. It is how a host moves to a new Ubuntu release, and how it gets a clean operating system without an upgrade in place. The root disk and the Docker disk are thrown away with the old VM. The persistent disk moves to the new one. See [Three disks](../concepts/host-layout.md#disks).

OpenTofu creates the new VM and `site.yml` provisions it, as for any host. The parts in between are by hand, because OpenTofu refuses to destroy a VM and knows nothing about moving a disk.

| Part | Done by |
| --- | --- |
| Taking the old VM out of OpenTofu's state | You, with `tofu` in a shell |
| Creating the new VM | OpenTofu, started by you from the same shell |
| Moving the persistent disk | You, on the Proxmox host |
| Provisioning, and restoring the host's SSH keys and its Komodo identity | The run |
| Deploying the host's Stacks | The run, through Komodo |
| Removing the old VM | You, on the Proxmox host |

km01 and ci01 each need more. Read [Rebuilding km01](#km01) or [Rebuilding ci01](#ci01) before step 1 for those two.

Status: written, not yet run.

## Prerequisites

- A shell prepared for runs after the handover, with the tunnel to the state database open. See [Running from a shell again](../foundation/handover.md#shell-runs). Semaphore cannot do a rebuild, because the rebuild runs `tofu` directly.
- The template to clone exists. The weekly build keeps the template of the current release fresh under the same VMID. For a new Ubuntu release, set `pve_template_ubuntu_version` and `pve_template_ubuntu_release` for the Proxmox host and build the template again. See [Proxmox and the template](../foundation/proxmox-and-template.md#template).
- The old VM is on the node where the new one is created. That is the `node_name` in the host's tfvars entry, or the server's `template_node` when the entry has none. With one Proxmox node there is nothing to check.
- A free VMID for the new VM. The old VM keeps its own until the last step.
- The host is healthy and has a recent backup.
- No container version changes in the same session. A newer version that has already written to the data can stop a rollback from being clean.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host being rebuilt, such as `id01` |
| `<address>` | The host's address, `ansible_host` in the inventory |
| `<old-vmid>` | The VMID of the VM being replaced |
| `<new-vmid>` | The VMID of its replacement |
| `<volume>` | The storage and volume name of the old VM's `scsi2` disk, found in [step 3](#snapshot) |
| `<dataset>` | The ZFS dataset behind that volume, found in [step 3](#snapshot) |
| `<admin>` | The admin account, `<abbr_name>admin` |

## 1. Read the state from the shell {#shell}

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

This is the same folder the run uses, so a later run finds it as you left it.

## 2. Shut the old VM down {#shutdown}

On the Proxmox host:

```bash
qm shutdown <old-vmid>
qm set <old-vmid> --name <host>-old --onboot 0
```

The containers stop with the VM and the persistent disk unmounts cleanly, which is what makes it safe to move. Komodo shows the Server as down until the new VM connects.

The new name frees the old one. OpenTofu finds a VM it manages by its name, and two VMs under one name confuse it. Turning off the start at boot keeps a restart of the Proxmox host from starting the old VM on the address the new one uses.

Check that it stopped:

```bash
qm status <old-vmid>
```

The answer is `status: stopped`.

## 3. Snapshot the persistent disk {#snapshot}

The snapshot is the point a rollback can return to. Find the disk's volume, then its dataset:

```bash
qm config <old-vmid> | grep '^scsi2'
pvesm path <volume>
```

`<volume>` is the storage and volume name at the start of the `scsi2` line, such as `local-zfs:vm-7013-disk-2`. The second command prints `/dev/zvol/<dataset>`. Note the size at the end of the `scsi2` line as well, for step 5.

```bash
zfs snapshot <dataset>@pre-rebuild
zfs list -t snapshot <dataset>
```

The list shows `<dataset>@pre-rebuild`.

## 4. Take the old VM out of the state {#state}

While the state holds the old VM, OpenTofu sees the host as built and creates nothing. It also refuses any plan that would replace the VM. Removing the entry changes nothing in Proxmox. It only makes OpenTofu forget the VM.

In the shell, in the folder from step 1:

```bash
tofu state rm 'module.vm["<host>"].proxmox_virtual_environment_vm.this'
tofu state list
```

The host's line is gone from the list, and every other VM's line is still there.

## 5. Describe the new VM {#describe}

In the private repo's `opentofu/prod.tfvars`, change two lines of the host's entry. Set `vm_id` to the new VMID, and add `started = false`:

```hcl
  id01 = {
    server       = "vh01"
    vm_id        = 7113
    started      = false
    cores        = 4
```

Leave the rest as it is. The address, the VLAN, and the size are the old VM's, and the `persist` entry's `size_gb` has to equal the size noted in step 3.

`started = false` has OpenTofu create the VM and leave it off, so the disk can be swapped before the first boot.

For a new Ubuntu release, also set `template_vm_id` for the server, under `servers`, to the new template's VMID. If the release's tags differ from the default, set `template_tags` there too. OpenTofu applies the tags to each of the server's VMs at that VM's next run. It never replaces a VM because the template changed.

From the ansible checkout, commit and push, then give the new file to the OpenTofu checkout:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Rebuild <host>"
git -C ../fleet-private push
cp ../fleet-private/opentofu/prod.tfvars \
  /tmp/ansible-opentofu-checkout/envs/prod/private.auto.tfvars
```

The Komodo files do not change.

## 6. Create the new VM {#create}

In the shell, in the folder from step 1, read the plan for this one VM:

```bash
tofu plan -target='module.vm["<host>"]'
```

The plan ends with `1 to add, 0 to change, 0 to destroy`. Anything else means the state or the tfvars file is not what this page expects, so stop and read the plan. Then apply it:

```bash
tofu apply -target='module.vm["<host>"]'
```

Answer `yes`. On the Proxmox host, check the result:

```bash
qm status <new-vmid>
qm config <new-vmid> | grep -E '^(name|scsi2)'
```

The VM is stopped, its name is the host's, and it has a `scsi2` disk. That disk is new and empty.

## 7. Move the persistent disk {#move-disk}

On the Proxmox host, take the empty disk off the new VM:

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

Then check that the old VM has let go of the disk:

```bash
qm config <old-vmid> | grep '^scsi2' || echo "no scsi2 on the old VM"
```

## 8. Start the new VM and run the host {#run}

In `opentofu/prod.tfvars`, remove the `started = false` line. Commit and push, and copy the file into the OpenTofu checkout, as in step 5. Read the plan once more:

```bash
cd /tmp/ansible-opentofu-checkout/envs/prod
tofu plan -target='module.vm["<host>"]'
```

The plan ends with `0 to add, 1 to change, 0 to destroy`, and the change is `started`. A plan that wants to change or add a disk has noticed the swap. Stop there, and see [Not yet confirmed](#unconfirmed).

The new VM's first boot gives it new SSH host keys, which the shell does not know. Remove the old entry so the run can accept them:

```bash
ssh-keygen -R <address>
```

From `~/src/ansible`, run the host:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

The command passes no onboarding key. The host's Komodo identity is on the disk you moved.

| Stage | What it does on a rebuilt host |
| --- | --- |
| Create the VM | Starts the VM |
| Wait | Waits for the first boot to finish |
| Provision | Mounts the persistent disk as it is, restores the saved SSH host keys, and points Periphery at its saved key. Everything on the root disk is made again, firewall rules included |
| Reboot | Restarts the VM one time if the package upgrade asks for it, as for a new host |
| Deploy | Has Komodo deploy each of the host's Stacks, since none is running |

The provision stage never formats a disk that carries a filesystem, so the data is untouched.

Restoring the host keys changes them a second time, back to the ones the host had before. If the run stops with the host unreachable and a message about a changed host key, remove the entry again with `ssh-keygen -R <address>` and run the host again. Every stage is safe to repeat.

## 9. Verify {#verify}

--8<-- "verify-run.md"

Log in to the host and check that the data came with the disk:

```bash
ssh <admin>@<address>
```

```bash
findmnt /srv/persist
sudo ls /opt/docker/volumes /opt/docker/logs
sudo ls /srv/persist/host/komodo /srv/persist/host/ssh
```

The disk is mounted, both folders hold the same project folders the old host had, and the last command lists `periphery.key` and the SSH host keys.

In Komodo, the host is the Server it was before, with the same Stacks. If the Server stays down, read Periphery's log on the host:

```bash
sudo -u komodo XDG_RUNTIME_DIR=/run/user/$(id -u komodo) \
  journalctl --user -u periphery.service -n 50
```

Check each service the way its stack's page does. See [Stacks](../stacks/index.md). Leave the old VM alone until they pass.

## 10. Remove the old VM {#remove}

Wait until you trust the new host. A few days is reasonable. Then, on the Proxmox host:

```bash
qm config <old-vmid> | grep '^scsi2' || echo "safe to destroy"
```

> [!WARNING]
> Go on only if the answer is `safe to destroy`. `qm destroy` deletes every disk the VM owns, and an old VM that still has a `scsi2` line owns the data.

```bash
qm destroy <old-vmid>
zfs destroy <dataset>@pre-rebuild
```

The snapshot holds every block it covers on the pool until it is destroyed, so do not leave it there.

## Rolling back {#rollback}

To give up on the new VM and return to the old one, on the Proxmox host:

```bash
qm shutdown <new-vmid>
qm disk move <new-vmid> scsi2 --target-vmid <old-vmid> --target-disk scsi2
qm set <new-vmid> --name <host>-new --onboot 0
qm set <old-vmid> --name <host> --onboot 1
```

The data is as the new VM left it. To have it as it was at the cutover, roll the dataset back before the old VM starts. The command discards everything the new VM wrote. After the two moves the disk may be under another name, so find the dataset again as in [step 3](#snapshot):

```bash
zfs rollback <dataset>@pre-rebuild
```

Start the old VM:

```bash
qm start <old-vmid>
```

The old VM has its own host keys on its root disk, which are the ones saved on the persistent disk, so remove the shell's entry for the address one more time if `ssh` complains.

Do not run the host while it is rolled back. OpenTofu's state now describes the new VM, and a run would start it on the address the old one is using. Either move the disk forward again and carry on from [step 8](#run), or make the rollback permanent. Making it permanent means rebuilding onto the old VM's description, which no page covers yet. See [Not yet confirmed](#unconfirmed).

## A host built by hand {#hand-built}

A VM made with `qm` is not in OpenTofu's state, and a rebuild is how it comes under OpenTofu. Two steps differ.

- Skip [step 4](#state). There is nothing to remove.
- In [step 5](#describe), add the host's whole entry to the tfvars file, with `started = false` in it. The host page has the entry.

The move in [step 7](#move-disk) needs the old VM to carry its data the way the run lays it out: on `scsi2`, as an ext4 filesystem labelled `persist`, with the `volumes`, `logs`, and `host` folders. See [The persistent disk](../concepts/host-layout.md#persist).

## Rebuilding km01 {#km01}

Komodo Core runs on km01, so nothing in the fleet can be deployed while km01 is down. Every other host keeps running its containers. Their Periphery agents reconnect when Core is back.

Follow steps 1 to 7 as written. The state database is on ci01, so the shell and the tunnel work as for any host. Then:

1. Do [step 8](#run) with one option added to the run, `--skip-tags komodo`. The last stage asks Core to deploy, and Core is not running yet.
2. Start Core by hand, as [The first run](../foundation/first-run.md#start-core) does. The environment file is on the persistent disk, so the link finds it and the build keeps every value in it. Do not edit the file. Core starts with the credentials its database already has.
3. Run km01 again with no option added. Komodo takes over Core's containers as it did on the first build, and deploys the rest of km01's Stacks.
4. Remove your checkout of docker-stacks from km01.

Skip [Setting up Komodo](../foundation/komodo-setup.md). The admin account, the keys, the Resource Sync, and every Variable and Secret are in Core's database, on the persistent disk. Core's own keypair is under `komodo-keys` on the same disk, so every host still trusts it. See [What to keep safe](../hosts/km01-komodo.md#keep).

## Rebuilding ci01 {#ci01}

ci01 holds Semaphore and the database with OpenTofu's state, so the state has to leave ci01 before the rebuild and return after it.

### Before step 2 {#ci01-before}

With ci01 still up and the tunnel open, do [step 1](#shell). Then copy the state into a file in the shell:

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

The list is the same as in step 1, read from the file this time. Close the tunnel.

### Steps 2 to 9 {#ci01-during}

Follow them as written, with one option added to every `ansible-playbook` command:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ci01 \
  -e vms_backend=local
```

The option keeps the run on the same file the `tofu` commands use.

### After step 9 {#ci01-after}

Put the state back. The database came across on the persistent disk, and it still holds the state as it was before the rebuild. Open the tunnel again as [The handover](../foundation/handover.md#tunnel) does, reading the container's address again since it may have changed. Set `PG_CONN_STR` as that page's step 2 does, then:

```bash
cd /tmp/ansible-opentofu-checkout/envs/prod
rm backend_override.tf
tofu init -migrate-state -force-copy
tofu state list
```

The list shows every VM. Then prove Semaphore with a run against km01 and one against ci01, as in [Prove Semaphore](../foundation/handover.md#prove).

Until the state is back, do not run ci01 from Semaphore. Semaphore reads the old state, in which ci01 is still the old VM.

Semaphore's Project, its Template, and the secrets in its Variable Group are in its database, so they come across with the disk.

## Order and pacing {#order}

Rebuild one host at a time. Start with the host that costs least to lose, and finish with ci01 and then km01. A rebuild that goes wrong on a small host shows what to fix before it happens on Semaphore or on Core.

## What's next

Clean the shell when the work is done. See [Clean the shell](../foundation/handover.md#clean).

The new VM's ID differs from the old one's, so it no longer follows whatever numbering the rest of the fleet has. Nothing depends on the number.

## Not yet confirmed {#unconfirmed}

No host has been rebuilt by these steps. Each point below came from the code and from the tools' documentation. Confirm them on the first real rebuild and correct this page.

- The moved disk and OpenTofu. The state records the empty disk OpenTofu created, and the VM now carries another volume under the same `scsi2`. The plan in [step 8](#run) shows whether the provider reads that as a change. If it does, the likely fix is a run of `tofu apply -refresh-only` for the VM, which has not been tried.
- `started = false` on a new clone, and the change to started in a later apply.
- `tofu state rm` against the real state database.
- Whether `qm disk move` with a target VM renames the volume without copying it, and whether it keeps `discard`, `ssd`, and `iothread`. [Step 7](#move-disk) checks the options and repairs them.
- Deleting the empty disk. The `unused0` name is what Proxmox gives the first detached disk, and the page has you read it before deleting.
- The SSH host keys during the run. The page expects them to change two times, and the second change may stop the run partway. A changed key that is refused in the wait stage shows as a wait that never ends, up to the stage's timeout of thirty minutes.
- That Periphery reconnects with its saved key and no onboarding key. If it does not, the fallback is a run with the onboarding key, and what Core does when a key arrives under a Server name it already knows is not known. Check what is attached to the old Server before deleting it.
- That Periphery accepts a private key kept outside its own root folder. The docker role sets it that way.
- The device names the docker role expects, `drive-scsi1` and `drive-scsi2`. Compare them with `ls -l /dev/disk/by-id` on a real VM.
- That the systemd drop-in keeps Docker from starting when a disk is missing, on a real boot with the disk detached, and that the bind mounts wait for `/srv/persist`.
- Rebuilding km01. Starting Core by hand against an existing database, and Komodo taking the containers over afterwards, follow the first build and have not been done on a rebuilt VM.
- Rebuilding ci01. Copying the state out of the database, and `-force-copy` replacing a state the database already holds, have not been tried.
- A permanent rollback. It would need the new VM removed from the state and from Proxmox, and the old VM brought into the state, and the opentofu repo imports nothing today.
- A host built by hand. Whether the hand-built hosts that run today carry their data the way [the move](#hand-built) needs has not been checked against them.
