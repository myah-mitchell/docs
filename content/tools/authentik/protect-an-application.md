# Putting an application behind a sign-in

This page puts Authentik's sign-in in front of a web interface that has no login of its own, or none you trust. You do it when you add such a container to a stack, or when an interface that was left open should stop being open. It uses [forward auth](index.md#forward-auth), so the application itself is not changed.

For an application that can speak OpenID Connect, use that instead. See [Signing in to an application with OpenID Connect](add-an-oidc-application.md).

Status: written, not yet run.

## Prerequisites

- The fleet has left bootstrap mode, and the `fleet-forward-auth` Provider exists. See [Set up the sign-in in Authentik](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md#authentik). In bootstrap mode every chain is forced to `chain-no-auth@file`, and nothing on this page takes effect.
- The container has a Traefik route already. See the [Traefik primer](../traefik/index.md).
- A clone of fleet-stacks you can push to, and the `akadmin` password.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<image>` | The container's folder under `containers/` in fleet-stacks, such as `dozzle` |
| `<host>` | The host that runs the stack, such as `ap01` |
| `<app-hostname>` | The name the interface answers on, such as `dozzle.ap01.home.myah-mitchell.com` |
| `<app-name>` | A name for the Application, such as `Dozzle` |
| `<container>` | The container's name on the host, from `docker ps` |

## Where the change is made {#where}

The sign-in has two sides. Traefik's side is a label in the container's compose file in fleet-stacks, which reaches the host when Komodo redeploys the stack. Authentik's side is a [Provider](index.md#provider) in its admin interface, which lives in Authentik's database and takes effect when it is saved.

The fleet's one Provider covers every name under `myah-mitchell.com`, so most applications need Traefik's side only: steps 1 and 2, then [Verify](#verify). Steps 3 to 5 are for an application that needs access rules of its own.

## 1. Put the chain on the route {#chain}

In `containers/<image>/compose.yaml`, set the route's middlewares label to the line every guarded container uses:

```yaml
      - "traefik.http.routers.$PROJECT_NAME-rtr.middlewares=${TRAEFIK_AUTH_CHAIN:-chain-authentik@file}"
```

Keep the router name the container already has in place of `$PROJECT_NAME-rtr`. The label replaces one that names `chain-no-auth@file`.

Then give the key a line in `containers/<image>/komodo.env`, left blank:

```text
#= Stack Specific Settings
#== Traefik
TRAEFIK_AUTH_CHAIN:
```

A blank value takes the default in the label, which is the chain that ends in [forward auth](index.md#chain). The key has to be there so that bootstrap mode can set it to `chain-no-auth@file` on a host that is still in that mode.

Generate the stack's files and check them, as for any change to a container. See [Generate and check](../../fleet-bootstrap/hosts/ap01-applications.md#build). Commit and push fleet-stacks.

## 2. Redeploy the stack {#deploy}

Write the host's Komodo file again, so that the new key is in the Stack's *Environment*, and commit the private repo. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).

Then run the host.

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `<host>`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover.

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The last stage redeploys the Stack, and Traefik picks the new label up from the container.

If the fleet's Provider is enough for this application, go to [Verify](#verify).

## 3. Create a Provider of its own {#provider}

Do this step and the two after it only when the application needs access rules of its own. A person who may use the `Fleet` Application can open everything the domain level Provider covers, and Authentik cannot narrow that for one hostname. A Provider in single application mode has its own Application, and so its own [bindings](index.md#bindings).

Open the admin interface at `https://authentik.id01.home.myah-mitchell.com/if/admin/` and sign in as `akadmin`.

1. Open *Applications > Providers*, click **Create**, and choose **Proxy Provider**.
2. In *Name*, enter `<app-name>-forward-auth`.
3. In *Authorization flow*, choose **default-provider-authorization-implicit-consent**. It lets a signed-in person through without a consent page.
4. Choose the mode **Forward auth (single application)**.
5. In *External host*, enter `https://<app-hostname>`.
6. Click **Finish**. The Provider appears in the list, with a warning that no Application uses it.

## 4. Create the Application {#application}

1. Open *Applications > Applications* and click **Create**.
2. In *Name*, enter `<app-name>`. Authentik fills in *Slug* from it.
3. In *Provider*, choose the Provider from step 3.
4. Click **Create**. The warning on the Provider goes away.

## 5. Assign it to the embedded outpost {#outpost}

A Provider answers nothing until its Application is assigned to an [outpost](index.md#outpost).

1. Open *Applications > Outposts* and click the edit control on the row *authentik Embedded Outpost*.
2. Under *Applications*, move `<app-name>` to the selected side. Leave `Fleet` selected.
3. Click **Update**. The row lists two Providers.

Then limit the Application to a group. Until it has a binding, every user may open it. See [Limit an Application to a group](add-a-user.md#binding).

## 6. Verify {#verify}

Open `https://<app-hostname>` in a private browser window, so that no earlier session answers for you. Authentik's sign-in page appears. After you sign in, the browser returns to the application and the page loads.

In Authentik, *Events > Logs* shows the sign-in, and an authorization for the Application that let you through.

If the page loads with no sign-in, the route is still on `chain-no-auth@file`. Read the label off the running container:

```bash
docker inspect <container> \
  --format '{{ range $k, $v := .Config.Labels }}{{ println $k $v }}{{ end }}' \
  | grep middlewares
```

The line ends in `chain-authentik@file` when the chain is on.

## Taking the sign-in off again {#remove}

Set `TRAEFIK_AUTH_CHAIN` to `chain-no-auth@file` for the stack in the host's `komodo_stack_env`, write the files again, and run the host. See [Stack values](../../fleet-bootstrap/concepts/fleet-private.md#stack-values). The compose file stays as it is.

If the application had a Provider of its own, remove its Application from the embedded outpost, then delete the Application and the Provider.

## What's next

Decide who may open it. See [Adding a user and a group](add-a-user.md).

## Not yet confirmed {#unconfirmed}

Nothing on this page has been run. The fleet is not built, and no Provider has been created in it.

- Authentik's labels in steps 3 to 5, for version 2025.8.4, which the compose file pins. The mode names, *External host*, and the menu paths follow Authentik's documentation. The buttons **Create**, **Finish**, and **Update**, the wording of the flow's name in the list, and the layout of the outpost's *Applications* picker were not read from a running Authentik.
- Whether a new Provider can be created from *Applications > Providers* before its Application, as [Leaving bootstrap mode](../../fleet-bootstrap/procedures/leave-bootstrap-mode.md#authentik) also does. Authentik's documentation leads with **Create with provider** on the Applications screen, which makes both in one wizard.
- A single application Provider beside the domain level one on the same outpost. The page expects the outpost to pick the Provider whose *External host* matches the request exactly, ahead of the one that matches by cookie domain.
- The return from the sign-in in single application mode. Authentik sends the browser back to `/outpost.goauthentik.io/callback` on the application's own hostname. That request reaches the Traefik of the application's VM, not id01. The page expects the forward auth middleware to hand it to the outpost like any other request, and that has not been tried.
- The *Events > Logs* entries named in [Verify](#verify).
- The label on the container after a redeploy, and whether Komodo redeploys a Stack when only its compose file changed in the repo.
