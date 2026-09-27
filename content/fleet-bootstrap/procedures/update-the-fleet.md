# Updating the fleet

A host never updates itself. Its packages, its kernel and its services are the ones the flake pins in `flake.lock`, and the host changes only when a deploy changes it. This page moves the pin forward, deploys the result one host at a time, and shows how to go back.

See [The NixOS flake](../concepts/nixos-flake.md).

The containers are not part of this. A stack's image versions are in docker-stacks, and Komodo deploys them.

Status: written, not yet run.

## Prerequisites

- The control shell, with nixos-fleet checked out at `~/src/nixos-fleet` and the right to push to it. See [The control shell](../foundation/control-shell.md).
- The fleet's SSH key in the SSH agent, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`.
- Every host is healthy and has a recent backup.
- The host's files in the private repo are generated, committed and pushed. See [After a change](../concepts/fleet-private.md#after-a-change).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host being updated, such as `id01` |
| `<address>` | The host's address, `ansible_host` in the inventory |
| `<admin>` | The admin account, `<abbr_name>admin` |
| `<vmid>` | The VM's ID, `vm_id` in its tfvars entry |

## 1. Move the pin {#lock}

From `~/src/nixos-fleet`, on an up-to-date `main`:

```bash
git pull
nix flake update
git diff --stat
```

`nix flake update` moves every input to the newest commit of the branch it follows. nixpkgs follows `nixos-26.05`, so the update brings that release's fixes and no new release. The diff shows `flake.lock` as the one changed file, or nothing when every input is current already.

To move one input and leave the rest, name it:

```bash
nix flake update nixpkgs
```

Check that every host of the fleet still evaluates with the new pin:

```bash
nix flake check --no-build --no-write-lock-file \
  --override-input fleet git+file://$HOME/src/fleet-private
```

Each host shows as a line that starts with `nixosConfigurations.`, and the command ends without an error. Then commit and push:

```bash
git add flake.lock
git commit -m "Update the flake's inputs"
git push
```

The run builds from the pushed `main` of nixos-fleet, so a pin that is not pushed reaches no host through the run.

Two things are pinned outside `flake.lock`. Periphery's version is in `packages/komodo-periphery.nix`, and it has to fit the version of Komodo Core. The NixOS release is the branch in `nixpkgs.url` in `flake.nix`.

## 2. Choose the order {#order}

Update one host at a time, and verify it before the next.

| Order | Host | Why here |
| --- | --- | --- |
| 1 | The host that costs least to lose, such as pk01 | A pin that breaks a host shows here first |
| 2 | Every other host except ci01 and km01 | Nothing the run needs lives on them |
| 3 | ci01 | Semaphore and OpenTofu's state are on it |
| 4 | km01 | Komodo Core is on it, and every deploy of a Stack goes through Core |

Run one host per run in Semaphore. The build itself happens on the host, but Semaphore evaluates the flake once for each host, and several at once can use more memory than its container has.

## 3. Deploy to a host {#deploy}

To see what a deploy would change, tick *Dry Run* in Semaphore or add `--check` to the command. The control node then evaluates each host's new system and lists what would be built. Nothing reaches the hosts, and nothing changes.

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  --tags nixos
```

///

The Template runs every stage, and the stages before and after the NixOS stage find nothing to change. With `--tags nixos` only that stage runs, so the shell needs neither the tunnel nor anything OpenTofu reads.

The stage builds the host's system on the host, makes it the system the host boots, and switches to it. A switch restarts the services whose package or configuration changed. Docker runs with `live-restore`, so a restart of the Docker daemon leaves the containers running.

<details>
<summary>Manual steps, instead of site.yml</summary>

The stage runs one command of the flake, and the same command works from a shell. From `~/src/ansible`:

```bash
nix run ../nixos-fleet#deploy-host -- --fleet ../fleet-private <host> <address>
```

It builds from the checkout at `~/src/nixos-fleet` as it is on disk, pushed or not. Add `--action dry-build` for what `--check` does, or `--action dry-activate` to also see which services a switch would restart. `dry-activate` builds the system on the host to find out. See [The commands](../concepts/nixos-flake.md#commands).

</details>

The run ends with `failed=0` and `unreachable=0` for the host. Log in to the host and read what it runs:

```bash
ssh <admin>@<address>
```

```bash
nixos-rebuild list-generations
systemctl --failed
docker ps
```

The first list marks the newest generation as current. The second list is empty, and the third shows the host's containers as up.

## 4. Restart the host when the kernel changed {#reboot}

A switch does not change the kernel that is running. On the host, compare the kernel the host booted with the kernel of the system it switched to:

```bash
readlink /run/booted-system/kernel /run/current-system/kernel
```

Two lines that are the same mean no restart is needed. Two that differ mean the new kernel waits for a restart. Restart the host when its stacks can be down for a minute:

```bash
sudo systemctl reboot
```

The containers come back with Docker, and Komodo shows the Server as connected again once Periphery has started.

To have a whole update take effect at a restart and not before, deploy it with `--action boot`. The host builds the new system and makes it the one to boot, and keeps running the old one until the restart. The run has no option for it, so use the command of the flake:

```bash
nix run ../nixos-fleet#deploy-host -- --fleet ../fleet-private \
  --action boot <host> <address>
```

## Rolling back {#rollback}

Every deploy leaves the system before it on the host as a generation. A rollback makes an older generation the current one. It builds nothing and needs nothing from the control node.

### On a host that answers {#rollback-switch}

Log in as the admin account, list the generations, and go back by one:

```bash
nixos-rebuild list-generations
sudo nixos-rebuild switch --rollback --no-reexec
```

The list then marks the generation before the newest as current. If the kernel differs between the two, restart the host as in [step 4](#reboot).

To go back further, name the generation by its number from the list, and switch to it:

```bash
sudo nix-env --profile /nix/var/nix/profiles/system --switch-generation <number>
sudo /nix/var/nix/profiles/system/bin/switch-to-configuration switch
```

### On a host that does not boot or answer {#rollback-grub}

GRUB lists the generations at boot, on the VM's serial console. On the Proxmox host, open the console and restart the VM from a second terminal:

```bash
qm terminal <vmid>
```

```bash
qm reset <vmid>
```

The menu waits two seconds, so press a key as soon as it shows. Choose *NixOS - All configurations*, then the generation before the newest. Leave the console with Ctrl+O.

The choice lasts for that one boot. Once the host answers, make it stay with the commands for [a host that answers](#rollback-switch).

### Make the rollback last {#rollback-pin}

> [!WARNING]
> A rollback on the host lasts until the next deploy. The next run builds the host from the pin and the files in the two repos, whatever generation the host runs.

Undo the change where it was made. For a pin, from `~/src/nixos-fleet`:

```bash
git revert <commit>
git push
```

`<commit>` is the commit that moved the pin. For a change to the host's own values, revert the commit in the private repo, generate the host's files again, and push. Then deploy to the host as in [step 3](#deploy).

The host collects generations older than 30 days once a week. A generation that old may be gone, and the way back to it is a deploy of the reverted pin.

## What's next

Build the installer ISO again after an update, so that a new VM or a rebuilt one starts from a current installer. See [The installer ISO](../foundation/proxmox-and-installer.md#installer-iso).

## Not yet confirmed {#unconfirmed}

No host has been updated or rolled back by these steps.

- `nix flake update` and `nix flake check` were run on the control node, against a copy of the flake. No deploy followed.
- A deploy with `--tags nixos` alone, and a dry run, against a real host.
- `nixos-rebuild switch --rollback --no-reexec` on a host. The command's source shows that it moves the system profile back by one generation and switches to it without building. It has not run on a host, which has no flake and no channel of its own.
- The two commands that switch to a generation by its number.
- The GRUB menu on the serial console: that `qm terminal` shows it, that two seconds are enough to stop it, and the names of its entries.
- What a switch restarts on a real host, and that the containers keep running through a restart of the Docker daemon.
- That a restart of the host brings every container back without a deploy from Komodo.
- An installer ISO older than the pin. The install builds the host's system from the flake and not from the ISO, so an older ISO is expected to install a newer system.
