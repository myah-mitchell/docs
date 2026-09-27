# semaphore-server

semaphore-server is Semaphore, which runs `site.yml` for every host after the handover, with a Postgres that also holds OpenTofu's state. It runs on one host, ci01. See [Semaphore (ci01)](../hosts/ci01-semaphore.md) for the build.

## What it runs {#services}

--8<-- "generated/semaphore-server/services.md"

| Service | Does |
| --- | --- |
| `semaphore` | Serves the web interface and the API on port 3000, and runs each Template's ansible and OpenTofu |
| `postgres` | Holds Semaphore's own database, and beside it the `tofu_state` database |
| `postgres-backup` | Dumps both databases each day, and keeps 7 daily, 4 weekly, and 6 monthly dumps |

The project is `semaphore`, so the containers are `semaphore-semaphore`, `semaphore-postgres`, and `semaphore-postgres-backup`.

Postgres and the backup container sit on `semaphore_backend`, a network marked internal. Nothing outside ci01 reaches the database, which is why the handover moves the state through an SSH tunnel. See [The handover](../foundation/handover.md#tunnel).

The image is `semaphoreui/semaphore:v2.13.13`, which ships OpenTofu 1.9.0.

## Values it reads {#values}

--8<-- "generated/semaphore-server/values.md"

The host page says what to put in each. See [Stage the values](../hosts/ci01-semaphore.md#values).

The four `SEMAPHORE_ADMIN_` values create the first admin account. The three that end in `_HASH` and `_ENCRYPTION` protect session cookies and every key stored in the *Key Store*. Changing one later ends every session or makes every stored key unreadable.

Postgres reads its own two Secrets and `SEMAPHORE_TOFU_STATE_PASSWORD` on the first start of an empty data folder, and never again.

## What the host needs {#host-setup}

--8<-- "generated/semaphore-server/host-setup.md"

The run creates all of it in the provision stage. The stack also needs a Traefik on the same host.

The three `semaphore-` folders belong to `101001` because the image runs as its own user, UID 1001, and not as the fleet's usual 1000. See [Why 100000 and 101000](../concepts/host-layout.md#uid-offsets).

`10-tofu-state.sh` creates a role named `tofu` and a database named `tofu_state` that the role owns. Postgres runs every script in `postgres-initdb` one time, when it starts on an empty data folder. See [The state database](../foundation/handover.md#state-database).

## Hostnames {#hostnames}

Traefik routes two names to Semaphore. With the host `ci01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Comes from |
| --- | --- |
| `semaphore.home.myah-mitchell.com` | `SEMAPHORE_SERVICE_NAME` on the sub-domain |
| `semaphore.ci01.home.myah-mitchell.com` | `SEMAPHORE_HOSTNAME` on the host |

The route takes its chain from `TRAEFIK_AUTH_CHAIN`. The run sets that key to `chain-no-auth@file` in bootstrap mode and leaves it blank outside it, and blank means `chain-authentik@file`. See [What it changes](../concepts/bootstrap-mode.md#changes).

Semaphore keeps its own sign-in in both modes.

## Verify {#verify}

In Komodo, the `semaphore-server` Stack shows as running with three services.

On the host, list the project's containers:

```bash
docker compose -p semaphore ps
```

Every container shows `healthy` in the *STATUS* column. Semaphore's own check asks its API for a ping, so `healthy` there means Semaphore is answering.

List the databases:

```bash
docker exec semaphore-postgres \
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -l'
```

The list includes `semaphore-db`, and `tofu_state` with `tofu` as its owner.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/semaphore` | Holds |
| --- | --- |
| `postgres-data` | Both live databases: every Project, key, and Template, and OpenTofu's state |
| `postgres-backup-data` | The dumps of both |
| `semaphore-config` | Semaphore's config file |

All three are on the persistent disk, so they survive a rebuild of the VM. The three encryption Secrets have to survive with them, since the keys in a restored database cannot be read under different ones.

Restore `tofu_state` on its own, never as part of a dump of the whole server. See [The state database](../foundation/handover.md#state-database).

## Not yet confirmed {#unconfirmed}

- The database listing above. It relies on the Postgres image letting a connection from inside the container in without a password.
- A first run of `tofu` from inside Semaphore. See [The handover](../foundation/handover.md#unconfirmed).
