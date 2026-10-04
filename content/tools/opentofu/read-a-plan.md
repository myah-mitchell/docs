# Reading a plan before applying

A plan is OpenTofu's list of what a run would do to a VM, made without doing it. Read one before any run that follows an edit to `opentofu/prod.tfvars`, and whenever a run stopped in its first stage and you want to know why. See [Plan and apply](index.md#plan-and-apply) for the idea.

There are two ways to get a plan. A run in check mode says whether there is anything to change. A plan made by hand, in a checkout, shows each change line by line.

Status: written, not yet run.

## Prerequisites

- The change to the tfvars file is committed and pushed, when the plan is to come from Semaphore. Semaphore clones the private repo for each run.
- For the **Command line** tab and for the plan by hand, a shell prepared for runs after the handover, with the tunnel to the state database open. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

`<host>` stands for the host's name, which is the key of its entry in the tfvars file, such as `id01`.

## 1. Run the host in check mode {#check}

/// tab | Semaphore

In Semaphore, start the **site** Template with *Target* set to the host's name, and tick **Dry Run**.

///

/// tab | Command line

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> --check --tags vms
```

///

In check mode the first stage stops at OpenTofu's plan, and no stage reaches the host. See [Seeing what a run would do](../../fleet-bootstrap/concepts/how-a-host-is-built.md#check) for the other stages.

Find the task named `Apply the configuration for this play's VMs` in the log.

| The task reports | The plan |
| --- | --- |
| `ok` | Has no change for this VM |
| `changed` | Would create or change the VM |
| `failed` | Would destroy something, or could not be made. The message says which |

The log does not print the plan itself. If `ok` is the answer you expected, stop here. Otherwise go on.

## 2. Make a checkout {#checkout}

The `tofu` command works in a folder that holds the configuration and the tfvars file. In the shell, make a fresh one in the place the run uses:

```bash
rm -rf /tmp/ansible-fleet-opentofu-checkout
git clone --depth 1 https://github.com/myah-mitchell/fleet-opentofu \
  /tmp/ansible-fleet-opentofu-checkout
cd /tmp/ansible-fleet-opentofu-checkout/envs/prod
cp ~/src/fleet-private/opentofu/prod.tfvars private.auto.tfvars
tofu init
tofu state list
```

`tofu init` downloads the provider and connects to the state. The list has one line for each VM OpenTofu has made:

```text
module.vm["ci01"].proxmox_virtual_environment_vm.this
module.vm["km01"].proxmox_virtual_environment_vm.this
```

An empty list means the shell is not reading the fleet's state. Stop, and check `PG_CONN_STR` and the tunnel. A plan against an empty state shows every VM as new.

The checkout holds a copy of the tfvars file. After a later edit to the file, copy it in again.

## 3. Make the plan {#plan}

In the folder of the checkout:

```bash
tofu plan -target='module.vm["<host>"]'
```

The `-target` option limits the plan to one VM, as the run does. See [Targeting](index.md#targeting). OpenTofu prints a warning that resource targeting is in effect, which is expected here.

The command changes nothing, in Proxmox or in the state.

## 4. Read it {#read}

A plan lists each resource it would act on, under a comment line that says what happens to it. Inside the resource, each line that differs carries a symbol.

| Symbol | Means |
| --- | --- |
| `+` | Created, or an attribute that is added |
| `~` | Changed in place. The line shows the old value, `->`, and the new one |
| `-` | Destroyed, or an attribute that is removed |
| `-/+` | Replaced: destroyed, then created again |

A change of memory looks like this. The lines without a symbol are context, and OpenTofu hides the attributes that stay as they are.

```text
  # module.vm["id01"].proxmox_virtual_environment_vm.this will be updated in-place
  ~ resource "proxmox_virtual_environment_vm" "this" {
        name = "id01"

      ~ memory {
          ~ dedicated = 8192 -> 12288
        }
    }

Plan: 0 to add, 1 to change, 0 to destroy.
```

Read the last line first. It counts the resources, and for one VM it has four forms.

| Last line | Means |
| --- | --- |
| `No changes.` in place of a count | The VM matches its entry |
| `1 to add, 0 to change, 0 to destroy` | The VM is not in the state, and would be created |
| `0 to add, 1 to change, 0 to destroy` | The VM exists and would be changed in place |
| Anything to destroy | Stop. The plan would delete a VM and its disks |

Then read every `~` line, and check that each is a change you made. One edit to the tfvars file gives one changed line, or one block of them.

> [!WARNING]
> A plan to add a VM that already runs means OpenTofu is reading the wrong state. Do not apply it. See [State](index.md#state).

Some changes restart the VM or have effects the plan does not show.

| Change in the entry | What the apply does |
| --- | --- |
| A disk size, made larger | Grows the disk. The filesystem is grown by hand. See [Growing a disk](../../fleet-bootstrap/procedures/grow-a-disk.md) |
| A disk size, made smaller | Fails. The provider does not shrink a disk |
| `ipv4_address`, `ipv4_gateway`, `dns_servers` | Rewrites the cloud-init drive and restarts the VM |
| `node_name` | Migrates the VM to that node |
| `cores`, `memory_mb` | See [Changing a VM's CPU or memory](resize-a-vm.md) |

With `prevent_destroy` set, a plan that would destroy or replace the VM does not print. The command fails with an error that names the resource. See [Refusing to destroy](index.md#prevent-destroy).

## 5. Apply it {#apply}

Run the host again, with **Dry Run** unticked or without `--check` and `--tags vms`. The run makes its own plan from the same files and applies it.

Run the host instead of typing `tofu apply` in the checkout. The run also checks the VM's network against the inventory, and takes the host through the stages that follow.

## What's next

Close the tunnel, and clean the shell when the work is done. See [Clean the shell](../../fleet-bootstrap/foundation/handover.md#clean).

## Not yet confirmed {#unconfirmed}

No plan has been made against a Proxmox host. The fleet-opentofu repo's plans were made offline.

- The **Dry Run** tick box on a run of the **site** Template as [The Semaphore project](../../fleet-bootstrap/foundation/semaphore-project.md#template) creates it. The label is the one the build guide uses, and it has not been read from Semaphore's screen.
- What the task prints in check mode. The role's module returns the plan's text in its result, which ansible shows only with `-v`, so the page says the log holds `ok` or `changed` and no more.
- `--check --tags vms` together. The tag limits the run to the first stage, which is all a plan needs.
- The sample plan. It was written by hand in the format OpenTofu prints, and a real one has more context lines and a count of hidden attributes.
- The wording of the error a plan gives when `prevent_destroy` stops it.
- `tofu init` and `tofu plan` through the tunnel against the real state database.
