# traefik-basic

traefik-basic is Traefik with the four helpers it needs, and nothing that depends on another host. It is a building block. No host lists it, and [traefik-agent](traefik-agent.md) includes it and adds the route publisher.

Every Traefik stack in the fleet runs the five services on this page, so the other Traefik pages describe only what they add.

## What it runs {#services}

--8<-- "generated/traefik-basic/services.md"

| Service | Does |
| --- | --- |
| `traefik` | Terminates TLS and routes requests to the containers on the `proxy` network |
| `error-pages` | Serves the page for any response from 400 to 599, and answers a hostname no route matches |
| `socket-proxy` | Gives Traefik a filtered, read-only view of the Docker API, which is how it finds containers |
| `socket-proxy-rw` | A second proxy that also allows `POST`, for logrotate alone |
| `logrotate` | Rotates Traefik's access log, then signals Traefik to open a new file |

The project is `traefik` in every Traefik stack, so the containers have the same names on every host: `traefik-traefik`, `traefik-error-pages`, and so on. A host runs one Traefik stack, so the names never collide.

Traefik publishes three ports on the host.

| Port | Entrypoint | Serves |
| --- | --- | --- |
| 80 | `http` | A redirect to HTTPS, for every request |
| 443 | `https` | Every application route |
| 8443 | `dashboard` | Traefik's own dashboard |

logrotate checks the log every five minutes. It rotates weekly, or sooner when the file reaches 50 MB, and keeps three old copies.

## The rules it ships with {#rules}

Traefik reads its middlewares and TLS options from files in `containers/traefik/rules` in fleet-stacks. A route names one of two chains.

| Chain | Applies |
| --- | --- |
| `chain-no-auth@file` | Rate limiting, secure headers, and compression |
| `chain-authentik@file` | The same three, then a forward to Authentik for a sign-in |

The forward goes to the host named in `AUTHENTIK_HOST`. The rate limit is an average of 100 requests a second, with a burst of 50.

A stack picks its chain through `TRAEFIK_AUTH_CHAIN`, and a blank value takes `chain-authentik@file`. See [Bootstrap mode](../concepts/bootstrap-mode.md#changes) for when the run sets it.

## Values it reads {#values}

--8<-- "generated/traefik-basic/values.md"

All five are created before the first host is built. See [the Traefik values](../foundation/komodo-setup.md#traefik).

`CROWDSEC_LAPI_HOST` is carried and not used. The bouncer plugin's lines are commented out in the Traefik service.

## What the host needs {#host-setup}

--8<-- "generated/traefik-basic/host-setup.md"

The log folder is mode `0755` because logrotate refuses to rotate a file inside a folder that a group can write to.

system-agent's vector reads the access log from that same folder. See [system-agent](system-agent.md#services).

## Hostnames {#hostnames}

The dashboard answers on port 8443 only. With the host `id01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, its names are:

| Hostname | Comes from |
| --- | --- |
| `traefik.id01.home.myah-mitchell.com` | `TRAEFIK_HOSTNAME` on the host |
| `id01.home.myah-mitchell.com` | The host's own name |

The dashboard route uses the chain in `TRAEFIK_AUTH_CHAIN`, as every application route does.

## How the Traefik stacks build on it {#chain}

| Stack | Is |
| --- | --- |
| traefik-basic | The five services above |
| [traefik-agent](traefik-agent.md) | traefik-basic and traefik-kop |
| [traefik-server](traefik-server.md) | traefik-agent and the Redis every host publishes to |
| [traefik-dmz](traefik-dmz.md) | traefik-agent, a replica of that Redis, and cloudflared |

[traefik-bootstrap](traefik-bootstrap.md) is outside the chain. It defines the same five services itself, under a second name for the Traefik service, which is how it gets different values in its `komodo.env`.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/traefik` | Holds |
| --- | --- |
| `traefik-certs` | `acme.json`, with the Let's Encrypt account and every certificate issued to it |

Losing the file costs a new certificate request on the next start, which counts against Let's Encrypt's rate limits.
