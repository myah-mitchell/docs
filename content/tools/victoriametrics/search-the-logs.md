# Searching the logs

Every host's container logs, journal, and Traefik access log end up in VictoriaLogs on ci01. This page shows where to search them and gives the queries that answer the usual questions, using the fields the fleet's agents set. Use it when a service misbehaves and you want its log without logging in to its host.

Nothing here changes anything. The queries are written in LogsQL. See [LogsQL](index.md#logsql) for the grammar, and [Log collection and streams](index.md#log-streams) for how the lines get there.

Status: written, not yet run.

## Prerequisites

- The fleet has left bootstrap mode, so the agents ship logs. See [Leaving bootstrap mode](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md).
- Your machine resolves ci01's service names, and you can sign in through Authentik.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | A host's short name, such as `id01` |
| `<container>` | A container's name as `docker ps` shows it, such as `core-ntfy` |
| `<unit>` | A systemd unit's full name, such as `sshd.service` |

## 1. Open a search page {#open}

Two pages search the same store. Use whichever you have open.

/// tab | VictoriaLogs

Open `https://logs.ci01.home.myah-mitchell.com/select/vmui` in a browser. Type a query in the box at the top and press Enter.

///

/// tab | Grafana

Open `https://grafana.ci01.home.myah-mitchell.com`, go to *Explore*, and choose the **VictoriaLogs** data source. Type a query in the query field and click **Run query**.

///

Both pages have a time range picker of their own. A `_time` filter in the query narrows the search inside that range, so set the picker at least as wide as the filter.

## 2. Find the stream {#stream}

Start by finding out what the stream you want is called. This lists the 20 streams that logged the most in the last hour:

```text
_time:1h | stats by (stream_name) count() as lines | sort by (lines desc) | limit 20
```

The name's form tells you the source.

| `stream_name` | Source | Example |
| --- | --- | --- |
| `container-<container>` | A container's output | `container-core-ntfy` |
| `<unit>` | The journal, for that systemd unit | `sshd.service` |
| `host-` and a file name | A `.log` file under `/var/log` | `host-audit-audit.log` |
| `syslog-` and the sender | A device sending syslog to port 5140 | `syslog-172.16.7.1` |

A container's name starts with its stack's project, so the same service on two hosts has the same stream name. [Step 4](#host) tells them apart.

## 3. Read one source {#source}

For a container, give its stream in braces. This returns the last 15 minutes of ntfy's output:

```text
_time:15m {stream_name="container-core-ntfy"}
```

For a service of the host itself, name its unit. This returns the last hour of the SSH daemon's journal:

```text
_time:1h {stream_name="sshd.service"}
```

The braces take the same matchers as a metrics query, so `=~` matches a regular expression. This returns every container of the victoriametrics project:

```text
_time:15m {stream_name=~"container-victoriametrics-.*"}
```

## 4. Narrow to one host {#host}

Every line carries a `host` field. For a line from the journal it is the host's own name. For a container's line it is the name of the Vector container that read it, which has the host's name inside it. A word filter matches both:

```text
_time:15m {stream_name="container-system-vmagent"} host:<host>
```

## 5. Filter by level and text {#filter}

Vector settles each line's severity into the field `level`, in capitals: `ERROR`, `WARN`, `INFO`, `DEBUG`, or `UNKNOWN` when it found none. This returns every error in the last hour, from anything:

```text
_time:1h level:ERROR
```

A quoted phrase is looked for in the text of the line. Filters separated by spaces must all match:

```text
_time:1h {stream_name="container-core-postfix"} "status=bounced"
```

To see which sources are producing the errors, count them by stream:

```text
_time:1h level:ERROR | stats by (stream_name) count() as errors | sort by (errors desc)
```

A line the parser could not read keeps the level `UNKNOWN`, whatever it says. When a search by level finds nothing, search for the text.

## 6. Search Traefik's access log {#traefik}

Traefik's access log has fields of its own and no `stream_name`. Its lines are the ones with a `RouterName`, and each is one request.

| Field | Holds |
| --- | --- |
| `RouterName`, `ServiceName` | The route that matched and the service it sent the request to |
| `DownstreamStatus` | The status code returned to the client, as a number |
| `RequestMethod`, `RequestPath` | The request |
| `Duration` | The time taken, in nanoseconds |
| `level` | `error` for a status of 500 or more, `warn` for 400 or more, otherwise `info`. Lower case, unlike every other source |

This returns every request in the last hour that ended in a server error:

```text
_time:1h RouterName:* DownstreamStatus:>=500
```

This counts the last hour's requests by route and status:

```text
_time:1h RouterName:* | stats by (RouterName, DownstreamStatus) count() as requests | sort by (requests desc)
```

Cookies and the `Authorization` header are replaced with `REDACTED` before a line leaves its host.

## When a search finds nothing {#nothing}

| Check | How |
| --- | --- |
| The time range | Widen the page's picker and the `_time` filter together |
| That anything arrives | Run `_time:5m` with no other filter. Lines from every host scroll past |
| The stream's name | Run the query from [step 2](#stream) again and copy the name from its result |
| The host's agents | See [When it goes wrong](index.md#troubleshooting) |

VictoriaLogs keeps a year of logs, or 5 GB, whichever is reached first. A busy fleet reaches the size limit long before the year.

## What's next

A search you run often can become an alert. See [Adding an alert rule](add-an-alert-rule.md#whats-next).

For the rest of the language, see the [LogsQL documentation](https://docs.victoriametrics.com/victorialogs/logsql/).

## Not yet confirmed {#unconfirmed}

- The whole page. No log has been shipped by a running fleet, so no field name or value has been seen in VictoriaLogs. Every one is read from `containers/vector/config/vector-system.yml` in fleet-stacks.
- The `host` field. Its values are what Vector's sources document, and the filter in step 4 depends on the Vector container's name holding the host's name.
- The example stream names for a file and for syslog, which are built from the config's rules and not observed.
- The labels in VictoriaLogs' page and in Grafana's *Explore*.
- How Traefik's access log is stored. Vector's sink names an index, `traefik-access`, and a time field, `@timestamp`. The page assumes VictoriaLogs keeps neither as a thing to filter on, and finds the lines by `RouterName` instead.
