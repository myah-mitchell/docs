# Adding a mailbox

This page gives one person a mailbox at the fleet's domain. Do it when someone new needs an address, after mx01 is built. The change is made in Authentik, by adding the person to a group, and Authentik's SCIM provider carries it to Stalwart.

Status: written, not yet run.

Nobody creates the account in Stalwart by hand. In the fleet's domain SCIM owns the accounts. See [Accounts come from Authentik](index.md#accounts-in-the-fleet).

## Prerequisites

- mx01 is finished, through [Send and receive](../../fleet-bootstrap/hosts/mx01-mail.md#mail-check).
- The person has an Authentik account. Its username becomes the part of the address before the `@`, so settle the username first.
- The Stalwart licence has a mailbox to spare. It is sold by mailbox count.
- You can sign in to Authentik's admin interface, and to Stalwart's WebUI with an administrator account.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<username>` | The person's Authentik username, such as `myah` |
| `<alias>` | A further address for the same mailbox, such as `hello@myah-mitchell.com` |
| `<test-sender>` | A mailbox outside the domain that you can send from |

## 1. Add the person to the group {#group}

In Authentik's admin interface, go to *Directory > Groups* and open `mail-users`. On its *Users* tab, click **Add existing user**, choose `<username>`, and confirm.

Membership of this group is the whole request. The `mail-scim` provider is filtered to the group, so it now sends Stalwart an account for the person. The group was created in [Create the group](../../fleet-bootstrap/hosts/mx01-mail.md#authentik-group).

## 2. Check that the account arrived {#verify}

In Stalwart's WebUI, go to *Management > Directory > Accounts*. The list holds `<username>@myah-mitchell.com`.

If it does not appear within a few minutes, open the `mail-scim` provider in Authentik under *Applications > Providers* and start a sync by hand. The provider's page shows the result of each sync, with Stalwart's reply when one failed.

| Reply | Cause |
| --- | --- |
| `400` with `invalidValue` | The domain in the account's name is not a domain in Stalwart, or *Allow SCIM Provisioning* is off for it |
| `400` with `invalidSyntax` | Authentik sent an attribute that belongs to no schema Stalwart knows |
| `401` or `403` | The token on `mail-scim` is wrong, or the `scim` account lost a permission |

Stalwart takes the account's name from the SCIM `userName`, which must be a full address. See [On Authentik](../../fleet-bootstrap/hosts/mx01-mail.md#scim-authentik) for the mapping that builds it.

## 3. Test delivery {#deliver}

From `<test-sender>`, send a message to `<username>@myah-mitchell.com`.

The mailbox exists from the moment SCIM created it, so the message is accepted even though the person has never signed in. A bounce that says the recipient is unknown means step 2 did not finish.

## 4. Have the person sign in {#sign-in}

The person opens `https://webmail.myah-mitchell.com` and signs in with their Authentik login. Bulwark shows the mailbox, with the test message in it.

A sign-in that Authentik refuses means the person is not in `mail-users`, since the application is bound to that group. A sign-in that Stalwart refuses means the name Authentik's token carries does not match the account's name. See [Sign in through Authentik](../../fleet-bootstrap/hosts/mx01-mail.md#oidc).

## Giving the mailbox another address {#alias}

An [alias](index.md#accounts) is a second address that delivers to the same mailbox. Use one for a role address such as `hello@`, where a second mailbox would cost a licence seat and need its own login.

In *Management > Directory > Accounts*, open the account, add `<alias>` under *Email Aliases*, and save. Send a message to `<alias>` from `<test-sender>`. It arrives in the same mailbox.

Check the alias again after Authentik's next sync of that person. SCIM owns the account, and Stalwart's documentation says a full update from the identity provider replaces the account's aliases with the ones it sends. If the alias is gone, it has to come from Authentik instead, as a further entry in the `emails` list of the SCIM property mapping.

## Removing a mailbox {#remove}

Remove the person from `mail-users` in Authentik. Then open the account in *Management > Directory > Accounts* and see what Stalwart was told.

An account that SCIM marks inactive can no longer sign in, but keeps its mail and still receives. Deleting the account is a separate act. Export or forward anything worth keeping before you delete it.

## What's next

A desktop or phone mail client is set up by the person, not by you. See [Later changes](../../fleet-bootstrap/hosts/mx01-mail.md#later) for what is known about that.

To take mail for another domain, see [Adding a mail domain](add-a-mail-domain.md).

## Not yet confirmed {#unconfirmed}

Nothing on this page has been run. The Stalwart parts come from its documentation and from the form definitions it ships at `v0.16.22`, which the fleet pins.

- How soon Authentik's SCIM provider sends a new group member. The control that starts a sync by hand is an icon on the provider's *Sync status* card, with no label.
- The replies in step 2's table. `invalidValue` and `invalidSyntax` are documented. The `401` and `403` rows are what a bad token or a missing permission would give.
- Whether an alias added in the WebUI survives Authentik's next update of the account.
- What Authentik sends when a person leaves `mail-users`: a delete, an inactive flag, or nothing.
- Whether deleting an account deletes its mail at once. Stalwart's documentation does not say.
- Where the WebUI shows how many of the licence's mailboxes are in use.
