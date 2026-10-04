# Changing a VM's CPU or memory

A VM's cores and memory are two lines in its entry in the tfvars file. Change them when a host runs short, or was given more than it uses. The edit is made in the private repo, and a run of the host has OpenTofu apply it to the VM in Proxmox.

For a disk, see [Growing a disk](../../fleet-bootstrap/procedures/grow-a-disk.md).

Status: written, not yet run.

## Prerequisites

- The host was built by the run, so its VM is in `opentofu/prod.tfvars` and in OpenTofu's [state](index.md#state).
- The Proxmox node has the cores and the memory to give. The fleet's VMs have a fixed amount of memory, so the node needs all of it free.
- A time when the host's stacks can stop for a few minutes. Expect the VM to restart.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host being changed, such as `id01` |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
| `<address>` | The host's address, `ansible_host` in the inventory |

## 1. Change the entry {#tfvars}

In the private repo's `opentofu/prod.tfvars`, set `cores` and `memory_mb` in the host's entry. Memory is in MB, so 12 GB is `12288`. This example takes id01 from 8 GB to 12 GB and leaves its four cores:

```hcl
  id01 = {
    server       = "vh01"
    vm_id        = 7131
    cores        = 4
    memory_mb    = 12288
```

An entry that has neither line uses the defaults, 2 cores and 2048 MB. Add the line to change it.

Change nothing else in the entry. From `~/src/fleet-ansible`, commit and push:

```bash
git -C ../fleet-private add opentofu/prod.tfvars
git -C ../fleet-private commit -m "Resize <host>"
git -C ../fleet-private push
```

The host's NixOS file and its Komodo file hold neither value, so there is nothing to generate.

## 2. Read the plan {#plan}

Run the host in check mode, and make the plan by hand if you want to see each line. See [Reading a plan before applying](read-a-plan.md).

The plan ends with `0 to add, 1 to change, 0 to destroy`. The changed lines are `cores`, inside the `cpu` block, and `dedicated`, inside the `memory` block, which is the name the provider gives `memory_mb`.

## 3. Run the host {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The first stage has OpenTofu change the VM. The later stages wait for the host to answer again and find nothing to change.

The run ends with `failed=0` and `unreachable=0` for the host.

<details>
<summary>Background: why the VM restarts</summary>

A running VM's virtual hardware is fixed when it starts. Proxmox can add cores or memory to a running guest only when hotplug is turned on for the VM, and the fleet's module does not turn it on. Proxmox therefore records the new values as pending, and they take effect at the next start.

The provider knows this and restarts the VM after a change that needs it. The containers stop with the VM and start again when Docker does.

</details>

## 4. Verify {#verify}

On the Proxmox host, read the VM's settings:

```bash
qm config <vmid> | grep -E '^(cores|memory)'
qm pending <vmid> | grep -E '(cores|memory)'
```

The first command shows the new values. The second shows one line for each setting, starting with `cur`.

If the second command also prints a line starting with `new`, the change is still pending and the VM has not restarted. Restart it:

```bash
qm reboot <vmid>
```

Then log in to the host and check what it sees:

```bash
ssh <admin>@<address>
```

```bash
nproc
free -m
```

`nproc` prints the number of cores. The *total* column of the `Mem:` line is a little under the memory you set, since the kernel keeps some for itself.

In Komodo, the host's Stacks show as running again.

## What's next

Nothing follows from this page. The host's own page says what its size was chosen for, and is the place to record a new one.

## Not yet confirmed {#unconfirmed}

No VM in the fleet has been resized by these steps. The fleet-opentofu repo's README lists the changes it planned against an installed VM, and cores and memory are not among them.

- That a change of `cores` or `memory_mb` plans an update in place and no replacement.
- The restart. The provider's documentation says it restarts a VM after a change that needs one. Whether it does so here, and how long the host's stacks are down, has not been seen.
- The run's wait stage after the restart. It waits for the SSH port, which may still answer for a moment before the VM goes down.
- The output of `qm pending`, with its `cur` and `new` lines, which was written from memory of Proxmox and not read from a host.
- Lowering memory below what the host's containers use.
