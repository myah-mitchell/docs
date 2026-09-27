# Komodo (km01)

km01 runs Komodo Core, which deploys every stack in the fleet, its own included. Every other host's Periphery connects to it, so it is the first VM built and the one the rest depend on.

Its own stack is [komodo-server](../stacks/komodo-server.md). km01's first build is part of the foundation, because Komodo cannot deploy the stack it runs in before it has started. See [The first run](../foundation/first-run.md), which uses this page for [step 1](#describe). Every run after the first is the ordinary one in [step 3](#run).

Status: written, not yet run.

## Prerequisites

- For the first build, the steps of [The first run](../foundation/first-run.md) that come before its link to this page.
- For any later run, a km01 that Komodo already manages.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add km01 to the `docker_host` group:

```yaml
    km01:
      ansible_host: 192.0.2.11
      serverHostname: "km01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - komodo-server
```

--8<-- "bootstrap-mode-stacks.md"

km01 is the group's first host, so give the group its `vars` with it. Every later host page adds a host and leaves these as they are:

```yaml
docker_host:
  vars:
    NIXOS: true
    network_gateway: "192.0.2.1"
    docker_stacks_internal_subnet: "192.0.2.0/24"
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

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  km01 = {
    server       = "vh01"
    vm_id        = 7011
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 7
    ipv4_address = "192.0.2.11/24"
    ipv4_gateway = "192.0.2.1"
    dns_servers  = ["192.0.2.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

Core, FerretDB, Postgres, and the backup container are light together, so two cores and 4 GB are enough. Their data and the dumps the backup keeps are small, and 20 GB holds them.

km01's address is long-lived. It is in `komodo_core_address`, which every host's Periphery dials.

The first run generates km01's files straight after these entries. After a later change to either entry, generate them again. See [After a change](../concepts/fleet-private.md#after-a-change).

## 2. Stage the values {#values}

komodo-server reads two Secrets, `KOMODO_DB_USERNAME` and `KOMODO_DB_PASSWORD`. They are created during the first build, from the file Core was started with. See [the database Secrets](../foundation/komodo-setup.md#komodo).

A later run needs nothing staged.

## 3. Run the build {#run}

For the first build, go back to [The first run](../foundation/first-run.md#km01-vm). The tabs below are for every run after it.

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `km01`.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

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

Open Komodo through Traefik, at `https://komodo.km01.home.myah-mitchell.com`. The name needs a DNS record pointing at km01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

The direct address, `http://192.0.2.11:9120`, keeps working in both modes. It is the one every Periphery and the run itself use.

## What to keep safe {#keep}

Two things on km01's persistent disk cost the most to lose.

| Path | Holds |
| --- | --- |
| `/opt/docker/volumes/komodo/komodo-keys` | Core's keypair. Without it every host has to be onboarded again |
| `/opt/docker/volumes/komodo/komodo-server.env` | The credentials Postgres was first started with, used to start Core by hand on a rebuilt km01 |

Every Variable and Secret in Komodo lives in Core's database, under `postgres-data`, and the backup container writes a dump of it each day to `postgres-backup-data`.

## What's next

On the first build, go back to [The first run](../foundation/first-run.md#describe) at the step that sent you here.

ci01 is the host built after km01. See [Automation and monitoring (ci01)](ci01-automation.md).

## Not yet confirmed {#unconfirmed}

- The whole page. km01 has not been built by the run.
- A run that redeploys the `komodo-server` Stack: that Periphery finishes the deploy after Core's container stops, and that the run's wait outlasts the time Core is away. See [The first run](../foundation/first-run.md#unconfirmed).
- Starting Core by hand on a rebuilt km01, from the environment file the persistent disk kept.
