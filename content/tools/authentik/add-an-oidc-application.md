# Signing in to an application with OpenID Connect

This page lets an application sign people in through Authentik with [OpenID Connect](index.md#oidc). You do it when you add an application that supports OIDC, which is the better choice over forward auth whenever the application offers it.

The example is Bulwark, the webmail on mx01, which is the one OIDC application fleet-stacks configures. Its full build is on [Mail (mx01)](../../fleet-bootstrap/hosts/mx01-mail.md). This page shows the same steps as a pattern, so that another application can follow them.

Status: written, not yet run.

## Prerequisites

- Authentik is up and you can sign in as `akadmin`.
- The application and the person's browser can both reach Authentik at the same address. Bulwark uses the public name, `auth.myah-mitchell.com`, which nothing publishes yet. See [Not yet confirmed](#unconfirmed).
- You know which settings the application reads its OIDC values from. For Bulwark they are in `containers/bulwark/komodo.env` in fleet-stacks.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<slug>` | The Application's slug in Authentik, `mail` for Bulwark |
| `<client-id>` | The Provider's client ID, from [step 2](#credentials) |
| `<client-secret>` | The Provider's client secret, from step 2 |
| `<host>` | The host that runs the application, `mx01` for Bulwark |

## Where the change is made {#where}

Authentik's side is an Application with an OAuth2/OpenID [Provider](index.md#provider), made in the admin interface and kept in Authentik's database. The application's side is three values: the issuer, the client ID, and the client secret. In the fleet the two credentials are Komodo Secrets and the issuer is a stack value in the private repo's inventory, and a run of the host carries them to the container.

No [outpost](index.md#outpost) is involved. The application talks to Authentik's server directly.

## 1. Create the Application and its Provider {#provider}

Open the admin interface at `https://authentik.id01.home.myah-mitchell.com/if/admin/`.

Open *Applications > Applications* and click **Create with provider**. Fill in the application:

| Field | Value for Bulwark |
| --- | --- |
| *Name* | `Mail` |
| *Slug* | `mail` |

Choose **OAuth2/OpenID Provider** as the provider type, then fill in the provider:

| Field | Value for Bulwark |
| --- | --- |
| *Authorization flow* | **default-provider-authorization-implicit-consent** |
| *Client type* | **Confidential** |
| *Redirect URIs* | **Regex**, `https://webmail\.myah-mitchell\.com/.*` |
| *Signing Key* | **authentik Self-signed Certificate** |

Submit the wizard. The Application appears in the list with its Provider beside it.

<details>
<summary>Background: what each of these settings decides</summary>

The slug becomes part of the issuer address, so choose it before anything is configured against it.

A confidential client is an application with a server side that can keep a secret, which Bulwark has. A public client is one that runs wholly in the browser or on a phone and gets no secret.

The redirect URI is the only address Authentik will send a signed-in browser back to. It stops another site from borrowing the application's client ID to collect sign-ins. Give the application's exact callback address where its documentation states one. Bulwark's is not documented, so the example allows any path on its hostname, to be tightened once Authentik's log shows the real one.

With a signing key, Authentik signs its tokens with a private key and publishes the public half, so anything can check a token. Without one it signs with the client secret, which only the holder of that secret can check. Stalwart checks Bulwark's tokens and does not hold the secret, so the `Mail` Provider needs the key.

</details>

## 2. Copy the credentials {#credentials}

Open *Applications > Providers* and open the new Provider. Copy the *Client ID* and the *Client Secret*. They are `<client-id>` and `<client-secret>`.

The same page lists the Provider's addresses. The issuer is:

```text
https://auth.myah-mitchell.com/application/o/<slug>/
```

Authentik's issuer ends in a slash. Whether the application wants the slash is the application's business: Bulwark wants it left off, and Stalwart wants it exactly as Authentik gives it.

## 3. Give the application its values {#values}

Create the two credentials in Komodo, as Secrets. See [Creating one](../../fleet-bootstrap/concepts/variables-and-secrets.md#create) for the clicks.

| Name | Kind | Value |
| --- | --- | --- |
| `MAIL_OIDC_CLIENT_ID` | Secret | `<client-id>` |
| `MAIL_OIDC_CLIENT_SECRET` | Secret | `<client-secret>` |

The stack's `komodo.env` already references both, as `BULWARK_OAUTH_CLIENT_ID` and `BULWARK_OAUTH_CLIENT_SECRET`.

The issuer is not a secret, and it differs per site, so it goes in the host's entry in the private repo's `hosts.yml`:

```yaml
      komodo_stack_env:
        stalwart-server:
          BULWARK_OAUTH_ISSUER_URL: "https://auth.myah-mitchell.com/application/o/mail"
```

For an application of your own, add the same three kinds of key to its container's `komodo.env`: two that reference Secrets, and one left blank for the inventory to fill. See [Give it its values](../../fleet-bootstrap/hosts/ap01-applications.md#new-values).

## 4. Keep forward auth off its route {#route}

An application that signs people in itself takes `chain-no-auth@file` on its Traefik route. Bulwark's container has this line, and an application of your own needs the same:

```yaml
      - "traefik.http.routers.$PROJECT_NAME-bulwark-rtr.middlewares=chain-no-auth@file"
```

With the sign-in chain on the route as well, a person would pass Authentik's forward auth and then be sent to Authentik again by the application. See [Forward auth from each VM's Traefik](index.md#chain).

## 5. Run the host {#run}

Write the host's files again and commit the private repo. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).

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

The last stage redeploys the Stack with the three values in its *Environment*.

## 6. Verify {#verify}

Ask Authentik for the Provider's discovery document, which is what the application reads at its start:

```bash
curl -s https://auth.myah-mitchell.com/application/o/<slug>/.well-known/openid-configuration
```

The answer is JSON, and its `issuer` is the address from step 2. An error page means the slug is wrong or Authentik is not reachable at that name.

Then open the application in a private browser window. For Bulwark that is `https://webmail.myah-mitchell.com`. It sends you to Authentik, and after the sign-in you are back in the application, signed in.

If Authentik shows a redirect URI error, the address in the error is the application's real callback. Put it in the Provider's *Redirect URIs*.

## What's next

Limit the Application to a group, since every user may use it until it has a binding. See [Limit an Application to a group](add-a-user.md#binding).

For Bulwark, the rest of the mail build follows. Stalwart has to trust the same Application before a mailbox opens. See [Sign in through Authentik](../../fleet-bootstrap/hosts/mx01-mail.md#oidc).

## Not yet confirmed {#unconfirmed}

Nothing on this page has been run. mx01 has not been built, and no Provider has been created.

- Authentik's labels, for version 2025.8.4, which the compose file pins. *Create with provider*, the wizard's pages, and *Applications > Providers* follow Authentik's documentation. That documentation names the provider type *OAuth2/OIDC* in one place, and this page keeps *OAuth2/OpenID Provider*, as [Mail (mx01)](../../fleet-bootstrap/hosts/mx01-mail.md#authentik-provider) has it. *Client type*, *Redirect URIs*, *Signing Key*, *Client ID*, *Client Secret*, and the wording of the flow's and the certificate's names were not read from a running Authentik.
- Whether the wizard asks for *Authorization flow*, or fills in a default.
- Authentik's public name. Bulwark's issuer is `auth.myah-mitchell.com`, and authentik-server carries no `kop-public` labels, so nothing publishes that name. See [Identity (id01)](../../fleet-bootstrap/hosts/id01-identity.md#unconfirmed).
- Bulwark's callback path, hence the regex in step 1.
- That Bulwark wants the issuer with no trailing slash. It comes from the comment in `containers/bulwark/komodo.env`.
- The discovery document's address answering through the public name.
