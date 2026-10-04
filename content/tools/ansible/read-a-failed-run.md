# Reading a failed run

A run of `site.yml` that stops prints a great deal before the line that matters. This page finds that line, says which stage it came from, and lists the stops the playbook makes on purpose with what each one wants. Use it whenever a recap shows a failure.

Status: written, not yet run.

Most stops are not faults. The roles check their inputs before they change anything, and each check prints a message that says what to fix. Nothing on this page changes the fleet. The fix is made where the message points, and the run is started again. See [Idempotence](index.md#idempotence) for why running again is safe.

## Prerequisites

- The output of the run: the terminal it ran in, or the run's log in Semaphore.
- For the stage names, [The four stages](../../fleet-bootstrap/concepts/how-a-host-is-built.md#stages).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host the message names |
| `<name>` | A stack, a variable, or an environment variable the message names |

## 1. Read the recap {#recap}

Go to the end of the output. The last block is the recap, with one line for each host:

```text
PLAY RECAP *********************************************************************
id01                       : ok=31   changed=0    unreachable=0    failed=1    skipped=9    rescued=0    ignored=0
```

A host with `failed=1` stopped at a task. Every host with `failed=0` went through the whole run.

A run with no recap at all stopped before its first task. See [Before the first task](#before-first-task).

## 2. Find the failing task {#task}

Search the output upwards from the recap for `fatal:`. The line above it is the task's header:

```text
TASK [nixos : Check the committed files match the inventory] *******************
fatal: [id01]: FAILED! => {"assertion": "not nixos_host_file.changed", "changed": false, "evaluated_to": false, "msg": "/home/you/src/fleet-private/nixos/fleet.json or /home/you/src/fleet-private/nixos/hosts/id01.json does not match what the inventory and fleet-stacks give for this host (the diff above shows how). Run nixos-sync.yml against this inventory, then commit and push what it writes."}
```

| Part | Says |
| --- | --- |
| `nixos` in the header | The role the task belongs to |
| The text after the colon | The task's name, which says what was being checked or done |
| `[id01]` | The host the task was for |
| `"msg"` | The message. Read this first |

A host shown as `[id01 -> localhost]` is a task for id01 that ran on the control node. That is every task in this playbook that runs a command, and it does not mean the control node is at fault. See [Delegation](index.md#delegation).

The role gives the stage:

| Role in the header | Stage |
| --- | --- |
| vms | Create the VM |
| None, and the task is *Wait for the host's SSH port* | Wait |
| nixos, provision, or stacks before the first komodo_stacks task | NixOS |
| komodo_stacks, or stacks after it | Deploy the stacks |

## 3. Match the message {#messages}

Find the opening of the message in the tables below. The words in the tables are the playbook's own, with the parts that vary left out.

### Create the VM {#stops-vms}

| The message says | Do this |
| --- | --- |
| `<name> is not set. OpenTofu reads it from the environment` | Set `TF_ENCRYPTION` or `PG_CONN_STR` in the control node's environment. See [What the run needs](../../fleet-bootstrap/concepts/how-a-host-is-built.md#needs) |
| `The variables file gives <host> the address` | Make the host's address, prefix length, gateway, and nameservers the same in `opentofu/prod.tfvars` and in `hosts.yml`. See [Describing a host](../../fleet-bootstrap/concepts/fleet-private.md#describe) |

The second stop ends the run for every host in it, not only the one named, so that no VM is made from a network that is in doubt.

A failure in the task *Apply the configuration for this play's VMs* is OpenTofu's own, and the message is OpenTofu's. See [OpenTofu](../opentofu/index.md#troubleshooting).

### Wait {#stops-wait}

The wait has one way to fail: the host's SSH port did not answer within 30 minutes.

Open the VM's console in Proxmox and see what it booted. A new VM that is not in the installer usually has no installer ISO to boot from. See [The installer ISO](../../fleet-bootstrap/foundation/proxmox-and-installer.md#installer-iso).

### NixOS {#stops-nixos}

These come before anything reaches the host.

| The message says | Do this |
| --- | --- |
| `does not match what the inventory and fleet-stacks give for this host` | Run `nixos-sync.yml`, commit, and push. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change) |
| `git has these files in nixos/ or secrets/ as changed, untracked or ignored` | Add and commit the files the message lists, in the private repo |
| `is not a git checkout` | Point `-i` at the inventory inside a git checkout of the private repo |
| `<host> needs short_name, abbr_name, location_abbr, domain_name and network_gateway` | Set the one that is missing. See [Identity values](../../fleet-bootstrap/concepts/fleet-private.md#identity) |
| `admin_ssh_public_keys and ansible_ssh_public_keys each need at least one SSH public key` | Set both in `group_vars/all/private.yml` |
| `Name the host in the inventory by its serverHostname in lower case` | Make the host's inventory name and its `serverHostname` agree |
| `opens a port to the internal subnet. Set docker_stacks_internal_subnet` | Set the subnet in the group's `vars` |
| `setup.yaml is missing. Check the stack name` | Correct the name in the host's `docker_stacks`. It is a folder name under `stacks/` in fleet-stacks |
| `which a stack listed there needs on this same host` | Add the stack that provides the service to the host's `docker_stacks` |

The first message in that table refers to "the diff above". The task before the failing one prints the difference between the committed file and what the inventory gives, line by line, and that difference is the change that was never generated.

These come from the install and the deploy.

| The message says | Do this |
| --- | --- |
| `answers at <address> neither as the installer nor as an installed host` | Check the VM is running, and that the control node holds the fleet's SSH key |
| `runs the installer, but this run does not know its VM` | Run again with the `vms` stage included. See [Choose the stages](run-part-of-a-run.md#stages) |
| `which is not in the inventory. Add it to pve_host` | Add the VM's Proxmox node to the pve_host group. See [The Proxmox servers](../../fleet-bootstrap/concepts/fleet-private.md#servers) |
| `has no pve_ssh_host_key in the inventory` | Set the node's SSH host key on its entry in `hosts.yml` |
| `The install finished, but <host> still answers at` | Open the VM's console in Proxmox to see how far the boot got |

A failure in *Install NixOS* or *Deploy the host's NixOS configuration* with none of these messages comes from the flake's command. Its own output is in the task's result, under `stderr`. See [NixOS](../nixos/index.md#troubleshooting).

### Deploy the stacks {#stops-komodo}

| The message says | Do this |
| --- | --- |
| `does not match what the inventory and fleet-stacks' komodo.env files give` | Run `komodo-sync.yml`, commit, and push |
| `komodo.env has no line for <name>` | Correct the key in the host's `komodo_stack_env`. Every key there must exist in that stack's `komodo.env` |
| `Komodo refused the API key and secret` | Check `KOMODO_API_KEY` and `KOMODO_API_SECRET` |
| `Komodo has no connected Server named <host>` | Read Periphery's log on the host. See [How a host joins Komodo](../../fleet-bootstrap/concepts/how-a-host-is-built.md#onboarding) |
| `Komodo would not run the fleet Resource Sync` | Read the HTTP status and the reply in the message. See [Setting up Komodo](../../fleet-bootstrap/foundation/komodo-setup.md) |
| `The fleet Resource Sync failed` | Open the sync's Update in Komodo, which has the full log |
| `These Stacks are not running` | Open each named Stack's latest Update in Komodo |

One line in this stage looks like a failure and is not. It starts `Skipping the deploy of <host>'s Stacks, since Komodo's API is not set up here`, the task reports `ok`, and the run goes on. It is what the first run of km01 prints, before Komodo exists.

The tasks that call Komodo's API hide their results, because a result carries the API key. A task that fails there shows a line saying the output was hidden in place of a message.

The only such task with no check after it is *Wait for the sync to finish*. When it fails, the sync did not complete within 15 minutes. Look at the sync's Update in Komodo.

### Before the first task {#before-first-task}

A run that prints an error and no `TASK` line stopped while Ansible was reading its inputs.

| The error is about | Do this |
| --- | --- |
| `target` being undefined | Add `-e target=<host>` to the command, or fill in *Target* in Semaphore |
| A host pattern that matches nothing | Check the name in `target` against the inventory, and the path after `-i` |
| Decrypting a file, or sops | Set the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. See [Secrets with sops](../../fleet-bootstrap/concepts/secrets-with-sops.md#keys) |
| A YAML syntax error with a line number | Fix the line in `hosts.yml` or `private.yml` |

## 4. Get more detail {#verbose}

If the message is not enough, run again from a shell with `-v` added. Ansible then prints each task's full result, with the output of every command a task ran.

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  -v
```

The tasks that hide their results stay hidden with `-v`.

## 5. Fix it and run again {#again}

Make the fix where the message points, then start the same run again. The stages that finished find nothing to change, and the run goes on from the stage that stopped. To skip straight to that stage, see [Running part of a run](run-part-of-a-run.md).

## What's next

A stop that is not in the tables is a fault in a tool the run called. The primers for [OpenTofu](../opentofu/index.md), [NixOS](../nixos/index.md), and [Komodo](../komodo/index.md) say where each keeps its own logs.

## Not yet confirmed {#unconfirmed}

- The example output in steps 1 and 2. The message text is the role's own. The layout around it, and the counts in the recap, are how Ansible prints a failed check, and were not copied from a run of this playbook.
- The wording of the errors in [Before the first task](#before-first-task), which come from Ansible and the sops plugin and not from the fleet's roles.
- Where Semaphore shows a run's output, and whether it keeps the whole of a long run.
- The line Ansible prints for a failed task whose output is hidden.
- Every stop, against a real fleet. The messages were read from the roles in the fleet-ansible repo.
