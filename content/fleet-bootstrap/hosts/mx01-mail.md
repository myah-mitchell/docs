# Mail (mx01)

mx01 runs [Stalwart](../../tools/stalwart/index.md), a mail server that holds real mailboxes for the domain, and Bulwark, a webmail client for it. Accounts come from [Authentik](../../tools/authentik/index.md): SCIM creates each mailbox, and people sign in with their Authentik login. SCIM, the System for Cross-domain Identity Management, is a protocol by which one system creates and removes accounts in another.

Its own [stack](../../tools/glossary.md#stack) is [stalwart-server](../stacks/stalwart-server.md). The host is optional. Nothing else in the fleet depends on it, and the mail other services send already goes through Postfix on ci01. Skip this page if you do not want to host your own mailboxes.

The page assumes a paid Stalwart Enterprise licence. SCIM provisioning, which keeps mailboxes in step with Authentik, is an Enterprise feature.

Status: written, not yet run.

The steps inside Stalwart and Bulwark come from their documentation. Read [Not yet confirmed](#unconfirmed) before you start.

This is the longest page in the guide, and it runs in four stretches.

| Steps | What they do |
| --- | --- |
| [1](#public-address) to [3](#ports) | Check that the site can send mail at all, describe the host, and open the network |
| [4](#authentik) to [7](#verify) | Prepare the sign-in, stage the values, and build the host |
| [8](#wizard) to [11](#domain) | Set up Stalwart, publish its web side, and give the domain its DNS records |
| [12](#scim) to [14](#mail-check) | Connect the accounts to Authentik, then send and receive a message |

At the end, each member of one Authentik group has a mailbox at the domain, reads it in a browser, and exchanges mail with the rest of the internet. The mail terms the page uses, from MX records to DKIM, are explained in the [Stalwart primer](../../tools/stalwart/index.md#ideas).

## Prerequisites

- The fleet has left bootstrap mode. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md), and [If the fleet is still in bootstrap mode](#bootstrap) for what mx01 can do before then.
- bh01 is finished, and Authentik answers on `auth.myah-mitchell.com` through its tunnel. Stalwart and Bulwark both check sign-ins against that public address. See [DMZ edge (bh01)](bh01-dmz-edge.md#publish).
- A Stalwart Enterprise licence key for the domain.
- A static public IPv4 address, an ISP that will set its reverse DNS record, and inbound port 25 not blocked by that ISP.
- A Cloudflare API token with DNS edit rights on the zone, for Stalwart's DNS records and certificate.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
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

The answer is `mx.myah-mitchell.com.`. If it is your ISP's own name, ask the ISP to set the PTR record for `<public-ip>` to `mx.myah-mitchell.com`. A PTR record maps an address back to a name, and receiving servers distrust mail from an address whose name does not match the server's.

Check blocklists by entering `<public-ip>` at `https://check.spamhaus.org`. A listing on the PBL, Spamhaus's Policy Blocklist, means your ISP has marked the range as not meant to send mail directly, and many providers refuse mail from it.

Check that outbound port 25 is open, from any machine on the site's internet connection:

```bash
nc -vz -w 5 gmail-smtp-in.l.google.com 25
```

The output ends with `succeeded`. A timeout means the ISP blocks the port.

If the blocklist check or the port check fails, Stalwart can still receive mail directly and send through a relay service. Set that up in Stalwart's outbound routing once [step 11](#domain) is done. The rest of this page is the same either way.

## 2. Describe the host {#describe}

In the [private repo](../../tools/glossary.md#private-repo)'s `hosts.yml`, add mx01 to the `docker_host` group:

```yaml
    mx01:
      ansible_host: 172.16.8.121
      network_gateway: "172.16.8.1"
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

`komodo_stack_env` sets values in a stack's environment for this host alone. See [Stack values](../concepts/fleet-private.md#stack-values).

`BULWARK_OAUTH_ISSUER_URL` is the address of the Authentik application that [step 4](#authentik) creates. The issuer has no trailing slash here. Bulwark wants it without one, while Stalwart in [step 13](#oidc) has to match Authentik's issuer exactly, slash included.

The four blank keys stop dockns, the service in system-agent that writes DNS records for a host's containers, from writing public DNS records for mx01. The public names come from tunnel routes in [step 10](#publish) and from Stalwart in step 11, and a dockns record for the same name would fight both. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  mx01 = {
    server       = "vh01"
    vm_id        = 8121
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 8
    ipv4_address = "172.16.8.121/24"
    ipv4_gateway = "172.16.8.1"
    dns_servers  = ["172.16.8.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 40 }
    }
  }
```

Two cores and 4 GB are enough for a household's mail. Stalwart is a single program with an embedded store, and Bulwark is one Node process.

The store holds the mail itself, so this is the one persistent disk that grows with use. Start at 40 GB and grow it as the mailboxes fill.

mx01 sits in the DMZ beside bh01 because it takes connections straight from the internet on its mail ports.

Then generate mx01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 3. Open the paths and forward the mail ports {#ports}

Allow these four paths on the router, between the DMZ and the internal VLAN. The run itself needs the first two.

| From | To | Port | Used for |
| --- | --- | --- | --- |
| The control node, ci01 at `172.16.7.121` | mx01 | `22/tcp` | The run installs and deploys over SSH |
| mx01 | km01, `172.16.7.101` | `9120/tcp` | Periphery dials Komodo Core |
| mx01 | tf01, `172.16.7.111` | `6379/tcp` | The route publisher writes mx01's routes |
| mx01 | ci01 and id01 | `443/tcp` | Telemetry, and the sign-in in front of mx01's dashboard |

dockns also needs to reach the UniFi console, at whatever address `DOCKNS_UNIFI_HOST` names. bh01 reaches mx01 inside the DMZ, which needs no rule unless your DMZ isolates its hosts from each other.

Outbound, mx01 needs the internet on ports 80 and 443 for NixOS packages, images, and Let's Encrypt, and on port 25 to deliver mail.

tf01's own firewall opens its Redis port to the internal subnet, and to the addresses in tf01's `docker_stacks_port_sources`. bh01's page added bh01 there. Add mx01's address to the same entry in `hosts.yml`:

```yaml
      docker_stacks_port_sources:
        - port: 6379
          proto: tcp
          sources: ["172.16.8.111/32", "172.16.8.121/32"]
```

Write tf01's file again, commit and push, and run tf01 again, as in [Admit the DMZ on tf01](bh01-dmz-edge.md#boundary-tf01). On tf01, check that the port takes mx01's address:

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport 6379 '
```

One of the lines names `172.16.8.121/32` after `-s`.

Then forward these four ports from the router's public side to `172.16.8.121`, TCP only:

| Port | Used for |
| --- | --- |
| `25` | Mail arriving from other servers |
| `465` | Mail clients sending, implicit TLS |
| `587` | Mail clients sending, STARTTLS |
| `993` | Mail clients reading, IMAP over TLS |

Do not forward 80, 443, or 8080. The web side reaches the internet through bh01's tunnel, never through a port forward.

Mail cannot take the tunnel, which carries web requests only. Other mail servers deliver to port 25 at the address the domain's MX record names, so mail has to arrive by a forward. See [How the fleet uses it](../../tools/stalwart/index.md#in-the-fleet) in the Stalwart primer.

mx01's own firewall opens the same four ports. They come from the stack's `setup.yaml`, through `nixos/hosts/mx01.json`, so no command on mx01 opens them. [Step 7](#verify) checks them.

## 4. Create the Authentik application {#authentik}

One Authentik application covers both services. Bulwark signs people in through it, and Stalwart accepts the tokens it issues.

<details>
<summary>Background: the two links between Authentik and the mail server</summary>

Authentik and Stalwart are joined twice, and the two links do different jobs.

The first is sign-in, set up here and switched on in [step 13](#oidc). It uses OpenID Connect (OIDC), a protocol in which an application sends the browser to Authentik, and Authentik hands back a signed token that says who signed in. Bulwark gets the token, and passes it to Stalwart with each request. Stalwart checks the signature against Authentik's published key, which is why the provider needs a signing key and why the issuer address has to match to the character.

The second is provisioning, set up in [step 12](#scim). Sign-in alone cannot create a mailbox before its owner first signs in, and mail for them would be refused until then. With SCIM, Authentik creates the account in Stalwart as soon as a person joins the group, and disables it when they leave.

Both links name a person the same way, as the Authentik username followed by the domain. Steps 12 and 13 each check that.

The Authentik primer explains [applications, providers, and OpenID Connect](../../tools/authentik/index.md#ideas).

</details>

### Create the group {#authentik-group}

In Authentik's admin interface, go to *Directory > Groups* and create a group named `mail-users`. Add **your own user** to it.

Only members of this group get a mailbox. That matters because the Stalwart licence is sold by mailbox count.

### Create the application and provider {#authentik-provider}

Go to *Applications > Applications* and click **Create with Provider**. Fill in the application:

| Field | Value |
| --- | --- |
| *Name* | `Mail` |
| *Slug* | `mail` |

Choose **OAuth2/OpenID Provider** as the provider type, then fill in the provider:

| Field | Value |
| --- | --- |
| *Authorization flow* | **default-provider-authorization-implicit-consent** |
| *Client type* | **Confidential** |
| *Redirect URIs/Origins (RegEx)* | **Regex**, `https://webmail\.myah-mitchell\.com/.*` |
| *Signing Key* | **authentik Self-signed Certificate** |

The form has no default for the flow, and lists each one as its slug followed by its name.

Copy the *Client ID* and *Client Secret* shown on that page. They are `<client-id>` and `<client-secret>`.

Without a signing key, Authentik signs tokens with the client secret, and Stalwart cannot check a token signed that way.

The redirect URI is the address Authentik may send a signed-in browser back to. It is a regex because Bulwark's exact callback path is not documented. Once sign-in works in [step 13](#oidc), tighten it to the path Authentik's logs show.

### Limit it to the group {#authentik-binding}

On the new application, open *Policy / Group / User Bindings*, click **Bind existing policy/group/user**, and bind the **mail-users** group.

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

In [Semaphore](../../tools/semaphore/index.md), run the **site** Template with *Target* set to `mx01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

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
ssh <admin>@172.16.8.121
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

The wizard has five screens and a last one that confirms:

1. On the first screen, set *Server hostname* to `mx.myah-mitchell.com` and *Default email domain* to `myah-mitchell.com`. Turn off **Automatically obtain TLS certificate**, and leave *Generate email signing keys* on.
2. Keep the storage defaults, which put everything in the embedded store.
3. For the directory, keep **Use the Internal Directory**.
4. For logging, choose **Console**, so that `docker logs` shows Stalwart's log.
5. For DNS, keep **Manual DNS Server Management**.

The certificate and the DNS provider wait for [step 11](#domain). With the certificate option on and DNS left manual, Stalwart would ask Let's Encrypt for a check on port 443 of the public address, which nothing forwards.

The last screen shows the permanent administrator account, `admin@myah-mitchell.com`, with a generated password. Stalwart shows the password this one time. Store both in your password manager.

The wizard writes `config.json`. Restart the `stalwart` container from Komodo, then sign in with the permanent administrator account at the same address.

After the restart, Stalwart builds its sign-in addresses from the stack's public URL, `https://mail.myah-mitchell.com`, which has no route until [step 10](#publish). If the sign-in page sends the browser to that name and it does not load, add `mail.myah-mitchell.com` to your hosts file with mx01's address until step 10 is done.

## 9. Finish Stalwart's server settings {#settings}

### Trust Traefik {#trust-proxy}

In the WebUI, go to *Settings > Network > HTTP > General* and turn on **Obtain remote IP from Forwarded header**.

Do this now, before anything reaches Stalwart from outside. Every web request arrives from the address of [Traefik](../../tools/traefik/index.md) on mx01. With the setting on, Stalwart reads the browser's address from the header Traefik adds. With it off, Stalwart's automatic ban can end up banning Traefik itself, which locks everyone out at once.

Then read the `proxy` network's subnet, on mx01:

```bash
docker network inspect proxy --format '{{range .IPAM.Config}}{{.Subnet}} {{end}}'
```

That is `<proxy-subnet>`. Go to *Settings > Security > Allowed IPs* and add `<proxy-subnet>`, so that the ban can never land on Traefik.

Leave *Trusted Networks* under *Settings > Network > General* empty. That list turns on the PROXY protocol for connections from the networks in it, which Traefik does not speak on a web route, so every web request would fail.

### Add the licence {#licence}

Go to *Settings > Enterprise*. For *License Key*, choose **Secret read from environment variable** and set *Variable Name* to `STALWART_LICENSE_KEY`.

Restart the `stalwart` container from Komodo so that it reads its settings again, then sign out and back in. The Enterprise sections of the WebUI are now available.

### Add Cloudflare as a DNS provider {#dns-provider}

Go to *Settings > Network > DNS > DNS Providers* and add a provider of type **Cloudflare**, with `<cf-api-token>` in *API Token*.

Stalwart uses it in [step 11](#domain), both to publish the domain's mail records and to prove it owns `mx.myah-mitchell.com` for a certificate.

## 10. Publish the web hostnames through bh01 {#publish}

Stalwart's web side, Bulwark, and the two well-known names mail software fetches all go through bh01's tunnel. Follow [Publishing a hostname](bh01-dmz-edge.md#publish) for each of these four:

| Hostname | Serves |
| --- | --- |
| `mail.myah-mitchell.com` | Stalwart's WebUI, JMAP, and SCIM |
| `webmail.myah-mitchell.com` | Bulwark |
| `autoconfig.myah-mitchell.com` | Mail client settings, from Stalwart |
| `mta-sts.myah-mitchell.com` | The domain's MTA-STS policy, from Stalwart |

Both services do their own authentication, so they are safe to publish before Authentik is wired in. Until [step 13](#oidc), only the administrator account from [step 8](#wizard) can sign in to anything.

Open `https://mail.myah-mitchell.com/admin` from outside your network, such as from a phone with Wi-Fi off. Stalwart's sign-in page loads.

## 11. Add the domain, its DNS records, and a certificate {#domain}

> [!WARNING]
> This step moves the domain's inbound mail to mx01. If `myah-mitchell.com` already receives mail somewhere else, that stops once the MX record changes. Turn off Cloudflare Email Routing for the zone first if it is on, because it owns the MX records while enabled.

### Create the A record by hand {#a-record}

In the Cloudflare dashboard, add an `A` record for `mx.myah-mitchell.com` pointing at `<public-ip>`, with the proxy status set to **DNS only**.

It has to be DNS only. Cloudflare's proxy carries web traffic, not mail. This is the name the MX record points other mail servers at, and the name in the reverse DNS record from [step 1](#public-address).

### Add the domain {#add-domain}

In the WebUI, go to *Management > Domains > Domains* and open `myah-mitchell.com`, which the wizard created.

Set *DNS Management* to **Automatic DNS management**, and choose **the Cloudflare DNS provider** from [step 9](#dns-provider) in *DNS Server*, so that Stalwart publishes and maintains its own records. Stalwart rotates its DKIM keys every 90 days by default, which only works if it can update DNS itself.

In *Record Types*, take out these four:

- *MTA-STS policy record*
- *Autoconfig records*
- *Legacy Autoconfig records*
- *Microsoft Autodiscover records*

Each of them publishes a CNAME record that points at `mx.myah-mitchell.com`, which answers on the mail ports only. Step 10's tunnel routes already own `autoconfig` and `mta-sts`, and a second record for the same name would replace them.

*MTA-STS policy record* also covers the TXT record at `_mta-sts`, which tells other servers the policy exists. With the type taken out, copy that one record from the zone file into Cloudflare by hand.

Save the domain. Once it has published, open the domain's menu in the list and choose **View Zone File**. Compare that zone with the zone in the Cloudflare dashboard. The zone holds MX, SPF, DKIM, DMARC, TLS reporting, MTA-STS, and the mail client SRV records. Between them they say where the domain's mail goes and how a receiver can tell real mail from forged, and the [Stalwart primer](../../tools/stalwart/index.md#ideas) explains each.

Stalwart publishes the SPF record `v=spf1 mx -all` and a DMARC record with `p=reject`. Together they tell receivers to refuse mail from the domain that mx01 did not send or sign. That includes the service mail Postfix on ci01 sends through its relay. See [Service mail once the domain has mailboxes](../../tools/stalwart/index.md#service-mail-and-dmarc) before you go on.

If the domain already has an SPF record, merge the two into one. A domain with two SPF records fails SPF entirely.

### Get a certificate for the mail ports {#certificate}

Traefik's certificate covers only the web side. Clients connecting to ports 465, 587, and 993, and servers using STARTTLS on 25, see Stalwart's own certificate.

Go to *Settings > TLS > ACME Providers* and create a provider. Leave *Directory URL* at its default, which is Let's Encrypt, set *Challenge type* to **DNS-01**, and enter **your address** in *Contact Email*. See [ACME](../../tools/glossary.md#acme) and [DNS-01](../../tools/glossary.md#dns-01) for how the challenge works.

Then open the domain again. Set *Certificate Management* to **ACME TLS certificate management**, choose the new provider in *ACME Provider*, and add `mx` to *Additional Hostnames*. Stalwart appends the domain to each name there. The DNS challenge is written through the domain's DNS provider, which is why the domain had to be on automatic DNS first.

Saving schedules the request. Watch it under *Management > Tasks > Scheduled*, and look under *Failed* if no certificate arrives.

Check it from any machine:

```bash
openssl s_client -connect mx.myah-mitchell.com:993 \
  -servername mx.myah-mitchell.com </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -ext subjectAltName
```

The issuer is Let's Encrypt, and the names include `mx.myah-mitchell.com`. From inside the network this needs hairpin NAT on the router, which lets an inside machine reach the site's own public address. Use an outside connection if the command hangs.

## 12. Turn on SCIM provisioning {#scim}

SCIM lets Authentik create, update, and disable Stalwart accounts as group membership changes. Without it, a mailbox only exists after its owner has signed in once, and mail sent to them before that is refused.

Do this before [step 13](#oidc). The administrator account from [step 8](#wizard) is the one you use here, and it may stop being able to sign in once Stalwart trusts Authentik.

### On Stalwart {#scim-stalwart}

In *Management > Domains > Domains*, open `myah-mitchell.com` and turn on **Allow SCIM Provisioning**.

In *Management > Directory > Accounts*, create a user account with `scim` as its *Username* and `myah-mitchell.com` as its *Domain*, to act as Authentik's service account. Under *Credentials*, give it **a password**.

An API key belongs to the account that creates it. Sign in to the WebUI as `scim@myah-mitchell.com` in a private browser window, go to *Account > Credentials > API Keys*, and create a key. Set its *Permissions* to **Replace all permissions** and list these five:

- `scimAccess`
- `authenticate`
- `sysAccountGet`
- `sysAccountCreate`
- `sysAccountUpdate`

Stalwart shows the secret once. That secret is `<scim-token>`.

The five let Authentik create, change, and disable accounts. Without `sysAccountDestroy`, Stalwart refuses a delete from Authentik, so no mailbox is removed by a sync.

Check the key from any machine:

```bash
curl -H "Authorization: Bearer <scim-token>" \
  "https://mail.myah-mitchell.com/scim/v2/Users?count=1"
```

The answer is JSON with a `ListResponse` in it. A `401` means the token is wrong, and a `403` names the missing permission or a licence that was not applied.

### On Authentik {#scim-authentik}

Stalwart takes an account's name from the SCIM `userName` and accepts only a full address there. Authentik's default mapping sends the bare username, so make a mapping that adds the domain first.

Go to *Customization > Property Mappings*, click **Create**, and choose **SCIM Provider Mapping**. Name it `mail-scim-username`, with this expression:

```python
return {
    "userName": f"{request.user.username}@myah-mitchell.com",
}
```

Then go to *Applications > Providers*, click **Create**, and choose **SCIM Provider**.

| Field | Value |
| --- | --- |
| *Name* | `mail-scim` |
| *URL* | `https://mail.myah-mitchell.com/scim/v2` |
| *Token* | `<scim-token>` |
| *Compatibility Mode* | **Default** |
| *Group* | **mail-users** |
| *User Property Mappings* | **authentik default SCIM Mapping: User** and **mail-scim-username** |

Authentik applies the selected mappings in order of name and lets a later one replace what an earlier one set. `mail-scim-username` sorts after the default, so its `userName` is the one sent.

Then edit the `Mail` application from [step 4](#authentik) and add **mail-scim** under *Backchannel Providers*.

### Check the first sync {#scim-sync}

Open the `mail-scim` provider in Authentik and start a sync from its *Sync status* card. In Stalwart, *Management > Directory > Accounts* now lists an account for each member of `mail-users`.

Each account's *Email Address* is the Authentik username followed by `@myah-mitchell.com`. Stalwart has to see the same name here as in step 13, which builds it the same way.

If the list is empty, the card's log in Authentik shows Stalwart's reply. An `invalidValue` there means the name was not a full address in a domain with SCIM turned on.

### Make yourself an administrator {#scim-admin}

In *Management > Directory > Accounts*, open **your own account**, the one SCIM created, and set *Roles* to **Administrator role**. This is the account you manage Stalwart with from [step 13](#oidc) onward.

## 13. Sign in through Authentik {#oidc}

Read [Recovering admin access](#recovery) before this step. If this goes wrong, the recovery procedure is how you get back in.

### Create the OIDC directory {#oidc-directory}

In the WebUI, go to *Settings > Authentication > Directories* and create a directory of type **OpenID Connect**:

| Field | Value |
| --- | --- |
| *Issuer URL* | `https://auth.myah-mitchell.com/application/o/mail/` |
| *Required Audience* | `<client-id>` |
| *Username Claim* | `preferred_username` |
| *Username Domain* | `myah-mitchell.com` |
| *Name Claim* | `name` |

The issuer must match Authentik's exactly, trailing slash included. A mismatch shows up in Stalwart's log as `InvalidIssuer`.

*Username Domain* turns an Authentik username such as `myah` into the account `myah@myah-mitchell.com`, which is the name SCIM created in [step 12](#scim).

### Switch authentication to it {#oidc-switch}

Go to *Settings > Authentication > General* and set *Authentication Directory* to **the OIDC directory** you just created.

Keep the existing admin session open in the first window. In a private browser window, open `https://webmail.myah-mitchell.com` and sign in with **your Authentik account**. Bulwark shows your mailbox.

If it fails, check Stalwart's log from mx01:

```bash
docker logs mail-stalwart 2>&1 | grep -iE 'oidc|jwt|issuer|audience'
```

## 14. Send and receive {#mail-check}

### Receive {#receive}

From a mailbox outside the domain, send a message to your own address at `myah-mitchell.com`. It arrives in Bulwark within a minute.

### Send {#send}

Reply to it from Bulwark. In the outside mailbox, open the message's original headers.

They show `spf=pass`, `dkim=pass`, and `dmarc=pass`. Those are the three checks a receiving server runs against the domain's DNS records to decide whether a message is really from it.

A `fail` or `none` on any of the three means the DNS records from [step 11](#domain) are missing or wrong. Fix it before sending real mail, because providers remember an address that sent unauthenticated mail.

### Check port 25 from outside {#port-25}

Use an outside SMTP test, such as MXToolbox's, against `mx.myah-mitchell.com`. It reports Stalwart's banner, working STARTTLS, and no open relay. An open relay is a server that forwards mail for anyone, and gets blocklisted for it.

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
ssh -L 8080:127.0.0.1:8080 <admin>@172.16.8.121
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
- The WebUI's menu paths and field labels in steps 9 to 13. They are read from the form definitions Stalwart ships at `v0.16.22`, and the wizard's labels in step 8 from Stalwart's documentation. None was read from a running WebUI.
- The wizard through Traefik. Stalwart's documentation suggests running it straight against port 8080, which the stack does not publish, and step 8's hosts file entry for `mail.myah-mitchell.com` has not been tried.
- Port 8080 after the wizard. Stalwart's documentation has a reverse proxy send the WebUI, JMAP, and SCIM there, and the stack has not been run to see it.
- The `_mta-sts` TXT record in step 11. Whether the zone file still lists it once its record type is taken out, and how its value changes when the policy does, are not known.
- Whether Stalwart puts back a record that was edited by hand in Cloudflare, such as a merged SPF record.
- Whether an administrator can add the API key from the `scim` account's own form in *Management > Directory > Accounts*, which would spare the second sign-in in step 12.
- Whether Authentik's access tokens carry the client ID as their audience and include `preferred_username`. Stalwart's `requireAudience` and `claimUsername` depend on both.
- The SCIM mapping in step 12. Authentik's merging of two mappings is read from its source at 2025.8.4, and no sync has been run. Stalwart's documentation says it accepts and discards standard attributes it does not use, such as `photos` and `locale`.
- The control that starts a sync on the provider's *Sync status* card, which has an icon and no label.
- Whether the step 8 administrator can still sign in once the OIDC directory is active. This page assumes not, which is why step 12 makes your own account an administrator first.
- Whether OIDC accounts can create app passwords in Stalwart's account manager at `/account`. Stalwart's documentation says both yes and no, and desktop mail clients without OAuth support need them.
- Bulwark's OAuth callback path, hence the regex redirect URI in step 4.
- Whether a port published from Docker shows Stalwart the real client address. Docker normally preserves it for IPv4, and step 14 checks.
- The recovery procedure, which comes from the container's notes in fleet-stacks. A host sets `DOCKER_CONTENT_TRUST=1` for commands typed in a shell, and whether `docker run` then accepts the image has not been tried.
- dockns on mx01 with the four keys blank, and whether it reaches the UniFi console from the DMZ.
- Whether tf01's firewall filters the Redis port at all, as on [bh01](bh01-dmz-edge.md#unconfirmed).
