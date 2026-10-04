# Adding a scrape target

A scrape target is an address that serves metrics, listed in a scrape job so that the fleet collects from it. Add one when you run something new that has a `/metrics` page, or an exporter for something that does not. See [Scraping and exporters](index.md#scraping) for the idea.

The change is an edit to one scrape config in fleet-stacks. Komodo carries it to the host when the Stack is deployed, and the scraper reads it when its container restarts.

Status: written, not yet run.

## Prerequisites

- The fleet has left bootstrap mode, so the agents run. See [Leaving bootstrap mode](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md).
- A clone of a fleet-stacks repo you can push to, which the fleet deploys from. See [Get a repo you can push to](../../fleet-bootstrap/hosts/ap01-applications.md#fork).
- The thing you want to scrape is running, and you know its port.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<name>` | A short name for the job, such as `alertmanager`. It becomes the `job` label on every series |
| `<port>` | The port the target serves its metrics on |
| `<host>` | A host that runs the scraper, such as `id01` |

## 1. Choose the scrape config {#choose}

Two programs scrape, and each has one file under `containers/` in fleet-stacks. Pick the file by where the target runs.

| The target is | Edit | Scraped by |
| --- | --- | --- |
| On every host, or on any host other than as part of victoriametrics-server | `vmagent/config/prometheus-system.yml` | vmagent, on each host, every 60 seconds |
| A service in the victoriametrics-server stack on ci01 | `victoriametrics/config/prometheus-vl-single.yml` | VictoriaMetrics, every 10 seconds |

Every host's vmagent reads the same file. A job added to it runs on every host, so it has to be written to suit a host that lacks the target. [Step 2](#add) shows how.

The scraper must be able to reach the target. A container can reach another by its service name only when both are in the same stack. vmagent can also reach any port open on the host's own address, and any name the fleet's DNS resolves.

## 2. Add the job {#add}

Add a job to the end of the `scrape_configs` list in the file you chose. The form depends on where the target is.

### A service in the victoriametrics-server stack {#same-stack}

This is the worked example. Alertmanager serves metrics on port 9093, and the repo's file has no job for it. Add this to `containers/victoriametrics/config/prometheus-vl-single.yml`:

```yaml
- job_name: alertmanager
  static_configs:
  - targets:
    - alertmanager:9093
```

The target is the service's name in the stack's `compose.yaml` and the port the program listens on inside its container. No path is given, because `/metrics` is the default.

### A port on every host {#host-port}

For something that listens on each host's own address, follow the `node` job in `prometheus-system.yml`:

```yaml
- job_name: <name>
  static_configs:
  - targets:
    - "%{SERVER_ADDRESS}:<port>"
```

`%{SERVER_ADDRESS}` becomes the host's full name, such as `id01.home.myah-mitchell.com`. The port also has to be open in the host's firewall, which is part of its NixOS configuration.

### Something only some hosts run {#some-hosts}

A static target that is missing shows as down on every host without it. Look the name up in DNS instead, as the repo's Traefik job does:

```yaml
- job_name: <name>
  dns_sd_configs:
  - names:
    - '<name>.%{SERVER_ADDRESS}'
    type: A
    port: <port>
```

A host where the name has no record finds no target, and nothing reports a failure.

### A target with a login or TLS {#protected}

Add `scheme: https`, a `basic_auth` block, or both. The `node` job in `prometheus-system.yml` shows all of it. Do not write a password in the file, since the repo is public. Mount it into the container as a file and name it in `password_file`, as that job does.

## 3. Commit and push {#push}

From your clone of fleet-stacks, for the worked example:

```bash
git add containers/victoriametrics/config/prometheus-vl-single.yml
git commit -m "Scrape Alertmanager's metrics"
git push
```

Push to the branch the fleet deploys from, which is `main` unless the inventory says otherwise.

## 4. Deploy the Stack and restart the scraper {#deploy}

1. In Komodo, open the Stack that holds the scraper and click **Deploy**. For the worked example that is `victoriametrics-server`. For a change to vmagent's file it is `system-agent-<host>`, on each host in turn.
2. Watch the deploy log until the Stack shows as *Running*. The deploy updates the clone of fleet-stacks on the host.
3. On the host, restart the scraper so that it reads the new file.

For the worked example, on ci01:

```bash
docker restart victoriametrics-victoriametrics
```

For a change to vmagent's file, on each host:

```bash
docker restart system-vmagent
```

The container shows as `healthy` again within a minute in `docker ps`.

<details>
<summary>Background: why a deploy is not enough</summary>

The scrape config is one file, mounted into the container from the clone. Docker ties such a mount to the file as it was when the container started. Git replaces a changed file with a new one, so a running container keeps seeing the old contents.

A deploy runs `docker compose up`, which leaves a container alone when nothing in its definition changed. A changed config file is not part of the definition. A restart makes Docker set the mount up again, against the new file.

Restarting vmagent loses nothing. What it had not yet sent is in its buffer on disk, and scraping resumes within seconds.

</details>

## 5. Verify {#verify}

Check the scraper's own list of targets first. For the worked example, open `https://metrics.ci01.home.myah-mitchell.com/targets` in a browser. The job `alertmanager` is listed with one target, and its state is *up*.

For a change to vmagent's file, ask the agent on the host:

```bash
docker exec system-vmagent wget -qO- http://127.0.0.1:8429/targets
```

The output has a line for the job `<name>` with `state=up`. A target that is down shows the error of its last scrape on the same line.

Then check that the data reached the store. In Grafana, open *Explore*, choose the **VictoriaMetrics** data source, and run:

```text
up{job="alertmanager"}
```

One series comes back with the value `1`. For a job in vmagent's file, there is one series for each host that has the target.

| Symptom | Cause |
| --- | --- |
| The job is not in the list of targets | The container was not restarted, or the deploy did not update the clone |
| The container does not come back after the restart | The file does not parse. Read the reason with `docker logs` and the container's name |
| The target is listed and down, with a name that does not resolve | The scraper and the target share no network. See [step 1](#choose) |
| The target is listed and down, with a refused connection | The port is wrong, or the host's firewall does not allow it |

## What's next

A new metric is worth an alert only when someone would act on it. See [Adding an alert rule](add-an-alert-rule.md).

To draw it, add a panel to a dashboard of your own in Grafana. A dashboard you create there is kept in Grafana's data folder. See [Data worth keeping](../../fleet-bootstrap/stacks/victoriametrics-server.md#data).

## Not yet confirmed {#unconfirmed}

- The whole procedure. No scrape target has been added to a running fleet.
- Whether Komodo's *Deploy* updates the clone when nothing in the Stack's definition changed, and whether it restarts the container by itself. The page assumes it updates the clone and does not restart.
- The labels in Komodo's UI.
- The form of vmagent's `/targets` output when asked with `wget`, and the wording of the state on VictoriaMetrics' `/targets` page.
- A scrape of a container in another stack. The blackbox exporter in core-infra is the case in point: nothing in the repo scrapes it, and its container shares only the Traefik network with VictoriaMetrics.
- The DNS form for a target on some hosts. The repo's own Traefik job uses it, and that job is itself unconfirmed. See [system-agent](../../fleet-bootstrap/stacks/system-agent.md#unconfirmed).
