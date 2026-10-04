# Setting up Komodo

This page takes a Komodo Core that has just started for the first time and gives it what the run needs: an admin account, an API key for ansible, an onboarding key for new hosts, the Resource Sync that reads the private repo, and the first Variables and Secrets.

At the end Komodo is ready for a run to hand it a host's Stacks, and the private repo holds two changes for the first run to commit. Most of the work is clicks in Komodo's web interface. Three steps also have you edit a file in the shell. If [Komodo](../../tools/komodo/index.md) is new to you, read its primer's [ideas](../../tools/komodo/index.md#ideas) first, since this page uses most of them.

Status: written, not yet run.

## Prerequisites

- Core is running on km01, from [The first run](first-run.md#start-core).
- The shell has the tools open and `~/.config/fleet/env` loaded, from [The control shell](control-shell.md).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<core-public-key>` | Core's public key, shown in Komodo in [step 2](#core-key) |
| `<komodo-api-key>` | The service user's API key, from [step 3](#service-user) |
| `<komodo-api-secret>` | The secret shown with that key |
| `<onboarding-key>` | The onboarding key, from [step 4](#onboarding-key) |

## 1. Create the admin account {#admin}

Open `http://172.16.7.101:9120` in a browser.

Enter a username and password, then click **Sign Up**. This is the first account on the instance, so it becomes the admin.

## 2. Give ansible Core's public key {#core-key}

In Komodo's UI, open *Settings*. Core's public key is at the top of the page. Copy **the key**.

Set it in the private repo's `group_vars/all/private.yml`, next to the address already there:

```yaml
komodo_core_address: "http://172.16.7.101:9120"
komodo_core_public_key: "<core-public-key>"
```

Neither value is secret. Every host's Periphery reads them to know where Core is and which Core to trust. See [Core and Periphery](../../tools/glossary.md#core-and-periphery).

Do not commit yet. The first run commits this change together with the one from [step 4](#onboarding-key), after it has written the generated files again.

## 3. Create the service user {#service-user}

1. Open *Settings > Users* and create a **service user** named `ansible`.
2. Make it an **admin**.
3. Create an **API key** for it, and copy **the key and the secret**. The secret is shown one time.

Add both to `~/.config/fleet/env` in the shell:

```bash
export KOMODO_API_KEY="<komodo-api-key>"
export KOMODO_API_SECRET="<komodo-api-secret>"
```

A service user is an account for a program. It has no password and cannot sign in to the UI, and the run calls Komodo's API with its key.

The user runs the Resource Sync, which creates Stacks, and reads Servers and Stacks. An admin is the simple way to allow that. The narrowest permissions that work have not been found yet.

## 4. Create the onboarding key {#onboarding-key}

Open *Settings > Onboarding* and create a key that has an expiry and is not privileged. Copy **the key**.

An [onboarding key](../../tools/glossary.md#onboarding-key) is what a new host's Periphery shows Core the first time it connects, so that Core accepts it and creates its [Server](../../tools/glossary.md#server).

The key is one of the fleet's secrets, and every host reads it from `secrets/fleet.yaml` in the private repo. Open that file with sops, from the private repo's folder:

```bash
cd ~/src/fleet-private
sops secrets/fleet.yaml
```

Replace the text `placeholder` with the key, and save:

```yaml
komodo-onboarding-key: "<onboarding-key>"
```

sops encrypts the file again when the editor closes. See [Editing a secret](../concepts/secrets-with-sops.md#edit). The first run commits the change.

<details>
<summary>Background: why one stored key, with an expiry and no privilege</summary>

One key onboards every new host until it expires, so it is stored and not made per host. A key for each host would mean a visit to Komodo's UI before every build, which is the kind of manual step the run exists to remove.

Anyone holding the key can add a Server under a new name. The expiry and the unprivileged setting limit that: the key stops working on a date, and it cannot replace the key of a Server that exists, so it cannot be used to pose as a host the fleet already has.

A host uses the key one time. After that, Core and the host's Periphery trust each other by their own keypairs, and a rebuilt host that keeps its persistent disk reconnects without the key. See [how a host joins Komodo](../concepts/how-a-host-is-built.md#onboarding).

</details>

When the key expires, create a new one, store it the same way, and commit. The next host built takes it from there.

## 5. Create the Resource Sync {#resource-sync}

A [Resource Sync](../../tools/glossary.md#resource-sync) makes Komodo's Stacks match files in a git repo. Here the files are each host's Stacks in the private repo, so Komodo needs a token that can read that repo.

1. On GitHub, create a **fine-grained personal access token** with read-only *Contents* access to the private repo and nothing else.
2. In Komodo, open *Settings > Providers* and add **the token** for `github.com`.
3. Open *Syncs* and create a Resource Sync named `fleet`, with the values below.

| Field | Value |
| --- | --- |
| *Mode* | **Git Repo** |
| *Git Provider* | `github.com`, with **the account** you just added |
| *Repo* | `<github-login>/fleet-private`, with your GitHub username |
| *Branch* | `main` |
| *Resource Paths* | `komodo/stacks` |
| *Delete Unmatched Resources* | **Off** |
| *Managed* | **Off** |

> [!WARNING]
> Leave *Delete Unmatched Resources* off. The files list only the Stacks the run manages, and with deletion on, the sync removes every other resource in Komodo.

Do not add a webhook, and do not run the sync as a whole from the UI.

The run executes it for one host's Stacks at a time, after that host is prepared. A full sync deploys every host's Stacks at once, including those of a host that does not exist yet.

The sync's *Pending* view shows what differs from the files for every host. It is a useful check after a push.

## 6. Create the operational defaults {#operational}

Create the nineteen Variables in the [operational defaults](../concepts/variables-and-secrets.md#operational) table, each with **the name and value** the table gives. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

Leave **Is Secret** unticked on all of them. They are settings, not credentials.

A Variable is a named value that Komodo puts into a stack's environment wherever the stack references it, and a Secret is a Variable whose value Komodo hides. See [Variables and Secrets](../../tools/glossary.md#variables-and-secrets).

Every stack reads these, so a missing one fails every deploy the same way:

```text
error while interpolating services.traefik.cpus: failed to cast to expected type: strconv.ParseFloat: parsing "[[GLOBAL_CPUS_LIMIT]]": invalid syntax
```

## 7. Create the database Secrets {#komodo}

On km01, print the two credentials Core is running on:

```bash
grep -E '^KOMODO_DB_(USERNAME|PASSWORD)=' /opt/docker/volumes/komodo/komodo-server.env
```

Create the Secrets `KOMODO_DB_USERNAME` and `KOMODO_DB_PASSWORD` with exactly **those values**, and tick **Is Secret** on both.

Core is running on credentials from the file made during [the first start](first-run.md#start-core). Komodo needs the same two values as Secrets before it deploys Core's stack itself, because from then on the stack takes them from Komodo and not from the file.

> [!WARNING]
> A value that differs from the file locks Core out of its own database on the next deploy. Postgres keeps the password it was first started with, whatever the stack is given later.

## 8. Create the Traefik values {#traefik}

Create the seven values in the [Traefik](../concepts/variables-and-secrets.md#traefik) table, and tick **Is Secret** on each one the table's *Kind* gives as Secret.

| Value | Where it comes from |
| --- | --- |
| The Cloudflare token and email | A Cloudflare API token with DNS edit rights on the zone, and the account's email |
| The Let's Encrypt email | An address you read. Expiry notices go there |
| The Authentik hostname | The name id01 will have. Enter it now, before id01 exists |
| The CrowdSec host | The literal text `unused` |
| The Redis server | The name tf01 will have |
| The Redis password | Generate one now, alphanumeric only |

km01's first Traefik is traefik-bootstrap, which carries five of these references without using them. They still have to exist before its first deploy. The values start to matter when the fleet leaves [bootstrap mode](../../tools/glossary.md#bootstrap-mode).

## What's next

Go back to the first run and hand Core over to Komodo. See [Run km01 in full](first-run.md#km01-full).

## Not yet confirmed {#unconfirmed}

- The whole page. Komodo has not been set up on a km01 that the run built.
- The labels and the places in Komodo's UI that the steps name.
- The narrowest permissions the service user works with. The page makes it an admin.
- A key that expires while hosts are running. A host that has joined does not use the key again, and a deploy that changes nothing but the key does not restart Periphery.
