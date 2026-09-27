# VictoriaMetrics (ci01)

victoriametrics-server is where the fleet's metrics, logs, and traces are stored, with Grafana to read them and vmalert to evaluate alert rules. Every host's agents send to it through one endpoint, vmauth.

This page is part of ci01's build, and has no build of its own. [Automation and monitoring (ci01)](ci01-automation.md) describes the host and runs it, and sends you here for the three steps below. The stack is [victoriametrics-server](../stacks/victoriametrics-server.md).

Status: written, not yet run.

## Prerequisites

- You are following [Automation and monitoring (ci01)](ci01-automation.md), and came here from its step 2, 4, or 5.

## 1. Stage the values {#values}

Create these three in Komodo. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

| Name | Kind | Value |
| --- | --- | --- |
| `GLOBAL_VMAUTH_USER` | Variable | Your choice |
| `GLOBAL_VMAUTH_PASS` | Secret | 96 alphanumeric characters |
| `GLOBAL_VMAUTH_HOST` | Variable | `vmauth.ci01.home.myah-mitchell.com` |

Generate the password in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 96; echo
```

`GLOBAL_VMAUTH_HOST` is a hostname with no scheme and no path. Each agent builds its own URL around it, over HTTPS.

The three are one login, used from both ends. victoriametrics-server gives the user and the password to vmauth, Grafana, and vmalert. Every host's agents, in system-agent, send the same two to the host named in the third. That is why the names start with `GLOBAL_`, and why no later host page stages them again.

The register lists the same three. See [Telemetry](../concepts/variables-and-secrets.md#telemetry).

Go back to [step 2 of ci01's page](ci01-automation.md#values).

## 2. Verify {#verify}

The `victoriametrics-server` Stack has seven services:

--8<-- "generated/victoriametrics-server/services.md"

Log in to ci01 and list the project's containers:

```bash
docker ps --filter name=victoriametrics- --format '{{.Names}}: {{.Status}}'
```

Seven containers show, each named `victoriametrics-` and the service, and each with `healthy` in its status.

Nothing is in the databases yet. The stack is the backend alone, and the agents that fill it are part of system-agent, which no host runs in bootstrap mode. See [system-agent](../stacks/system-agent.md#verify) for the check that data arrives.

Go back to [step 4 of ci01's page](ci01-automation.md#verify).

## 3. Sign in to Grafana {#first-access}

Open `https://grafana.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Sign in as `admin` with the password `admin`. Grafana asks for a new password. Enter one, and store it in your password manager.

> [!WARNING]
> Grafana's route never asks Authentik for a sign-in, in either mode. Until the password is changed, anyone on the internal network can sign in as its admin.

Open *Connections > Data sources*. Four are listed, and all four come from docker-stacks:

```text
VictoriaLogs
VictoriaMetrics
VictoriaMetrics-prometheus
VictoriaTraces
```

Each one reads through vmauth with the login from [step 1](#values).

Go back to [step 5 of ci01's page](ci01-automation.md#first-access).

## Hostnames {#hostnames}

Each service answers on its name under the host, such as `grafana.ci01.home.myah-mitchell.com`.

| Name | Service | Sign-in outside bootstrap mode |
| --- | --- | --- |
| `grafana` | Grafana | Grafana's own |
| `vmauth` | The endpoint agents write to | The login from step 1 |
| `metrics`, `logs`, `traces` | The three databases | Authentik |
| `vmalert`, `alertmanager` | Alerting | Authentik |

In bootstrap mode nothing is in front of the last five, and none of them has a login of its own. See [Bootstrap mode](../concepts/bootstrap-mode.md#effects).

## What it keeps, and for how long {#retention}

| Folder under `/opt/docker/volumes/victoriametrics` | Holds | Kept for |
| --- | --- | --- |
| `victoriametrics-data` | Metrics | 60 days |
| `victorialogs-data` | Logs | One year, or 5 GB |
| `victoriatraces-data` | Traces | One year, or 5 GB |
| `grafana-data` | Grafana's users and settings | Until deleted |

The limits are arguments in each container's definition in docker-stacks. The dashboards and data sources are read from the repo on every start, so a change made to one of them in Grafana does not last.

## Alerts go nowhere yet {#alerts}

vmalert evaluates the rules in docker-stacks and hands what fires to Alertmanager. Alertmanager's one receiver, `blackhole`, drops everything. Sending alerts to ntfy is a change to `containers/alertmanager/config/alertmanager.yml` in docker-stacks.

## Not yet confirmed {#unconfirmed}

- The whole page. victoriametrics-server has not been deployed by the run.
- Whether vmauth refuses a request that carries no login. Its config routes every request under `unauthorized_user`, and the login is set as its HTTP server's own, which may or may not cover what it forwards. The command below settles it: `401` means the login is enforced, and `200` means anything that reaches vmauth can read all three databases.
- The menu path to the data sources, which follows Grafana 12.

```bash
curl -sk -o /dev/null -w '%{http_code}\n' \
  'https://vmauth.ci01.home.myah-mitchell.com/api/v1/query?query=up'
```
