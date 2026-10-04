# traefik-agent

traefik-agent is a VM's own [Traefik](../../tools/traefik/index.md), the reverse proxy that sends each hostname to the right container, with the publisher that offers chosen [routes](../../tools/glossary.md#route) to the rest of the fleet. It runs on every VM that serves a web interface, once the fleet has left [bootstrap mode](#bootstrap).

The Traefik on the VM terminates TLS and asks Authentik for a sign-in itself, so a request for one of the VM's services does not pass through the [hub](../../tools/glossary.md#hub) on tf01.

tf01 and bh01 do not list it. Their stacks, [traefik-server](traefik-server.md) and [traefik-dmz](traefik-dmz.md), include it.

## What it runs {#services}

--8<-- "generated/traefik-agent/services.md"

The first five are traefik-basic, included whole. See [traefik-basic](traefik-basic.md#services) for what each does and the ports Traefik publishes.

| Service | Does |
| --- | --- |
| `traefik-kop` | Copies the routes of labelled containers into the Redis on tf01, where the hub's Traefik reads them |

traefik-kop publishes a route only for a container that carries labels starting `kop-public.traefik.`. A container with the ordinary `traefik.` labels alone stays local to its VM, so reaching the hub is a choice made for each service.

Each published route points back at the service's own name on its VM, such as `ntfy.ci01.home.myah-mitchell.com`. The container sets that with its `kop.bind.ip` label. A container without the label is published at the VM's name, such as `id01.home.myah-mitchell.com`. traefik-kop reads the Docker socket directly, since it cannot use the socket proxy, and it looks for changes every ten seconds.

The Stack in Komodo carries the host's name, such as `traefik-agent-id01`. The containers are named after the [project](../../tools/glossary.md#project), `traefik`, as in every Traefik stack.

## In bootstrap mode {#bootstrap}

The run leaves traefik-agent out on a host in bootstrap mode, because traefik-kop needs the Redis on tf01. traefik-bootstrap is deployed in its place. See [traefik-bootstrap](traefik-bootstrap.md) and [Bootstrap mode](../concepts/bootstrap-mode.md#changes).

The two never run on one VM together. Both bind ports 80, 443, and 8443. The swap from one to the other is part of [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

## Values it reads {#values}

--8<-- "generated/traefik-agent/values.md"

All seven are created before the first host is built. See [the Traefik values](../foundation/komodo-setup.md#traefik).

| What | Depends on |
| --- | --- |
| The certificate | `CF_API_EMAIL`, `CF_DNS_API_TOKEN`, and `LE_EMAIL`. See [Certificates from Let's Encrypt](../concepts/bootstrap-mode.md#certificates) |
| The sign-in | `AUTHENTIK_HOST`, and Authentik running on id01 |
| Published routes | `REDIS_SERVER` and `REDIS_PASSWORD`, and the Redis running on tf01 |

`TRAEFIK_AUTH_CHAIN` is blank in this stack's `komodo.env`, which takes `chain-authentik@file`.

## What the host needs {#host-setup}

--8<-- "generated/traefik-agent/host-setup.md"

traefik-kop needs no folder and no port of its own. It connects outward to port 6379 on tf01.

## Hostnames {#hostnames}

The dashboard answers on port 8443, under the same two names as in every Traefik stack. See [traefik-basic](traefik-basic.md#hostnames).

## Verify {#verify}

In Komodo, the `traefik-agent-<host>` Stack shows as running with six services.

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p traefik-agent-<host> ps
```

Every container shows `healthy` in the *STATUS* column.

Open the dashboard in a browser, with your host in place of `id01`:

```text
https://traefik.id01.home.myah-mitchell.com:8443
```

The browser shows no certificate warning, and Authentik asks for a sign-in before the dashboard loads.

A warning means Traefik is still serving its self-signed certificate. Look for the resolver's error in Traefik's log:

```bash
docker logs traefik-traefik 2>&1 | grep -i acme
```

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/traefik` | Holds |
| --- | --- |
| `traefik-certs` | `acme.json`, with the Let's Encrypt account and every certificate issued to it |

The published routes are not data to keep. traefik-kop builds them from the containers' labels.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- traefik-kop's health check asks the program for its version. A traefik-kop that cannot reach Redis still shows as healthy, so check its log when a published route is missing on tf01.
