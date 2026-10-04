# Variables and Secrets

Every [Komodo](../../tools/komodo/index.md) Variable and Secret the fleet's stacks read, what each one holds, and which stacks read it. Come here from a host page to see what a value is for, or before a deploy to check that nothing is missing.

This page is generated from the `komodo.env` files in fleet-stacks by `scripts/fleet_facts.py` in this repo. Change a description in `scripts/fleet-register.yaml` and run the script again. An edit made here is lost on the next run.

## How a stack gets its values {#how}

A container is configured through environment variables, and a [stack](../../tools/glossary.md#stack) collects the ones its containers read in one place. Each stack in fleet-stacks has a `komodo.env` file, which becomes the Stack's *Environment* in Komodo. A line in it takes its value one of three ways.

| The line reads | Where the value comes from |
| --- | --- |
| `KEY: [[NAME]]` | The Komodo Variable or Secret called `NAME`, filled in by Komodo at deploy time |
| `KEY: value` | fleet-stacks, the same on every host |
| `KEY:` | Nothing. The stack's own default applies, unless the inventory sets the key |

The [inventory](../../tools/glossary.md#inventory) can set any key for one host or for all of them, through `komodo_stack_env`. It also fills in `SERVER_NAME`, `SUB_DOMAIN_NAME`, `DOMAIN_NAME`, and `TRAEFIK_AUTH_CHAIN` by itself. See [The private repo](fleet-private.md#stack-values).

A Secret is a Variable created with **Is Secret** ticked. Komodo hides its value in the UI and in deploy logs. The two resolve the same way, so the *Kind* column below says only how to create each one.

<details>
<summary>Background: why a value is a reference and not written in the file</summary>

fleet-stacks is public, and `komodo.env` is a file in it. A password written there would be published.

A reference keeps the value out of every repo. The file says only that the stack wants the Variable called `NAME`, and the value is typed into Komodo once, where its database holds it. Komodo puts the value in place of the reference as it deploys, so it exists on the host and in Komodo and nowhere else.

A Variable also gives a value one home. A dozen stacks can reference `GLOBAL_PUID`, and changing it is one edit in Komodo followed by a redeploy of the stacks that read it.

</details>

> [!WARNING]
> A reference with nothing behind it reaches the container as the literal text `[[NAME]]`. Komodo does not stop the deploy, and the failure usually surfaces as a type error or a failed login. Create every value a stack reads before the run that deploys it.

## Creating one {#create}

1. In Komodo's UI, open *Settings > Variables* and click **New Variable**.
2. In *Name*, enter **the name** exactly as the table gives it.
3. In *Value*, enter **the value**.
4. Tick **Is Secret** when the table's *Kind* is Secret.
5. Click **Save**. The name appears in the list.

Make a secret in these stacks alphanumeric only: 48 characters for a database password, 96 for any other generated secret. Several stacks put a password straight into a connection URL, where a symbol breaks the URL.

## Blanking a reference {#blanking}

When a host does not use a value its stack references, set that key to blank in the inventory. The reference is then gone from that host's Stack, and no Variable has to exist for it:

```yaml
komodo_stack_env:
  authentik-server:
    AUTHENTIK_EMAIL__USERNAME: ""
    AUTHENTIK_EMAIL__PASSWORD: ""
```

Where a table below gives `unused` as the value, the stack reads the reference on every host and ignores what it holds. Create it with that value once, which costs less than blanking the key on every host.

A host's `komodo_stack_env` replaces a group's. Ansible does not merge the two, so a host that sets its own lists every stack and key it needs. See [The private repo](fleet-private.md#stack-values).

## What Komodo does not hold {#elsewhere}

Komodo holds the values a stack reads and nothing else. The secrets a host's own configuration reads, such as the hash of the account password and the Komodo onboarding key, are in files in the private repo that are encrypted with [sops](../../tools/sops/index.md), and so are the secrets Ansible reads. See [Secrets with sops](secrets-with-sops.md#files).

## Operational defaults {#operational}

Every stack reads these nineteen, so they are created once, in [Setting up Komodo](../foundation/komodo-setup.md#operational), before anything is deployed through Komodo. They are the same values `scripts/base-testing.env` in fleet-stacks uses for local testing. Adjust them to taste.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `GLOBAL_PUID` | Variable | `1000` | Every stack |
| `GLOBAL_PGID` | Variable | `1000` | Every stack |
| `GLOBAL_TZ` | Variable | Your timezone, for example `America/Chicago` | Every stack |
| `GLOBAL_DOCKER_VOLUMES` | Variable | `/opt/docker/volumes` | Every stack |
| `GLOBAL_DOCKER_LOGS` | Variable | `/opt/docker/logs` | Every stack |
| `GLOBAL_PROXY_NETWORK` | Variable | `proxy` | Every stack |
| `GLOBAL_MEM_LIMIT` | Variable | `2G` | Every stack |
| `GLOBAL_MEM_SWAP_LIMIT` | Variable | `2.5G` | Every stack |
| `GLOBAL_MEM_RESERVATION` | Variable | `64M` | Every stack |
| `GLOBAL_PIDS_LIMIT` | Variable | `200` | Every stack |
| `GLOBAL_CPUS_LIMIT` | Variable | `2` | Every stack |
| `GLOBAL_RESTART_GRACE` | Variable | `1m` | Every stack |
| `GLOBAL_RESTART_MODE` | Variable | `unless-stopped` | Every stack |
| `GLOBAL_LOG_MAX_SIZE` | Variable | `10m` | Every stack |
| `GLOBAL_LOG_MAX_FILE` | Variable | `3` | Every stack |
| `GLOBAL_HEALTH_INTERVAL` | Variable | `60s` | Every stack |
| `GLOBAL_HEALTH_TIMEOUT` | Variable | `10s` | Every stack |
| `GLOBAL_HEALTH_RETRIES` | Variable | `5` | Every stack |
| `GLOBAL_HEALTH_START` | Variable | `10s` | Every stack |

## Komodo's database {#komodo}

Komodo Core keeps its data in FerretDB on Postgres. Core is started by hand the first time, from a file that holds these two values, and then takes over its own Stack. The values in Komodo must match the ones in that file, or the first deploy through Komodo locks Core out of its own database. Staged in [Setting up Komodo](../foundation/komodo-setup.md#komodo).

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `KOMODO_DB_USERNAME` | Secret | The username from the first start, for example `komodo-admin` | [komodo-server](../stacks/komodo-server.md) |
| `KOMODO_DB_PASSWORD` | Secret | The password from the first start, 48 alphanumeric characters | [komodo-server](../stacks/komodo-server.md) |

## Traefik {#traefik}

Every Traefik stack carries the same five references, because each is built on the same base service. The two Redis values are read only by the stacks that run traefik-kop or a Redis replica. Staged in [Setting up Komodo](../foundation/komodo-setup.md#traefik), before the first host, because traefik-bootstrap carries the references too.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `CF_API_EMAIL` | Secret | The Cloudflare account email that owns the DNS token | [traefik-agent](../stacks/traefik-agent.md), [traefik-basic](../stacks/traefik-basic.md), [traefik-bootstrap](../stacks/traefik-bootstrap.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `CF_DNS_API_TOKEN` | Secret | A Cloudflare API token, scoped to edit DNS for the zone | [traefik-agent](../stacks/traefik-agent.md), [traefik-basic](../stacks/traefik-basic.md), [traefik-bootstrap](../stacks/traefik-bootstrap.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `LE_EMAIL` | Secret | The address to register the Let's Encrypt account under | [traefik-agent](../stacks/traefik-agent.md), [traefik-basic](../stacks/traefik-basic.md), [traefik-bootstrap](../stacks/traefik-bootstrap.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `GLOBAL_AUTHENTIK_HOST` | Variable | `authentik.id01.home.myah-mitchell.com`, the hostname with no scheme | [traefik-agent](../stacks/traefik-agent.md), [traefik-basic](../stacks/traefik-basic.md), [traefik-bootstrap](../stacks/traefik-bootstrap.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `GLOBAL_CROWDSEC_LAPI_HOST` | Variable | `unused`. CrowdSec was cut from the plan, and the bouncer stays off while `CROWDSEC_LAPI_KEY` is blank | [traefik-agent](../stacks/traefik-agent.md), [traefik-basic](../stacks/traefik-basic.md), [traefik-bootstrap](../stacks/traefik-bootstrap.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `TRAEFIK_KOP_REDIS_SERVER` | Secret | `tf01.home.myah-mitchell.com` | [traefik-agent](../stacks/traefik-agent.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |
| `TRAEFIK_KOP_REDIS_PASSWORD` | Secret | Your choice, alphanumeric only | [traefik-agent](../stacks/traefik-agent.md), [traefik-dmz](../stacks/traefik-dmz.md), [traefik-server](../stacks/traefik-server.md) |

traefik-bootstrap has no certificate resolver and no forward auth, so it carries the first five without using them. The values still have to exist, or the literal `[[...]]` text reaches the container.

## Semaphore {#semaphore}

Read by semaphore-server on ci01. Staged on [Semaphore (ci01)](../hosts/ci01-semaphore.md#values), which also shows how to generate the three keys.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `SEMAPHORE_ADMIN_USER` | Secret | Your choice | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_ADMIN_NAME` | Secret | Your choice | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_ADMIN_EMAIL` | Secret | Your choice | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_ADMIN_PASSWORD` | Secret | Your choice, alphanumeric only | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_COOKIE_HASH` | Secret | The first generated key, 32 random bytes as base64 | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_COOKIE_ENCRYPTION` | Secret | The second generated key | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_ACCESS_KEY_ENCRYPTION` | Secret | The third generated key | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_POSTGRES_USER` | Secret | Your choice | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_POSTGRES_PASSWORD` | Secret | Your choice, alphanumeric only | [semaphore-server](../stacks/semaphore-server.md) |
| `SEMAPHORE_TOFU_STATE_PASSWORD` | Secret | Your choice, alphanumeric only. The `tofu` role's password for the OpenTofu state database | [semaphore-server](../stacks/semaphore-server.md) |

The three keys encrypt what Semaphore stores. Changing one later makes every stored login and access key unreadable, so keep a copy of all three somewhere safe.

## Telemetry {#telemetry}

Every agent sends its metrics, logs, and traces to vmauth on ci01 with this one login, and victoriametrics-server reads the same three to accept it. Staged on [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md#values).

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `GLOBAL_VMAUTH_USER` | Variable | Your choice | [system-agent](../stacks/system-agent.md), [victoriametrics-agent](../stacks/victoriametrics-agent.md), [victoriametrics-server](../stacks/victoriametrics-server.md) |
| `GLOBAL_VMAUTH_PASS` | Secret | Your choice, alphanumeric only | [system-agent](../stacks/system-agent.md), [victoriametrics-agent](../stacks/victoriametrics-agent.md), [victoriametrics-server](../stacks/victoriametrics-server.md) |
| `GLOBAL_VMAUTH_HOST` | Variable | `vmauth.ci01.home.myah-mitchell.com`, the hostname with no scheme | [system-agent](../stacks/system-agent.md), [victoriametrics-agent](../stacks/victoriametrics-agent.md) |

## Mail {#mail-relay}

Postfix on ci01 relays the fleet's service mail. The first value is its login at the upstream relay, staged on [Core infrastructure (ci01)](../hosts/ci01-core-infra.md#values). The rest tell a stack how to reach Postfix. authentik-server is the only stack that reads them today, so they are staged on [Identity (id01)](../hosts/id01-identity.md#values).

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `POSTFIX_RELAYHOST_PASSWORD` | Secret | The password of the account at the upstream relay | [core-infra](../stacks/core-infra.md) |
| `GLOBAL_EMAIL_HOST` | Variable | ci01's address, such as `172.16.7.121` | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_PORT` | Variable | `25` | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_USER` | Variable | Not created. See the note below | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_PASS` | Secret | Not created. See the note below | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_TLS` | Variable | `false` | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_SSL` | Variable | `false` | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_EMAIL_FROM` | Variable | The address service mail is sent as, such as `authentik@myah-mitchell.com` | [authentik-server](../stacks/authentik-server.md) |

Postfix takes mail from the internal subnet with no login, so `GLOBAL_EMAIL_USER` and `GLOBAL_EMAIL_PASS` have nothing to hold, and a made-up value would have the stack try a login Postfix does not offer. A stack that reads them has its two keys set to blank in the inventory instead. See [Blanking a reference](#blanking).

## Authentik {#authentik}

Read by authentik-server on id01. Staged on [Identity (id01)](../hosts/id01-identity.md#values).

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `AUTHENTIK_SECRET_KEY` | Secret | 96 alphanumeric characters of your choice | [authentik-server](../stacks/authentik-server.md) |
| `AUTHENTIK_POSTGRES_USER` | Secret | Your choice | [authentik-server](../stacks/authentik-server.md) |
| `AUTHENTIK_POSTGRES_PASSWORD` | Secret | Your choice, alphanumeric only | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_GEOIPUPDATE_ACCOUNT_ID` | Secret | Your MaxMind account ID | [authentik-server](../stacks/authentik-server.md) |
| `GLOBAL_GEOIPUPDATE_LICENSE_KEY` | Secret | A MaxMind licence key | [authentik-server](../stacks/authentik-server.md) |

## dockns {#dockns}

dockns writes DNS records for the containers that carry its labels, and system-agent carries it to every VM. The two UniFi values are read on every VM, and dockns writes no internal record today, so they are staged for later. The three Cloudflare values and the public address matter only on a VM that hosts something the internet reaches. Staged on [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md#values), which is where system-agent first deploys.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `DOCKNS_UNIFI_HOST` | Variable | The local URL of the site's UniFi console, such as `https://172.16.7.1`, not `api.ui.com` | [system-agent](../stacks/system-agent.md) |
| `DOCKNS_UNIFI_API_KEY` | Secret | A local API key from that console, with permission to manage DNS records | [system-agent](../stacks/system-agent.md) |
| `DOCKNS_CF_API_KEY` | Secret | A Cloudflare API token with DNS edit rights on the zone | [system-agent](../stacks/system-agent.md) |
| `DOCKNS_CF_ACCOUNT_ID` | Secret | From the account overview page in the Cloudflare dashboard | [system-agent](../stacks/system-agent.md) |
| `DOCKNS_CF_ZONE_ID` | Secret | From the zone overview page for the domain | [system-agent](../stacks/system-agent.md) |
| `DOCKNS_WAN_IP` | Variable | The site's public address, the one public records point at | [system-agent](../stacks/system-agent.md) |

A host with nothing public on it has the three Cloudflare keys and `DOCKNS_WAN_IP` set to blank in the inventory. The UniFi values belong to one site's console. A fleet on two sites needs a pair per site, under names of your own such as `DOCKNS_UNIFI_HOST_CLOUD`, with the second site's hosts pointed at them through `komodo_stack_env`.

## Stalwart and Bulwark {#mail-server}

Read by stalwart-server on mx01, which is optional. Staged on [Mail (mx01)](../hosts/mx01-mail.md#values). The two OIDC values come from the Authentik application that page creates.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `STALWART_LICENSE_KEY` | Secret | The Stalwart Enterprise licence key | [stalwart-server](../stacks/stalwart-server.md) |
| `BULWARK_SESSION_SECRET_KEY` | Secret | 96 alphanumeric characters of your choice | [stalwart-server](../stacks/stalwart-server.md) |
| `MAIL_OIDC_CLIENT_ID` | Secret | The Authentik provider's client ID | [stalwart-server](../stacks/stalwart-server.md) |
| `MAIL_OIDC_CLIENT_SECRET` | Secret | The Authentik provider's client secret | [stalwart-server](../stacks/stalwart-server.md) |

## CrowdSec {#crowdsec}

Read by crowdsec-agent only. CrowdSec was cut from the plan and no host runs the stack, so nothing stages this value. It is listed because the stack still references it.

| Name | Kind | Value | Read by |
| --- | --- | --- | --- |
| `GLOBAL_CROWDSEC_LAPI_URL` | Variable | The CrowdSec server's API URL | [crowdsec-agent](../stacks/crowdsec-agent.md) |
