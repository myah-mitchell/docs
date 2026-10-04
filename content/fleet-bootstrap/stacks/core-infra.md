# core-infra

core-infra is where the fleet's notifications land, where its outgoing mail is relayed, and where uptime is checked from. It runs on one host, ci01. See [Core infrastructure (ci01)](../hosts/ci01-core-infra.md) for the build.

## What it runs {#services}

--8<-- "generated/core-infra/services.md"

| Service | Does |
| --- | --- |
| `ntfy` | Push notifications, over HTTP, to a phone or a browser |
| `mailrise` | Takes mail on port 8025 and turns each message into an ntfy notification |
| `postfix` | Takes mail on port 25 and relays it to your mail provider |
| `mailpit` | Keeps a copy of every message Postfix takes, to read in a browser |
| `blackbox-exporter` | Probes an address over HTTP, TCP, ICMP, or DNS when asked to, and reports the result as metrics |
| `uptime-kuma` | Checks services on a schedule and keeps their history |

The project is `core`, so the containers are named `core-` and the service, such as `core-postfix`.

mailrise is for senders that can only send mail, such as Proxmox. Postfix is for mail meant to reach a mailbox. Every message through Postfix is also copied to Mailpit over the stack's internal network, and the copy never leaves ci01. Mailpit keeps 5000 messages or 30 days, whichever is reached first.

ntfy refuses everything by default. A publisher or a subscriber needs an account or a token made in ntfy, and nobody can sign up.

## Values it reads {#values}

--8<-- "generated/core-infra/values.md"

The host page says what to put in it. See [Stage the values](../hosts/ci01-core-infra.md#values).

Three more keys decide where Postfix sends mail. They are settings with no reference behind them, so they are set in the inventory. See [Stack values](../concepts/fleet-private.md#stack-values).

| Key | Holds | Left blank |
| --- | --- | --- |
| `POSTFIX_RELAYHOST` | The relay's host and port, as `[<relay-host>]:<relay-port>` | Postfix delivers to each recipient's own mail server |
| `POSTFIX_RELAYHOST_USERNAME` | The account at the relay | Postfix does not log in |
| `POSTFIX_ALLOWED_SENDER_DOMAINS` | The sender domains Postfix relays for, separated by spaces | The fleet's domain alone |

The square brackets around the host tell Postfix to connect to it directly and skip the MX lookup.

## What the host needs {#host-setup}

--8<-- "generated/core-infra/host-setup.md"

The stack also needs a Traefik on the same host for the four web interfaces. The two mail ports work without one.

The host's firewall opens both mail ports to the internal subnet and to nothing else. Neither port asks for a login, so that rule is all that decides who may send. See [Not yet confirmed](#unconfirmed).

The copy of `mailrise.conf` holds a placeholder where an ntfy token goes, and mailrise can deliver nothing until the token is real. The host page covers the token.

mailrise picks the ntfy topic from the recipient. As committed, mail for `backups@mailrise.xyz` goes to `alerts-backups`. Mail for `infra@mailrise.xyz` goes to `alerts-infra`.

## Hostnames {#hostnames}

Four services have a route. With the host `ci01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Service | Sign-in |
| --- | --- | --- |
| `ntfy.ci01.home.myah-mitchell.com` | `ntfy` | ntfy's own |
| `mailpit.ci01.home.myah-mitchell.com` | `mailpit` | From the chain |
| `blackbox-exporter.ci01.home.myah-mitchell.com` | `blackbox-exporter` | From the chain |
| `uptime-kuma.ci01.home.myah-mitchell.com` | `uptime-kuma` | From the chain |

Each also answers with `ci01.` taken out of the name. ntfy answers on `ntfy.myah-mitchell.com` as well, and is the one service here labelled to be published through the hub on tf01.

Three routes take their chain from `TRAEFIK_AUTH_CHAIN`. The run sets that key to `chain-no-auth@file` in bootstrap mode. See [What it changes](../concepts/bootstrap-mode.md#changes).

> [!WARNING]
> In bootstrap mode Mailpit is open to anyone who can reach ci01. Its copies include password reset and sign-in links.

ntfy uses `chain-no-auth` in both modes, because what publishes to it cannot follow a redirect to Authentik.

## Verify {#verify}

In Komodo, the `core-infra` Stack shows as running with six services.

On the host, list the project's containers:

```bash
docker compose -p core ps
```

Every container shows `healthy` in the *STATUS* column. The checks for mailrise and Postfix each speak SMTP to the service, so `healthy` there means it answers inside the container.

Check the two published ports from another host on the internal subnet:

```bash
nc -zv 192.0.2.12 25
nc -zv 192.0.2.12 8025
```

Each command reports that the connection succeeded.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/core` | Holds |
| --- | --- |
| `ntfy-data` | ntfy's accounts, tokens, and access rules |
| `uptime-kuma-data` | Every monitor and its history |
| `mailrise-secrets` | `mailrise.conf`, with the ntfy token in it |
| `postfix-data` | The mail queue, which holds what is waiting for the relay |

All four are on the persistent disk, so they survive a rebuild of the VM. `mailpit-data` holds copies only, and `blackbox.yml` is the repo's example until you edit it.

## Not yet confirmed {#unconfirmed}

- What scrapes blackbox-exporter. A comment in fleet-stacks says vmagent does, over the stack's internal network, but vmagent runs in another project and no scrape config in the repo names it.
- Postfix with `POSTFIX_RELAYHOST_PASSWORD` set and no relay host.
- The two mail ports from outside the internal subnet. Docker publishes a port through rules of its own, and whether the host's rule for the subnet is what limits a published port has not been tried.
