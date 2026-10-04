# victoriametrics-server

victoriametrics-server is where the fleet's metrics, logs, and traces are stored, queried, and turned into alerts. It is the [VictoriaMetrics](../../tools/victoriametrics/index.md) stores, with Grafana beside them for dashboards. It runs on one host, ci01. See [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md) for the build.

## What it runs {#services}

--8<-- "generated/victoriametrics-server/services.md"

| Service | Does |
| --- | --- |
| `victoriametrics` | Stores metrics, for 60 days |
| `victorialogs` | Stores logs, for a year or until they fill 5 GB |
| `victoriatraces` | Stores traces, for a year or until they fill 5 GB |
| `vmauth` | The one address the agents on every VM send to. Passes each request to the right store by its path |
| `vmalert` | Evaluates the alert rules in the repo against the stores, and hands alerts to alertmanager |
| `grafana` | Dashboards, with its four data sources and the dashboards in the repo already loaded |
| `alertmanager` | Groups the alerts vmalert hands it and mails each group to mailrise in [core-infra](core-infra.md), which posts it to ntfy |

The [project](../../tools/glossary.md#project) is `victoriametrics`, so the containers are named `victoriametrics-` and the service, such as `victoriametrics-grafana`.

The stack is the backend alone. It collects nothing from the host it runs on. ci01's own metrics and logs come from [system-agent](system-agent.md), which ci01 lists like every other VM.

alertmanager's config is `containers/alertmanager/config/alertmanager.yml` in fleet-stacks, mounted from the clone. It has one receiver, which sends every alert as mail to `infra@mailrise.xyz` at `core-mailrise:8025`, and sends another message when an alert clears. mailrise posts each message to the ntfy topic `alerts-infra`.

Delivery depends on the other stack. `core-mailrise` is the mailrise container of core-infra, reached by name over the proxy network both stacks join, so core-infra has to run on the same host. The ntfy token is in `mailrise.conf` and not in alertmanager's file, so nothing is delivered until that token is real. See [Give mailrise its token](../hosts/ci01-core-infra.md#mailrise).

## Values it reads {#values}

--8<-- "generated/victoriametrics-server/values.md"

The host page says what to put in each. See [Stage the values](../hosts/ci01-victoriametrics.md#values).

The two are the login vmauth is given. The agents in system-agent read the same two on every host, with `GLOBAL_VMAUTH_HOST` for where to send.

## What the host needs {#host-setup}

--8<-- "generated/victoriametrics-server/host-setup.md"

The stack also needs a Traefik on the same host.

## Hostnames {#hostnames}

Seven services have a route, and each route answers on its name under the host, the sub-domain, and the domain. With the host `ci01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, the names under the host are:

| Hostname | Service | Sign-in |
| --- | --- | --- |
| `grafana.ci01.home.myah-mitchell.com` | `grafana` | Grafana's own |
| `vmauth.ci01.home.myah-mitchell.com` | `vmauth` | vmauth's own login |
| `metrics.ci01.home.myah-mitchell.com` | `victoriametrics` | From the chain |
| `logs.ci01.home.myah-mitchell.com` | `victorialogs` | From the chain |
| `traces.ci01.home.myah-mitchell.com` | `victoriatraces` | From the chain |
| `vmalert.ci01.home.myah-mitchell.com` | `vmalert` | From the chain |
| `alertmanager.ci01.home.myah-mitchell.com` | `alertmanager` | From the chain |

Take `ci01.` out of a name for the one under the sub-domain, and `ci01.home.` for the one under the domain. Each route also answers on the container's name under the host, such as `victoriametrics-grafana.ci01.home.myah-mitchell.com`.

Five routes take their [chain](../../tools/glossary.md#auth-chain) from `TRAEFIK_AUTH_CHAIN`. The run sets that key to `chain-no-auth@file` in bootstrap mode, which leaves those five interfaces open to anyone who can reach ci01. See [What it changes](../concepts/bootstrap-mode.md#changes).

Grafana and vmauth use `chain-no-auth` in both modes. Grafana has its own sign-in, and the agents that write to vmauth cannot follow a redirect to Authentik.

vmauth asks for the login itself. The compose file passes the two values as `--httpAuth.username` and `--httpAuth.password`, and vmauth's HTTP server checks them before it looks at `auth-vl-single.yml`. A request to a forwarded path without the login gets `401`. The file's `unauthorized_user` block then routes what passed the check, which is why it names no user of its own.

vmauth skips its login for paths that end in `/delete_series`, `/reset`, `/config`, `/reload`, or `/snapshot`, and leaves each to a key the program behind it checks. Two of them fall under the `/api/v1/.*` route, so vmauth forwards them to VictoriaMetrics without its login:

```text
/api/v1/admin/tsdb/delete_series
/api/v1/admin/status/metric_names_stats/reset
```

VictoriaMetrics guards both. The compose file starts it with `--deleteAuthKey` and `--metricNamesStatsResetAuthKey`, each set to the Secret `VICTORIAMETRICS_ADMIN_AUTH_KEY`, and it answers `401` unless the request carries that value in the query argument `authKey`. The key is not the vmauth password, because a query argument can end up in a proxy's access log. An empty key leaves both paths open.

> [!WARNING]
> The `metrics`, `logs`, and `traces` names go from Traefik straight to each store, not through vmauth. The chain is all that guards them, and in bootstrap mode that is nothing. Keep every name in the table off public DNS.

Inside the stack, vmalert and Grafana query through vmauth with the same login. vmalert writes its own state straight to `victoriametrics:8428` on the stack's internal network, where no login applies.

## Verify {#verify}

In Komodo, the `victoriametrics-server` Stack shows as running with seven services.

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p victoriametrics-server ps
```

Every container shows `healthy` in the *STATUS* column. The three stores, vmauth, vmalert, Grafana, and alertmanager are each checked by a request to their own health endpoint.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/victoriametrics` | Holds |
| --- | --- |
| `victoriametrics-data` | The metrics |
| `victorialogs-data` | The logs |
| `victoriatraces-data` | The traces |
| `grafana-data` | Grafana's users, and any dashboard made in its interface |

All four are on the [persistent disk](../../tools/glossary.md#persistent-disk), so they survive a rebuild of the VM.

The alert rules, the data sources, and the dashboards that ship with the stack are in fleet-stacks, not on the disk.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- What vmauth's login covers. The account above is read from vmauth's source at `v1.133.0` and the stack's files, and no request has been sent to a running vmauth.
- VictoriaMetrics refusing the two admin paths without `authKey`. The two flags are in the compose file, and no request has been sent to either path.
- Alerts reaching ntfy. The path from alertmanager through mailrise to the `alerts-infra` topic is read from the two stacks' files, and no alert has been sent along it.
- Whether traces reach `victoriatraces`. vmauth has a route for them, and no agent in the repo is set to send any.
