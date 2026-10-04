# Adding a module to the flake

This page gives every host something the inventory has no setting for: a program, a service, a kernel setting. The change is a new module in the fleet-nixos repo, tried on one host, pushed, and then deployed to the rest. Use it when [Changing a host's setting](change-a-host-setting.md#find) sends you here.

Status: written, not yet run.

The steps take one module as their example: turning on tmux, so that a session on a host outlives a dropped connection. See [Modules and options](index.md#modules) for what a module is.

## Prerequisites

- The control shell, with fleet-nixos, fleet-ansible, and the private repo checked out next to each other under `~/src`, and the right to push to fleet-nixos. See [The control shell](../../fleet-bootstrap/foundation/control-shell.md).
- The fleet's SSH key in `~/.ssh/config`, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. Step 4 deploys from the shell.
- The private repo's files are generated, committed, and pushed. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).
- A host that can be down for a few minutes if the change goes wrong, to try the module on.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host the module is tried on, such as `pk01` |
| `<address>` | That host's address, `ansible_host` in the inventory |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |

## 1. Find the option {#option}

Search for what you want in [the NixOS option search](https://search.nixos.org/options), with the release set to the one in `nixpkgs.url` in `flake.nix`. The search for tmux gives `programs.tmux.enable`, which takes true or false.

If the search has no option and you only need a program installed, add the package's name to the list in `modules/packages.nix` instead of writing a module, and go to [step 3](#check).

## 2. Write the module {#write}

From `~/src/fleet-nixos`, on an up-to-date `main`, create `modules/tmux.nix`:

```nix
# tmux, so that a session outlives a dropped connection.
{
  programs.tmux.enable = true;
}
```

Open with a comment that says what the module is for, as every module in the folder does. One module covers one concern.

Add the file to the `imports` list in `modules/default.nix`, in alphabetical order:

```nix
    ./system.nix
    ./tmux.nix
    ./users.nix
```

Then tell git about the new file:

```bash
git add modules/tmux.nix
```

The flake is built from the files git tracks. Without this, the build stops and says the file is not tracked.

<details>
<summary>Background: a module that differs from host to host</summary>

The example is on for every host, so it reads nothing from the fleet. A module that depends on a host's values reads them from the `fleet` options, as `modules/ntp.nix` reads `config.fleet.ntpServers`. When a feature switch decides whether it applies, the module wraps its settings in `lib.mkIf`, as `modules/mosh.nix` does.

A new value or switch is a larger change, in three places that have to agree: the option in `modules/options.nix`, the key in `lib/fleet.nix`, which stops the build when a host's file lacks it, and the nixos role in fleet-ansible, which writes the key into every host's file from the inventory. This page does not cover it.

</details>

## 3. Check that every host still evaluates {#check}

Format the files, then run the flake's checks against the example fleet inside the repo:

```bash
nix fmt modules/tmux.nix modules/default.nix
nix flake check
```

The second command ends without an error. It evaluates each example host and fails on a `.nix` file that is not formatted.

Run the checks again against your own fleet:

```bash
nix flake check --no-build --no-write-lock-file \
  --override-input fleet git+file://$HOME/src/fleet-private
```

Then read the new option's value for the host you will try it on:

```bash
nix eval .#nixosConfigurations.<host>.config.programs.tmux.enable \
  --override-input fleet git+file://$HOME/src/fleet-private \
  --no-write-lock-file
```

```text
true
```

An option name that does not exist, or a value of the wrong type, stops any of these commands with a message naming the option and the file. Nothing has reached a host so far.

## 4. Try it on one host {#try}

From `~/src/fleet-nixos`, deploy the checkout as it is on disk to one host, with the action `test`:

```bash
nix run .#deploy-host -- --fleet ../fleet-private \
  --action test <host> <address>
```

The host builds the new system and activates it, and the boot menu keeps the previous system as its default. If the change leaves the host unreachable, restart the VM from Proxmox and it comes back as it was. See [Build, activate, switch, and boot](index.md#switch).

Log in and check the result:

```bash
ssh <admin>@<address>
```

```bash
tmux -V
systemctl --failed
```

The first command prints tmux's version, and the second list is empty.

## 5. Commit and push {#push}

From `~/src/fleet-nixos`:

```bash
git add modules/
git commit -m "Add tmux to every host"
git push
```

The run clones fleet-nixos from the pushed `main` at its start, so a module that is not pushed reaches no host through the run.

## 6. Deploy to every host {#deploy}

Run each host, one per run, starting with the host from step 4. That run makes the tried system the host's boot default.

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

Each run ends with `failed=0` and `unreachable=0` for its host. Take the hosts in the order [Updating the fleet](../../fleet-bootstrap/procedures/update-the-fleet.md#order) gives, and verify each as in step 4 before the next.

If a host is worse off after its run, go back to its previous generation, then revert the commit in fleet-nixos and push. See [Rolling back](../../fleet-bootstrap/procedures/update-the-fleet.md#rollback).

## What's next

A new VM is installed from the flake and not from the ISO's contents, so the installer ISO does not need building again for a new module.

## Not yet confirmed {#unconfirmed}

The example module was added to a copy of the flake on a workstation. It evaluated for the example host ex01 with `programs.tmux.enable` true, the two files passed the formatter, and the build refused the module until `git add` was run. No host has been deployed with it.

- `nix flake check` in full with the new module. Only the evaluation of one host and the formatter were run.
- `deploy-host --action test` against a host, and a restart returning the host to its previous system.
- A run with `--tags nixos` alone against a built host.
- That `nix fmt` with file names formats those files with the Nix version on the control shell. The flake's formatter is nixfmt.
