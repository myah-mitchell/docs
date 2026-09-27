# victoriametrics-agent

victoriametrics-agent is the set of collectors that read a host's metrics and logs and send them to VictoriaMetrics. No host lists it, and no stack includes it. See [Not in the plan](index.md#unused).

The per-VM role belongs to [system-agent](system-agent.md). It carries the same collectors, reads Traefik's access log as well, and adds container DNS and a Dozzle agent.

To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/victoriametrics-agent/services.md"

| Service | Does |
| --- | --- |
| `vmagent` | Scrapes itself, vlagent, cadvisor, and the host's Node Exporter every 10 seconds, and forwards the metrics |
| `vlagent` | Receives logs from vector and forwards them |
| `vector` | Reads container logs, the host's journal, `.log` files under `/var/log`, and syslog on port 5140 |
| `cadvisor` | Reports what each container uses of the CPU, memory, disk, and network |
| `socket-proxy` | Gives vector a filtered view of the Docker socket |

The project is `victoriametrics`, so the containers are named `victoriametrics-` and the service, such as `victoriametrics-vmagent`.

vmagent and vlagent each keep up to 100 MB of unsent data on disk, so a short outage of the receiving end loses nothing.

vector and cadvisor run in the host's user namespace. The journal and the files under `/var/log` cannot be read from inside the remapped one.

vmagent reads the Node Exporter's certificate and scrape password from `/etc/node-exporter` on the host. The host's NixOS configuration puts both there, and the password never reaches Komodo. See [system-agent](system-agent.md#host-setup).

## Values it reads {#values}

--8<-- "generated/victoriametrics-agent/values.md"

Both agents send to `https://` and the value of `VMAUTH_HOST`, and sign in with the user and password. The three are staged on [VictoriaMetrics (ci01)](../hosts/ci01-victoriametrics.md#values).

## What the host needs {#host-setup}

--8<-- "generated/victoriametrics-agent/host-setup.md"

The stack has no route, so it needs no Traefik on the host.

Its vector publishes port 5140 on the host, and so does the one in system-agent. Two stacks cannot both hold the port on one host.

## Verify {#verify}

On the host, list the project's containers:

```bash
docker compose -p victoriametrics ps
```

Every container shows `healthy` in the *STATUS* column. The checks on vmagent and vlagent ask each agent's own health endpoint, so `healthy` means the agent is up. It does not mean the receiving end accepted anything.

To see that, look for the host's metrics and logs in Grafana. See [victoriametrics-server](victoriametrics-server.md#verify).
