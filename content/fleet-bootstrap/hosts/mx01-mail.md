# Mail (mx01)

mx01 runs Stalwart, a mail server that holds real mailboxes for the domain, and Bulwark, a webmail client for it. Accounts come from Authentik: SCIM creates each mailbox, and people sign in with their Authentik login.

Its own stack is [stalwart-server](../stacks/stalwart-server.md). The host is optional. Nothing else in the fleet depends on it, and the mail other services send already goes through Postfix on ci01. Skip this page if you do not want to host your own mailboxes.

The page assumes a paid Stalwart Enterprise licence. SCIM provisioning, which keeps mailboxes in step with Authentik, is an Enterprise feature.

Status: written, not yet run.

The steps inside Stalwart and Bulwark come from their documentation. Read [Not yet confirmed](#unconfirmed) before you start.

## Prerequisites

- The fleet has left bootstrap mode. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md), and [If the fleet is still in bootstrap mode](#bootstrap) for what mx01 can do before then.
- bh01 is finished, and Authentik answers on `auth.myah-mitchell.com` through its tunnel. Stalwart and Bulwark both check sign-ins against that public address. See [DMZ edge (bh01)](bh01-dmz-edge.md#publish).
- A Stalwart Enterprise licence key for the domain.
- A static public IPv4 address, an ISP that will set its reverse DNS record, and inbound port 25 not blocked by that ISP.
- A Cloudflare API token with DNS edit rights on the zone, for Stalwart's DNS records and certificate.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `<abbr_name>admin` |
| `<public-ip>` | The site's static public IPv4 address |
| `<license-key>` | Your Stalwart Enterprise licence key |
| `<client-id>` | The Authentik provider's client ID, from [step 4](#authentik) |
| `<client-secret>` | The Authentik provider's client secret, from step 4 |
| `<proxy-subnet>` | The `proxy` Docker network's subnet on mx01, read in [step 9](#settings) |
| `<cf-api-token>` | The Cloudflare API token from the prerequisites |
| `<scim-token>` | The Stalwart API key created in [step 12](#scim) |
| `<recovery-password>` | A throwaway password, chosen only for [recovery](#recovery) |

## 1. Check the public address {#public-address}

Do this before building anything. A residential range that other mail servers refuse is the most common reason self-hosted mail fails, and no setting on mx01 fixes it.

Check the reverse DNS record, from any machine:

```bash
dig -x <public-ip> +short
```

The answer is `mx.myah-mitchell.com.`. If it is your ISP's own name, ask the ISP to set the PTR record for `<public-ip>` to `mx.myah-mitchell.com`.

Check blocklists by entering `<public-ip>` at `https://check.spamhaus.org`. A listing on the PBL means your ISP has marked the range as not meant to send mail directly, and many providers refuse mail from it.

Check that outbound port 25 is open, from any machine on the site's internet connection:

```bash
nc -vz -w 5 gmail-smtp-in.l.google.com 25
```

The output ends with `succeeded`. A timeout means the ISP blocks the port.

If the blocklist check or the port check fails, Stalwart can still receive mail directly and send through a relay service. Set that up in Stalwart's outbound routing once [step 11](#domain) is done. The rest of this page is the same either way.

## 2. Describe the host {#describe}

In the private repo's `hosts.yml`, add mx01 to the `docker_host` group:

```yaml
    mx01:
      ansible_host: 198.51.100.12
      network_gateway: "198.51.100.1"
      serverHostname: "mx01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - stalwart-server
      komodo_stack_env:
        stalwart-server:
          BULWARK_OAUTH_ISSUER_URL: "https://auth.myah-mitchell.com/application/o/mail"
        system-agent:
          DOCKNS_WAN_IP: ""
          DOCKNS_CF_API_KEY: ""
          DOCKNS_CF_ACCOUNT_ID: ""
          DOCKNS_CF_ZONE_ID: ""
```

`network_gateway` is the DMZ's gateway, which a host on the DMZ sets for itself, as [bh01](bh01-dmz-edge.md#describe) does.

The issuer has no trailing slash here. Bulwark wants it without one, while Stalwart in [step 13](#oidc) has to match Authentik's issuer exactly, slash included.

The four blank keys stop dockns from writing public DNS records for mx01. The public names come from tunnel routes in [step 10](#publish) and from Stalwart in step 11, and a dockns record for the same name would fight both. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  mx01 = {
    server       = "vh01"
    vm_id        = 8012
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 8
    ipv4_address = "198.51.100.12/24"
    ipv4_gateway = "198.51.100.1"
    dns_servers  = ["198.51.100.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 40 }
    }
  }
```

Two cores and 4 GB are enough for a household's mail. Stalwart is a single program with an embedded store, and Bulwark is one Node process. The store holds the mail itself, so this is the one persistent disk that grows with use. Start at 40 GB and grow it as the mailboxes fill.

mx01 sits in the DMZ beside bh01 because it takes connections straight from the internet on its mail ports.

Then generate mx01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 3. Open the paths and forward the mail ports {#ports}

Allow these on the router, between the DMZ and the internal VLAN. The run itself needs the first two.

| From | To | Port | Used for |
| --- | --- | --- | --- |
| The control node, ci01 at `192.0.2.12` | mx01 | `22/tcp` | The run installs and deploys over SSH |
| mx01 | km01, `192.0.2.11` | `9120/tcp` | Periphery dials Komodo Core |
| mx01 | tf01, `192.0.2.15` | `6379/tcp` | The route publisher writes mx01's routes |
| mx01 | ci01 and id01 | `443/tcp` | Telemetry, and the sign-in in front of mx01's dashboard |

dockns also needs to reach the UniFi console, at whatever address `DOCKNS_UNIFI_HOST` names. bh01 reaches mx01 inside the DMZ, which needs no rule unless your DMZ isolates its hosts from each other.

Outbound, mx01 needs the internet on ports 80 and 443 for NixOS packages, images, and Let's Encrypt, and on port 25 to deliver mail.

tf01's own firewall opens its Redis port to one range, which bh01's page set to hold the DMZ. Check that the range holds mx01's address, on tf01:

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport 6379 '
```

The range after `-s` includes `198.51.100.12`. If it does not, widen `docker_stacks_internal_subnet` on tf01 and run tf01 again. See [Admit the DMZ on tf01](bh01-dmz-edge.md#boundary-tf01).

Then forward these ports from the router's public side to `198.51.100.12`, TCP only:

| Port | Used for |
| --- | --- |
| `25` | Mail arriving from other servers |
| `465` | Mail clients sending, implicit TLS |
| `587` | Mail clients sending, STARTTLS |
| `993` | Mail clients reading, IMAP over TLS |

Do not forward 80, 443, or 8080. The web side reaches the internet through bh01's tunnel, never through a port forward.

mx01's own firewall opens the same four ports. They come from the stack's `setup.yaml`, through `nixos/hosts/mx01.json`, so no command on mx01 opens them. [Step 7](#verify) checks them.

## 4. Create the Authentik application {#authentik}

One Authentik application covers both services. Bulwark signs people in through it, and Stalwart accepts the tokens it issues.

### Create the group {#authentik-group}

In Authentik's admin interface, go to *Directory > Groups* and create a group named `mail-users`. Add yourself to it.

Only members of this group get a mailbox. That matters because the Stalwart licence is sold by mailbox count.

### Create the application and provider {#authentik-provider}

Go to *Applications > Applications* and click **Create with provider**. Fill in the application:

| Field | Value |
| --- | --- |
| *Name* | `Mail` |
| *Slug* | `mail` |

Choose *OAuth2/OpenID Provider* as the provider type, then fill in the provider:

| Field | Value |
| --- | --- |
| *Client type* | Confidential |
| *Redirect URIs* | Regex, `https://webmail\.myah-mitchell\.com/.*` |
| *Signing Key* | `authentik Self-signed Certificate` |

Copy the *Client ID* and *Client Secret* shown on that page. They are `<client-id>` and `<client-secret>`.

The signing key matters. Without one, Authentik signs tokens with the client secret, and Stalwart cannot check a token signed that way.

The redirect URI is a regex because Bulwark's exact callback path is not documented. Once sign-in works in step 13, tighten it to the path Authentik's logs show.

### Limit it to the group {#authentik-binding}

On the new application, open *Policy / Group / User Bindings*, click **Bind existing policy / group / user**, and bind the `mail-users` group.

The application's issuer is `https://auth.myah-mitchell.com/application/o/mail/`, with the trailing slash.

## 5. Stage the values {#values}

Create these four in Komodo before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

| Name | Kind | Value |
| --- | --- | --- |
| `STALWART_LICENSE_KEY` | Secret | `<license-key>` |
| `BULWARK_SESSION_SECRET_KEY` | Secret | 96 alphanumeric characters |
| `MAIL_OIDC_CLIENT_ID` | Secret | `<client-id>` |
| `MAIL_OIDC_CLIENT_SECRET` | Secret | `<client-secret>` |

Generate the session key in a shell:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 96; echo
```

`BULWARK_SESSION_SECRET_KEY` encrypts Bulwark's remember-me sessions and synced settings. Changing it later signs everyone out and discards their synced settings.

Every other value the three stacks read exists already, from [Setting up Komodo](../foundation/komodo-setup.md#traefik) and [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md#values).

## 6. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `mx01`.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=mx01
```

///

The run creates the VM, installs NixOS on it, deploys its configuration, and has Komodo deploy three Stacks: `system-agent-mx01`, `traefik-agent-mx01`, and `stalwart-server`.

Stalwart starts in its setup mode, with no mail services running yet. Bulwark waits for Stalwart to be healthy and then starts, though it cannot sign anyone in until step 13.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/system-agent/manual.md"

--8<-- "generated/traefik-agent/manual.md"

--8<-- "generated/stalwart-server/manual.md"

--8<-- "manual-stack-deploy.md"

</details>

## 7. Verify {#verify}

--8<-- "verify-run.md"

The `stalwart-server` Stack has two services:

--8<-- "generated/stalwart-server/services.md"

Log in to mx01 and check the firewall and the folders:

```bash
ssh <admin>@198.51.100.12
```

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport (25|465|587|993) '
sudo ls -ln /opt/docker/volumes/mail /opt/docker/volumes/mail/bulwark-data
```

Four rules show, one for each mail port. None names a source address after `-s`, and each ends in `-j nixos-fw-accept`. The two `stalwart-` folders are owned by `102000`, and `bulwark-data` and the four folders inside it by `101001`.

Neither service runs as the fleet's shared user. Each runs as its own image's user, which the host sees with Docker's offset added. See [UID offsets](../concepts/host-layout.md#uid-offsets).

`stalwart-data` holds every mailbox, account, and setting you make in Stalwart's WebUI. Back it up.

## 8. Run Stalwart's setup wizard {#wizard}

Read the one-time admin password Stalwart printed on first start, on mx01:

```bash
docker logs mail-stalwart 2>&1 | grep -A8 'bootstrap mode'
```

Stalwart calls its own first-start state bootstrap mode, which has nothing to do with the fleet's. The password changes every time Stalwart starts in that state, so read it again after any restart.

Open `https://mail.mx01.home.myah-mitchell.com/admin` in a browser. The name needs a DNS record pointing at mx01, or an entry in your own hosts file. Sign in as `admin` with that password.

Work through the wizard:

1. Set the server hostname to `mx.myah-mitchell.com`.
2. Keep the default embedded data store.
3. Create the permanent administrator account, and store its password in your password manager.

The wizard writes `config.json` and restarts Stalwart. Sign back in with the permanent administrator account at the same address.

## 9. Finish Stalwart's server settings {#settings}

### Trust Traefik {#trust-proxy}

Read the `proxy` network's subnet, on mx01:

```bash
docker network inspect proxy --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}'
```

That is `<proxy-subnet>`. In the WebUI, go to *Settings > Network > General* and add `<proxy-subnet>` to the trusted proxy networks.

Do this now, before anything reaches Stalwart from outside. Every web request arrives from Traefik's address, and Stalwart's automatic ban can end up banning Traefik itself, which locks everyone out at once.

### Add the licence {#licence}

Go to *Settings > Enterprise*. Set the licence key's source to *Environment Variable*, with the variable name `STALWART_LICENSE_KEY`.

Restart the `stalwart` container from Komodo so that it reads its settings again, then sign out and back in. The Enterprise sections of the WebUI are now available.

### Add Cloudflare as a DNS provider {#dns-provider}

Go to *Settings > Network > DNS > DNS Providers* and add a *Cloudflare* provider, with `<cf-api-token>` as its secret.

Stalwart uses it in step 11, both to publish the domain's mail records and to prove it owns `mx.myah-mitchell.com` for a certificate.

## 10. Publish the web hostnames through bh01 {#publish}

Stalwart's web side, Bulwark, and the two well-known names mail software fetches all go through bh01's tunnel. Follow [Publishing a hostname](bh01-dmz-edge.md#publish) for each of these four:

| Hostname | Serves |
| --- | --- |
| `mail.myah-mitchell.com` | Stalwart's WebUI, JMAP, and SCIM |
| `webmail.myah-mitchell.com` | Bulwark |
| `autoconfig.myah-mitchell.com` | Mail client settings, from Stalwart |
| `mta-sts.myah-mitchell.com` | The domain's MTA-STS policy, from Stalwart |

Both services do their own authentication, so they are safe to publish before Authentik is wired in. Until step 13, only the administrator account from [step 8](#wizard) can sign in to anything.

Open `https://mail.myah-mitchell.com/admin` from outside your network, such as from a phone with Wi-Fi off. Stalwart's sign-in page loads.

## 11. Add the domain, its DNS records, and a certificate {#domain}

> [!WARNING]
> This step moves the domain's inbound mail to mx01. If `myah-mitchell.com` already receives mail somewhere else, that stops once the MX record changes. Turn off Cloudflare Email Routing for the zone first if it is on, because it owns the MX records while enabled.

### Create the A record by hand {#a-record}

In the Cloudflare dashboard, add an `A` record for `mx.myah-mitchell.com` pointing at `<public-ip>`, with the proxy status set to *DNS only*.

It has to be DNS only. Cloudflare's proxy carries web traffic, not mail.

### Add the domain {#add-domain}

In the WebUI, go to *Management > Domains > Domains*. Open `myah-mitchell.com` if the wizard created it, or create it.

Link it to the Cloudflare DNS provider from step 9, so that Stalwart publishes and maintains its own records. Stalwart rotates its DKIM keys every 90 days by default, which only works if it can update DNS itself.

Exclude the `autoconfig`, `autodiscover`, and `mta-sts` CNAME records from what Stalwart publishes. Step 10's tunnel routes already own `autoconfig` and `mta-sts`, and a second record for the same name would replace them.

Once it has published, compare the domain's expected zone, shown in its `dnsZoneFile` field, with the zone in the Cloudflare dashboard. The zone holds MX, SPF, DKIM, DMARC, TLS reporting, MTA-STS, and the mail client SRV records.

If the domain already has an SPF record, merge the two into one. A domain with two SPF records fails SPF entirely.

### Get a certificate for the mail ports {#certificate}

Traefik's certificate covers only the web side. Clients connecting to ports 465, 587, and 993, and servers using STARTTLS on 25, see Stalwart's own certificate.

Add an ACME provider for Let's Encrypt that uses the DNS-01 challenge through the Cloudflare DNS provider, for `mx.myah-mitchell.com`. Restart the `stalwart` container once it reports the certificate as issued.

Check it from any machine:

```bash
openssl s_client -connect mx.myah-mitchell.com:993 \
  -servername mx.myah-mitchell.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer
```

The subject is `mx.myah-mitchell.com` and the issuer is Let's Encrypt. From inside the network this needs hairpin NAT on the router, so use an outside connection if it hangs.

## 12. Turn on SCIM provisioning {#scim}

SCIM lets Authentik create, update, and disable Stalwart accounts as group membership changes. Without it, a mailbox only exists after its owner has signed in once, and mail sent to them before that is refused.

Do this before step 13. The administrator account from step 8 is the one you use here, and it may stop being able to sign in once Stalwart trusts Authentik.

### On Stalwart {#scim-stalwart}

In *Management > Domains > Domains*, open `myah-mitchell.com` and turn on `allowScimProvisioning`.

In *Management > Accounts*, create an account named `scim` in that domain, to act as Authentik's service account. Give it these permissions:

- `scimAccess`
- `authenticate`
- `sysAccountGet`
- `sysAccountCreate`
- `sysAccountUpdate`

On that account, go to *Credentials > API Keys* and create a key in *Replace* mode. Stalwart shows the secret one time. That secret is `<scim-token>`.

### On Authentik {#scim-authentik}

Go to *Applications > Providers*, click **Create**, and choose *SCIM Provider*.

| Field | Value |
| --- | --- |
| *Name* | `mail-scim` |
| *URL* | `https://mail.myah-mitchell.com/scim/v2` |
| *Token* | `<scim-token>` |
| *Compatibility mode* | Default |
| *Group* filter | `mail-users` |

Then edit the `Mail` application from step 4 and add `mail-scim` under *Backchannel Providers*.

### Check the first sync {#scim-sync}

Open the `mail-scim` provider in Authentik and start a sync. In Stalwart, *Management > Accounts* now lists an account for each member of `mail-users`.

Check how the account names came out. Stalwart has to see the same name here as in step 13, which builds it from the Authentik username plus `@myah-mitchell.com`.

If the accounts are named with the bare username instead, add a SCIM property mapping in Authentik under *Customization > Property Mappings* and select it on `mail-scim`:

```python
return {
    "userName": f"{request.user.username}@myah-mitchell.com",
}
```

### Make yourself an administrator {#scim-admin}

In *Management > Accounts*, open your own account, the one SCIM created, and give it the administrator role. This is the account you manage Stalwart with from step 13 onward.

## 13. Sign in through Authentik {#oidc}

Read [Recovering admin access](#recovery) before this step. If this goes wrong, the recovery procedure is how you get back in.

### Create the OIDC directory {#oidc-directory}

In the WebUI, create a directory of type OIDC:

| Field | Value |
| --- | --- |
| `issuerUrl` | `https://auth.myah-mitchell.com/application/o/mail/` |
| `requireAudience` | `<client-id>` |
| `claimUsername` | `preferred_username` |
| `usernameDomain` | `myah-mitchell.com` |
| `claimName` | `name` |

The issuer must match Authentik's exactly, trailing slash included. A mismatch shows up in Stalwart's log as `InvalidIssuer`.

`usernameDomain` turns an Authentik username such as `myah` into the account `myah@myah-mitchell.com`, which is the name SCIM created in step 12.

### Switch authentication to it {#oidc-switch}

Go to *Settings > Authentication > General* and set the directory to the OIDC directory you just created.

Keep the existing admin session open in the first window. In a private browser window, open `https://webmail.myah-mitchell.com` and sign in with your Authentik account. Bulwark shows your mailbox.

If it fails, check Stalwart's log from mx01:

```bash
docker logs mail-stalwart 2>&1 | grep -iE 'oidc|jwt|issuer|audience'
```

## 14. Send and receive {#mail-check}

### Receive {#receive}

From a mailbox outside the domain, send a message to your own address at `myah-mitchell.com`. It arrives in Bulwark within a minute.

### Send {#send}

Reply to it from Bulwark. In the outside mailbox, open the message's original headers. They show `spf=pass`, `dkim=pass`, and `dmarc=pass`.

A `fail` or `none` on any of the three means the DNS records from step 11 are missing or wrong. Fix it before sending real mail, because providers remember an address that sent unauthenticated mail.

### Check port 25 from outside {#port-25}

Use an outside SMTP test, such as MXToolbox's, against `mx.myah-mitchell.com`. It reports Stalwart's banner, working STARTTLS, and no open relay.

Then check that Stalwart saw the tester's real address and not a Docker one:

```bash
docker logs mail-stalwart 2>&1 | tail -50
```

## If the fleet is still in bootstrap mode {#bootstrap}

mx01 is placed after the fleet leaves bootstrap mode because most of this page needs what bootstrap mode leaves out. A run in bootstrap mode deploys `traefik-bootstrap-mx01` and `stalwart-server`, and nothing else.

| Part of mx01 | In bootstrap mode | After it |
| --- | --- | --- |
| Mail ports | Open, and served by Stalwart | The same |
| Web certificate | Self-signed, so the browser warns | Let's Encrypt |
| Public web names | None. mx01 has no route publisher | Published through bh01 |
| Sign-in through Authentik | Not possible. Authentik has no public name | Works from step 13 |
| Metrics and logs | Not shipped | Shipped to ci01 |

Steps 1 to 9 work in bootstrap mode, apart from the Authentik application, whose public address nothing answers on yet. Steps 10, 12, and 13 have to wait.

## Recovering admin access {#recovery}

Use this if no administrator can sign in, for example after an OIDC setting in step 13 goes wrong.

Stop the `stalwart` container from Komodo. Then on mx01, start a one-off copy in recovery mode against the same volumes:

```bash
docker run --rm -it --name mail-stalwart-recovery \
  --volumes-from mail-stalwart \
  -e STALWART_RECOVERY_MODE=1 \
  -e STALWART_RECOVERY_ADMIN=recovery:<recovery-password> \
  -p 127.0.0.1:8080:8080 \
  stalwartlabs/stalwart:v0.16.22
```

Recovery mode runs only the admin interface, with no mail services, and listens only on mx01's loopback address. Reach it from your admin machine through an SSH tunnel:

```bash
ssh -L 8080:127.0.0.1:8080 <admin>@198.51.100.12
```

Open `http://127.0.0.1:8080/admin` and sign in as `recovery` with `<recovery-password>`. Fix the problem, press **Ctrl+C** in the recovery container's terminal, and start the `stalwart` container again from Komodo.

> [!WARNING]
> Never add either recovery variable to the stack itself. `STALWART_RECOVERY_ADMIN` is an administrator login that bypasses every directory.

## Later changes {#later}

Desktop and phone mail clients are the next thing to try. Clients that support OAuth can sign in through Authentik directly. The rest need an app password from `https://mail.myah-mitchell.com/account`, if that works out. See [Not yet confirmed](#unconfirmed).

Two changes are possible later without rebuilding anything here.

Postfix on ci01 can relay through Stalwart in place of an outside relay, with `POSTFIX_RELAYHOST` set to `[mx.myah-mitchell.com]:587`. That needs a Stalwart account Postfix can log in to with a password, which the OIDC directory does not give it.

Inbound and outbound mail can move to a pair of cloud servers that relay to mx01 over a private link. That changes the MX record and Stalwart's outbound route, and removes the need for the port forwards in [step 3](#ports).

## What's next

mx01 is finished, and nothing else in the running order waits on it.

ap01 is the last host, and the pattern for hosts of your own. See [Applications (ap01)](ap01-applications.md).

## Not yet confirmed {#unconfirmed}

Each of these came from documentation or from reading the stack, not from a running system. Confirm them on the first real run and correct this page.

- The whole page. mx01 has not been built by the run.
- Authentik's public name. Both services check sign-ins against `auth.myah-mitchell.com`, and authentik-server carries no `kop-public` labels, so bh01 has no route for it yet.
- Whether Stalwart's health check passes before the wizard has run. Bulwark waits for it, and so does the run's last stage.
- The exact WebUI menu paths and field labels in steps 8 to 13. Stalwart moved its configuration into the WebUI in 0.16, and most published guides still describe the older TOML files.
- Whether port 8080 serves the whole WebUI, JMAP, and SCIM after the wizard finishes, or only during setup. The compose file routes all web traffic there.
- Whether Authentik's access tokens carry the client ID as their audience and include `preferred_username`. Stalwart's `requireAudience` and `claimUsername` depend on both.
- The account name Authentik's SCIM provider sends, and whether Stalwart accepts Authentik's default user attributes such as `photos` and `locale`. Stalwart returns an error for attributes it does not recognise.
- Whether the step 8 administrator can still sign in once the OIDC directory is active. This page assumes not, which is why step 12 makes your own account an administrator first.
- Whether OIDC accounts can create app passwords in Stalwart's account manager at `/account`. Stalwart's documentation says both yes and no, and desktop mail clients without OAuth support need them.
- Bulwark's OAuth callback path, hence the regex redirect URI in step 4.
- Whether a port published from Docker shows Stalwart the real client address. Docker normally preserves it for IPv4, and step 14 checks.
- The recovery procedure, which comes from the container's notes in docker-stacks. A host sets `DOCKER_CONTENT_TRUST=1` for commands typed in a shell, and whether `docker run` then accepts the image has not been tried.
- dockns on mx01 with the four keys blank, and whether it reaches the UniFi console from the DMZ.
- Whether tf01's firewall filters the Redis port at all, as on [bh01](bh01-dmz-edge.md#unconfirmed).
