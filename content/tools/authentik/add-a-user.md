# Adding a user and a group

This page gives a person an account in Authentik, puts them in a group, and limits an Application to that group. You do it when someone new needs to reach the fleet's web interfaces, or when an Application that is open to every user should be open to some.

All of it is done in Authentik's admin interface. Nothing is written to a repo, and each change takes effect when it is saved. See [Users and groups](index.md#users-and-groups) and [Policies and bindings](index.md#bindings) for the ideas.

Status: written, not yet run.

## Prerequisites

- Authentik is up and you can sign in as `akadmin`, or as another member of the group authentik Admins. See [Create the admin account](../../fleet-bootstrap/hosts/id01-identity.md#first-access).
- The Application you want to limit exists. For the fleet's interfaces behind forward auth, that is `Fleet`. See [Set up the sign-in in Authentik](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md#authentik).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<group>` | The group's name, such as `fleet-operators` |
| `<username>` | The person's username, lower case with no spaces, such as `myah` |
| `<application>` | The Application to limit, such as `Fleet` |

## 1. Create the group {#group}

Open the admin interface at `https://authentik.id01.home.myah-mitchell.com/if/admin/`.

1. Open *Directory > Groups* and click **Create**.
2. In *Name*, enter `<group>`.
3. Leave *Is superuser* off. It would make every member an administrator of Authentik itself.
4. Click **Create**. The group appears in the list with no members.

Name a group for what its members may do, not for who they are. One group for each Application you intend to limit is a sound start.

## 2. Create the user {#user}

1. Open *Directory > Users* and click **Create**.
2. In *Username*, enter `<username>`.
3. In *Name*, enter the person's full name, and in *Email*, their address. Authentik sends recovery mail there.
4. Leave *Path* as it is, and leave **Is active** ticked.
5. Click **Create**. The user appears in the list.

The account has no password yet, so nobody can sign in with it.

## 3. Give the account a password {#password}

Open the user from the list and click **Set password**. Enter a password, save it, and pass it to the person by a channel you trust. Ask them to change it at their first sign-in, in their own settings.

To let the person choose the password instead, click **Create recovery link** on the same page and send them the link. It opens a page where they set a password, and it works once.

## 4. Add the user to the group {#membership}

1. On the user's page, open the *Groups* tab.
2. Click **Add to existing group**.
3. Select `<group>` and confirm. The group appears in the tab's list.

The membership counts from the person's next request. Nothing has to be redeployed.

On a fleet with mail, the group `mail-users` is special. Adding a person to it creates their mailbox, and the Stalwart licence is counted in mailboxes. See [Create the group](../../fleet-bootstrap/hosts/mx01-mail.md#authentik-group).

## 5. Limit an Application to the group {#binding}

An Application with no binding is open to every user. The first binding closes it to everyone the bindings do not name.

> [!WARNING]
> Add your own account to `<group>` before you bind it. The binding applies to you as well, and on `Fleet` it decides who reaches Semaphore and every other interface behind the chain. Authentik's own admin interface stays open to you either way.

1. Open *Applications > Applications* and click `<application>`.
2. Open the tab *Policy / Group / User Bindings*.
3. Click **Bind existing policy/group/user**.
4. Choose **Group**, select `<group>`, and click **Create**. The tab lists one binding.

To let a second group in, add a second binding. The Application's *Policy engine mode* is **ANY** by default, which admits a person who matches any one binding.

`Fleet` is one Application in front of every interface behind forward auth, so its bindings admit a person to all of them or to none. To give one interface rules of its own, give it a Provider of its own. See [Create a Provider of its own](protect-an-application.md#provider).

## 6. Verify {#verify}

Open an interface behind the Application in a private browser window and sign in as `<username>`. The page loads.

Then check the other direction with an account that is not in the group. Authentik shows a page saying the request was denied, and the interface does not load.

In the admin interface, the Application's page can also test one person without signing in as them. Open *Applications > Applications*, click `<application>`, and use **Check access** with the user selected.

## Removing a person {#remove}

Open *Directory > Users*, open the user, and click **Deactivate**. A deactivated account cannot sign in, and its sessions end. Deactivate in preference to deleting, so that the account's history in *Events > Logs* keeps its name.

To take away one Application only, remove the person from the group in the user's *Groups* tab.

## What's next

Put more interfaces behind the sign-in. See [Putting an application behind a sign-in](protect-an-application.md).

## Not yet confirmed {#unconfirmed}

Nothing on this page has been run against the fleet's Authentik, which is version 2025.8.4 by its compose file.

- The labels. The menu paths, the fields and buttons in steps 1 to 5, *Check access*, and *Deactivate* are read from Authentik's source at version 2025.8.4. None was read from a running Authentik.
- The *Create* button inside the binding dialog, which was not found in the source.
- The wording of the page a denied person sees.
- Whether a superuser such as `akadmin` passes an Application's bindings without being named in one. The warning in step 5 assumes not.
- Whether deactivating a user ends sessions that forward auth already let through, or only stops new sign-ins.
- Recovery links. They need a recovery flow set on the brand, and whether the default install has one was not checked.
