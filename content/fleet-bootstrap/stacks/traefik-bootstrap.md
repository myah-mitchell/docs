# traefik-bootstrap

traefik-bootstrap is a Traefik that needs nothing from another host. It stands in for [traefik-agent](traefik-agent.md) on a host in bootstrap mode, so that the host's web interfaces answer on their real hostnames before Authentik and the Traefik hub exist.

No host lists it. The inventory lists traefik-agent, and the run swaps this stack in while the host is in bootstrap mode. See [What it changes](../concepts/bootstrap-mode.md#changes).

## What it runs {#services}

--8<-- "generated/traefik-bootstrap/services.md"

These are the same five services as traefik-basic, from the same definitions. See [traefik-basic](traefik-basic.md#services) for what each does and the ports Traefik publishes.

traefik-kop is the one service of traefik-agent that is missing. A host on traefik-bootstrap publishes no route to tf01 and is reached only through its own Traefik.

The Stack in Komodo carries the host's name, such as `traefik-bootstrap-id01`. The project is `traefik`, as in every Traefik stack, so the containers are named `traefik-traefik`, `traefik-error-pages`, and so on.

## How it differs from the real Traefik {#differences}

Three values in its `komodo.env` make the whole difference: the TLS options, a blank certificate resolver, and the chain with no sign-in. See [How traefik-bootstrap differs from the real Traefik](../concepts/bootstrap-mode.md#traefik) for the values and why each is needed.

The result for the reader is a certificate the browser warns about and no sign-in in front of any web interface. See [What you see in bootstrap mode](../concepts/bootstrap-mode.md#effects).

## Values it reads {#values}

--8<-- "generated/traefik-bootstrap/values.md"

The stack uses none of the five. With no resolver named, nothing asks Cloudflare or Let's Encrypt for anything, and the chain it sets never forwards to Authentik. The references are still in its `komodo.env`, so the values have to exist before the first deploy. See [the Traefik values](../foundation/komodo-setup.md#traefik).

## What the host needs {#host-setup}

--8<-- "generated/traefik-bootstrap/host-setup.md"

The folders and rules are the same as traefik-agent's. A host that leaves bootstrap mode keeps all of them, and the run has nothing new to create for the Traefik that takes over.

## Hostnames {#hostnames}

The dashboard answers on port 8443, under the same two names as in every Traefik stack. See [traefik-basic](traefik-basic.md#hostnames).

Application hostnames do not change when the host leaves bootstrap mode. Only the certificate and the sign-in do.

## Verify {#verify}

In Komodo, the `traefik-bootstrap-<host>` Stack shows as running with five services.

On the host, list the project's containers:

```bash
docker compose -p traefik ps
```

Every container shows `healthy` in the *STATUS* column.

Open the dashboard in a browser, with your host in place of `id01`:

```text
https://traefik.id01.home.myah-mitchell.com:8443
```

--8<-- "certificate-warning.md"

The dashboard loads with no sign-in. Under *HTTP Routers* it lists a route for each web interface the host's other stacks serve.

## Removing it {#removing}

The run never deletes a Stack. After a host leaves bootstrap mode, its traefik-bootstrap Stack is deleted by hand in Komodo, before traefik-agent deploys, because both bind ports 80, 443, and 8443. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

## Not yet confirmed {#unconfirmed}

Traefik serving its self-signed certificate when the resolver name is blank follows its documentation. It has not been checked on a host built by the run. See [Bootstrap mode](../concepts/bootstrap-mode.md#unconfirmed).
