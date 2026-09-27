# The Semaphore project

Semaphore is running on ci01 with nothing in it. This page gives it what the shell has: the fleet's SSH key, the two repos, the inventory, the run's secrets, and one Template that runs `site.yml`.

Status: written, not yet run as a whole. The Project, the keys, the repositories, and the inventory follow the steps the real Semaphore was set up with. The **site** Template has not run from Semaphore against a real fleet.

## Prerequisites

- ci01 is built and its Stacks are running, from [The first run](first-run.md#ci01).
- The shell still holds `~/.ssh/fleet-ansible` and `~/.config/fleet/env`.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<github-login>` | Your GitHub username |
| `<tofu-state-password>` | The value of the Komodo Secret `SEMAPHORE_TOFU_STATE_PASSWORD` |
| `<admin-password>` | The admin account's password, the one typed at the prompt during the first run |
| `<onboarding-key>` | The value of `KOMODO_ONBOARDING_KEY` in the environment file |

## 1. Sign in {#sign-in}

Open `https://semaphore.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Sign in with the values of the Komodo Secrets `SEMAPHORE_ADMIN_USER` and `SEMAPHORE_ADMIN_PASSWORD`.

## 2. Create the Project {#project}

Create a Project named `fleet-provisioning`.

A Project holds everything the next steps create: the Key Store, Repositories, Inventory, Variable Groups, and Templates.

Do not name it `ansible`. A Repository, a login, and a key inside it already carry that name.

## 3. Add the keys {#keys}

Open *Key Store* and click **New Key**. Create two entries.

The first is the fleet's SSH key:

| Field | Value |
| --- | --- |
| *Name* | `ansible-bootstrap-key` |
| *Type* | **SSH Key** |
| *Username* | `ansible` |
| *Private Key* | The contents of `~/.ssh/fleet-ansible` in the shell |

*Username* is the login every connection uses, so the inventory does not set one.

The second lets Semaphore clone the private repo:

| Field | Value |
| --- | --- |
| *Name* | `fleet-private-read` |
| *Type* | **Login with password** |
| *Login* | `<github-login>` |
| *Password* | A fine-grained personal access token with read-only *Contents* access to the private repo |

The token Komodo's Git provider holds has the same scope. One token can serve both, or each can have its own so that one can be revoked alone.

## 4. Add the repositories {#repositories}

Open *Repositories* and click **New Repository**. Create two entries.

| Field | ansible | fleet-private |
| --- | --- | --- |
| *Name* | `ansible` | `fleet-private` |
| *URL* | `https://github.com/myah-mitchell/ansible` | `https://github.com/myah-mitchell/fleet-private` |
| *Branch* | `main` | `main` |
| *Access Key* | **None** | **fleet-private-read** |

The ansible repo is public, so it needs no key.

## 5. Create the inventory {#inventory}

Open *Inventory* and click **New Inventory**.

| Field | Value |
| --- | --- |
| *Name* | `ansible-fleet` |
| *Type* | **File** |
| *Repository* | **fleet-private** |
| *Path* | `hosts.yml` |
| *User Credentials* | **ansible-bootstrap-key** |

Semaphore clones the private repo for each run, so a pushed change applies to the next run with nothing to paste. The run finds `group_vars/`, `opentofu/prod.tfvars`, and `komodo/stacks/` next to the inventory file, the same as it does in the shell.

## 6. Create the Variable Group {#variables}

Open *Variable Groups*, click **New Group**, and name it `fleet-private`.

The group has two tabs, *Variables* and *Secrets*, and each tab has two sections. Only the *Secrets* tab is used.

| Section | What Semaphore does with it | Used for |
| --- | --- | --- |
| *Variables* tab, *Extra Variables* | Passes it as `--extra-vars` | Nothing. Leave it empty |
| *Variables* tab, *Environment Variables* | Sets it in the run's environment | Nothing. Leave it empty |
| *Secrets* tab, *Extra Variables* | Passes it as `--extra-vars`, masked | The two ansible secrets |
| *Secrets* tab, *Environment Variables* | Sets it in the run's environment, masked | What OpenTofu and the Komodo role read |

An extra variable beats every value in the inventory, so nothing a host might set for itself goes in the group. The identity values stay in `hosts.yml`.

### Secrets tab, Extra Variables {#extra-variables}

| Name | Value |
| --- | --- |
| `server_password` | `<admin-password>` |
| `komodo_onboarding_key` | `<onboarding-key>` |

Semaphore has no terminal to ask on. Without `server_password` a run leaves every password as it is, and a new host's admin account has none.

### Secrets tab, Environment Variables {#environment-variables}

Copy four of these from `~/.config/fleet/env`, each without the word `export` and without the quotes around the value.

| Name | Value |
| --- | --- |
| `TF_ENCRYPTION` | The four-line block from the environment file |
| `TF_VAR_server_api_tokens` | The JSON object from the environment file |
| `KOMODO_API_KEY` | From the environment file |
| `KOMODO_API_SECRET` | From the environment file |
| `PG_CONN_STR` | The line below |

```text
postgres://tofu:<tofu-state-password>@postgres:5432/tofu_state?sslmode=disable
```

`postgres` is the database's name on the network Semaphore's containers share. The link is not encrypted and never leaves ci01, and OpenTofu encrypts the state before writing it.

> [!WARNING]
> `TF_ENCRYPTION` has to hold the same passphrase the shell used. With a different one, Semaphore cannot read the state the handover gives it.

## 7. Create the Template {#template}

Open *Task Templates*, click **New Template**, and choose the **Ansible Playbook** app.

| Field | Value |
| --- | --- |
| *Name* | `site` |
| *Playbook Filename* | `site.yml` |
| *Repository* | **ansible** |
| *Inventory* | **ansible-fleet** |
| *Variable Groups* | **fleet-private** |
| *Tags* | Empty, so every stage runs |

Open the Template's *Survey Variables* tab and add one entry:

| Field | Value |
| --- | --- |
| *Name* | `target` |
| *Title* | **Target** |
| *Type* | **String** |
| *Required* | **Yes** |

Each run asks for *Target*. Answer with a host's name from the inventory, or a group's.

Bootstrap mode is not a Survey Variable, for the same reason the identity values are not in the group. It stays in the inventory, where a host can differ from the fleet.

Do not run the Template yet. OpenTofu's state is still in the shell, and a run from Semaphore now would find an empty database.

## What's next

Move the state across, prove Semaphore with a run, and clean the shell. See [The handover](handover.md).
