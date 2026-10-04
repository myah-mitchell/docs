# stalwart-server

stalwart-server is [Stalwart](../../tools/stalwart/index.md), a mail server that holds mailboxes for the domain, and Bulwark, a webmail client for it. The stack is optional, and nothing else in the fleet depends on it. It runs on one host, mx01. See [Mail (mx01)](../hosts/mx01-mail.md) for the build.

## What it runs {#services}

--8<-- "generated/stalwart-server/services.md"

| Service | Does |
| --- | --- |
| `stalwart` | Takes and sends mail on the four mail ports. On port 8080 it serves its web interface, the discovery documents, and JMAP, the mail protocol over HTTP that webmail uses |
| `bulwark` | Webmail, on port 3000. It reads mail from Stalwart over JMAP and signs people in through Authentik |

The [project](../../tools/glossary.md#project) is `mail`, so the containers are `mail-stalwart` and `mail-bulwark`.

The stack has no database container. Stalwart keeps every mailbox, account, and setting in its own data folder. Its config file is written by the setup wizard on the first start.

Neither service sits on an internal network. Stalwart has to reach other mail servers, and both have to reach Authentik's public name.

## Values it reads {#values}

--8<-- "generated/stalwart-server/values.md"

The host page says what to put in each and when. See [Stage the values](../hosts/mx01-mail.md#values).

Two more keys are settings with no reference behind them, so they are set in the inventory. See [Stack values](../concepts/fleet-private.md#stack-values).

| Key | Holds | Left blank |
| --- | --- | --- |
| `BULWARK_OAUTH_ISSUER_URL` | The issuer address of the Authentik provider made for mail | Sign-in through Authentik cannot work |
| `BULWARK_JMAP_SERVER_URL` | Stalwart's public address | `https://mail.` and the domain |

## What the host needs {#host-setup}

--8<-- "generated/stalwart-server/host-setup.md"

The stack also needs a Traefik on the same host for the web side.

The owners differ from the fleet's usual one because neither image runs as UID 1000. Stalwart runs as 2000 and Bulwark as 1001, which the host sees as 102000 and 101001. See [Why 100000 and 101000](../concepts/host-layout.md#uid-offsets).

The four mail ports are open to any address. Mail cannot pass through an HTTP router, so Stalwart publishes them on the host itself, and the network's router forwards them from the internet.

| Port | Carries |
| --- | --- |
| 25 | Mail from other servers |
| 465 | Submission from mail clients, TLS from the first byte |
| 587 | Submission from mail clients, with STARTTLS |
| 993 | IMAP, TLS from the first byte |

## Hostnames {#hostnames}

Traefik routes six names to Stalwart and four to Bulwark. With the host `mx01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Service |
| --- | --- |
| `mail.myah-mitchell.com` | `stalwart`. The public name, which Stalwart builds its discovery documents from |
| `autoconfig.myah-mitchell.com` | `stalwart`. Mail clients fetch their settings from it |
| `mta-sts.myah-mitchell.com` | `stalwart`. Other mail servers fetch the domain's TLS policy from it |
| `mail.home.myah-mitchell.com` | `stalwart` |
| `mail.mx01.home.myah-mitchell.com` | `stalwart` |
| `stalwart.mx01.home.myah-mitchell.com` | `stalwart` |
| `webmail.myah-mitchell.com` | `bulwark`. The public name |
| `webmail.home.myah-mitchell.com` | `bulwark` |
| `webmail.mx01.home.myah-mitchell.com` | `bulwark` |
| `bulwark.mx01.home.myah-mitchell.com` | `bulwark` |

Both routes use the `chain-no-auth` [chain](../../tools/glossary.md#auth-chain) in [both modes](../concepts/bootstrap-mode.md). Stalwart does its own authentication, for clients that cannot follow a redirect, and Bulwark signs people in through Authentik itself.

Both services are labelled to be published through the [hub](../../tools/glossary.md#hub) on tf01, which happens once mx01 runs traefik-agent.

## Verify {#verify}

In Komodo, the `stalwart-server` Stack shows as running with two services.

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p stalwart-server ps
```

Both containers show `healthy` in the *STATUS* column. Each check asks the service's own HTTP port for its health, so it says nothing about the mail ports. Bulwark starts after Stalwart is healthy.

Check a mail port from another host:

```bash
nc -zv 172.16.8.121 25
```

The command reports that the connection succeeded.

## Data worth keeping {#data}

| Folder under `/opt/docker/volumes/mail` | Holds |
| --- | --- |
| `stalwart-data` | Every mailbox, account, and setting |
| `stalwart-config` | The config file the setup wizard wrote |
| `bulwark-data` | Bulwark's admin settings and each person's synced settings |

All three are on the [persistent disk](../../tools/glossary.md#persistent-disk), so they survive a rebuild of the VM. `stalwart-data` grows with the mail it holds, so watch the disk it is on.

## Not yet confirmed {#unconfirmed}

- The whole stack. It was composed from Stalwart's and Bulwark's documentation and has not run in the fleet.
- Port 8080 after the setup wizard finishes. Stalwart's documentation has a reverse proxy send the web interface, JMAP, and SCIM there, and every route does. It has not been seen on a running container.
- Whether a port published from Docker shows Stalwart the sender's real address.
- The stack in bootstrap mode. Bulwark needs Authentik reachable at its public name, and the public names need the hub and the tunnel.
