# Core infrastructure (ci01)

core-infra is the fleet's plumbing for messages. It has five parts.

| Service | Job |
| --- | --- |
| ntfy | Push notifications, to a browser or a phone |
| mailrise | Takes mail from Proxmox, which can only send mail, and publishes it to ntfy |
| Postfix | The [relay](../../tools/glossary.md#relay) every service in the fleet sends its mail through |
| Mailpit | Keeps a copy of every message Postfix handles |
| Uptime Kuma | Uptime checks |

This page is part of ci01's build, and has no build of its own. [Automation and monitoring (ci01)](ci01-automation.md) describes the host and runs it, and sends you here for the steps below. The stack is [core-infra](../stacks/core-infra.md).

Status: written, not yet run.

## Prerequisites

- You are following [Automation and monitoring (ci01)](ci01-automation.md), and came here from its step 2, 4, or 5.
- A mailbox you can read, to receive a test message.

## Placeholders

| Placeholder | Meaning |
| --- | --- |
| `<ntfy-user>` | The name of your own ntfy account, created in step 3 |
| `<ntfy-token>` | The publishing token ntfy prints in step 3 |
| `<test-recipient>` | The address of a mailbox you can read |

## 1. Stage the values {#values}

Postfix hands the fleet's mail to a relay outside the fleet, such as your mail provider's submission service, and logs in there with an account. Two of its settings are in ci01's inventory entry, from [step 1 of ci01's page](ci01-automation.md#describe). The password is a Secret.

| Key | Set in | Value |
| --- | --- | --- |
| `POSTFIX_RELAYHOST` | The inventory | The relay and its port, such as `[smtp.myah-mitchell.com]:587` |
| `POSTFIX_RELAYHOST_USERNAME` | The inventory | The account's login |
| `POSTFIX_RELAYHOST_PASSWORD` | Komodo | The account's password |

The square brackets have Postfix connect to that host itself, with no lookup of the domain's MX records.

Create `POSTFIX_RELAYHOST_PASSWORD` in Komodo, with **Is Secret** ticked. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks. The register lists it under [Mail](../concepts/variables-and-secrets.md#mail-relay), with the values other stacks use to reach Postfix. Those are staged with id01.

Postfix relays only mail whose From address is in the fleet's domain, matched exactly. To send from another domain or from a sub-domain, add `POSTFIX_ALLOWED_SENDER_DOMAINS` beside the other two keys, with every domain in it and spaces between them.

<details>
<summary>Background: why the fleet's mail goes through Postfix and a relay</summary>

Services send mail for password resets, alerts, and reports. Each one could be given the relay's address and login, but then the relay's password sits in every stack, and changing relay means changing them all.

With Postfix on ci01 in between, a service is told one thing, ci01's address on port 25, and needs no login. Its port is opened to the internal subnet only. It checks the sender's domain, and it holds the one copy of the relay's password. It also queues mail while the relay is down, and copies every message to Mailpit, where you can read what a service sent without waiting for it to arrive.

Postfix could deliver straight to each recipient's mail server, and does when no relay is set. Receiving servers judge mail by the address it comes from, and a home connection has no standing with them, so that mail is junked or refused. A relay sends from addresses the receivers already trust, and is set up to send for your domain.

</details>

### Running with no relay {#no-relay}

Leave the two keys out of the inventory, and blank the password there so that no Secret has to exist:

```yaml
      komodo_stack_env:
        core-infra:
          POSTFIX_RELAYHOST_PASSWORD: ""
```

Postfix then delivers straight to each recipient's mail server. Most providers junk or refuse mail sent that way from a home connection. Mailpit still gets its copy of every message, which is enough to see what a service sent.

Go back to [step 2 of ci01's page](ci01-automation.md#values).

## 2. Verify {#verify}

The `core-infra` Stack has six services:

--8<-- "generated/core-infra/services.md"

Log in to ci01 and list the [project](../../tools/glossary.md#project)'s containers. The project is `core`:

```bash
docker ps --filter name=core- --format '{{.Names}}: {{.Status}}'
```

Six containers show, each named `core-` and the service, and each with `healthy` in its status. mailrise starts only after ntfy is healthy, so when both are missing, look at ntfy first.

Check the rules for the two ports the stack publishes on the host:

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport (25|8025) '
```

Two rules show, each with the internal subnet after `-s`, which is `172.16.7.0/24` in these pages. Neither service asks for a login. Postfix relays for any private address, and mailrise takes whatever arrives, so neither port is ever opened wider.

### Send a test message through Postfix {#postfix-test}

This proves the path every service's mail takes: the port, the firewall, the sender check, the relay, and the copy to Mailpit.

On a machine in the internal subnet, write a short message. Its From address is in the fleet's domain:

```bash
printf 'From: test@myah-mitchell.com\r\nTo: <test-recipient>\r\nSubject: core-infra test\r\n\r\nSent through Postfix on ci01.\r\n' > core-infra-test.eml
```

Send it to ci01 with curl, which speaks SMTP:

```bash
curl --url smtp://172.16.7.121:25 \
  --mail-from test@myah-mitchell.com \
  --mail-rcpt <test-recipient> \
  --upload-file core-infra-test.eml
```

curl prints nothing when Postfix accepts the message. Add `-v` to see Postfix's reply when it does not.

On ci01, read what Postfix did with it:

```bash
docker logs core-postfix 2>&1 | grep 'status='
```

Two lines show for the message, both with `status=sent`. One names Mailpit as the relay, which is the copy, and the other names yours.

Open `https://mailpit.ci01.home.myah-mitchell.com` in a browser. The test message is at the top of the list. Then check the mailbox of `<test-recipient>`, and its spam folder.

| Symptom | Cause |
| --- | --- |
| curl times out | Port 25 is not open from your address |
| `Client host rejected` | Your address is outside the private ranges Postfix relays for |
| `Recipient address rejected` | The From domain is not one Postfix relays for |
| `SASL authentication failed` | The relay's login or password is wrong |

A message with `status=bounced` and a reply from the relay was refused there. Most relays send only for domains set up on the account.

Delete `core-infra-test.eml` once the message arrives.

Go back to [step 4 of ci01's page](ci01-automation.md#verify).

## 3. Create ntfy's accounts {#ntfy}

ntfy sorts messages into topics. A sender publishes to a topic by name, and whoever subscribes to that topic receives the message. The fleet's ntfy denies everything to everyone until an account is given access, so nothing can publish or subscribe yet.

On ci01, create your own account, which is the one you read notifications with:

```bash
docker exec -it core-ntfy ntfy user add --role=admin <ntfy-user>
```

ntfy asks for a password, twice. Enter **a password of your own** both times, and store it in your password manager.

Then create a second account that can only publish, and only to the alert topics:

```bash
docker exec -it core-ntfy ntfy user add --role=user publisher
docker exec -it core-ntfy ntfy access publisher 'alerts-*' write-only
docker exec -it core-ntfy ntfy token add publisher
```

ntfy asks for a password for `publisher` as well. Enter **any long random password**. Nothing signs in with it, because the account is used through its token.

The last command prints a token that starts with `tk_`. That is `<ntfy-token>`. Store it in your password manager, since mailrise and Uptime Kuma both use it.

Confirm both accounts exist:

```bash
docker exec core-ntfy ntfy user list
```

The list shows `<ntfy-user>` as an admin, and `publisher` with write-only access to `alerts-*`.

## 4. Give mailrise its token {#mailrise}

mailrise takes mail on port 8025 and publishes it to ntfy. It routes on the recipient's address:

| Mail addressed to | Published to topic |
| --- | --- |
| `backups@mailrise.xyz` | `alerts-backups` |
| `infra@mailrise.xyz` | `alerts-infra` |

`mailrise.xyz` is mailrise's own stand-in domain. It is never looked up, and mail to any other domain is refused.

ci01's configuration put mailrise's config on the host, with a stand-in where the token goes. On ci01, put the token in both places and restart the container:

```bash
sudo sed -i 's/REPLACE_WITH_NTFY_TOKEN/<ntfy-token>/g' \
  /opt/docker/volumes/core/mailrise-secrets/mailrise.conf
docker restart core-mailrise
```

The file is copied only when nothing is at its path, so the token survives every later run and a rebuild.

On your own machine, watch the backups topic. The `--resolve` option sends the request to ci01 whether or not DNS has the name:

```bash
curl -sk -u <ntfy-user> \
  --resolve ntfy.home.myah-mitchell.com:443:172.16.7.121 \
  https://ntfy.home.myah-mitchell.com/alerts-backups/json
```

curl asks for the account's password, prints a line with `"event":"open"`, and waits.

In a second terminal, send mailrise a message:

```bash
printf 'From: test@mailrise.xyz\r\nTo: backups@mailrise.xyz\r\nSubject: mailrise test\r\n\r\nSent through mailrise on ci01.\r\n' > mailrise-test.eml
curl --url smtp://172.16.7.121:8025 \
  --mail-from test@mailrise.xyz \
  --mail-rcpt backups@mailrise.xyz \
  --upload-file mailrise-test.eml
```

The first terminal prints a line with `"event":"message"` and `"topic":"alerts-backups"`. Stop the watch with Ctrl+C.

## 5. Send Proxmox's notifications to mailrise {#proxmox}

In Proxmox VE, open *Datacenter > Notifications*, click **Add**, and choose **SMTP**. Fill in the target:

| Field | Value |
| --- | --- |
| *Endpoint Name* | `mail-to-ntfy` |
| *Server* | `172.16.7.121` |
| *Port* | `8025` |
| *Encryption* | **None** |
| *Authenticate* | Unticked |
| *From Address* | `pve@mailrise.xyz` |
| *Additional Recipient(s)* | `backups@mailrise.xyz` |

The server and port are mailrise on ci01. Encryption and the login are off because the fleet's mailrise is set up with neither, and its port is opened to the internal subnet only.

Start the watch from step 4 again, select the `mail-to-ntfy` target, and click **Test**. The watch prints a line with `"event":"message"`.

Do the same in Proxmox Backup Server, with `pbs@mailrise.xyz` as the From address. The From address plays no part in routing. It is what tells the two apart in the notification.

Keep the mail target Proxmox had before as a second target for a couple of weeks. A mistake anywhere in this path means no notification at all.

## 6. Set up Uptime Kuma {#uptime-kuma}

Open `https://uptime-kuma.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Uptime Kuma has no default account. The first visit asks you to create the admin account. Enter **a username and a password**, click **Create**, and store the password in your password manager.

Add the notification before any monitor exists, so that every monitor picks it up. Open *Settings > Notifications* and click **Setup Notification**:

| Field | Value |
| --- | --- |
| *Notification Type* | `ntfy` |
| *Friendly Name* | `ntfy alerts-infra` |
| *ntfy Topic* | `alerts-infra` |
| *Server URL* | `http://ntfy` |
| *Priority* | `3` |
| *Authentication Method* | **Access Token** |
| *Access Token* | `<ntfy-token>` |
| *Default enabled* | **Ticked** |

*Server URL* is ntfy's name on the network the two containers share, over plain HTTP. The request never passes through Traefik.

Start the watch from step 4 with `alerts-infra` in place of `alerts-backups`, then click **Test**. Uptime Kuma reports that the message was sent, and the watch prints a line with `"event":"message"`. Click **Save**.

| Error | Cause |
| --- | --- |
| `forbidden` | The token is wrong, or the topic does not start with `alerts-` |
| `ENOTFOUND ntfy` | Uptime Kuma cannot resolve ntfy's name, so the two share no network |

Go back to [step 5 of ci01's page](ci01-automation.md#first-access).

## Subscribing a phone {#phone}

The ntfy apps need a name that resolves and a certificate the phone trusts. ci01 has neither in [bootstrap mode](../../tools/glossary.md#bootstrap-mode), so this waits until the fleet has left it. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

Open `https://ntfy.home.myah-mitchell.com` in the phone's browser first. When it loads with no certificate warning, add that address as a server in the app, sign in as `<ntfy-user>` with **your ntfy password**, and subscribe to `alerts-backups` and `alerts-infra`.

## Hostnames {#hostnames}

Each service answers on its name under the host, such as `mailpit.ci01.home.myah-mitchell.com`.

| Name | Service | Sign-in outside bootstrap mode |
| --- | --- | --- |
| `ntfy` | ntfy | ntfy's own accounts |
| `uptime-kuma` | Uptime Kuma | Authentik, then its own account |
| `mailpit` | Mailpit | Authentik |
| `blackbox-exporter` | The probe exporter | Authentik |

ntfy also answers on `ntfy.home.myah-mitchell.com`, which is the address it gives out in its own links, and on `ntfy.myah-mitchell.com`.

In bootstrap mode Mailpit has nothing in front of it, and it holds a copy of every message the fleet sends, password resets included. It keeps 5000 messages or 30 days, whichever is less. See [Bootstrap mode](../concepts/bootstrap-mode.md#effects).

## Not yet confirmed {#unconfirmed}

- The whole page. core-infra has not been deployed by the run.
- The `ntfy` commands in step 3 and what they print, which come from ntfy's documentation and not from a run against version 2.11.0.
- The field names in Proxmox and Uptime Kuma, and Uptime Kuma's two error messages.
- The controls **Add** and **SMTP** in Proxmox, and **Create** on Uptime Kuma's first page.
- That `ntfy user add` asks for a password for the `publisher` account too.
- Whether the ntfy apps refuse a self-signed certificate. The page assumes they do.
- Notifications on iOS with the app closed. ntfy delivers those through an upstream server, set with `NTFY_UPSTREAM_BASE_URL`. fleet-stacks has no key for it, so it cannot be set from the inventory, and needs a change to ntfy's container definition.
- Whether the firewall's two rules decide who reaches ports 25 and 8025. Docker publishes a port with rules of its own, and what arrives for a published port is forwarded to the container, so it may never pass the chain the host's rules are in.
- Whether the client's own address reaches Postfix through the published port. Postfix decides by that address, so if Docker shows it the bridge's address instead, every sender looks local.
- blackbox-exporter is deployed and nothing probes through it. No scrape job in fleet-stacks names it, and no alert rule reads its results.
