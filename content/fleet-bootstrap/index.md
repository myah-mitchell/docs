# Fleet bootstrap

These pages build a fleet of Docker hosts on Proxmox, starting with nothing but the Proxmox host. Every VM is created blank by OpenTofu, installed with NixOS from one flake, and given its stacks by Komodo, all in a single ansible run started from Semaphore.

Read [Conventions](https://github.com/myah-mitchell/fleet-stacks/blob/main/docs/conventions.md) first if you have not. Every page here assumes its naming and secrets rules.

## How the section is laid out {#layout}

| Part | Holds | Read it |
| --- | --- | --- |
| [Concepts](concepts/how-a-host-is-built.md) | What the run does, the NixOS flake, the private repo and its secrets, bootstrap mode, the host's layout, and the register of every value | Once, before the first host |
| [The foundation](foundation/index.md) | Proxmox, the installer ISO, km01, ci01, Komodo, and Semaphore, built from a shell | Once, in order |
| Hosts | One page per host, in the order below | One per build |
| [Stacks](stacks/index.md) | Reference for every stack: what it runs, reads, and needs | When you need a fact |
| Procedures | Work that is not tied to one host | When the occasion comes |

## Running order {#running-order}

| Order | Page | Builds | Status |
| --- | --- | --- | --- |
| 1 | [The control shell](foundation/control-shell.md) | The first control node, the age keys, and the private repo's first contents | Written, not yet run |
| 2 | [Proxmox and the installer ISO](foundation/proxmox-and-installer.md) | The installer ISO and the API token | Written, not yet run |
| 3 | [The first run](foundation/first-run.md) with [Komodo (km01)](hosts/km01-komodo.md) | km01 and Komodo Core | Written, not yet run |
| 4 | [Setting up Komodo](foundation/komodo-setup.md) | Komodo's users, keys, sync, and first values | Written, not yet run |
| 5 | [Automation and monitoring (ci01)](hosts/ci01-automation.md) | ci01 and its three stacks | Written, not yet run |
| 6 | [The Semaphore project](foundation/semaphore-project.md) | Semaphore's Project and the **site** Template | Written, not yet run |
| 7 | [The handover](foundation/handover.md) | Semaphore as the control node | Written, not yet run |
| 8 | [Identity (id01)](hosts/id01-identity.md) | Authentik | Written, not yet run |
| 9 | [Certificates (pk01)](hosts/pk01-certificates.md) | step-ca | Written, not yet run |
| 10 | [Traefik hub (tf01)](hosts/tf01-traefik-hub.md) | The internal hub and its Redis | Written, not yet run |
| 11 | [DMZ edge (bh01)](hosts/bh01-dmz-edge.md) | The public edge and the tunnel | Written, not yet run |
| 12 | [Leaving bootstrap mode](procedures/leave-bootstrap-mode.md) | The real Traefik, sign-in, and telemetry on every host | Written, not yet run |
| 13 | [Mail (mx01)](hosts/mx01-mail.md) | Mailboxes. Optional | Written, not yet run |
| 14 | [Applications (ap01)](hosts/ap01-applications.md) | A host of your own, as a worked example | Written, not yet run |

Rows 1 to 7 are the foundation, and [The foundation](foundation/index.md) explains why they come in that order. From row 8 on, every host is one run of the **site** Template.

ci01 has three more pages, one for each of its stacks: [Semaphore](hosts/ci01-semaphore.md), [VictoriaMetrics](hosts/ci01-victoriametrics.md), and [Core infrastructure](hosts/ci01-core-infra.md). The ci01 page sends you through them.

id01 comes before pk01, tf01, and bh01 because the others can wait. Nothing asks Authentik for a sign-in, and nothing publishes a route to tf01, until the fleet leaves bootstrap mode. bh01 needs tf01 first, because its Redis replicates tf01's.

The fleet leaves bootstrap mode at row 12, with every host it was waiting for up. mx01 and ap01 are built after that, in normal mode, as any host added later is.

mx01 is optional and nothing else depends on it. The service mail every stack sends goes through Postfix on ci01.

## What the statuses mean {#statuses}

"Written, not yet run" means the page was assembled from the playbooks, the flake, the compose files, and the generated facts, and checked against them. Nobody has followed it against a real host, and every page has that status. Treat every UI label and every wait in such a page as needing confirmation, and correct the page as you go.

Each page lists what it could not confirm under *Not yet confirmed*.

## Bootstrap mode {#bootstrap-mode}

Most stacks expect three things another host provides: a sign-in from Authentik on id01, a telemetry backend on ci01, and the hub on tf01. None exists when the first hosts are built.

The fleet starts in bootstrap mode, where each host runs a stand-in Traefik that depends on no other host, and leaves the mode in one procedure when the hosts it was waiting for are up. See [Bootstrap mode](concepts/bootstrap-mode.md).

## Procedures {#procedures}

| Page | Covers |
| --- | --- |
| [Adding a host](procedures/add-a-host.md) | The short form of every host page, for a host of your own |
| [Leaving bootstrap mode](procedures/leave-bootstrap-mode.md) | Moving every host to the real Traefik, the sign-in chain, and telemetry |
| [Deploying a stack by hand](procedures/deploy-a-stack-by-hand.md) | Creating a Stack in Komodo without the run |
| [Rebuilding a VM](procedures/rebuild-a-vm.md) | Installing a host again and keeping its persistent disk |
| [Growing a disk](procedures/grow-a-disk.md) | Making a host's disk larger |
| [Updating the fleet](procedures/update-the-fleet.md) | Moving the hosts to newer versions of NixOS and its packages |

## What is not covered {#not-covered}

These pages build the fleet's VMs. They do not install Proxmox itself, and they do not cover a backup server or any other machine that is not one of these VMs.

[Conventions](https://github.com/myah-mitchell/fleet-stacks/blob/main/docs/conventions.md) and [Project layout](https://github.com/myah-mitchell/fleet-stacks/blob/main/scripts/project-layout.md) describe the fleet-stacks repo itself, so they stay in that repo.
