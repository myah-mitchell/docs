# traefik-dmz

traefik-dmz is the fleet's public edge. It is traefik-agent with a replica of the hub's Redis and a Cloudflare Tunnel connector, so the internet reaches the fleet through an outbound connection and no forwarded port. It runs on one host, bh01. See [DMZ edge (bh01)](../hosts/bh01-dmz-edge.md) for the build.

## What it runs {#services}

--8<-- "generated/traefik-dmz/services.md"

The first six are traefik-agent, included whole. See [traefik-agent](traefik-agent.md#services) and [traefik-basic](traefik-basic.md#services) for what each does.

| Service | Does |
| --- | --- |
| `redis` | A read-only replica of the Redis on tf01. It publishes no port |
| `cloudflared` | Holds the tunnel open to Cloudflare, and hands each public request to this stack's Traefik |

A public request takes this path: Cloudflare, the tunnel, cloudflared, Traefik on bh01, then the route Traefik finds for the hostname. Traefik reads its routes from the local replica, through the Redis provider. See [The Redis provider](../concepts/bootstrap-mode.md#redis-provider).

The replica means the edge keeps the routes it last saw when tf01 is unreachable.

cloudflared runs as a named tunnel with its settings in a file on the host. The public hostnames it accepts are listed in that file, under `ingress`, and are not managed in Cloudflare's dashboard.

The containers are named after the project, `traefik`, as in every Traefik stack. cloudflared's ingress rules depend on that, since each one sends its requests to `traefik-traefik`.

## In bootstrap mode {#bootstrap}

The stack is a Traefik already, so the run keeps it and adds no stand-in. The run sets `TRAEFIK_AUTH_CHAIN` to `chain-no-auth@file` while bh01 is in bootstrap mode. See [What it changes](../concepts/bootstrap-mode.md#changes).

## Values it reads {#values}

--8<-- "generated/traefik-dmz/values.md"

All seven are created before the first host is built. See [the Traefik values](../foundation/komodo-setup.md#traefik).

`REDIS_SERVER` is tf01's name. The replica copies from it, and bh01's traefik-kop publishes to it. `REDIS_PASSWORD` is the password both use there.

cloudflared reads no Variable and no Secret. Its credential is a file on the host.

## What the host needs {#host-setup}

--8<-- "generated/traefik-dmz/host-setup.md"

The run copies the example `config.yml`, which holds a placeholder for the tunnel's ID. Two things are left to you, because they come from your Cloudflare account: the real ID in that file, and the tunnel's credentials file in `cloudflared-secrets`. The host page has the steps. See [DMZ edge (bh01)](../hosts/bh01-dmz-edge.md).

The stack opens no port for Redis. The replica and traefik-kop both connect outward, to port 6379 on tf01.

## Hostnames {#hostnames}

The dashboard answers on port 8443, under the same two names as in every Traefik stack. See [traefik-basic](traefik-basic.md#hostnames).

Public hostnames are the ones listed under `ingress` in cloudflared's `config.yml`. Each needs a DNS record in Cloudflare that points at the tunnel.

## Verify {#verify}

In Komodo, the `traefik-dmz` Stack shows as running with eight services.

On the host, list the project's containers:

```bash
docker compose -p traefik ps
```

Every container shows `healthy` in the *STATUS* column. cloudflared's check passes only while the tunnel has a connection to Cloudflare, so `healthy` there means the tunnel is up.

Ask the replica whether it is in step with tf01:

```bash
docker exec traefik-redis redis-cli info replication
```

The output includes these two lines:

```text
role:slave
master_link_status:up
```

A replica that cannot reach tf01 reports `master_link_status:down` and goes on serving the routes it has.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/traefik` | Holds |
| --- | --- |
| `traefik-certs` | `acme.json`, with the Let's Encrypt account and every certificate issued to it |
| `cloudflared-secrets` | The tunnel's credentials file. Anyone holding it can serve the tunnel's hostnames |
| `cloudflared-config` | `config.yml`, with the tunnel's ID and the public hostnames |

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on a host built by the run.
- The path from bh01 to the Redis on tf01. tf01's firewall rule for port 6379 allows the internal subnet, and bh01 is on the DMZ. The replica and traefik-kop need a rule on tf01 and on the network's firewall that the run does not create.
- Traefik reading the replica. The stack gives Traefik's Redis provider a password, and the replica asks for none. Redis may refuse a sign-in it did not ask for.
- The replica's health check. It sends a write, which a read-only replica refuses.
- The example ingress rule. It sends requests to Traefik's port 80, where every request is redirected to HTTPS. A public request may be redirected without end.
- cloudflared before the tunnel exists. With the placeholder still in `config.yml` the container cannot connect, and whether it then keeps the Stack from showing as running has not been tried.
