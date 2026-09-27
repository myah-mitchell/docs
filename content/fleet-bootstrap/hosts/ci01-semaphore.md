# Semaphore (ci01)

Semaphore runs the fleet's ansible from a web interface. After the handover it is the control node for every host, and the Postgres beside it holds OpenTofu's state.

This page is part of ci01's build, and has no build of its own. [Automation and monitoring (ci01)](ci01-automation.md) describes the host and runs it, and sends you here for the three steps below. The stack is [semaphore-server](../stacks/semaphore-server.md).

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

The `semaphore-server` Stack has three services:

--8<-- "generated/semaphore-server/services.md"

Log in to ci01 and list the project's containers:

```bash
docker ps --filter name=semaphore- --format '{{.Names}}: {{.Status}}'
```

Three containers show, each with `healthy` in its status:

```text
semaphore-semaphore
semaphore-postgres
semaphore-postgres-backup
```

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

Go back to [step 5 of ci01's page](ci01-automation.md#first-access).

## What to keep safe {#keep}

Everything Semaphore holds is in its database, encrypted with the three keys from [step 1](#values).

| Folder under `/opt/docker/volumes/semaphore` | Holds |
| --- | --- |
| `postgres-data` | Semaphore's database and the OpenTofu state database |
| `postgres-backup-data` | A dump of both databases, written each day |

Both are on the persistent disk, so they survive a rebuild of the VM. The backup keeps 7 daily, 4 weekly, and 6 monthly dumps.

## Not yet confirmed {#unconfirmed}

- The whole page. semaphore-server has not been deployed by the run.
- What Semaphore does with a changed `SEMAPHORE_ADMIN_PASSWORD` after the account exists. Change the password in Semaphore's own interface until that is known.
- The `psql` check in [step 2](#verify). It relies on the Postgres image trusting connections made from inside its own container.
