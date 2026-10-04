# Adding a variable to the inventory

Everything the build knows about a host is a variable in the inventory. This page sets one: for a single host, for a group, or for the whole fleet. Use it when a host needs a value that differs from the default, such as a swap file, another nameserver, or a value for one of its stacks.

Status: written, not yet run.

The change is made in the private repo, in `hosts.yml` or in `group_vars/all/private.yml`. Nothing reads the inventory on a host. The two sync playbooks turn it into generated files, git carries those to the flake and to Komodo, and a run of the host applies them. See [The private repo](../../fleet-bootstrap/concepts/fleet-private.md).

## Prerequisites

- A shell with the checkouts from [The control shell](../../fleet-bootstrap/foundation/control-shell.md#checkouts), and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`.
- The value is not a secret. A secret never goes in the inventory. See [Secrets](../../fleet-bootstrap/concepts/fleet-private.md#secrets).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host's name in the inventory, such as `id01` |
| `<role>` | The role that reads the variable, found in [step 1](#name) |
| `<variable>` | The variable's name, found in [step 1](#name) |

## 1. Find the variable's name {#name}

A variable does something only when a [role](index.md#roles) reads it. Ansible accepts any name, so a misspelt one is ignored without a message.

In `~/src/fleet-ansible`, open `roles/<role>/defaults/main.yml` for the role that owns the setting. Each variable there has its default and a comment saying what it does.

| Setting | Role | Listed in |
| --- | --- | --- |
| A host's network, swap, feature flags, accounts, and SSH keys | nixos | [Describing a host](../../fleet-bootstrap/concepts/fleet-private.md#describe) |
| A host's stacks, bootstrap mode, and the internal subnet | stacks | [Describing a host](../../fleet-bootstrap/concepts/fleet-private.md#describe) |
| A stack's values, and how long the run waits for Stacks | komodo_stacks | [Stack values](../../fleet-bootstrap/concepts/fleet-private.md#stack-values) |
| Where OpenTofu keeps its state | vms | [What the run needs](../../fleet-bootstrap/concepts/how-a-host-is-built.md#needs) |

## 2. Choose the scope {#scope}

Set the value in the widest place where it is true for every host under it. A narrower place wins over a wider one, so one host can still differ. See [Variables](index.md#variables).

| The value is for | Put it | In |
| --- | --- | --- |
| One host | Under the host's name | `hosts.yml` |
| Every host in a group | Under the group's `vars` | `hosts.yml` |
| Every host, and it names the fleet | Under `all: vars:` | `hosts.yml` |
| Every host, and it is a key, an address, or a list | At the top level of the file | `group_vars/all/private.yml` |

Three rules limit the choice.

- A fleet value has one setting for all NixOS hosts. The values that end up in `nixos/fleet.json` cannot differ between hosts, and `nixos-sync.yml` stops when they do. Set them under `all: vars:` or in `private.yml`. See [Identity values](../../fleet-bootstrap/concepts/fleet-private.md#identity) and [Fleet values](../../fleet-bootstrap/concepts/fleet-private.md#fleet-values).
- A list or a dictionary is replaced, not merged. A host that sets `komodo_stack_env` loses everything its group set in that variable, so it lists every stack and key it needs.
- The fleet-ansible repo's own `group_vars/all/` is not a place for your values. That repo is public, and Ansible ranks its `group_vars` above the private repo's.

## 3. Set the value {#set}

Edit the file in `~/src/fleet-private`. This example gives id01 a swap file of 1024 MiB, while the group keeps its own value:

```yaml
docker_host:
  hosts:
    id01:
      ansible_host: 172.16.7.131
      serverHostname: "id01"
      swap_size_mib: 1024
  vars:
    swap_size_mib: 512
```

Keep the type the role's default has. A number stays unquoted, a flag is `true` or `false`, and a list stays a list even with one entry.

## 4. Check what Ansible reads {#check}

From `~/src/fleet-ansible`, print the host's variables:

```bash
ansible-inventory -i ../fleet-private/hosts.yml --host <host>
```

The output is one JSON object with the host's and its groups' values merged. `<variable>` appears in it with the new value. For the example, the line reads:

```text
    "swap_size_mib": 1024,
```

A value that shows here and has no effect later is usually a misspelt name. Compare it with the role's defaults file from [step 1](#name).

## 5. Generate the files and commit {#generate}

Run both sync playbooks, read the diff, commit, and push. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change) for the commands.

The diff shows where the variable went:

| The variable | Changes |
| --- | --- |
| An identity value or a fleet value | `nixos/fleet.json`, which every host reads |
| A host's network, swap, flag, or stack list | `nixos/hosts/<host>.json` |
| A stack value, the stack list, or bootstrap mode | `komodo/stacks/<host>.toml` |
| A setting of the run itself, such as a wait | No file. The run reads it from the inventory |

In the example, the diff of `nixos/hosts/id01.json` shows `swapMiB` going from 512 to 1024.

If the diff is empty and the variable is not a setting of the run, the name is wrong or a narrower place already sets it.

## 6. Run the hosts that changed {#run}

/// tab | Semaphore

Run the **site** Template with *Target* set to `<host>`.

///

/// tab | Command line

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The recap line for the host shows `failed=0`. A change to `nixos/fleet.json` reaches every host, one run each. To run only the stage the change touches, see [Running part of a run](run-part-of-a-run.md).

<details>
<summary>Background: why the run refuses an inventory change that was not generated</summary>

The flake and Komodo never read the inventory. They read the generated files, from git. If the run deployed straight from the inventory, the files in git would describe a host that no longer exists in that form, and the next person to read the repo would be misled.

So `site.yml` works the files out again at the start of the NixOS stage and of the Komodo stage, compares them with the committed ones, and stops at a difference. The inventory, the generated files, and the host then always agree. See [The two sync playbooks](index.md#sync-playbooks).

</details>

## What's next

When the run stops, see [Reading a failed run](read-a-failed-run.md).

## Not yet confirmed {#unconfirmed}

- The whole procedure against a real private repo and a real host. `nixos-sync.yml` and `komodo-sync.yml` have been run against a copy of the private repo with placeholder secrets.
- The exact layout of what `ansible-inventory --host` prints. The example line was not taken from a run.
- A host that takes a new swap size from a deploy without a reboot.
