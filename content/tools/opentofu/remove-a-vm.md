# Removing a VM

This page destroys a VM that OpenTofu made, with all of its disks, and takes it out of OpenTofu's state. Use it to retire a host for good. The run can never do this, so it is done by hand with the `tofu` command, after one deliberate edit to a checkout of the fleet-opentofu repo.

To replace a VM and keep its data, see [Replacing the VM](../../fleet-bootstrap/procedures/rebuild-a-vm.md#replace-vm). To install a host again on the same VM, see [Rebuilding a VM](../../fleet-bootstrap/procedures/rebuild-a-vm.md).

Status: written, not yet run.

> [!WARNING]
> Destroying a VM deletes its persistent disk, which holds every stack's data on that host. Nothing here can be undone without a backup.

## Prerequisites

- A backup of anything on the host that is worth keeping. See [What to back up](../../fleet-bootstrap/concepts/host-layout.md#backups).
- Nothing else in the fleet depends on the host. km01 and ci01 hold Komodo, Semaphore, and the state database, and this page is not for them.
- A shell prepared for runs after the handover, with the tunnel to the state database open. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).
- The host's entry is still in `opentofu/prod.tfvars`. It comes out in [step 5](#tfvars), after the VM is gone.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host being removed, which is the key of its entry in the tfvars file |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |

## 1. Make a checkout and find the VM {#checkout}

Make a fresh checkout and list the state, as [Make a checkout](read-a-plan.md#checkout) does. The list includes the host's line:

```text
module.vm["<host>"].proxmox_virtual_environment_vm.this
```

If the line is missing, OpenTofu did not make this VM or has already forgotten it. There is nothing for this page to do, and the VM is removed in Proxmox by hand.

## 2. Lift the guard in the checkout {#guard}

The module refuses to destroy a VM. In the checkout, turn that off:

```bash
cd /tmp/ansible-fleet-opentofu-checkout/envs/prod
sed -i 's/prevent_destroy = true/prevent_destroy = false/' ../../modules/vm/main.tf
git diff --stat
```

The last command reports one file changed, `modules/vm/main.tf`, with one line added and one removed.

The edit stays in this checkout. Do not commit or push it. The repo on GitHub keeps the guard, and so does every run.

Do not start a run from this shell between here and [step 6](#clean). A run from a shell clones into this same folder and resets it to the repo on GitHub, which puts the guard back.

<details>
<summary>Background: why removing a VM takes an edit</summary>

A VM's entry can vanish from a plan's input by accident: a key renamed in the tfvars file, a run with an old copy of the file, a VM moved to another server. OpenTofu reads each of those as a VM to destroy, and destroying a VM deletes its data.

The module therefore sets `prevent_destroy` on the VM resource, and the ansible role refuses any plan that contains a destroy. Neither has a switch in the tfvars file or the inventory. The one way past is to change the module's own file, which nobody does without meaning to. See [Refusing to destroy](index.md#prevent-destroy).

</details>

## 3. Read the plan {#plan}

Ask for the plan that destroys this one VM:

```bash
tofu plan -destroy -target='module.vm["<host>"]'
```

The plan names one resource, with the host's name in its address, and marks every line with `-`. It ends with this line:

```text
Plan: 0 to add, 0 to change, 1 to destroy.
```

Stop if the count to destroy is anything but 1, or if the address is not the host's. See [Reading a plan before applying](read-a-plan.md#read) for the symbols.

## 4. Destroy the VM {#destroy}

Destroy the one VM, by its address:

```bash
tofu destroy -target='module.vm["<host>"]'
```

> [!WARNING]
> Never leave out `-target` in this checkout. With the guard lifted, `tofu destroy` without it plans to destroy every VM in the fleet.

OpenTofu prints the same plan and asks for confirmation. Check the address once more, then answer `yes`. The command ends with `Destroy complete! Resources: 1 destroyed.`

The provider asks a running VM to shut down first and waits up to 30 minutes for it, so the command can sit for a while on a VM whose guest does not answer.

Confirm it in the state and on the Proxmox host:

```bash
tofu state list
```

```bash
qm status <vmid>
```

The host's line is gone from the list, and every other VM's line is still there. `qm status` answers that the VM's configuration file does not exist.

## 5. Take the entry out of the tfvars file {#tfvars}

In the private repo's `opentofu/prod.tfvars`, delete the host's whole entry from `vms`, from its name to its closing brace. From `~/src/fleet-ansible`, commit and push:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Remove the VM of <host>"
git -C ../fleet-private push
```

While the entry is in the file, a run of the host creates the VM again, blank.

## 6. Remove the checkout {#clean}

Delete the checkout, and the lifted guard with it:

```bash
rm -rf /tmp/ansible-fleet-opentofu-checkout
```

Close the tunnel, and clean the shell. See [Clean the shell](../../fleet-bootstrap/foundation/handover.md#clean).

## What's next

The VM is gone. The rest of the fleet still knows the host, and these are not OpenTofu's to remove.

- The host's entry in `hosts.yml`. Take it out, then generate the fleet's files again and commit them. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).
- The host's Server and Stacks in Komodo. The sync never deletes, so delete them there. See [Limits](../../fleet-bootstrap/concepts/how-a-host-is-built.md#limits).

## Forgetting a VM without destroying it {#forget}

To have OpenTofu stop managing a VM that keeps running, take it out of the state and leave Proxmox alone. That needs no edit to the module. See [Take the old VM out of the state](../../fleet-bootstrap/procedures/rebuild-a-vm.md#state), then remove the entry from the tfvars file as in [step 5](#tfvars).

## Not yet confirmed {#unconfirmed}

No VM has been destroyed by these steps. The fleet-opentofu repo's README says only that removing a VM means editing `modules/vm/main.tf` on purpose, and the commands here follow from that.

- A targeted `tofu destroy` with the guard lifted, against a real Proxmox host and the real state database.
- The shutdown before the delete. The provider's documentation says it shuts a running VM down and waits `timeout_shutdown_vm`, 1800 seconds by default, and the module sets neither that nor `stop_on_destroy`. If the destroy fails on a running VM, shut it down with `qm shutdown <vmid>` on the Proxmox host and run the command again.
- That the API token's role can delete a VM and its disks. The role in [Create the API token](../../fleet-bootstrap/foundation/proxmox-and-installer.md#token) has `VM.Allocate` and `Datastore.AllocateSpace`, which is what Proxmox asks for.
- That the destroy removes the cloud-init drive and all three disks, and leaves no volume behind on the datastore. The provider's documentation has `purge_on_destroy` and `delete_unreferenced_disks_on_destroy` on by default, and the module changes neither.
- The wording of `qm status` for a VMID that does not exist.
- What generating the fleet's files does with the files of a host that left the inventory, under `nixos/` and `komodo/stacks/` in the private repo.
