# komodo-server

komodo-server is [Komodo](../../tools/komodo/index.md) Core with its database. Core is the part of Komodo that holds the web interface and decides what runs where, and [Periphery](../../tools/glossary.md#core-and-periphery) is the agent on each host that carries it out. Core deploys every stack in the fleet, this one included, and every host's Periphery connects to it.

It runs on one host, km01. See [Komodo (km01)](../hosts/km01-komodo.md) for the build.

## What it runs {#services}

--8<-- "generated/komodo-server/services.md"

| Service | Does |
| --- | --- |
| `ferretdb` | Stands between Core and Postgres. Core expects a MongoDB database, so FerretDB speaks MongoDB's protocol to it and stores what it is given in Postgres |
| `postgres` | Postgres with the DocumentDB extension. Holds every Komodo resource, Variable, and Secret |
| `postgres-backup` | Dumps the database each day, and keeps 7 daily, 4 weekly, and 6 monthly dumps |
| `komodo` | Komodo Core: the web interface and the API, on port 9120 |

The [project](../../tools/glossary.md#project) is `komodo`, so the containers are named `komodo-` and the service, such as `komodo-postgres`. Core's container is `komodo-komodo`.

FerretDB, Postgres, and the backup container sit on a network marked internal. Core joins that network and `proxy`, and publishes port 9120 on the host.

## Values it reads {#values}

--8<-- "generated/komodo-server/values.md"

Each [Secret](../../tools/glossary.md#variables-and-secrets) feeds two keys. Postgres is created with the pair, and FerretDB and Core log in with it. Postgres takes the pair on the first start of an empty data folder, so the Secrets have to hold what that first start used. See [Stage the values](../hosts/km01-komodo.md#values).

## What the host needs {#host-setup}

--8<-- "generated/komodo-server/host-setup.md"

The stack also needs a Traefik on the same host for the routes below. Port 9120 works without one.

Port 9120 is open to any address because every Periphery in the fleet dials it, and so does each [run](../../tools/glossary.md#run).

`core.config.toml` is Core's config file, mounted read-only. The copy the run makes is upstream's default, unchanged.

## Hostnames {#hostnames}

Traefik routes four names to Core. With the host `km01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Comes from |
| --- | --- |
| `komodo.myah-mitchell.com` | `KOMODO_HOSTNAME` on the domain |
| `komodo.home.myah-mitchell.com` | `KOMODO_HOSTNAME` on the sub-domain |
| `komodo.km01.home.myah-mitchell.com` | `KOMODO_HOSTNAME` on the host |

The fourth is the project name on the host, which here is the same as the third.

The route uses the `chain-no-auth` [chain](../../tools/glossary.md#auth-chain) in [both modes](../concepts/bootstrap-mode.md). Core has its own sign-in, and the API has to answer clients that cannot follow a redirect to Authentik.

The direct address, `http://172.16.7.101:9120`, does not go through Traefik. It is the one in `komodo_core_address`.

## Verify {#verify}

In Komodo, the `komodo-server` Stack shows as running with four services.

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p komodo-server ps
```

`komodo-ferretdb`, `komodo-postgres`, and `komodo-postgres-backup` show `healthy` in the *STATUS* column. `komodo-komodo` has no health check, so it shows `Up` and nothing more. A Core that answers on port 9120 is the check for it.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/komodo` | Holds |
| --- | --- |
| `komodo-keys` | Core's keypair, which every Periphery trusts |
| `postgres-data` | The live database |
| `postgres-backup-data` | The dumps |
| `komodo-secrets` | `core.config.toml` |

All four are on the [persistent disk](../../tools/glossary.md#persistent-disk), so they survive a rebuild of the VM. See [What to keep safe](../hosts/km01-komodo.md#keep) for what losing each one costs.

`komodo-cache` holds clones of repos, which Core makes again when they are missing.
