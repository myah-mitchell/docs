# Stacks

A stack is a set of containers that Komodo deploys together, defined in the `stacks/` folder of the docker-stacks repo. These pages are reference: what each stack runs, the values it reads, what it needs on the host, and how to check it. None of them deploys anything. A host gets a stack by listing it under `docker_stacks` in the inventory and being run. See [How a host is built](../concepts/how-a-host-is-built.md).

The tables of services, values, folders, and firewall rules on each page are generated from the docker-stacks repo, so they match what the run does.

## One per host {#per-host}

Each of these is what a specific VM is for.

| Stack | Provides | Host |
| --- | --- | --- |
| [komodo-server](komodo-server.md) | Komodo Core and its database | [km01](../hosts/km01-komodo.md) |
| [semaphore-server](semaphore-server.md) | Semaphore, and the database that holds OpenTofu's state | [ci01](../hosts/ci01-semaphore.md) |
| [victoriametrics-server](victoriametrics-server.md) | Metrics, logs, traces, alerting, and Grafana | [ci01](../hosts/ci01-victoriametrics.md) |
| [core-infra](core-infra.md) | Notifications, the mail relay, and uptime checks | [ci01](../hosts/ci01-core-infra.md) |
| [authentik-server](authentik-server.md) | The identity provider | [id01](../hosts/id01-identity.md) |
| [step-ca-server](step-ca-server.md) | The internal certificate authority | [pk01](../hosts/pk01-certificates.md) |
| [traefik-server](traefik-server.md) | The internal Traefik hub and the Redis every host publishes routes to | [tf01](../hosts/tf01-traefik-hub.md) |
| [traefik-dmz](traefik-dmz.md) | The public edge, with the tunnel to Cloudflare | [bh01](../hosts/bh01-dmz-edge.md) |
| [stalwart-server](stalwart-server.md) | Mailboxes for the domain. Optional | [mx01](../hosts/mx01-mail.md) |

## One per VM {#per-vm}

| Stack | Provides | Runs on |
| --- | --- | --- |
| [system-agent](system-agent.md) | Metrics, logs, container DNS, and a Dozzle agent | Every VM but ci01, which has the collectors in victoriametrics-server |
| [traefik-agent](traefik-agent.md) | The VM's own Traefik, and the route publisher | Every VM that serves a web interface, outside bootstrap mode |
| [traefik-bootstrap](traefik-bootstrap.md) | A stand-in Traefik with no dependency on another host | Every VM that serves a web interface, in bootstrap mode |

Komodo wants Stack names unique, so the Stack for one of these carries the host's name on the end, such as `system-agent-id01`. Container and network names come from the project name and do not change.

traefik-agent and traefik-bootstrap both bind ports 80, 443, and 8443, so a VM runs one or the other. The inventory always lists traefik-agent, and the run swaps in traefik-bootstrap while the host is in bootstrap mode. See [Bootstrap mode](../concepts/bootstrap-mode.md).

## Building blocks {#layers}

These are pulled into the stacks above through Compose `include`. Each works as a stack on its own, but no host in the plan lists one.

| Stack | Provides | Included by |
| --- | --- | --- |
| [traefik-basic](traefik-basic.md) | Traefik, its error pages, and its socket proxies | traefik-agent |
| [victoriametrics-agent](victoriametrics-agent.md) | The metric and log collectors | victoriametrics-server |
| [dozzle-agent](dozzle-agent.md) | The Dozzle agent | dozzle-server |

traefik-agent is a building block as well as a stack of its own. traefik-server and traefik-dmz include it, so tf01 and bh01 do not list it.

## Not in the plan {#unused}

| Stack | Provides | Why no host lists it |
| --- | --- | --- |
| [dozzle-server](dozzle-server.md) | A log viewer for every VM's Dozzle agent | No host chosen yet |
| [crowdsec-server](crowdsec-server.md) | The CrowdSec local API | Cloudflare and the network's own intrusion detection cover the same ground |
| [crowdsec-agent](crowdsec-agent.md) | A CrowdSec log processor | The same |
| [technitium-server](technitium-server.md) | A DNS server | dockns writes records to the network's own DNS |

The folders stay in the repo because the container definitions still work. Use one on a host of your own the way [Applications (ap01)](../hosts/ap01-applications.md) describes.

## Starting a new stack {#template}

The repo's `template` stack defines the four standard networks (`proxy`, `frontend`, `backend`, and `socket_proxy`) and no services. Copy it to start a stack of your own. See [Applications (ap01)](../hosts/ap01-applications.md#new-stack).
