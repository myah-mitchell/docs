# Adding an alert rule

An alert rule is a query that vmalert runs on a timer, raising an alert for every series the query returns. Add one when there is a condition you would act on if you knew about it. See [Alert rules](index.md#alert-rules) for the parts of a rule.

The change is a rule file in fleet-stacks, under `containers/vmalert/config/`. Komodo carries it to ci01 when the victoriametrics-server Stack is deployed, and vmalert reads it when its container restarts.

Status: written, not yet run.

## Prerequisites

- The fleet has left bootstrap mode, so the stores hold data to evaluate. See [Leaving bootstrap mode](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md).
- A clone of a fleet-stacks repo you can push to, which the fleet deploys from. See [Get a repo you can push to](../../fleet-bootstrap/hosts/ap01-applications.md#fork).
- You can sign in to Grafana on ci01. See [Sign in to Grafana](../../fleet-bootstrap/hosts/ci01-victoriametrics.md#first-access).

> [!NOTE]
> A firing alert notifies nobody yet. Alertmanager's committed config discards everything, so this page ends with the alert showing in vmalert and Alertmanager. See [vmalert and Alertmanager](index.md#alerting).

## The worked rule {#worked-rule}

The rule added here fires when a host's vmagent is running and cannot scrape that host's Node Exporter for five minutes. The repo ships rules for what Node Exporter reports, and none for Node Exporter going quiet.

## 1. Write the query first {#query}

In Grafana, open *Explore*, choose the VictoriaMetrics data source, and run the query without its condition:

```text
up{job="node"}
```

One series comes back for each host, each with the value `1`. This shows the query selects what you mean before a condition hides it.

Now add the condition:

```text
up{job="node"} == 0
```

Nothing comes back while every Node Exporter answers. An alert rule fires for each series its query returns, so an empty result is the healthy state.

## 2. Add the rule file {#file}

Keep your own rules in a file of their own, apart from the rule sets that ship in the folder. A later update to one of those then never touches yours.

Create `containers/vmalert/config/alerts-fleet.yml` in your clone of fleet-stacks:

```yaml
groups:
  - name: fleet
    rules:
      - alert: NodeExporterDown
        expr: up{job="node"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Node Exporter is down on {{ $labels.instance }}"
          description: "vmagent on {{ $labels.instance }} has not been able to scrape Node Exporter for 5 minutes."
```

The name must end in `.yml`. vmalert loads `/etc/alerts/*.yml`, which is this folder inside the container, and skips every other name.

The `for` of five minutes covers five scrapes, since vmagent scrapes once a minute. A `for` shorter than about two scrapes lets one lost scrape fire the alert.

<details>
<summary>Background: what this rule cannot see</summary>

`up` is written by the scraper, and here the scraper is the vmagent on the same host. A host that is switched off sends nothing at all. Its `up` series stops, the query returns no series for it, and this rule stays silent.

A rule for a host that has gone quiet has to notice that a series is missing, not that its value is 0. That is a different query, built on functions such as `absent`, and is left out here to keep the example to one idea. Uptime Kuma, which checks from outside, covers that case today.

</details>

## 3. Commit and push {#push}

From your clone of fleet-stacks:

```bash
git add containers/vmalert/config/alerts-fleet.yml
git commit -m "Alert when a Node Exporter cannot be scraped"
git push
```

Push to the branch the fleet deploys from, which is `main` unless the inventory says otherwise.

## 4. Deploy the Stack and restart vmalert {#deploy}

1. In Komodo, open the `victoriametrics-server` Stack and click **Deploy**.
2. Watch the deploy log until the Stack shows as *Running*. The deploy updates the clone of fleet-stacks on ci01.
3. On ci01, have vmalert check the rule files without loading them.
4. Restart vmalert so that it reads the folder again.

The check for step 3 runs a second copy of the program inside the container, which reads the files and exits:

```bash
docker exec victoriametrics-vmalert /vmalert-prod -rule='/etc/alerts/*.yml' -dryRun
```

It prints no error when every file parses. When it names a file and a line, fix the file, push, and deploy again before going on. vmalert refuses to start with a rule file it cannot read, so a restart with a broken file stops every alert.

The restart for step 4:

```bash
docker restart victoriametrics-vmalert
```

vmalert keeps the state of its alerts in VictoriaMetrics and reads it back at start, so alerts that were pending or firing carry on from where they were.

## 5. Check the rule loaded {#loaded}

On ci01, ask vmalert for its rules and count the ones with the new name:

```bash
docker exec victoriametrics-vmalert wget -qO- http://127.0.0.1:8880/api/v1/rules \
  | grep -c NodeExporterDown
```

The answer is `1`. vmalert returns all its rules on one line, so the count is of lines and not of rules.

In a browser, `https://vmalert.ci01.home.myah-mitchell.com` shows the same thing: the group `fleet` is in the list of groups, with one rule and no error beside it.

When the container does not come back after the restart, a file did not parse. vmalert's log names the file and the line:

```bash
docker logs --tail 20 victoriametrics-vmalert
```

## 6. Test it {#test}

Make the condition true on one host and watch the alert go through its states. Pick a host whose metrics you can do without for ten minutes.

On that host, stop Node Exporter:

```bash
sudo systemctl stop prometheus-node-exporter
```

Within two minutes the alert `NodeExporterDown` shows on vmalert's page as *pending*, with the host's name in its `instance` label. Five minutes after that it shows as *firing*.

Open `https://alertmanager.ci01.home.myah-mitchell.com`. The same alert is listed there, with the labels `alertname`, `instance`, `job`, and `severity`. Those labels are what a route in Alertmanager would match on.

Start Node Exporter again:

```bash
sudo systemctl start prometheus-node-exporter
```

The alert leaves vmalert's page at the next evaluation after a scrape works. Alertmanager drops it a few minutes later.

> [!WARNING]
> Start Node Exporter again before you leave the host. While it is stopped, the host reports nothing about its disks, memory, or CPU, and every rule that reads them is blind.

## What's next

To have alerts reach a person, give Alertmanager a real receiver in `containers/alertmanager/config/alertmanager.yml`, and route on the `severity` label the rules set. The path from there to ntfy is not built. See [Alerts go nowhere yet](../../fleet-bootstrap/hosts/ci01-victoriametrics.md#alerts).

A rule can read logs as well as metrics. A group with `type: vlogs` holds LogsQL queries, and the repo has an example in `containers/vmalert/config/vlogs-example-alerts.yml-disabled`.

## Not yet confirmed {#unconfirmed}

- The whole procedure. No rule has been added to a running fleet.
- Whether Komodo's **Deploy** updates the clone when nothing in the Stack's definition changed. The page assumes it does.
- The labels in Komodo's UI, and the layout and state names on vmalert's and Alertmanager's pages.
- The check in step 4. It assumes the program is at `/vmalert-prod` in the image, and that the new file is already in the mounted folder before the restart.
- The form of the `/api/v1/rules` answer, which the count in step 5 depends on.
- The times in step 6. They follow from a scrape every 60 seconds, vmalert's default evaluation every minute, and the rule's `for`.
- Whether Node Exporter's unit is named `prometheus-node-exporter` on a host. The name is the one fleet-nixos refers to in `modules/node-exporter.nix`.
- The links vmalert puts on an alert. Its container is started with `--external.url=http://127.0.0.1:3000`, so a link to the alert's source opens only on a machine where Grafana answers at that address.
