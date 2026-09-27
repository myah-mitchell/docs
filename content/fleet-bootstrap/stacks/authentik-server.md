# authentik-server

authentik-server is Authentik, the fleet's identity provider, with the database, cache, and helpers it needs. It runs on one host, id01. See [Identity (id01)](../hosts/id01-identity.md) for the build.

## What it runs {#services}

--8<-- "generated/authentik-server/services.md"

| Service | Does |
| --- | --- |
| `authentik-server` | Serves the web interface, the API, and the sign-in flows, on port 9000 inside the `proxy` network |
| `authentik-worker` | Runs background tasks: migrations, outgoing mail, outpost management |
| `postgres` | Holds every user, group, application, and flow |
| `postgres-backup` | Dumps the database each day, and keeps 7 daily, 4 weekly, and 6 monthly dumps |
| `redis` | Cache and task queue for the server and the worker |
| `geoipupdate` | Downloads the GeoLite2 City and ASN databases every 8 hours |
| `socket-proxy` | Gives the worker a filtered view of the Docker socket, which it uses to manage outposts |

The project is `authentik`, so the containers are named `authentik-` and the service, such as `authentik-postgres`. The two Authentik containers are `authentik-authentik-server` and `authentik-authentik-worker`.

Postgres, Redis, and the socket proxy sit on networks marked internal. Only `authentik-server` joins `proxy`, where Traefik reaches it.

## Values it reads {#values}

--8<-- "generated/authentik-server/values.md"

The host page says what to put in each and when. See [Stage the values](../hosts/id01-identity.md#values).

id01 blanks the two mail login keys in its inventory entry, because Postfix on ci01 offers no login. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

## What the host needs {#host-setup}

--8<-- "generated/authentik-server/host-setup.md"

The run creates all of it in the provision stage. The stack also needs a Traefik on the same host, which is traefik-bootstrap in bootstrap mode and traefik-agent after it.

## Hostnames {#hostnames}

Traefik routes five names to `authentik-server`. With the host `id01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Comes from |
| --- | --- |
| `auth.myah-mitchell.com` | `AUTHENTIK_SERVICE_NAME`, meant as the public name |
| `authentik.myah-mitchell.com` | `AUTHENTIK_HOSTNAME` on the domain |
| `authentik.home.myah-mitchell.com` | `AUTHENTIK_HOSTNAME` on the sub-domain |
| `authentik.id01.home.myah-mitchell.com` | `AUTHENTIK_HOSTNAME` on the host |

The fifth is the project name on the host, which here is the same as the fourth.

The route uses `chain-no-auth` in both modes. Authentik cannot ask itself for a sign-in.

The container carries no `kop-public` labels, so the route publisher sends none of these names to tf01, and the public name is not reachable from the internet as the repo stands.

A second route answers `/outpost.goauthentik.io/` on any name under the domain. It is what lets an application behind the sign-in chain finish its redirect.

## Verify {#verify}

In Komodo, the `authentik-server` Stack shows as running with seven services.

On the host, list the project's containers:

```bash
docker compose -p authentik ps
```

Every container shows `healthy` in the *STATUS* column. The server's own check asks port 9000 for a page, so `healthy` there means Authentik is answering.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/authentik` | Holds |
| --- | --- |
| `postgres-data` | The live database |
| `postgres-backup-data` | The dumps |
| `authentik-media` | Uploaded icons and images |

All three are on the persistent disk, so they survive a rebuild of the VM. `AUTHENTIK_SECRET_KEY` has to survive with them, since a database restored under a different key cannot be read.
