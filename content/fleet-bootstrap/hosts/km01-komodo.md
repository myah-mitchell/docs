# Komodo (km01)

km01 runs [Komodo](../../tools/komodo/index.md) Core, which deploys every [stack](../../tools/glossary.md#stack) in the fleet, its own included. Every other host runs Komodo's agent, Periphery, which connects to Core and does the deploying on its host. See [Core and Periphery](../../tools/glossary.md#core-and-periphery).

km01 is the first VM built, because no other host can be given its stacks until Core is there to deploy them. At the end of this page km01 is a NixOS host that Komodo manages, with Komodo's UI answering on its own hostname.

Its own stack is [komodo-server](../stacks/komodo-server.md). km01's first build is part of the foundation, because Komodo cannot deploy the stack it runs in before it has started. See [The first run](../foundation/first-run.md), which uses this page for [step 1](#describe). Every run after the first is the ordinary one in [step 3](#run).

Status: written, not yet run.

## Prerequisites

- For the first build, the steps of [The first run](../foundation/first-run.md) that come before its link to this page.
- For any later run, a km01 that Komodo already manages.

## 1. Describe the host {#describe}

A host is described in two files of the [private repo](../../tools/glossary.md#private-repo): the [inventory](../../tools/glossary.md#inventory), `hosts.yml`, and OpenTofu's variables file, `opentofu/prod.tfvars`.

### The inventory entry {#describe-inventory}

In `hosts.yml`, add km01 to the `docker_host` group:

```yaml
    km01:
      ansible_host: 172.16.7.101
      serverHostname: "km01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - komodo-server
```

| Key | Holds |
| --- | --- |
| `ansible_host` | The host's address. Ansible connects to it, and the host is given it as its static address |
| `serverHostname` | The hostname the host is given, and the name of its Server in Komodo |
| `docker_stacks` | The stacks the host runs, each by its folder name under `stacks/` in the fleet-stacks repo |

Every host page has an entry of this shape. The later pages explain only what they add to it.

--8<-- "bootstrap-mode-stacks.md"

km01 is the group's first host, so give the group its `vars` with it. Every later host page adds a host and leaves these as they are:

```yaml
docker_host:
  vars:
    NIXOS: true
    network_gateway: "172.16.7.1"
    docker_stacks_internal_subnet: "172.16.7.0/24"
    FIREWALL: true
    DOCKER: true
    KOMODO: true
    NODE_EXPORTER: true
```

| Key | Holds |
| --- | --- |
| `NIXOS` | Marks a host as one the run installs NixOS on |
| `network_gateway` | The gateway of the internal network. A host on another network sets its own |
| `docker_stacks_internal_subnet` | The subnet a port is opened to when a stack opens it to the internal network only |
| `FIREWALL`, `DOCKER`, `KOMODO`, `NODE_EXPORTER` | What every host in the group runs: the firewall, Docker, Periphery, and Node Exporter |

See [Describing a host](../concepts/fleet-private.md#describe) for the keys a host can set beside these.

### The VM entry {#describe-vm}

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  km01 = {
    server       = "vh01"
    vm_id        = 7101
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 7
    ipv4_address = "172.16.7.101/24"
    ipv4_gateway = "172.16.7.1"
    dns_servers  = ["172.16.7.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

[OpenTofu](../../tools/opentofu/index.md) creates the VM in Proxmox from this entry. The file is its [tfvars](../../tools/glossary.md#tfvars) file, and every host page has an entry with these fields.

| Field | Holds |
| --- | --- |
| `server` | The Proxmox server the VM is created on, by its name under `servers` in the same file |
| `vm_id` | The VM's ID in Proxmox. These pages use the VLAN followed by the last part of the address in three digits |
| `cores`, `memory_mb` | The VM's size |
| `vlan_id` | The [VLAN](../../tools/glossary.md#vlan) the VM's network card is on: `7` is the internal network in these pages |
| `ipv4_address`, `ipv4_gateway`, `dns_servers` | The network the installer starts with. The address carries its prefix length here |
| `tags` | Tags shown on the VM in Proxmox, added to the two OpenTofu always sets |
| `extra_disks` | The [persistent disk](../../tools/glossary.md#persistent-disk), always on `scsi2`, with its size in GB |

The OS disk and the Docker disk are not in the entry because their defaults, 20 GB and 40 GB, suit every host in these pages. See [Describing a host](../concepts/fleet-private.md#describe) for the optional fields, and [The Proxmox servers](../concepts/fleet-private.md#servers) for `vh01`.

Core, FerretDB, Postgres, and the backup container are light together, so two cores and 4 GB are enough. Their data and the dumps the backup keeps are small, and 20 GB holds them.

km01's address is long-lived. It is in `komodo_core_address`, which every host's Periphery dials.

<details>
<summary>Background: why the address is written in both files</summary>

The two files are read by different tools at different moments. OpenTofu reads the tfvars entry when it creates the VM, and passes the address to the installer through the VM's [cloud-init](../../tools/glossary.md#cloud-init) drive. That is what lets the run reach a machine with nothing installed on it.

The inventory is what the installed host is built from. NixOS gives the host `ansible_host` as its static address, and ansible connects to the same address.

Nothing copies one file into the other, so the run compares them. It stops when the address, the prefix length, the gateway, or the nameservers differ between the two.

</details>

The first run generates km01's files straight after these entries. After a later change to either entry, generate them again. See [After a change](../concepts/fleet-private.md#after-a-change).

## 2. Stage the values {#values}

A stack takes its settings and credentials from Variables and Secrets held in Komodo, which have to exist before the run that deploys the stack. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

komodo-server reads two Secrets, `KOMODO_DB_USERNAME` and `KOMODO_DB_PASSWORD`. They are the login Core's database was first started with, and Core has to keep presenting the same one.

They are created during the first build, from the file Core was started with. See [the database Secrets](../foundation/komodo-setup.md#komodo).

A later run needs nothing staged.

## 3. Run the build {#run}

For the first build, go back to [The first run](../foundation/first-run.md#km01-vm). The tabs below are for every run after it.

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `km01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=km01
```

///

When a run changes the definition of the `komodo-server` Stack, Komodo redeploys the containers Core runs in. The UI drops for up to a minute, and the run waits for it to come back.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/traefik-bootstrap/manual.md"

--8<-- "generated/komodo-server/manual.md"

### Start Core by hand

Core is the one stack Komodo cannot deploy while Core is down. Start it with Compose, as [The first run](../foundation/first-run.md#start-core) does. On a km01 that has been built before, the environment file is already on the persistent disk, and `build.py` keeps every value that is set in it.

--8<-- "manual-stack-deploy.md"

</details>

## 4. Verify {#verify}

--8<-- "verify-run.md"

The `komodo-server` Stack has four services:

--8<-- "generated/komodo-server/services.md"

Open Komodo through [Traefik](../../tools/traefik/index.md), at `https://komodo.km01.home.myah-mitchell.com`. The name needs a DNS record pointing at km01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

The direct address, `http://172.16.7.101:9120`, keeps working in both modes. It is the one every Periphery and the run itself use.

## What to keep safe {#keep}

Two things on km01's persistent disk cost the most to lose.

| Path | Holds |
| --- | --- |
| `/opt/docker/volumes/komodo/komodo-keys` | Core's keypair. Without it every host has to be onboarded again |
| `/opt/docker/volumes/komodo/komodo-server.env` | The credentials Postgres was first started with, used to start Core by hand on a rebuilt km01 |

Every Variable and Secret in Komodo lives in Core's database, under `postgres-data`, and the backup container writes a dump of it each day to `postgres-backup-data`.

## What's next

On the first build, go back to the page that sent you here: [Proxmox and the installer ISO](../foundation/proxmox-and-installer.md) for the inventory entry, or [The first run](../foundation/first-run.md#describe) for the VM.

ci01 is the host built after km01. See [Automation and monitoring (ci01)](ci01-automation.md).

## Not yet confirmed {#unconfirmed}

- The whole page. km01 has not been built by the run.
- A run that redeploys the `komodo-server` Stack: that Periphery finishes the deploy after Core's container stops, and that the run's wait outlasts the time Core is away. See [The first run](../foundation/first-run.md#unconfirmed).
- Starting Core by hand on a rebuilt km01, from the environment file the persistent disk kept.
