# Adding a mail domain

This page has Stalwart take mail for a second domain, beside the one mx01 was built with. Do it when you own another domain and want addresses in it to land in the fleet's mailboxes. The change is made in Stalwart's WebUI, and Stalwart publishes the domain's DNS records by itself.

Status: written, not yet run.

The first domain is set up on mx01's page, and this page follows the same choices. See [Add the domain, its DNS records, and a certificate](../../fleet-bootstrap/hosts/mx01-mail.md#domain).

## Prerequisites

- mx01 is finished for the first domain, through [Send and receive](../../fleet-bootstrap/hosts/mx01-mail.md#mail-check).
- The new domain's DNS zone is in Cloudflare, in the account the first domain's zone is in.
- The domain receives no mail anywhere else, or you are ready for that to stop.
- You can sign in to Stalwart's WebUI with an administrator account.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<new-domain>` | The domain being added |
| `<selector>` | The selector of one of the domain's DKIM keys, read in [step 3](#dkim) |
| `<username>` | The account that gets the first address in the new domain |
| `<test-sender>` | A mailbox outside both domains that you can send from |

## 1. Let the Cloudflare token edit the new zone {#token}

In the Cloudflare dashboard, open *My Profile > API Tokens* and edit the token Stalwart uses. Under *Zone Resources*, add the zone `<new-domain>` beside the first one, and save.

Stalwart writes the new domain's records with the DNS provider from [Add Cloudflare as a DNS provider](../../fleet-bootstrap/hosts/mx01-mail.md#dns-provider). The token's secret does not change, so nothing changes in Stalwart.

## 2. Create the domain {#create}

> [!WARNING]
> Saving the domain publishes its MX record, which moves all inbound mail for `<new-domain>` to mx01. Turn off Cloudflare Email Routing for the zone first if it is on.

In the WebUI, go to *Management > Domains > Domains* and create a domain:

| Field | Value |
| --- | --- |
| *Domain Name* | `<new-domain>` |
| *DKIM Management* | **Automatic DKIM management** |
| *DNS Management* | **Automatic DNS management**, with the Cloudflare DNS provider in *DNS Server* |
| *Record Types* | The default list without *MTA-STS policy record*, *Autoconfig records*, *Legacy Autoconfig records*, and *Microsoft Autodiscover records* |
| *Certificate Management* | **Manual TLS certificate management** |
| *Allow SCIM Provisioning* | **On** |

Save it. Stalwart schedules a task that publishes the records.

The four record types are left out because nothing would answer them. Traefik on mx01 routes `mta-sts.` and `autoconfig.` for the fleet's own domain only, from the labels in `containers/stalwart/compose.yaml`. A published MTA-STS record whose policy cannot be fetched is worse than none.

The domain needs no certificate of its own. Its MX record points at `mx.myah-mitchell.com`, so servers and clients for every domain connect to that name and see the certificate from [Get a certificate for the mail ports](../../fleet-bootstrap/hosts/mx01-mail.md#certificate).

<details>
<summary>Background: why a separate domain and not a domain alias</summary>

Stalwart's domain record has an `aliases` field, which makes further domain names equivalent to the first: every address in one exists in the other. That is less work, and it fits a domain that is only a second spelling of the first.

A domain of its own gets its own DKIM keys and its own DNS records from Stalwart, which is what receivers check when mail is sent from the new domain's addresses. See [DKIM](index.md#dkim) and [DMARC](index.md#dmarc).

</details>

## 3. Check the DKIM keys {#dkim}

Go to *Management > Domains > DKIM Signatures*. Two signatures show for `<new-domain>`, one Ed25519 and one RSA, each in the stage *active*.

Note the selector of either one. It is `<selector>`, and looks like `v1-ed25519-20261004`.

Stalwart makes these keys, publishes them, and replaces them every 90 days. No key is created or copied by hand. See [DKIM](index.md#dkim).

## 4. Check the published records {#dns}

Go to *Management > Tasks*. The DNS task for the domain is no longer under *Scheduled*, and nothing is under *Failed*. A failed task records its reason, and a token that cannot edit the zone is the likely one.

Read the records from any machine:

```bash
dig +short MX <new-domain>
dig +short TXT <new-domain>
dig +short TXT _dmarc.<new-domain>
dig +short TXT <selector>._domainkey.<new-domain>
```

| Query | Shows |
| --- | --- |
| MX | `mx.myah-mitchell.com.` with a priority |
| TXT on the domain | One record starting `v=spf1` |
| TXT on `_dmarc` | A record starting `v=DMARC1` |
| TXT on the selector | A record starting `v=DKIM1` |

Then open the domain's menu in the list, choose **View Zone File**, and compare it with the zone in the Cloudflare dashboard. Each line has a record in the zone, apart from the four types left out in step 2.

If the TXT query shows two records starting `v=spf1`, the domain had one already. Merge them into one in Cloudflare, because a domain with two fails [SPF](index.md#spf) entirely.

## 5. Give an account an address in the domain {#address}

Add `<username>@<new-domain>` as an alias on the person's account. See [Giving the mailbox another address](add-a-mailbox.md#alias).

Accounts stay in the first domain. The fleet's sign-in builds every account name from the Authentik username and the first domain, in the OIDC directory's *Username Domain* and in the SCIM mapping, so a person has one account and reaches the new domain through an alias. See [Accounts come from Authentik](index.md#accounts-in-the-fleet).

## 6. Send and receive {#mail-check}

From `<test-sender>`, send a message to `<username>@<new-domain>`. It arrives in the person's mailbox in Bulwark.

Reply from Bulwark with the new address as the sender. In the outside mailbox, open the reply's original headers. They show `spf=pass`, `dkim=pass`, and `dmarc=pass`, with `<new-domain>` as the domain in each.

A `fail` or `none` means a record from step 4 is missing or wrong. Fix it before sending real mail from the domain.

## Service mail from the new domain {#service-mail}

This page does not change what the fleet's services send as. Postfix on ci01 relays only for the domains in `POSTFIX_ALLOWED_SENDER_DOMAINS`, which is the fleet's first domain unless you set it. See [Stage the values](../../fleet-bootstrap/hosts/ci01-core-infra.md#values).

If a service is to send from `<new-domain>`, add the domain there, and make sure the relay signs for the new domain or is covered by its SPF record. Stalwart publishes a DMARC record with `p=reject` for every domain it holds. See [Service mail once the domain has mailboxes](index.md#service-mail-and-dmarc).

## What's next

To give more people an address in the domain, repeat [step 5](#address) for each.

## Not yet confirmed {#unconfirmed}

Nothing on this page has been run. The labels and menu paths are read from the form definitions Stalwart ships at `v0.16.22`, which the fleet pins, and not from a running WebUI.

- Whether leaving a record type out removes a record that is already published, and whether the zone file still lists the types left out.
- Whether both DKIM keys exist as soon as the domain is saved, or only after a first scheduled task.
- Cloudflare's labels in step 1.
- That the MX record Stalwart publishes for a second domain names the server's hostname, `mx.myah-mitchell.com`.
- Whether an alias in the new domain can be added in the WebUI to an account that SCIM owns, and whether it survives a sync. See [Adding a mailbox](add-a-mailbox.md#unconfirmed).
- Whether Bulwark lets a person choose an alias as the sender, which step 6 depends on.
- Whether the Cloudflare token from mx01's page was created for one zone. If it already covers every zone in the account, step 1 is not needed.
