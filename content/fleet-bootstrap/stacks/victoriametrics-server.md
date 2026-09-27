# victoriametrics-server

victoriametrics-server is where the fleet's metrics, logs, and traces are stored, queried, and turned into alerts. It runs on one host, ci01. See [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md) for the build.

## What it runs {#services}

--8<-- "generated/victoriametrics-server/services.md"

The first five come from [victoriametrics-agent](victoriametrics-agent.md), which this stack includes. They collect from ci01 itself.

| Service | Does |
| --- | --- |
| `vlagent` | Buffers logs and forwards them to vmauth |
| `vmagent` | Scrapes metrics on the host and forwards them to vmauth |
| `vector` | Reads the journal, `/var/log`, and container logs, and takes syslog on port 5140 |
| `cadvisor` | Measures each container's use of the host |
| `socket-proxy` | Gives vector a filtered view of the Docker socket |

The other seven are the backend.

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

alertmanager's config is `containers/alertmanager/config/alertmanager.yml` in docker-stacks, mounted from the clone. As committed it has one receiver, which discards what it is given. Alerts show in vmalert and alertmanager and go nowhere else until that file names a real receiver.

## Values it reads {#values}

--8<-- "generated/victoriametrics-server/values.md"

The host page says what to put in each. See [Stage the values](../hosts/ci01-victoriametrics.md#values).

The same three are read by the agents on every other host, which is how they find vmauth and log in to it.

vmagent also reads the host's Node Exporter login from two files under `/etc/node-exporter`. The provision stage writes them, and the password in them never leaves the host.

## What the host needs {#host-setup}

--8<-- "generated/victoriametrics-server/host-setup.md"

The run creates all of it in the provision stage. The stack also needs a Traefik on the same host.

Port 5140 is vector's syslog listener, for devices that cannot run an agent. It is open to the internal subnet only.

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

In Komodo, the `victoriametrics-server` Stack shows as running with twelve services.

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

All four are on the persistent disk, so they survive a rebuild of the VM. The three folders that belong to the agents hold what is waiting to be sent, up to 100 MB each for vmagent and vlagent.

The alert rules, the data sources, and the dashboards that ship with the stack are in docker-stacks, not on the disk.

## Not yet confirmed {#unconfirmed}

- Sharing a host with [system-agent](system-agent.md). Both run a vector that publishes port 5140 on the host, and two containers cannot hold one port. ci01 leaves system-agent off its list for that reason.
- Whether traces reach `victoriatraces`. vmauth has a route for them, and no agent in the repo is set to send any.
