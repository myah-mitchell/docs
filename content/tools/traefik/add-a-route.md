# Adding a route to a service

This page gives a container a hostname behind its VM's Traefik, with a certificate and, if you choose, a sign-in. Do it when you add a container that serves a web interface, or when an existing one needs another name or a different chain.

The change is made in the container's Compose file in the fleet-stacks repo. A push, and a deploy of the stack by Komodo, carry it to the host. Traefik itself is never edited or restarted. See [Provider](index.md#providers) for why.

Status: written, not yet run.

## Prerequisites

- The container has a folder under `containers/` in fleet-stacks, and a stack extends it. For a new one, do [Add a stack of your own](../../fleet-bootstrap/hosts/ap01-applications.md#new-stack) first and come back for the labels.
- The host lists traefik-agent in its `docker_stacks`, or is tf01 or bh01. See [The Traefik stacks](index.md#stacks).
- A checkout of fleet-stacks you can push to, on a machine with Python 3 and PyYAML.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<image>` | The container's folder under `containers/`, such as `uptime-kuma` |
| `<key-prefix>` | The prefix of the container's keys, such as `UPTIME_KUMA` |
| `<port>` | The port the application listens on inside the container, such as `3001` |
| `<stack>` | The stack that runs the container, such as `core-infra` |
| `<host>` | The host that runs the stack, such as `ci01` |

## 1. Choose the hostnames {#hostnames}

Decide which names the route answers on. The fleet builds every name from the same four values, so a route written one time works on any host. See [Naming](https://github.com/myah-mitchell/fleet-stacks/blob/main/docs/conventions.md#naming).

| Name | Built as | Use it for |
| --- | --- | --- |
| `uptime-kuma.ci01.home.myah-mitchell.com` | Service, server, sub-domain, domain | Every route. It always means this VM |
| `uptime-kuma.home.myah-mitchell.com` | Service, sub-domain, domain | A service the site has one of |
| `uptime-kuma.myah-mitchell.com` | Service, domain | A service that is published to the internet, and no other |

Keep each name to one level below a name the certificate covers. The certificate has wildcards for the domain, the sub-domain, and the server, and a wildcard covers one level. See [TLS termination and certificate resolvers](index.md#tls).

The container's `komodo.env` holds the two words the names are built from. Check both lines are there:

```text
<key-prefix>_HOSTNAME: <image>
<key-prefix>_SERVICE_NAME: <image>
```

## 2. Join the proxy network {#network}

In `containers/<image>/compose.yaml`, add `proxy` to the service's networks:

```yaml
    networks:
      - proxy
      - frontend
      - backend
```

Traefik reaches a container over the `proxy` network and no other. The stack's own `compose.yaml` has to declare it, as the stack template does:

```yaml
networks:
  proxy:
    name: ${PROXY_NETWORK}
    external: true
```

## 3. Add the labels {#labels}

In the same file, give the service these labels. They are the ones the Uptime Kuma container carries, with the names made general:

```yaml
    labels: ## Traefik Labels
      - "traefik.enable=true"
      - "traefik.docker.network=${PROXY_NETWORK}"
      - "traefik.http.routers.$PROJECT_NAME-<image>-rtr.rule=
        Host(`${<key-prefix>_SERVICE_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`) ||
        Host(`${<key-prefix>_HOSTNAME}.${SERVER_NAME}.${SUB_DOMAIN_NAME}${DOMAIN_NAME}`)"
      - "traefik.http.routers.$PROJECT_NAME-<image>-rtr.middlewares=${TRAEFIK_AUTH_CHAIN:-chain-authentik@file}"
      - "traefik.http.services.$PROJECT_NAME-<image>-svc.loadbalancer.server.port=<port>"
```

| Label | Does |
| --- | --- |
| `traefik.enable=true` | Lets Traefik see the container. Without it the rest are ignored |
| `traefik.docker.network` | Says which of the container's networks Traefik uses to reach it |
| `routers.<name>.rule` | The [router](index.md#routers) and the hostnames it matches |
| `routers.<name>.middlewares` | The [chain](index.md#chains) a request passes through |
| `services.<name>.loadbalancer.server.port` | The [service](index.md#services): the port inside the container |

Start the router's and the service's names with `$PROJECT_NAME`, as the fleet's containers do. A name has to be unique on the VM's Traefik, and two containers that define the same router name cancel each other out.

The labels name no entrypoint and no certificate. The `https` entrypoint is the default and brings TLS with it. See [Entrypoint](index.md#entrypoints).

Leave out `SUB_DOMAIN_NAME` in a third `Host` only for a service you intend to publish to the internet. ntfy's container shows that form.

## 4. Choose the chain {#chain}

Keep the `middlewares` line from step 3 for an interface that should sit behind Authentik's sign-in. The variable takes `chain-authentik@file` when it is blank, and lets bootstrap mode switch the stack to the other chain.

Then give the key a line in `containers/<image>/komodo.env`, so the run can fill it in:

```text
#= Stack Specific Settings
#== Traefik
TRAEFIK_AUTH_CHAIN:
```

For a service that signs its own users in, or one that other machines call, write the other chain as a fixed value and add no key:

```yaml
      - "traefik.http.routers.$PROJECT_NAME-<image>-rtr.middlewares=chain-no-auth@file"
```

> [!WARNING]
> `chain-no-auth@file` puts no sign-in in front of the route. Use it only for a service with a login of its own.

<details>
<summary>Background: which chain the fleet's own containers use</summary>

ntfy, Komodo, Grafana, step-ca, vmauth, Stalwart, and Bulwark fix `chain-no-auth@file`. Each has its own login or token, and several are called by other services, which cannot follow a redirect to a sign-in page. Authentik fixes it too, since nothing can sign in to reach the sign-in.

Uptime Kuma, Mailpit, Semaphore, Dozzle, Technitium, the blackbox exporter, and the VictoriaMetrics interfaces take the variable. Some of those have no login at all, so the chain is the only thing guarding them.

A forward auth sign-in also needs the service to be known to Authentik. In this fleet one Provider covers every interface behind the chain. See [Forward auth](index.md#forward-auth).

</details>

## 5. Declare the need for a Traefik {#needs}

In `containers/<image>/setup.yaml`, say that the container needs a Traefik on its host:

```yaml
needs_host:
  - name: traefik
```

The run reads this to stop when a host lists the stack with no Traefik stack beside it, and to add the stand-in in bootstrap mode. See [What it changes](../../fleet-bootstrap/concepts/bootstrap-mode.md#changes).

## 6. Generate and push {#build}

From the root of the fleet-stacks checkout, generate the stack's files:

```bash
python3 scripts/build.py
```

The output ends with `Build complete.`

Check that Compose accepts the stack:

```bash
docker compose --env-file stacks/<stack>/.env \
  -f stacks/<stack>/compose.yaml config -q
```

The command prints nothing when the stack is valid.

Commit the container's folder and the stack's generated files together, and push. Komodo deploys from the pushed `main` branch.

## 7. Deploy {#deploy}

If a key was added to a `komodo.env`, write the host's Komodo file again first. A new key reaches a Stack only through that file. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `<host>`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The run's last stage has Komodo sync the host's Stacks, and the sync deploys a Stack whose definition changed.

If only labels changed, the Stack's definition in Komodo is the same as before and the sync may leave it alone. In Komodo's UI, open *Resources > Stacks*, open the Stack, and click **Deploy**. Komodo pulls the repo and recreates the container with its new labels.

## 8. Verify {#verify}

The name needs a DNS record pointing at the host, or an entry in your own machine's hosts file.

Open the host's Traefik dashboard:

```text
https://traefik.<host>.home.myah-mitchell.com:8443
```

Under *HTTP Routers*, the new router is listed with its rule and no error. Open it. The middleware shown is the chain you chose, and the service shows one server.

Then open the route itself, with your names in place of the example:

```text
https://uptime-kuma.ci01.home.myah-mitchell.com
```

The browser shows no certificate warning. Behind `chain-authentik@file`, Authentik asks for a sign-in and the application loads after it. Behind `chain-no-auth@file`, the application loads directly.

On a host in bootstrap mode the certificate is self-signed and no chain asks for a sign-in. See [What you see in bootstrap mode](../../fleet-bootstrap/concepts/bootstrap-mode.md#effects).

If the router is missing or the page is wrong, see [When it goes wrong](index.md#troubleshooting).

## What's next

To offer the route to the hub on tf01, or to the internet, see [Publishing a route beyond its VM](publish-a-route.md).

## Not yet confirmed {#unconfirmed}

- The whole page. No route has been added through these steps on a running host.
- Whether the sync redeploys a Stack when only a Compose file in fleet-stacks changed. The page gives the **Deploy** button as the fallback.
- The wording of the dashboard's router page, which follows Traefik's documentation.
- What a browser sees behind `chain-authentik@file` for a service Authentik's Provider does not cover.
