# Semaphore (ci01)

Semaphore runs the fleet's ansible from a web interface. After the handover it is the control node for every host, and the Postgres beside it holds OpenTofu's state. The stack also gives Semaphore the nix that a run installs and deploys a host with.

This page is part of ci01's build, and has no build of its own. [Automation and monitoring (ci01)](ci01-automation.md) describes the host and runs it, and sends you here for the steps below. The stack is [semaphore-server](../stacks/semaphore-server.md).

Status: written, not yet run.

## Prerequisites

- You are following [Automation and monitoring (ci01)](ci01-automation.md), and came here from its step 2, 4, or 5.

## 1. Stage the values {#values}

Three of Semaphore's values are keys of 32 random bytes, written as base64. Generate them in a shell:

```bash
head -c32 /dev/urandom | base64
head -c32 /dev/urandom | base64
head -c32 /dev/urandom | base64
```

Each line of output is 44 characters long and ends in `=`.

Create these ten in Komodo, each with **Is Secret** ticked. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

| Name | Value |
| --- | --- |
| `SEMAPHORE_ADMIN_USER` | The admin account's login, your choice |
| `SEMAPHORE_ADMIN_NAME` | Its display name |
| `SEMAPHORE_ADMIN_EMAIL` | Its email address |
| `SEMAPHORE_ADMIN_PASSWORD` | Your choice, alphanumeric only |
| `SEMAPHORE_COOKIE_HASH` | The first generated key |
| `SEMAPHORE_COOKIE_ENCRYPTION` | The second generated key |
| `SEMAPHORE_ACCESS_KEY_ENCRYPTION` | The third generated key |
| `SEMAPHORE_POSTGRES_USER` | Your choice |
| `SEMAPHORE_POSTGRES_PASSWORD` | 48 alphanumeric characters |
| `SEMAPHORE_TOFU_STATE_PASSWORD` | 48 alphanumeric characters |

Generate each 48-character value in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48; echo
```

> [!WARNING]
> The three keys encrypt what Semaphore stores. Changing one later makes every stored login and access key unreadable and ends every session. Keep a copy of all three in your password manager.

`SEMAPHORE_TOFU_STATE_PASSWORD` is the password of the `tofu` role, which owns the state database. You need it again for `PG_CONN_STR` in [The Semaphore project](../foundation/semaphore-project.md#environment-variables), and in [The handover](../foundation/handover.md#move). Keep a copy of it as well.

Postgres reads the three database values on the first start of an empty data folder, and never again. A value changed in Komodo after that reaches the containers and not the database, so Semaphore's login fails. See [The state database](../foundation/handover.md#state-database) for changing the `tofu` role's password later.

The register lists the same ten. See [Semaphore](../concepts/variables-and-secrets.md#semaphore).

Go back to [step 2 of ci01's page](ci01-automation.md#values).

## 2. Verify {#verify}

The `semaphore-server` Stack has four services:

--8<-- "generated/semaphore-server/services.md"

Three of them keep running. The other one, nix, runs one time at each deploy and exits, and Komodo leaves it out when it works out the Stack's state.

Log in to ci01 and list the project's running containers:

```bash
docker ps --filter name=semaphore- --format '{{.Names}}: {{.Status}}'
```

Three containers show, each with `healthy` in its status:

```text
semaphore-semaphore
semaphore-postgres
semaphore-postgres-backup
```

### Check nix {#verify-nix}

List the container that has exited, and read its log:

```bash
docker ps -a --filter name=semaphore-nix --format '{{.Names}}: {{.Status}}'
docker logs semaphore-nix
```

The status of `semaphore-nix` starts with `Exited (0)`. After the first deploy the log is one line that starts with `Filled /nix-data from this image`. After any later deploy it is `/nix-data already holds a store. Left as it is.`

Run nix the way a run does, inside Semaphore's container:

```bash
docker exec semaphore-semaphore /nix/var/nix/profiles/default/bin/nix --version
```

It prints the version of nix, which is the tag of the nix image in docker-stacks.

### Check the state database {#verify-state}

Check that the first start created the state database:

```bash
docker exec semaphore-postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -l'
```

The list includes `tofu_state`, with `tofu` in the *Owner* column.

If `tofu_state` is missing, the script that creates it did not run. Check that the file below exists, and read the container's log for the first start:

```bash
sudo ls -ln /opt/docker/volumes/semaphore/postgres-initdb/
docker logs semaphore-postgres 2>&1 | grep -i tofu
```

The folder holds `10-tofu-state.sh`, owned by `100000`.

Go back to [step 4 of ci01's page](ci01-automation.md#verify).

## 3. Sign in {#first-access}

Open `https://semaphore.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Sign in with the values of `SEMAPHORE_ADMIN_USER` and `SEMAPHORE_ADMIN_PASSWORD`. Semaphore opens with no Project in it.

| Hostname | Used for |
| --- | --- |
| `semaphore.ci01.home.myah-mitchell.com` | Reaching Semaphore by its host |
| `semaphore.home.myah-mitchell.com` | The short name, once DNS records exist for it |

In bootstrap mode Semaphore's own login is all that guards it. Semaphore holds the key to every host in the fleet, so its route asks Authentik for a sign-in first once the fleet leaves bootstrap mode. See [Bootstrap mode](../concepts/bootstrap-mode.md#effects).

Giving Semaphore its Project, keys, inventory, and Template is a foundation step. See [The Semaphore project](../foundation/semaphore-project.md), which the end of ci01's page sends you to.

## 4. Add sops to nix {#sops}

Ansible decrypts the fleet's secrets with sops, and neither Semaphore's image nor the nix image has it. On ci01, add it to nix's default profile:

```bash
docker exec semaphore-semaphore /nix/var/nix/profiles/default/bin/nix \
  --extra-experimental-features 'nix-command flakes' \
  profile add --profile /nix/var/nix/profiles/default nixpkgs#sops
```

Confirm that it is there:

```bash
docker exec semaphore-semaphore /nix/var/nix/profiles/default/bin/sops --version
```

The profile is in `nix-data`, so sops is still there after a redeploy. Run the first command again whenever `nix-data` has been emptied and filled again.

Go back to [step 5 of ci01's page](ci01-automation.md#first-access).

## Nix for the runs {#nix}

The run calls nix on the control node, and after the handover the control node is Semaphore's container. Three parts of the stack put nix there.

| Part | What it is |
| --- | --- |
| The service nix | A container that copies `/nix` from its own image into `nix-data` when the folder holds no store, then exits. It leaves a filled folder as it is |
| The folder `nix-data` | Under `/opt/docker/volumes/semaphore`, owned by `101001`, and mounted in Semaphore's container at `/nix` |
| The key `NIX_HOSTNAME` | A line in the stack's `komodo.env`, set to `nix`. It gives the container its name, `semaphore-nix`, and takes no Variable or Secret |

Semaphore starts only after the service nix has finished. The copy belongs to the owner of the folder, which is the user Semaphore runs as, so Semaphore runs nix as that user with no daemon.

Komodo's Stack lists nix under `ignore_services`. `komodo-sync.yml` writes that line into `komodo/stacks/ci01.toml`, and without it Komodo reports the Stack as unhealthy, because one of its services has exited.

A run sees nix and sops only through three values in the Template's Variable Group: `PATH`, `NIX_CONFIG`, and `SOPS_AGE_KEY`. See [The Semaphore project](../foundation/semaphore-project.md#nix) for each value.

Semaphore's container evaluates a host's configuration and builds nothing. The build happens on the host being deployed to, which is what `nixos_build_on: remote` in the ansible repo sets.

### Moving to another version of nix {#nix-version}

The nix image's tag sets the version of a new fill only. To move a filled folder to the image's version:

1. In Komodo, open the `semaphore-server` Stack and click **Destroy**. Komodo takes the Stack's containers down.
2. On ci01, empty the folder:

    ```bash
    sudo find /opt/docker/volumes/semaphore/nix-data -mindepth 1 -delete
    ```

3. In Komodo, click **Deploy** on the same Stack. The service nix fills the folder from its image.
4. Add sops again, as in [step 4](#sops).

## What to keep safe {#keep}

Everything Semaphore holds is in its database, encrypted with the three keys from [step 1](#values).

| Folder under `/opt/docker/volumes/semaphore` | Holds |
| --- | --- |
| `postgres-data` | Semaphore's database and the OpenTofu state database |
| `postgres-backup-data` | A dump of both databases, written each day |

Both are on the persistent disk, so they survive a rebuild of the VM. The backup keeps 7 daily, 4 weekly, and 6 monthly dumps.

`nix-data` is on the same disk and needs no backup. The service nix fills it again, and [step 4](#sops) adds sops again.

## Not yet confirmed {#unconfirmed}

- The whole page. semaphore-server has not been deployed by the run.
- What Semaphore does with a changed `SEMAPHORE_ADMIN_PASSWORD` after the account exists. Change the password in Semaphore's own interface until that is known.
- The `psql` check in [step 2](#verify-state). It relies on the Postgres image trusting connections made from inside its own container.
- The service nix under Docker's `userns-remap`: that the container's root can write into `nix-data` and hand the copy to the folder's owner.
- nix in Semaphore's container: that it runs as Semaphore's user with no daemon, and that `nix profile add` can write the profile in `nix-data`.
- What the commands in [Check nix](#verify-nix) and [step 4](#sops) print.
- The steps in [Moving to another version of nix](#nix-version), and the label **Destroy** in Komodo.
- Whether Semaphore's memory limit, 2 GB with the operational defaults, is enough for a run against several hosts. Each host's configuration is evaluated in Semaphore's container.
