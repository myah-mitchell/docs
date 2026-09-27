# Identity (id01)

id01 runs Authentik, the fleet's identity provider. Once the fleet leaves bootstrap mode, every other stack's web interface asks Authentik for a sign-in first, so id01 is the first host built after the foundation.

Its own stack is [authentik-server](../stacks/authentik-server.md). Authentik cannot sit behind Authentik, so its route never asks for a sign-in, in either mode.

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- Postfix on ci01 accepts mail from the internal subnet. See [Core infrastructure (ci01)](ci01-core-infra.md#verify).
- A MaxMind account, for the free GeoLite2 databases. [Step 2](#values) says what happens without one.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add id01 to the `docker_host` group:

```yaml
    id01:
      ansible_host: 192.0.2.13
      serverHostname: "id01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - authentik-server
      komodo_stack_env:
        authentik-server:
          AUTHENTIK_EMAIL__USERNAME: ""
          AUTHENTIK_EMAIL__PASSWORD: ""
```

--8<-- "bootstrap-mode-stacks.md"

The two blank keys remove a login Authentik would otherwise try against Postfix, which offers none. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  id01 = {
    server       = "vh01"
    vm_id        = 7013
    cores        = 4
    memory_mb    = 8192
    vlan_id      = 7
    ipv4_address = "192.0.2.13/24"
    ipv4_gateway = "192.0.2.1"
    dns_servers  = ["192.0.2.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

Authentik's worker is what the four cores and 8 GB are for, with Postgres beside it. The database holds every user, group, application, and flow, and 20 GB is plenty for it.

id01 is on the internal VLAN. Anything the internet is to reach goes through the tunnel on bh01, never through id01 itself.

Then generate id01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 2. Stage the values {#values}

Create these in Komodo before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

### Authentik's own {#values-authentik}

| Name | Kind | Value |
| --- | --- | --- |
| `AUTHENTIK_SECRET_KEY` | Secret | 96 alphanumeric characters |
| `AUTHENTIK_POSTGRES_USER` | Secret | Your choice |
| `AUTHENTIK_POSTGRES_PASSWORD` | Secret | 48 alphanumeric characters |

Generate the two long values in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 96; echo
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48; echo
```

> [!WARNING]
> `AUTHENTIK_SECRET_KEY` signs sessions and encrypts what Authentik stores. Changing it later ends every session and makes every stored credential unreadable. Keep a copy in your password manager.

### MaxMind {#values-maxmind}

| Name | Kind | Value |
| --- | --- | --- |
| `GLOBAL_GEOIPUPDATE_ACCOUNT_ID` | Secret | Your MaxMind account ID |
| `GLOBAL_GEOIPUPDATE_LICENSE_KEY` | Secret | A licence key created in that account |

Without an account, create both with the value `unused`, so that the references resolve. geoipupdate then fails to sign in, and nothing else in the stack reads its databases. What that does to the run is [not yet confirmed](#unconfirmed), so the account is the safer choice.

### Mail {#values-mail}

Authentik sends its mail through Postfix on ci01. These five are settings, so leave **Is Secret** unticked.

| Name | Value |
| --- | --- |
| `GLOBAL_EMAIL_HOST` | ci01's address, `192.0.2.12` in these pages |
| `GLOBAL_EMAIL_PORT` | `25` |
| `GLOBAL_EMAIL_TLS` | `false` |
| `GLOBAL_EMAIL_SSL` | `false` |
| `GLOBAL_EMAIL_FROM` | The address service mail is sent as, such as `authentik@myah-mitchell.com` |

The sender's domain has to be one Postfix on ci01 accepts, which is the fleet's own domain unless you changed `POSTFIX_ALLOWED_SENDER_DOMAINS`. TLS stays off because the connection never leaves the internal network. Postfix applies TLS itself when it hands the mail to your relay.

`GLOBAL_AUTHENTIK_HOST` exists already, from [Setting up Komodo](../foundation/komodo-setup.md#traefik).

## 3. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `id01`.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=id01
```

///

The run creates the VM, installs NixOS on it, deploys its configuration, and has Komodo deploy two Stacks: `traefik-bootstrap-id01` and `authentik-server`.

Authentik's first start is slow. It runs its whole database migration before the server answers, and the worker restarts a few times while Postgres comes up. The run waits up to fifteen minutes for a host's Stacks.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/traefik-bootstrap/manual.md"

--8<-- "generated/authentik-server/manual.md"

--8<-- "manual-stack-deploy.md"

</details>

## 4. Verify {#verify}

--8<-- "verify-run.md"

The `authentik-server` Stack has seven services:

--8<-- "generated/authentik-server/services.md"

## 5. Create the admin account {#first-access}

Open Authentik's setup flow in a browser:

```text
https://authentik.id01.home.myah-mitchell.com/if/flow/initial-setup/
```

The name needs a DNS record pointing at id01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Enter an email address and a password for the `akadmin` account, and store the password in your password manager. The flow runs one time. A later visit to the same address goes to the normal sign-in page.

This account can grant itself access to anything Authentik guards, which after bootstrap mode is the whole fleet.

| Hostname | Used for |
| --- | --- |
| `authentik.id01.home.myah-mitchell.com` | Reaching Authentik on the internal network |
| `auth.myah-mitchell.com` | The public name. Nothing publishes it yet. See [Not yet confirmed](#unconfirmed) |

Nothing asks Authentik for a sign-in yet. That starts when the fleet leaves bootstrap mode, which is also where each application gets its Provider. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

## What's next

Build pk01, the certificate authority. See [Certificates (pk01)](pk01-certificates.md).

## Not yet confirmed {#unconfirmed}

- The whole page. id01 has not been built by the run.
- The public name. The route publisher sends a route to tf01 only for a container that carries `kop-public` labels, and Authentik's container has none, so `auth.myah-mitchell.com` cannot reach the tunnel on bh01 as the repo stands.
- geoipupdate with the value `unused`. Its health check only asks the program for its version, so a failed download does not show there. If the container exits and restarts instead, the Stack never shows as running, and the run's last wait fails after fifteen minutes with everything else up.
