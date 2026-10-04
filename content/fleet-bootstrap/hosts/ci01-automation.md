# Automation and monitoring (ci01)

ci01 runs what the rest of the fleet is operated with: Semaphore, which runs every build after the handover, the VictoriaMetrics backend every host reports to, and the fleet's notifications, mail relay, and uptime checks. It is the second VM built, and the last one built from the control shell.

One run builds the host and deploys its three stacks. Each stack has a page of its own for its values, its checks, and its first sign-in.

| Stack | Provides | Page |
| --- | --- | --- |
| [semaphore-server](../stacks/semaphore-server.md) | Semaphore, and the database that holds OpenTofu's state | [Semaphore (ci01)](ci01-semaphore.md) |
| [victoriametrics-server](../stacks/victoriametrics-server.md) | Metrics, logs, traces, alerting, and Grafana | [VictoriaMetrics (ci01)](ci01-victoriametrics.md) |
| [core-infra](../stacks/core-infra.md) | Notifications, the mail relay, and uptime checks | [Core infrastructure (ci01)](ci01-core-infra.md) |

ci01's first build is part of the foundation. See [The first run](../foundation/first-run.md#ci01), which sends you to this page and has you follow it to the end.

Status: written, not yet run.

## Prerequisites

- km01 is built and Komodo deploys its own Stack, through [step 5 of The first run](../foundation/first-run.md#km01-full).
- The operational defaults and the Traefik values exist in Komodo, from [Setting up Komodo](../foundation/komodo-setup.md#operational).
- The login of an account at an SMTP relay, such as your mail provider's submission service. [Core infrastructure (ci01)](ci01-core-infra.md#values) says how to run without one.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add ci01 to the `docker_host` group:

```yaml
    ci01:
      ansible_host: 192.0.2.12
      serverHostname: "ci01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - semaphore-server
        - victoriametrics-server
        - core-infra
      komodo_stack_env:
        core-infra:
          POSTFIX_RELAYHOST: "[smtp.myah-mitchell.com]:587"
          POSTFIX_RELAYHOST_USERNAME: "relay@myah-mitchell.com"
```

--8<-- "bootstrap-mode-stacks.md"

victoriametrics-server is the backend alone, so ci01 reports nothing about itself until system-agent is deployed, when the fleet leaves bootstrap mode.

The two Postfix keys say where the fleet's mail is handed on and under which account. Replace both with your relay's, and keep the square brackets. See [Core infrastructure (ci01)](ci01-core-infra.md#values) for what each key does.

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  ci01 = {
    server       = "vh01"
    vm_id        = 7012
    cores        = 4
    memory_mb    = 8192
    vlan_id      = 7
    ipv4_address = "192.0.2.12/24"
    ipv4_gateway = "192.0.2.1"
    dns_servers  = ["192.0.2.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 100 }
    }
  }
```

Semaphore and core-infra are light. victoriametrics-server is what the four cores and 8 GB are for, with seven services that include three databases and Grafana.

The 100 GB disk is for those databases. Metrics are kept for 60 days with no cap on size. Logs and traces are kept for a year, each capped at 5 GB.

ci01's address is long-lived. Every stack that sends mail has it in `GLOBAL_EMAIL_HOST`, and Proxmox sends its notifications to it.

Then generate ci01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 2. Stage the values {#values}

Create every value ci01's stacks read, in Komodo, before the run. Work through these three sections in order, then come back here.

| Section | Creates |
| --- | --- |
| [Semaphore's values](ci01-semaphore.md#values) | Ten Secrets |
| [VictoriaMetrics' values](ci01-victoriametrics.md#values) | Two Variables and one Secret |
| [Core infrastructure's values](ci01-core-infra.md#values) | One Secret |

The run does not check that a value exists. A missing one reaches the container as literal text, and the stack fails in a way that does not name the cause. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

In Komodo, open *Settings > Variables* and search for `SEMAPHORE`, `VMAUTH`, and `POSTFIX` in turn. The three searches list ten, three, and one name.

## 3. Run the build {#run}

On the first build Semaphore does not exist yet, so the run comes from the control shell. Use the **Command line** tab.

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `ci01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, with the environment file loaded.

On the first build, add the option [The first run](../foundation/first-run.md#ci01) gives, which keeps OpenTofu's state in the shell. On any later run, prepare the shell first. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ci01
```

///

The run creates the VM, installs NixOS on it, deploys its configuration, and has Komodo deploy four Stacks: `traefik-bootstrap-ci01`, `semaphore-server`, `victoriametrics-server`, and `core-infra`.

The first deploy pulls about twenty images. The run waits up to fifteen minutes for a host's Stacks, and a run that gives up while images are still downloading passes when run again.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/traefik-bootstrap/manual.md"

--8<-- "generated/semaphore-server/manual.md"

--8<-- "generated/victoriametrics-server/manual.md"

--8<-- "generated/core-infra/manual.md"

--8<-- "manual-stack-deploy.md"

</details>

## 4. Verify {#verify}

--8<-- "verify-run.md"

Then check each stack on its own page, and come back here after each one.

| Stack | Check |
| --- | --- |
| semaphore-server | [Verify Semaphore](ci01-semaphore.md#verify) |
| victoriametrics-server | [Verify VictoriaMetrics](ci01-victoriametrics.md#verify) |
| core-infra | [Verify core infrastructure](ci01-core-infra.md#verify) |

## 5. Sign in and finish each service {#first-access}

Three of the services have no account until you make one, one has a default password to replace, and Semaphore's nix has no sops yet. Do these before moving on.

| Service | What to do |
| --- | --- |
| Semaphore | [Sign in](ci01-semaphore.md#first-access) with the admin account from its Secrets, then [add sops to its nix](ci01-semaphore.md#sops) |
| Grafana | [Sign in and replace the default password](ci01-victoriametrics.md#first-access) |
| ntfy, mailrise, and Uptime Kuma | [Steps 3 to 6 of Core infrastructure](ci01-core-infra.md#ntfy) |

## What's next

On the first build, configure Semaphore to run the playbook the shell has been running. See [The Semaphore project](../foundation/semaphore-project.md).

After the foundation, the next host is id01. See [Identity (id01)](id01-identity.md).

## Not yet confirmed {#unconfirmed}

- The whole page. ci01 has not been built by the run.
- Whether fifteen minutes is enough for the first deploy of all four Stacks on a host with no images. The nix image is among them, and its service copies the whole of `/nix` before Semaphore starts.
- A run from Semaphore that redeploys semaphore-server. See [The handover](../foundation/handover.md#unconfirmed).
