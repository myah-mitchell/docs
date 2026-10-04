# VictoriaMetrics (ci01)

victoriametrics-server is where the fleet's metrics, logs, and traces are stored, with Grafana to read them and vmalert to evaluate alert rules. Every host's agents send to it through one endpoint, vmauth.

The [VictoriaMetrics primer](../../tools/victoriametrics/index.md#ideas) explains the three databases, the agents, and how [telemetry](../../tools/glossary.md#telemetry) travels from a host to here. This page only stages, checks, and signs in.

This page is part of ci01's build, and has no build of its own. [Automation and monitoring (ci01)](ci01-automation.md) describes the host and runs it, and sends you here for the three steps below. The stack is [victoriametrics-server](../stacks/victoriametrics-server.md).

Status: written, not yet run.

## Prerequisites

- You are following [Automation and monitoring (ci01)](ci01-automation.md), and came here from its step 2, 4, or 5, or from the page before this one in that step's order. Each step below ends with a link to where that step goes next.

## 1. Stage the values {#values}

Create these four in Komodo. The first three are the one login every agent presents to vmauth. The fourth is the key VictoriaMetrics asks for before it deletes series. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

| Name | Kind | Value |
| --- | --- | --- |
| `GLOBAL_VMAUTH_USER` | Variable | The login's username, your choice |
| `GLOBAL_VMAUTH_PASS` | Secret | Its password, 96 alphanumeric characters |
| `GLOBAL_VMAUTH_HOST` | Variable | Where agents send, `vmauth.ci01.home.myah-mitchell.com` |
| `VICTORIAMETRICS_ADMIN_AUTH_KEY` | Secret | A second value from the same command. Never the vmauth password |

Generate the password in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 96; echo
```

`GLOBAL_VMAUTH_HOST` is a hostname with no scheme and no path. Each agent builds its own URL around it, over HTTPS.

The three are one login, used from both ends. victoriametrics-server gives the user and the password to vmauth, Grafana, and vmalert. Every host's agents, in system-agent, send the same two to the host named in the third.

That is why the names start with `GLOBAL_`, and why no later host page stages them again.

The register lists all four. See [Telemetry](../concepts/variables-and-secrets.md#telemetry).

Go on to [Core infrastructure's values](ci01-core-infra.md#values), the last of the three sections in [step 2 of ci01's page](ci01-automation.md#values).

## 2. Verify {#verify}

The `victoriametrics-server` Stack has seven services:

--8<-- "generated/victoriametrics-server/services.md"

Log in to ci01 and list the project's containers:

```bash
docker ps --filter name=victoriametrics- --format '{{.Names}}: {{.Status}}'
```

Seven containers show, each named `victoriametrics-` and the service, and each with `healthy` in its status.

Nothing is in the databases yet. The stack is the backend alone, and the agents that fill it are part of system-agent, which no host runs in [bootstrap mode](../../tools/glossary.md#bootstrap-mode). See [system-agent](../stacks/system-agent.md#verify) for the check that data arrives.

Go on to [Verify core infrastructure](ci01-core-infra.md#verify), the last of the three checks in [step 4 of ci01's page](ci01-automation.md#verify).

## 3. Sign in to Grafana {#first-access}

Open `https://grafana.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Sign in as `admin` with the password `admin`. Grafana asks for a new password. Enter **a new password**, and store it in your password manager.

> [!WARNING]
> Grafana's route never asks Authentik for a sign-in, in either mode. Until the password is changed, anyone on the internal network can sign in as its admin.

Open *Connections > Data sources*. Four are listed, and all four come from fleet-stacks:

```text
VictoriaLogs
VictoriaMetrics
VictoriaMetrics-prometheus
VictoriaTraces
```

Each one reads through vmauth with the login from [step 1](#values).

Go on to [Create ntfy's accounts](ci01-core-infra.md#ntfy), the last row in [step 5 of ci01's page](ci01-automation.md#first-access).

## Hostnames {#hostnames}

Each service answers on its name under the host, such as `grafana.ci01.home.myah-mitchell.com`. The last column says what guards each [route](../../tools/glossary.md#route) once the fleet has left bootstrap mode.

| Name | Service | Sign-in outside bootstrap mode |
| --- | --- | --- |
| `grafana` | Grafana | Grafana's own |
| `vmauth` | The endpoint agents write to | The login from step 1 |
| `metrics`, `logs`, `traces` | The three databases | Authentik |
| `vmalert`, `alertmanager` | Alerting | Authentik |

In bootstrap mode nothing is in front of the last five, and none of them has a login of its own. See [Bootstrap mode](../concepts/bootstrap-mode.md#effects).

<details>
<summary>Background: why Grafana and vmauth never ask Authentik for a sign-in</summary>

Most routes in the fleet pass through Authentik first, which is done with [forward auth](../../tools/glossary.md#forward-auth): Traefik asks Authentik whether the browser is signed in, and sends it to a sign-in page when it is not. That works for a person in a browser and for nothing else.

vmauth's callers are the agents on every host. An agent cannot follow a redirect to a sign-in page, so it presents the username and password from step 1 with every request instead.

Grafana is used by people, but it keeps accounts, roles, and API tokens of its own, and its route is set to skip the Authentik check in fleet-stacks. Its own sign-in is the only one, which is why the default password has to go before anything else is done.

</details>

## What it keeps, and for how long {#retention}

| Folder under `/opt/docker/volumes/victoriametrics` | Holds | Kept for |
| --- | --- | --- |
| `victoriametrics-data` | Metrics | 60 days |
| `victorialogs-data` | Logs | One year, or 5 GB |
| `victoriatraces-data` | Traces | One year, or 5 GB |
| `grafana-data` | Grafana's users and settings | Until deleted |

The limits are arguments in each container's definition in fleet-stacks. The dashboards and data sources are read from the repo on every start, so a change made to one of them in Grafana does not last.

## Where alerts go {#alerts}

vmalert evaluates the rules in fleet-stacks and hands what fires to Alertmanager. Alertmanager sends every alert as mail to `infra@mailrise.xyz`, and mailrise posts it to the ntfy topic `alerts-infra`. It sends another message when the alert clears.

Two things on ci01 have to be in place before an alert reaches ntfy:

- core-infra is running. Alertmanager reaches mailrise by its container name, `core-mailrise`, on port 8025, over the proxy network the two stacks share.
- `mailrise.conf` holds the real ntfy token in its `infra` entry. See [Give mailrise its token](ci01-core-infra.md#mailrise).

Alertmanager's own file, `containers/alertmanager/config/alertmanager.yml` in fleet-stacks, holds no secret, because the token is in mailrise's. Subscribe to `alerts-infra` to read the alerts. See [Subscribing a phone](ci01-core-infra.md#phone).

## Not yet confirmed {#unconfirmed}

- The whole page. victoriametrics-server has not been deployed by the run.
- vmauth refusing a request that carries no login. Its source shows the HTTP server's own login covers what it forwards, apart from paths that end in `/delete_series`, `/reset`, `/config`, `/reload`, or `/snapshot`. No request has been sent to try it. The command below settles it: `401` means the login is enforced.
- VictoriaMetrics refusing the two admin paths vmauth forwards without its login, the one that deletes series and the one that resets the metric name statistics. It is started with a key for each, the value of `VICTORIAMETRICS_ADMIN_AUTH_KEY`, and is expected to answer `401` to a request with no `authKey` query argument. No request has been sent to either. See [Hostnames](../stacks/victoriametrics-server.md#hostnames).
- What guards the `metrics`, `logs`, and `traces` names. They reach the databases through Traefik without passing vmauth, so the chain is all that guards them, and no request has been sent to see it refuse one.
- An alert reaching ntfy. The path from Alertmanager through mailrise to `alerts-infra` is read from the two stacks' files, and no alert has been sent along it.
- The menu path to the data sources, which follows Grafana 12.

```bash
curl -sk -o /dev/null -w '%{http_code}\n' \
  'https://vmauth.ci01.home.myah-mitchell.com/api/v1/query?query=up'
```
