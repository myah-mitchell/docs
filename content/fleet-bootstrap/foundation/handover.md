# The handover

The shell has done its work. This page moves OpenTofu's state from the shell's file into the database on ci01, proves that Semaphore can run the fleet, and removes the secrets from the shell.

Status: written, not yet run. The state move was tried with OpenTofu 1.12.6 against a local Postgres and read back with 1.9.0, the version in Semaphore's image. See [Not yet confirmed](#unconfirmed) for the rest.

## Prerequisites

- Semaphore has its Project and the **site** Template, from [The Semaphore project](semaphore-project.md).
- The shell has `~/.config/fleet/env` loaded, and the state file from the first run is where the run left it.
- You have a password manager, or another encrypted store, to keep four secrets in.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
| `<password>` | The `tofu` role's password, the Komodo Secret `SEMAPHORE_TOFU_STATE_PASSWORD` |
| `<postgres-ip>` | The database container's address inside ci01, found in [step 1](#tunnel) |

## 1. Open a tunnel to the state database {#tunnel}

The database listens on a network inside ci01 and nowhere else. SSH carries a port of the shell's to it.

Log in to ci01 and read the container's address:

```bash
ssh <admin>@172.16.7.121
```

```bash
docker inspect semaphore-postgres \
  -f '{{ (index .NetworkSettings.Networks "semaphore_backend").IPAddress }}'
```

Log out. In a second terminal in the shell, open the tunnel and leave it running:

```bash
ssh -N -L 15432:<postgres-ip>:5432 <admin>@172.16.7.121
```

The command prints nothing and does not return. While it runs, port 15432 in the shell reaches the database.

## 2. Move the state {#move}

In the first terminal, point OpenTofu at the tunnel. The password is the value of the Komodo Secret `SEMAPHORE_TOFU_STATE_PASSWORD`:

```bash
read -rs -p "Password of the tofu role: " tofuPassword; echo
export PG_CONN_STR="postgres://tofu:${tofuPassword}@localhost:15432/tofu_state?sslmode=disable"
```

The first run left a checkout of the fleet-opentofu repo behind, set to keep state in a file. Remove that setting and let OpenTofu copy the state to the backend the repo declares:

```bash
cd /tmp/ansible-fleet-opentofu-checkout/envs/prod
rm backend_override.tf
tofu init -migrate-state -force-copy
```

The output includes `Successfully configured the backend "pg"!`. Read the state back from the database:

```bash
tofu state list
```

The list includes one line for each VM the shell created:

```text
module.vm["ci01"].proxmox_virtual_environment_vm.this
module.vm["km01"].proxmox_virtual_environment_vm.this
```

The state is encrypted the same way in both places, with the passphrase in `TF_ENCRYPTION`.

### If the checkout is gone {#no-checkout}

`/tmp` does not always survive a restart of the machine. The state file is in your home folder and does. Make the checkout again, pointed at the file, then go back to the `rm` above:

```bash
git clone --depth 1 https://github.com/myah-mitchell/fleet-opentofu \
  /tmp/ansible-fleet-opentofu-checkout
cd /tmp/ansible-fleet-opentofu-checkout/envs/prod
cat > backend_override.tf <<EOF
terraform {
  backend "local" {
    path = "$HOME/.local/state/fleet-opentofu/prod.tfstate"
  }
}
EOF
tofu init
```

## 3. Prove Semaphore {#prove}

In Semaphore, run the **site** Template with *Target* set to `km01`.

The run passes through every stage and leaves km01 as it was. Its recap shows `failed=0` and `unreachable=0` for km01. `changed` is not zero: the `nixos` stage reports a change each time it deploys, and the `komodo` stage each time it syncs, whether or not the host ends up different.

| The stage | Proves that Semaphore |
| --- | --- |
| `vms` | Reads the state, decrypts it, and reaches the Proxmox API |
| `wait` | Reaches km01's SSH port |
| `nixos` | Decrypts the private repo with the deploy key, clones fleet-nixos, and reaches km01 over SSH with the fleet's key |
| `komodo` | Reaches Komodo's API with the service user's key |

A run that fails in the `vms` stage with a message about creating a VM did not find the state. Check `PG_CONN_STR` and `TF_ENCRYPTION` in the Variable Group, then run it again. Proxmox refuses a second VM under an ID that is taken, so the failed run has created nothing.

Run the Template again with *Target* set to `ci01`.

Close the tunnel with Ctrl+C in the second terminal.

## 4. Store what outlives the shell {#keep}

Semaphore holds every secret the run needs, and shows none of them again. Semaphore also lives on ci01, so the day ci01 is rebuilt, a shell has to do it.

Put these in your password manager before the next step deletes them:

| Secret | Where it is |
| --- | --- |
| The fleet's SSH private key | `~/.ssh/fleet-ansible` |
| The deploy age key | `~/.config/fleet/deploy.key` |
| The run's secrets, state passphrase included | `~/.config/fleet/env`, the whole file |
| The `tofu` role's password | The Komodo Secret `SEMAPHORE_TOFU_STATE_PASSWORD` |

The admin age key is in the password manager already, from [The control shell](control-shell.md#age-keys). It is the one key that can add a host to the secrets, so check it is there.

> [!WARNING]
> Without the state passphrase nobody can read the state, in the database or in a backup of it. Every VM would have to be imported again.

## 5. Clean the shell {#clean}

Delete the state, the checkouts the run made, the environment file, and the two keys:

```bash
rm -rf ~/.local/state/fleet-opentofu /tmp/ansible-fleet-opentofu-checkout /tmp/ansible-fleet-nixos-checkout
rm ~/.config/fleet/env ~/.config/fleet/deploy.key
rm ~/.ssh/fleet-ansible ~/.ssh/fleet-ansible.pub
```

Remove the `Match` block for the fleet's key from `~/.ssh/config`. Left in place, it points at a file that is gone, and every login to a host fails until it is taken out.

Close every terminal that loaded the environment file. The values stay in a terminal's memory until it exits.

The checkouts under `~/src` can stay. The private repo's secrets are encrypted, and without the deploy key the shell cannot read them.

## What's next

The foundation is finished. Every host from here is one run of the **site** Template, in the order the [running order](../index.md#running-order) gives. The next host is id01. See [Identity (id01)](../hosts/id01-identity.md).

## The state database {#state-database}

The state lives in `tofu_state`, a second database on Semaphore's Postgres. A role named `tofu` owns that database and nothing else, so Semaphore's own login cannot read it.

A script in the stack's `postgres-initdb` folder creates both, on the first start of an empty data folder and never again. Changing the role's password later is an `ALTER ROLE` by hand, followed by the new value in `PG_CONN_STR`.

The backup container dumps both databases. Restore `tofu_state` on its own. Restoring the whole server from a dump rolls the state back with everything else, and an old state makes OpenTofu try to create VMs that exist.

## Running from a shell again {#shell-runs}

Three cases need a shell after the handover: Semaphore is down, ci01 itself is being rebuilt, or a run needs an option the Template does not pass.

Set the shell up as [The control shell](control-shell.md) does, without creating a key or a passphrase. Restore the fleet's SSH key, the deploy age key, and the environment file from your password manager, to the paths the table in [step 4](#keep) gives, and put the `Match` block back in `~/.ssh/config`.

With ci01 up, the state stays in the database. Open the tunnel from [step 1](#tunnel), and add this line to the environment file with the `tofu` role's password in it:

```bash
export PG_CONN_STR="postgres://tofu:<password>@localhost:15432/tofu_state?sslmode=disable"
```

Then run the command from the host page's **Command line** tab as it is written. Do not add `vms_backend=local`. That option starts a second, empty state, and OpenTofu then tries to create every VM in the run again.

With ci01 down, the database is down with it. See [Rebuilding ci01](../procedures/rebuild-a-vm.md#ci01) for how the state is taken out before the rebuild and put back after it.

Clean the shell again when the work is done, as in [step 5](#clean).

## Not yet confirmed {#unconfirmed}

- The tunnel. The host can reach a container on an internal Docker network by its address, and the host's sshd does not turn TCP forwarding off, but the two have not been tried together on ci01.
- The state move against the real database. It was tried against a local Postgres, with a state that held no Proxmox VM.
- A first run of `tofu` from inside Semaphore.
- What the `vms` stage does when it finds no state. The page's claim that Proxmox refuses the duplicate ID follows from how Proxmox treats VM IDs, and has not been provoked.
- The `nixos` stage from Semaphore: sops with the key from `SOPS_AGE_KEY`, the clone of fleet-nixos, and the flake's `ssh` calls with the key from Semaphore's agent.
- The recap of a run that changes nothing on the host. The `nixos` and `komodo` stages report a change by design, and the count has not been seen from a real run.
- A run against ci01 from Semaphore, which is a run against the host Semaphore is on. A deploy that restarts Semaphore's own container, or a sync that redeploys semaphore-server, should stop the run partway, and pass when run again.
