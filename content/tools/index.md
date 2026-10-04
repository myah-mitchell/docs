# Tools

A primer for each tool the fleet is built from, and how-tos for the changes you make with it. The [build guide](../fleet-bootstrap/index.md) tells you what to do and links here for why it works.

Every primer has the same sections: what the tool is, the ideas you need, how the fleet uses it, how to find your way around, how to make a change, and what to check when it goes wrong. The first three are what the build guide assumes, and it links to them where each tool first appears. Come back for the rest when you have something to change.

A how-to is one task from start to finish. Each one carries a status line, since none has been run against a live fleet yet, and lists what is still unconfirmed at its end.

For a single term, see the [glossary](glossary.md). For how the tools fit together, see [The fleet at a glance](../fleet-bootstrap/concepts/the-fleet-at-a-glance.md).

## Building a host {#building}

These tools take a host from nothing to running containers.

| Tool | Its job | How-tos |
| --- | --- | --- |
| [OpenTofu](opentofu/index.md) | Creates the VM in Proxmox | [Reading a plan before applying](opentofu/read-a-plan.md), [Changing a VM's CPU or memory](opentofu/resize-a-vm.md), [Removing a VM](opentofu/remove-a-vm.md) |
| [NixOS](nixos/index.md) | The operating system, built from a description | [Changing a host's setting](nixos/change-a-host-setting.md), [Opening a firewall port](nixos/open-a-firewall-port.md), [Adding a module to the flake](nixos/add-a-module.md) |
| [Ansible](ansible/index.md) | Runs the other tools in order | [Running part of a run](ansible/run-part-of-a-run.md), [Adding a variable to the inventory](ansible/add-an-inventory-variable.md), [Reading a failed run](ansible/read-a-failed-run.md) |
| [Semaphore UI](semaphore/index.md) | Starts runs from a web page and keeps their history | [Adding a Task Template](semaphore/add-a-template.md), [Reading a task's log](semaphore/read-a-task-log.md) |
| [sops with age](sops/index.md) | Keeps secrets in git, encrypted | [Adding a secret for the hosts](sops/add-a-secret.md) |

## Running containers {#containers}

| Tool | Its job | How-tos |
| --- | --- | --- |
| [Docker Compose](docker-compose/index.md) | Defines a set of containers in a file | [Looking inside a stack on a host](docker-compose/inspect-a-stack.md) |
| [Komodo](komodo/index.md) | Deploys the stacks to every host | [Adding a stack to a host](komodo/add-a-stack-to-a-host.md), [Writing a new stack](komodo/write-a-new-stack.md), [Updating a container image](komodo/update-an-image.md) |

## Serving what runs {#serving}

| Tool | Its job | How-tos |
| --- | --- | --- |
| [Traefik](traefik/index.md) | Routes a hostname to its container, with TLS | [Adding a route to a service](traefik/add-a-route.md), [Publishing a route beyond its VM](traefik/publish-a-route.md) |
| [Authentik](authentik/index.md) | One sign-in for every web interface | [Putting an application behind a sign-in](authentik/protect-an-application.md), [Adding a user and a group](authentik/add-a-user.md), [Signing in to an application with OpenID Connect](authentik/add-an-oidc-application.md) |
| [VictoriaMetrics](victoriametrics/index.md) | Stores metrics and logs, and raises alerts | [Adding a scrape target](victoriametrics/add-a-scrape-target.md), [Adding an alert rule](victoriametrics/add-an-alert-rule.md), [Searching the logs](victoriametrics/search-the-logs.md) |
| [step-ca](step-ca/index.md) | The fleet's own certificate authority | [Trusting the fleet's root certificate](step-ca/trust-the-root.md) |
| [Stalwart](stalwart/index.md) | Mailboxes | [Adding a mailbox](stalwart/add-a-mailbox.md), [Adding a mail domain](stalwart/add-a-mail-domain.md) |

## Defined, not deployed {#not-deployed}

fleet-stacks defines these two stacks, and no host in the build guide runs them. Each primer says what adding it would take.

| Tool | Its job |
| --- | --- |
| [CrowdSec](crowdsec/index.md) | Bans addresses that behave like attackers |
| [Technitium](technitium/index.md) | A DNS server |

## Where to start {#start}

You need not read every primer before you build. If you want to read ahead, follow the order the build guide meets them: Ansible, OpenTofu, NixOS, and sops for the first run, then Docker Compose and Komodo, then Semaphore. Traefik and Authentik come next, when the fleet leaves bootstrap mode. The rest can wait until you build the host that runs them.
