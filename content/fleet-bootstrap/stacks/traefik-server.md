# traefik-server

traefik-server is the fleet's Traefik hub. It is traefik-agent with a Redis beside it, and that Redis is where every other VM's traefik-kop publishes its routes. It runs on one host, tf01. See [Traefik hub (tf01)](../hosts/tf01-traefik-hub.md) for the build.

## What it runs {#services}

--8<-- "generated/traefik-server/services.md"

The first six are traefik-agent, included whole. See [traefik-agent](traefik-agent.md#services) and [traefik-basic](traefik-basic.md#services) for what each does.

| Service | Does |
| --- | --- |
| `redis` | Holds the routes every traefik-kop in the fleet publishes. It asks for a password and publishes port 6379 on the host |

The hub's Traefik has one thing turned on that a VM's own Traefik does not: the Redis provider, which reads those routes. The stack sets `TRAEFIK_REDIS_ENDPOINTS` to `redis:6379` to turn it on. See [The Redis provider](../concepts/bootstrap-mode.md#redis-provider).

tf01's own traefik-kop publishes to the same Redis, through the host's published port.

The containers are named after the project, `traefik`, as in every Traefik stack. The Redis container is `traefik-redis`.

## In bootstrap mode {#bootstrap}

The stack is a Traefik already, so the run keeps it and adds no stand-in. It gets its certificate from Let's Encrypt in either mode. The run sets `TRAEFIK_AUTH_CHAIN` to `chain-no-auth@file` while tf01 is in bootstrap mode, so the dashboard has no sign-in until the fleet leaves it. See [What it changes](../concepts/bootstrap-mode.md#changes).

## Values it reads {#values}

--8<-- "generated/traefik-server/values.md"

All seven are created before the first host is built. See [the Traefik values](../foundation/komodo-setup.md#traefik).

`REDIS_PASSWORD` has three readers here: Redis sets it as its own password, traefik-kop signs in with it, and Traefik's Redis provider does the same. `REDIS_SERVER` is the name traefik-kop dials, which is tf01's own.

## What the host needs {#host-setup}

--8<-- "generated/traefik-server/host-setup.md"

The host's firewall opens port 6379 to the internal subnet and to nothing else. Redis holds the routing of the whole fleet, and on that subnet the password is all that guards it.

## Hostnames {#hostnames}

The dashboard answers on port 8443, under the same two names as in every Traefik stack. See [traefik-basic](traefik-basic.md#hostnames).

## Verify {#verify}

In Komodo, the `traefik-server` Stack shows as running with seven services.

On the host, list the project's containers:

```bash
docker compose -p traefik ps
```

Every container shows `healthy` in the *STATUS* column.

Ask Redis for an answer, with the value of the Komodo Secret `TRAEFIK_KOP_REDIS_PASSWORD`:

```bash
read -rs -p "Redis password: " redisPassword; echo
docker exec -e REDISCLI_AUTH="$redisPassword" traefik-redis redis-cli ping
```

The command prints `PONG`.

Open the dashboard in a browser:

```text
https://traefik.tf01.home.myah-mitchell.com:8443
```

The browser shows no certificate warning. Under *HTTP Routers*, a route published by another VM shows Redis as its provider.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/traefik` | Holds |
| --- | --- |
| `traefik-certs` | `acme.json`, with the Let's Encrypt account and every certificate issued to it |

Redis has no folder on the host, so its contents go when the container is replaced. Nothing in it is original. Every route comes from a container's labels on some VM.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- Port 6379 from outside the internal subnet. Docker publishes a port through rules of its own, and whether the host's rule is what limits a published port has not been tried.
- The Redis health check. It sends a write with no password, which a Redis that asks for one refuses. If the check fails on that refusal, the container shows as unhealthy while working.
- How soon the routes return after Redis is replaced. traefik-kop looks for changes every ten seconds, and whether it writes again when nothing has changed has not been tried.
