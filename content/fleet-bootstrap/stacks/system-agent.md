# system-agent

system-agent is what every VM but ci01 runs for the fleet's own sake: it ships the VM's metrics and logs to ci01, writes its DNS records, and offers its container logs to a central Dozzle. It carries no Traefik, so it goes on a VM whether or not that VM serves a web interface.

Every host lists it, and no host runs it while in bootstrap mode. See [In bootstrap mode](#bootstrap).

## What it runs {#services}

--8<-- "generated/system-agent/services.md"

| Service | Does |
| --- | --- |
| `vmagent` | Scrapes metrics on the VM and sends them to vmauth on ci01 |
| `vlagent` | Sends the logs vector hands it to vmauth on ci01 |
| `vector` | Collects container logs, the journal, files under `/var/log`, syslog, and Traefik's access log |
| `cadvisor` | Measures each container's use of CPU, memory, disk, and network |
| `dozzle-agent` | Serves the VM's container logs on port 7007, for a Dozzle server to read |
| `dockns` | Writes DNS records for the containers that carry its labels |
| `socket-proxy` | Gives vector, dozzle-agent, and dockns a filtered view of the Docker API |

The Stack in Komodo carries the host's name, such as `system-agent-id01`. The project is `system`, so the containers are named `system-vmagent`, `system-vector`, and so on. The Dozzle agent is `system-dozzle-agent`.

vmagent scrapes five targets once a minute: itself, vlagent, cadvisor, the host's Node Exporter, and the Traefik on the same VM. It looks the Traefik up by name, so a VM without one has no target and reports no failure.

vmagent and vlagent each keep up to 100 MB of unsent data on disk while ci01 is unreachable, and send it when ci01 is back.

vector listens for syslog on UDP port 5140. It reads Traefik's access log from `/opt/docker/logs/traefik/traefik`, the folder the VM's Traefik stack writes to, and finds nothing there on a VM without one.

## In bootstrap mode {#bootstrap}

The stack's `setup.yaml` says it needs vmauth, which is on ci01. A host in bootstrap mode has that need unmet, so the run leaves the stack out. See [What it changes](../concepts/bootstrap-mode.md#changes).

Two things follow until the host leaves bootstrap mode. Its metrics and logs are not shipped, and nothing writes its DNS records. See [What you see in bootstrap mode](../concepts/bootstrap-mode.md#effects).

The stack first deploys when the fleet leaves bootstrap mode. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

## Values it reads {#values}

--8<-- "generated/system-agent/values.md"

The three telemetry values are the one login every agent uses. They exist from the time ci01 is built. See [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md#values).

The six dockns values are created when the fleet leaves bootstrap mode. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md#values).

| dockns values | Needed on |
| --- | --- |
| `DOCKNS_UNIFI_HOST`, `DOCKNS_UNIFI_API_KEY` | Every VM |
| The three `DOCKNS_CF_` values and `DOCKNS_WAN_IP` | A VM that hosts something the internet reaches |

On a VM with nothing public, set the second row's four keys to blank under `komodo_stack_env` in the inventory:

```yaml
komodo_stack_env:
  system-agent:
    DOCKNS_WAN_IP: ""
    DOCKNS_CF_API_KEY: ""
    DOCKNS_CF_ACCOUNT_ID: ""
    DOCKNS_CF_ZONE_ID: ""
```

See [Blanking a reference](../concepts/variables-and-secrets.md#blanking). The same place points a second site's hosts at that site's UniFi console. See [dockns](../concepts/variables-and-secrets.md#dockns).

## What the host needs {#host-setup}

--8<-- "generated/system-agent/host-setup.md"

dockns runs as root inside its container, which the host sees as `100000`. The other three folders belong to `101000`. See [UID offsets](../concepts/host-layout.md#uid-offsets).

vmagent also mounts two files that the provision stage writes with Node Exporter, outside the stack's own setup:

| File | Holds |
| --- | --- |
| `/etc/node-exporter/node_exporter.crt` | Node Exporter's self-signed certificate |
| `/etc/node-exporter/scrape-password` | This host's scrape password, owned by `101000` and mode `0400` |

The password is generated on each host and never leaves it, so no Komodo Secret holds it. A host's vmagent scrapes its own Node Exporter and no other.

## Verify {#verify}

In Komodo, the `system-agent-<host>` Stack shows as running with seven services.

On the host, list the project's containers:

```bash
docker compose -p system ps
```

Every container that has a health check shows `healthy` in the *STATUS* column.

The agents show as healthy whether or not anything reaches ci01, so check the far end. In Grafana on ci01, run this query with your host in place of `id01`:

```text
up{instance=~".*id01.*"}
```

The result has a series with the value `1` for each of vmagent, vlagent, cadvisor, and `node`. A VM with a Traefik has one more, for the job `traefik-traefik`.

A missing `node` series with the rest present means vmagent did not read the scrape password. Check that `/etc/node-exporter/scrape-password` is a file and not a folder. Docker creates a folder at a mount's source when nothing is there.

For logs, open VictoriaLogs on ci01 and filter on `stream_name`.

| `stream_name` starts with | Comes from |
| --- | --- |
| `container-` | A container's output |
| A systemd unit's name | The journal |
| `host-` | A file under `/var/log` |
| `syslog-` | A device sending syslog to port 5140 |

Traefik's access log goes to its own index, `traefik-access`, and appears once the VM's Traefik has routed a request.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/system` | Holds |
| --- | --- |
| `dockns-data` | `record-db.json`, dockns's own list of the records it has written |

The other three folders are buffers and checkpoints. Losing them loses at most what had not been sent.

## Not yet confirmed {#unconfirmed}

The stack has not been deployed on any host. These are the points most likely to need work.

- Sharing a host with victoriametrics-server. That stack has collectors of its own, and its vector publishes port 5140 on the host as this stack's does. Two containers cannot hold one port, so ci01 leaves system-agent off its list.
- dockns and the labels. Three containers in docker-stacks carry dockns labels (ntfy, Stalwart, and Bulwark), and those labels name a server called `technitium`. This stack gives dockns two servers, `cloudflare` and `unifi`. Until the labels change and the other containers gain them, dockns writes no internal record.
- The Traefik scrape. vmagent shares no Docker network with the Traefik stack, and Traefik publishes no metrics port on the host.
- Syslog over TCP. The stack publishes port 5140 for TCP and UDP and the firewall allows both. vector's syslog source listens on UDP alone.
