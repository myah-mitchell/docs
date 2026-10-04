# Changing a host's setting

This page changes one value of a built host's operating system: a feature turned on or off, the swap size, a nameserver, a time server. You make the change in the inventory, generate the host's file again, and run the host. Use it whenever a host should differ from what it is now and the inventory already has a key for the difference.

Status: written, not yet run.

Nothing is edited on the host. A host's system is built from its configuration, so an edit made on the host is undone by the next deploy. See [Declarative configuration](index.md#declarative).

## Prerequisites

- The control shell, with fleet-ansible, fleet-nixos, and the private repo checked out next to each other under `~/src`. See [The control shell](../../fleet-bootstrap/foundation/control-shell.md).
- The host is built and healthy.
- The private repo has no uncommitted change under `nixos/` or `secrets/`.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host's name in the inventory, such as `bh01` |
| `<address>` | The host's address, `ansible_host` in the inventory |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |

The steps take one change as their example: turning mosh off on bh01, the host that faces the internet.

## 1. Find where the setting lives {#find}

Find the kind of setting in this table. The rest of the page covers the first two rows.

| The setting | Lives in | Reaches |
| --- | --- | --- |
| A feature flag or a network value of one host or one group | `hosts.yml` in the private repo | The hosts that entry covers |
| A value every host shares, such as the SSH keys or the time servers | `group_vars/all/private.yml`, or `all: vars:` in `hosts.yml` | Every host |
| A secret, such as the accounts' password | `secrets/fleet.yaml`, through sops | Every host. See [Changing a secret](../../fleet-bootstrap/concepts/secrets-with-sops.md#edit) |
| A port, folder, or seed file a stack needs | The container's `setup.yaml` in fleet-stacks | Every host that runs the stack. See [Opening a firewall port](open-a-firewall-port.md) |
| Anything the inventory has no key for, such as a package | A module in fleet-nixos | Every host. See [Adding a module to the flake](add-a-module.md) |
| The VM's memory, cores, or disks | `opentofu/prod.tfvars` | The VM, through OpenTofu and not NixOS |

[Describing a host](../../fleet-bootstrap/concepts/fleet-private.md#describe) lists the keys and flags a host or group can set, with their defaults. [Fleet values](../../fleet-bootstrap/concepts/fleet-private.md#fleet-values) lists the shared ones.

## 2. Edit the inventory {#edit}

In `~/src/fleet-private/hosts.yml`, set the key on the host's own entry:

```yaml
    bh01:
      ansible_host: 172.16.8.111
      serverHostname: "bh01"
      MOSH: false
```

A key on a host beats the same key in its group's `vars`. To change every host of a group, set the key under the group's `vars` and leave the hosts alone.

## 3. Generate the host's file {#generate}

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
git -C ../fleet-private add hosts.yml group_vars/ nixos/
git -C ../fleet-private diff --cached
```

The playbook connects to no host. The diff shows your edit, and the same change in the generated file `nixos/hosts/<host>.json`:

```text
-    "mosh": true,
+    "mosh": false,
```

A change to a shared value shows in `nixos/fleet.json`. If a file you did not expect has changed, stop and read why before going on: fleet-stacks may have changed since the files were last generated.

<details>
<summary>Background: why the file is added before anything else</summary>

The flake reads the private repo through git and takes only the files git tracks, in the state git knows them. `git add` is what makes the new content visible to a build. The run goes further and refuses to start while anything under `nixos/` or `secrets/` is uncommitted. See [Flakes and the lock file](index.md#flakes).

</details>

## 4. Check the value before it reaches the host {#check}

From `~/src/fleet-nixos`, ask the flake what the host's configuration now holds:

```bash
nix eval .#nixosConfigurations.<host>.config.fleet.features.mosh \
  --override-input fleet git+file://$HOME/src/fleet-private \
  --no-write-lock-file
```

```text
false
```

The command evaluates the whole configuration, so it also proves that the host still evaluates. Nothing is built and the host is not contacted. For another setting, replace the part after `config.` with the option that carries it. `modules/options.nix` in fleet-nixos lists the options under `fleet`.

## 5. Commit and push {#commit}

From `~/src/fleet-ansible`:

```bash
git -C ../fleet-private commit -m "Turn mosh off on <host>"
git -C ../fleet-private push
```

Semaphore builds from the pushed copy of the private repo, so a change that is not pushed reaches no host through it.

## 6. Run the host {#run}

To see what the deploy would build first, tick *Dry Run* in Semaphore or add `--check` to the command. See [Seeing what a run would do](../../fleet-bootstrap/concepts/how-a-host-is-built.md#check).

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  --tags nixos
```

///

The run ends with `failed=0` and `unreachable=0` for the host. The NixOS stage builds the new system on the host and switches to it, which restarts only the services the change touches. See [Build, activate, switch, and boot](index.md#switch).

A change to `nixos/fleet.json` reaches every host, one run each. Run one host per run, in the order [Updating the fleet](../../fleet-bootstrap/procedures/update-the-fleet.md#order) gives.

## 7. Verify on the host {#verify}

Log in to the host:

```bash
ssh <admin>@<address>
```

```bash
nixos-rebuild list-generations
systemctl --failed
```

The first list marks a new generation, dated today, as current. The second list is empty.

Then check the setting itself. For the example, the firewall no longer opens mosh's ports:

```bash
sudo iptables -S nixos-fw | grep 60000
```

The command prints nothing.

If the host is worse off than before, go back to the previous generation and then undo the commit. See [Rolling back](../../fleet-bootstrap/procedures/update-the-fleet.md#rollback).

## What's next

- To open a port, see [Opening a firewall port](open-a-firewall-port.md).
- To change something the inventory has no key for, see [Adding a module to the flake](add-a-module.md).

## Not yet confirmed {#unconfirmed}

The inventory keys, the generated file, and the `nix eval` command were checked against the repos, and the command was run against the example fleet in fleet-nixos. No host has been changed by these steps.

- A run with `--tags nixos` alone against a built host, and what it restarts.
- That a switch which turns mosh off removes the rule for UDP ports 60000 to 61000 from the `nixos-fw` chain without a restart of the host. The evaluated configuration lists that range only while the feature is on.
- That a changed `swap_size_mib` resizes an existing swap file at a switch. It may take a restart of the host.
