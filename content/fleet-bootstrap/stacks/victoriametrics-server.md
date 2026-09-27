# victoriametrics-server

victoriametrics-server is where the fleet's metrics, logs, and traces are stored, queried, and turned into alerts. It runs on one host, ci01. See [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md) for the build.

## What it runs {#services}

--8<-- "generated/victoriametrics-server/services.md"

| Service | Does |
| --- | --- |
| `victoriametrics` | Stores metrics, for 60 days |
| `victorialogs` | Stores logs, for a year or until they fill 5 GB |
| `victoriatraces` | Stores traces, for a year or until they fill 5 GB |
| `vmauth` | The one way in. Sends each request to the right store by its path |
| `vmalert` | Evaluates the alert rules in the repo against the stores, and hands alerts to alertmanager |
| `grafana` | Dashboards, with both data sources and the dashboards in the repo already loaded |
| `alertmanager` | Groups and routes alerts |

The project is `victoriametrics`, so the containers are named `victoriametrics-` and the service, such as `victoriametrics-grafana`.

The stack is the backend alone. It collects nothing from the host it runs on. ci01's own metrics and logs come from [system-agent](system-agent.md), which ci01 lists like every other VM.

alertmanager's config is `containers/alertmanager/config/alertmanager.yml` in docker-stacks, mounted from the clone. As committed it has one receiver, which discards what it is given. Alerts show in vmalert and alertmanager and go nowhere else until that file names a real receiver.

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
| `vmauth.ci01.home.myah-mitchell.com` | `vmauth` | None at Traefik |
| `metrics.ci01.home.myah-mitchell.com` | `victoriametrics` | From the chain |
| `logs.ci01.home.myah-mitchell.com` | `victorialogs` | From the chain |
| `traces.ci01.home.myah-mitchell.com` | `victoriatraces` | From the chain |
| `vmalert.ci01.home.myah-mitchell.com` | `vmalert` | From the chain |
| `alertmanager.ci01.home.myah-mitchell.com` | `alertmanager` | From the chain |

Take `ci01.` out of a name for the one under the sub-domain, and `ci01.home.` for the one under the domain. Each route also answers on the container's name under the host, such as `victoriametrics-grafana.ci01.home.myah-mitchell.com`.

Five routes take their chain from `TRAEFIK_AUTH_CHAIN`. The run sets that key to `chain-no-auth@file` in bootstrap mode, which leaves those five interfaces open to anyone who can reach ci01. See [What it changes](../concepts/bootstrap-mode.md#changes).

Grafana and vmauth use `chain-no-auth` in both modes. Grafana has its own sign-in, and the agents that write to vmauth cannot follow a redirect to Authentik.

> [!WARNING]
> The vmauth login does not guard the data. The committed `auth-vl-single.yml` defines only an unauthorized user, so vmauth forwards every request that matches a path, with or without the login. Keep vmauth's names off public DNS.

## Verify {#verify}

In Komodo, the `victoriametrics-server` Stack shows as running with seven services.

On the host, list the project's containers:

```bash
docker compose -p victoriametrics ps
```

Every container shows `healthy` in the *STATUS* column. The three stores, vmauth, vmalert, Grafana, and alertmanager are each checked by a request to their own health endpoint.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/victoriametrics` | Holds |
| --- | --- |
| `victoriametrics-data` | The metrics |
| `victorialogs-data` | The logs |
| `victoriatraces-data` | The traces |
| `grafana-data` | Grafana's users, and any dashboard made in its interface |

All four are on the persistent disk, so they survive a rebuild of the VM.

The alert rules, the data sources, and the dashboards that ship with the stack are in docker-stacks, not on the disk.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- Whether traces reach `victoriatraces`. vmauth has a route for them, and no agent in the repo is set to send any.
