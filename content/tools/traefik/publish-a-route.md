# Publishing a route beyond its VM

This page offers a service's route to the Traefik hub on tf01 and to the edge on bh01, so the service can be reached through a host other than its own. Do it for a service that needs a name served by the hub, or one that is to be reached from the internet.

The change is a second set of labels on the container, in the fleet-stacks repo. traefik-kop on the service's VM reads them and writes the route into the Redis on tf01. See [Publishing a route beyond its VM](index.md#publishing) for how the parts fit.

Status: written, not yet run.

## Prerequisites

- The service has a working route on its own VM. See [Adding a route to a service](add-a-route.md).
- The fleet has left bootstrap mode. A host on the stand-in runs no traefik-kop and publishes nothing. See [Bootstrap mode's stand-in](index.md#bootstrap).
- The service's host runs traefik-agent, and tf01 is built.
- The value of the Komodo Secret `TRAEFIK_KOP_REDIS_PASSWORD`, for the check on tf01.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<image>` | The container's folder under `containers/`, such as `ntfy` |
| `<key-prefix>` | The prefix of the container's keys, such as `NTFY` |
| `<project>` | The project name of the stack that runs it, such as `core` |
| `<stack>` | That stack's folder under `stacks/`, such as `core-infra` |
| `<host>` | The host that runs the stack, such as `ci01` |

## What publishing reaches {#reach}

Publishing has one switch, and it does not choose between the hub and the edge. Every published route is in tf01's Redis, and bh01's Redis copies all of it, so both Traefiks hold the route.

| To be reached | The route needs | And also |
| --- | --- | --- |
| Through the hub on tf01 | The `kop-public` labels | An internal DNS record that points the name at tf01 |
| From the internet | The `kop-public` labels, with the public name in the rule | The name under `ingress` on bh01, and its DNS record in Cloudflare |

Holding a route does not expose it. A request only arrives at a Traefik when DNS sends the name there, and the tunnel on bh01 passes only the hostnames listed in cloudflared's config. See [The edge on bh01 and the tunnel](index.md#edge).

## 1. Add the kop-public labels {#labels}

In `containers/<image>/compose.yaml`, add these labels below the container's `traefik.` labels. They are the ones ntfy's container carries, with the names made general:

```yaml
      ## Traefik-KOP Labels
      - "kop-public.traefik.enable=true"
      - "kop-public.traefik.http.routers.$PROJECT_NAME-<image>-kop-rtr.rule=
        Host(`${<key-prefix>_SERVICE_NAME}.${DOMAIN_NAME}`) ||
        Host(`${<key-prefix>_SERVICE_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`) ||
        Host(`${<key-prefix>_SERVICE_NAME}.${SERVER_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`) ||
        Host(`${<key-prefix>_HOSTNAME}.${SERVER_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`)"
      - "kop-public.traefik.http.routers.$PROJECT_NAME-<image>-kop-rtr.middlewares=chain-no-auth@file"
      - "kop-public.traefik.http.services.$PROJECT_NAME-<image>-kop-svc.loadbalancer.server.url=https://${<key-prefix>_SERVICE_NAME}"
      - "kop.bind.ip=${<key-prefix>_SERVICE_NAME}.${SERVER_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}"
```

| Label | Does |
| --- | --- |
| `kop-public.traefik.enable=true` | Lets traefik-kop publish the container |
| `routers.<name>-kop-rtr.rule` | The hostnames the hub and the edge match |
| `routers.<name>-kop-rtr.middlewares` | The chain the hub and the edge run, from their own rules files |
| `services.<name>-kop-svc.loadbalancer.server.url` | Makes the published service use HTTPS |
| `kop.bind.ip` | The name the published service points at: the service's name on its own VM |

Remove from the rule any name that should not be served elsewhere. The first `Host`, with no sub-domain, is the public name. Leave it out for a route that is to stay internal.

The router's and the service's names end in `-kop-rtr` and `-kop-svc`, so they differ from the local ones. They also have to be unique across the whole fleet, since every VM publishes into one Redis. Two hosts that run the same stack would publish the same names.

<details>
<summary>Background: why the published service points at a name and not at the container</summary>

A local route sends to the container's address on the `proxy` network, which only exists on that VM. The hub is on another host and cannot use it. The container publishes no port on its host either.

The one way in from another host is the VM's own Traefik on port 443. The two service labels make traefik-kop write an HTTPS address built from the service's name on its VM, such as `ntfy.ci01.home.myah-mitchell.com`. That name resolves to ci01, and ci01's Traefik has a local router for it.

The request is therefore routed twice, and it passes through a chain twice: the chain in the `kop-public` label on the hub or the edge, then the chain of the local router on the VM. The sign-in, where there is one, is asked for by the VM's Traefik.

The hub does not check the VM's certificate. The Traefik service sets `--serversTransport.insecureSkipVerify=true`.

</details>

## 2. Add the local name, if it is missing {#local-name}

Check that the local router's rule, in the `traefik.` labels, includes the name `kop.bind.ip` builds:

```yaml
        Host(`${<key-prefix>_SERVICE_NAME}.${SERVER_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`) ||
```

It should also include every name in the published rule. The hub forwards a request with its hostname unchanged, and the VM's Traefik needs a router that matches it. ntfy's local rule and published rule list the same four names for that reason.

## 3. Generate, push, and deploy {#deploy}

Generate the stack's files, commit, push, and deploy the Stack on `<host>`, the same way as for a local route. See [Generate and push](add-a-route.md#build) and [Deploy](add-a-route.md#deploy).

No key is added to any `komodo.env`, so the host's Komodo file does not change.

## 4. Verify the publisher {#verify-kop}

On `<host>`, read the route publisher's log:

```bash
docker logs --tail 20 traefik-traefik-kop
```

The log shows no connection error. traefik-kop looks for changes every ten seconds, and its health check passes even when it cannot reach Redis, so the log is the place to look.

## 5. Verify on tf01 {#verify-hub}

Log in to tf01 and list the published routers in Redis, with the value of `TRAEFIK_KOP_REDIS_PASSWORD`:

```bash
read -rs -p "Redis password: " redisPassword; echo
docker exec -e REDISCLI_AUTH="$redisPassword" traefik-redis \
  redis-cli --scan --pattern 'traefik/http/routers/*'
```

The output includes keys for `<project>-<image>-kop-rtr`.

Then open the hub's dashboard:

```text
https://traefik.tf01.home.myah-mitchell.com:8443
```

Under *HTTP Routers*, the router `<project>-<image>-kop-rtr` is listed with Redis as its provider and no error.

Ask the hub for the service, without changing DNS, from a machine on the internal network. Put the name you published in place of the example:

```bash
curl -sS -o /dev/null -w '%{http_code}\n' \
  --resolve ntfy.home.myah-mitchell.com:443:172.16.7.111 \
  https://ntfy.home.myah-mitchell.com/
```

`--resolve` sends the request to tf01 whatever DNS says. The command prints the status the service itself gives, such as `200`. A `404` means the hub matched no router, and a `502` means the hub could not reach the VM's Traefik.

## 6. Send the name to the hub or the edge {#names}

For a name served by the hub, point its record at tf01 in the DNS server the fleet's machines use.

For a public name, add it to the tunnel on bh01 and create its record in Cloudflare. See [Publishing a hostname](../../fleet-bootstrap/hosts/bh01-dmz-edge.md#publish).

> [!WARNING]
> A hostname on the tunnel is on the internet from the moment its DNS record exists. Publish only a service that signs its users in itself, or one whose local route uses the Authentik chain.

## Taking a route back {#unpublish}

Remove the `kop-public` labels and the `kop.bind.ip` label, then generate, push, and deploy again. For a public name, remove its rule from cloudflared's `config.yml` on bh01 and its record in Cloudflare first.

## Not yet confirmed {#unconfirmed}

- The whole page. No route has been published in a running fleet.
- The address traefik-kop writes from `loadbalancer.server.url` and `kop.bind.ip`. The page takes it to be `https://` and the name in `kop.bind.ip`, on port 443. The comments in `containers/template/compose.yaml` say so, and it has not been seen in Redis.
- The layout of the keys in Redis. `traefik/http/routers/` follows the default root key of Traefik's Redis provider.
- Whether traefik-kop removes a route from Redis when its labels go.
- Which internal names the fleet points at tf01. No page or repo file sets that, and every route also answers on its own VM.
- A public route behind `chain-authentik@file`. The sign-in would need Authentik's own name to be reachable from the internet, and authentik-server carries no `kop-public` labels. See [DMZ edge (bh01)](../../fleet-bootstrap/hosts/bh01-dmz-edge.md#unconfirmed).
- Whether bh01's Traefik can read its replica at all. See [traefik-dmz](../../fleet-bootstrap/stacks/traefik-dmz.md#unconfirmed).
