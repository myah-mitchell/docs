# Identity (id01)

id01 runs [Authentik](../../tools/authentik/index.md), the fleet's identity provider: the one place that holds the fleet's users and decides who is signed in. Once the fleet leaves [bootstrap mode](../../tools/glossary.md#bootstrap-mode), every other stack's web interface asks Authentik for a sign-in first, so id01 is the first host built after the foundation.

Its own stack is [authentik-server](../stacks/authentik-server.md). Authentik cannot sit behind Authentik, so its route never asks for a sign-in, in either mode. [Step 5](#first-access) says why.

At the end of this page Authentik is running with one admin account, and nothing uses it yet. Its first start is slow, so allow the run up to a quarter of an hour.

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- The handover cleaned the shell, and describing a host needs the deploy age key. Restore it for steps 1 to 3, as in [Running from a shell again](../foundation/handover.md#shell-runs).
- Postfix on ci01 accepts mail from the internal subnet. See [Core infrastructure (ci01)](ci01-core-infra.md#verify).
- A MaxMind account, for the free GeoLite2 databases. [Step 2](#values) says what happens without one.

## 1. Describe the host {#describe}

In the [private repo](../../tools/glossary.md#private-repo)'s `hosts.yml`, add id01 to the `docker_host` group. The first three keys are the ones [km01's entry](km01-komodo.md#describe-inventory) explains:

```yaml
    id01:
      ansible_host: 172.16.7.131
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

`komodo_stack_env` sets keys of one stack's *Environment* for this host, and here it blanks two. That removes a login Authentik would otherwise try against Postfix, which offers none. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

In `opentofu/prod.tfvars`, add its VM inside `vms`. The fields are the ones [km01's entry](km01-komodo.md#describe-vm) explains:

```hcl
  id01 = {
    server       = "vh01"
    vm_id        = 7131
    cores        = 4
    memory_mb    = 8192
    vlan_id      = 7
    ipv4_address = "172.16.7.131/24"
    ipv4_gateway = "172.16.7.1"
    dns_servers  = ["172.16.7.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

Authentik's worker is what the four cores and 8 GB are for, with Postgres beside it. The database holds every user, group, application, and flow, and 20 GB is plenty for it.

id01 is on the internal VLAN. Anything the internet is to reach goes through the [tunnel](../../tools/glossary.md#tunnel) on bh01, never through id01 itself.

Then generate id01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 2. Stage the values {#values}

Create these in Komodo before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

### Authentik's own {#values-authentik}

| Name | Kind | Value | Used for |
| --- | --- | --- | --- |
| `AUTHENTIK_SECRET_KEY` | Secret | 96 alphanumeric characters | Signing sessions and encrypting what Authentik stores |
| `AUTHENTIK_POSTGRES_USER` | Secret | Your choice | The login of Authentik's database |
| `AUTHENTIK_POSTGRES_PASSWORD` | Secret | 48 alphanumeric characters | The same login |

Generate the two long values in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 96; echo
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48; echo
```

> [!WARNING]
> `AUTHENTIK_SECRET_KEY` signs sessions and encrypts what Authentik stores. Changing it later ends every session and makes every stored credential unreadable. Keep a copy in your password manager.

### MaxMind {#values-maxmind}

The stack's geoipupdate service downloads MaxMind's GeoLite2 databases, which map an address to a country and a city. It signs in to MaxMind with these two.

| Name | Kind | Value |
| --- | --- | --- |
| `GLOBAL_GEOIPUPDATE_ACCOUNT_ID` | Secret | Your MaxMind account ID |
| `GLOBAL_GEOIPUPDATE_LICENSE_KEY` | Secret | A licence key created in that account |

Without an account, create both with the value `unused`, so that the references resolve. geoipupdate then fails to sign in, and nothing else in the stack reads its databases. What that does to the run is [not yet confirmed](#unconfirmed), so the account is the safer choice.

### Mail {#values-mail}

Authentik sends its mail, such as a password reset, through Postfix on ci01. These five say where Postfix is and how to talk to it. They are settings, so leave **Is Secret** unticked.

| Name | Value |
| --- | --- |
| `GLOBAL_EMAIL_HOST` | ci01's address, `172.16.7.121` in these pages |
| `GLOBAL_EMAIL_PORT` | `25` |
| `GLOBAL_EMAIL_TLS` | `false` |
| `GLOBAL_EMAIL_SSL` | `false` |
| `GLOBAL_EMAIL_FROM` | The address service mail is sent as, such as `authentik@myah-mitchell.com` |

The sender's domain has to be one Postfix on ci01 accepts, which is the fleet's own domain unless you changed `POSTFIX_ALLOWED_SENDER_DOMAINS`. TLS stays off because the connection never leaves the internal network. Postfix applies TLS itself when it hands the mail to your relay.

The names start with `GLOBAL_` because they are not Authentik's alone. Any stack that sends mail through Postfix reads the same five.

`GLOBAL_AUTHENTIK_HOST` exists already, from [Setting up Komodo](../foundation/komodo-setup.md#traefik).

## 3. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `id01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

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

Enter **an email address** and **a password** for the `akadmin` account, and store the password in your password manager. The flow runs one time. A later visit to the same address goes to the normal sign-in page.

This account can grant itself access to anything Authentik guards, which after bootstrap mode is the whole fleet.

| Hostname | Used for |
| --- | --- |
| `authentik.id01.home.myah-mitchell.com` | Reaching Authentik on the internal network |
| `auth.myah-mitchell.com` | The public name. Nothing publishes it yet. See [Not yet confirmed](#unconfirmed) |

Nothing asks Authentik for a sign-in yet. That starts when the fleet leaves bootstrap mode, which is also where Authentik gets its first Provider, the object that says how a sign-in is done. One Provider there covers every web interface under the fleet's domain. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

<details>
<summary>Background: why Authentik's own route never asks for a sign-in</summary>

Outside bootstrap mode, a route in the fleet is guarded by [forward auth](../../tools/glossary.md#forward-auth). Before Traefik passes a request to an application, it asks Authentik whether the browser is signed in. When it is not, the browser is sent to Authentik's sign-in page.

That sign-in page is served by Authentik, on this route. If the route were guarded the same way, a browser sent to the sign-in page would be stopped on the way to it and sent to the sign-in page again, with no end.

So Authentik's route uses the chain with no sign-in in both modes, and Authentik guards itself with its own login. That is why the `akadmin` password matters as much as it does. The [auth chain](../../tools/glossary.md#auth-chain) entry says what a chain is.

</details>

## What's next

Build pk01, the certificate authority. See [Certificates (pk01)](pk01-certificates.md).

## Not yet confirmed {#unconfirmed}

- The whole page. id01 has not been built by the run.
- The public name. The route publisher sends a route to tf01 only for a container that carries `kop-public` labels, and Authentik's container has none, so `auth.myah-mitchell.com` cannot reach the tunnel on bh01 as the repo stands.
- geoipupdate with the value `unused`. Its health check only asks the program for its version, so a failed download does not show there. If the container exits and restarts instead, the Stack never shows as running, and the run's last wait fails after fifteen minutes with everything else up.
