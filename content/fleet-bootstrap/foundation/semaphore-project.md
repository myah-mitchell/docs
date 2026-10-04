# The Semaphore project

Semaphore is running on ci01 with nothing in it. This page gives it what the shell has: the fleet's SSH key, the two repos, the inventory, the run's secrets, the settings nix needs, and one Template that runs `site.yml`.

Status: written, not yet run.

## Prerequisites

- ci01 is built and its Stacks are running, from [The first run](first-run.md#ci01).
- sops is in nix's profile on ci01, from [Semaphore (ci01)](../hosts/ci01-semaphore.md#sops).
- The shell still holds `~/.ssh/fleet-ansible`, `~/.config/fleet/env`, and `~/.config/fleet/deploy.key`.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<github-login>` | Your GitHub username |
| `<tofu-state-password>` | The value of the Komodo Secret `SEMAPHORE_TOFU_STATE_PASSWORD` |
| `<container-path>` | The `PATH` of Semaphore's container, read in [step 7](#nix) |

## 1. Sign in {#sign-in}

Open `https://semaphore.ci01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ci01, or an entry in your own hosts file.

--8<-- "certificate-warning.md"

Sign in with the values of the Komodo Secrets `SEMAPHORE_ADMIN_USER` and `SEMAPHORE_ADMIN_PASSWORD`.

## 2. Create the Project {#project}

Create a Project named `fleet-provisioning`.

A Project holds everything the next steps create: the Key Store, Repositories, Inventory, Variable Groups, and Templates.

Do not name it `ansible`. A login and a key inside it already carry that name.

## 3. Add the keys {#keys}

Open *Key Store* and click **New Key**. Create two entries.

The first is the fleet's SSH key:

| Field | Value |
| --- | --- |
| *Name* | `ansible-bootstrap-key` |
| *Type* | **SSH Key** |
| *Username* | `ansible` |
| *Private Key* | The contents of `~/.ssh/fleet-ansible` in the shell |

*Username* is the login every connection uses, so the inventory does not set one. The run's connections are made by the flake's commands, which call `ssh` and take the key from the agent Semaphore starts for the run.

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

| Field | fleet-ansible | fleet-private |
| --- | --- | --- |
| *Name* | `fleet-ansible` | `fleet-private` |
| *URL* | `https://github.com/myah-mitchell/fleet-ansible` | `https://github.com/myah-mitchell/fleet-private` |
| *Branch* | `main` | `main` |
| *Access Key* | **None** | **fleet-private-read** |

The fleet-ansible repo is public, so it needs no key.

The other three repos get no entry. The run clones each of them itself, from an address the fleet-ansible repo holds.

| Repo | Cloned by | Address in |
| --- | --- | --- |
| fleet-nixos | The nixos role | `nixos_repo_url` |
| fleet-opentofu | The vms role | `vms_repo_url` |
| fleet-stacks | The stacks role | `docker_stacks_repo_url` |

Each address is built from `github_user` in the fleet-ansible repo's `group_vars/all/vars.yml`, so a fork changes that one value. All three are cloned without a credential.

## 5. Create the inventory {#inventory}

Open *Inventory* and click **New Inventory**.

| Field | Value |
| --- | --- |
| *Name* | `ansible-fleet` |
| *Type* | **File** |
| *Repository* | **fleet-private** |
| *Path* | `hosts.yml` |
| *User Credentials* | **ansible-bootstrap-key** |

Semaphore clones the private repo for each run, so a pushed change applies to the next run with nothing to paste. The run finds `group_vars/`, `opentofu/prod.tfvars`, `komodo/stacks/`, `nixos/`, and `secrets/` next to the inventory file, the same as it does in the shell.

## 6. Create the Variable Group {#variables}

Open *Variable Groups*, click **New Group**, and name it `fleet-private`.

The group has two tabs, *Variables* and *Secrets*, and each tab has two sections. Only the two *Environment Variables* sections are used.

| Section | What Semaphore does with it | Used for |
| --- | --- | --- |
| *Variables* tab, *Extra Variables* | Passes it as `--extra-vars` | Nothing. Leave it empty |
| *Variables* tab, *Environment Variables* | Sets it in the run's environment | The two settings nix needs, in [step 7](#nix) |
| *Secrets* tab, *Extra Variables* | Passes it as `--extra-vars`, masked | Nothing. Leave it empty |
| *Secrets* tab, *Environment Variables* | Sets it in the run's environment, masked | What OpenTofu, sops, and the Komodo role read |

### Extra Variables {#extra-variables}

Both *Extra Variables* sections stay empty. An extra variable beats every value in the inventory, so nothing a host might set for itself goes in the group. The identity values stay in `hosts.yml`.

The run's secrets are not extra variables either. They are in the private repo, encrypted, and the run decrypts them with the deploy key.

| Secret | Where the run reads it |
| --- | --- |
| The password of the admin account | `server-password-hash` in `secrets/fleet.yaml`, read by each host |
| The onboarding key | `komodo-onboarding-key` in `secrets/fleet.yaml`, read by each host |
| `server_password`, for a Proxmox host | `group_vars/all/secrets.sops.yaml` |

### Secrets tab, Environment Variables {#environment-variables}

Copy four of these from `~/.config/fleet/env`, each without the word `export` and without the quotes around the value.

| Name | Value |
| --- | --- |
| `TF_ENCRYPTION` | The four-line block from the environment file |
| `TF_VAR_server_api_tokens` | The JSON object from the environment file |
| `KOMODO_API_KEY` | From the environment file |
| `KOMODO_API_SECRET` | From the environment file |
| `SOPS_AGE_KEY` | The line of `~/.config/fleet/deploy.key` that starts with `AGE-SECRET-KEY-` |
| `PG_CONN_STR` | The line below |

```text
postgres://tofu:<tofu-state-password>@postgres:5432/tofu_state?sslmode=disable
```

`postgres` is the database's name on the network Semaphore's containers share. The link is not encrypted and never leaves ci01, and OpenTofu encrypts the state before writing it.

The shell names the deploy key's file in `SOPS_AGE_KEY_FILE`. Semaphore has no such file, so it gets the key itself, in `SOPS_AGE_KEY`.

> [!WARNING]
> `TF_ENCRYPTION` has to hold the same passphrase the shell used. With a different one, Semaphore cannot read the state the handover gives it.

## 7. Give the runs nix {#nix}

The run calls `nix` and `sops`, and both are in a folder that is not on the `PATH` of Semaphore's container. A run sees only the environment Semaphore hands it, so the group sets two more values. See [Nix for the runs](../hosts/ci01-semaphore.md#nix) for where that nix comes from.

On ci01, read the container's own `PATH`:

```bash
docker exec semaphore-semaphore printenv PATH
```

In the group's *Variables* tab, add two entries to *Environment Variables*:

| Name | Value |
| --- | --- |
| `PATH` | `<container-path>:/nix/var/nix/profiles/default/bin` |
| `NIX_CONFIG` | The two lines below |

```ini
experimental-features = nix-command flakes
sandbox = false
```

| Value | Why |
| --- | --- |
| `PATH` | A `PATH` set here replaces the one a run would otherwise get, so it repeats the container's and adds nix's profile after it |
| `experimental-features` | Turns on the flake commands |
| `sandbox` | Turns off the build sandbox, which a container without privileges cannot set up |

The container's `PATH` names the version of Ansible in the image. Read it again, and set the value again, after the image changes.

sops is in the same profile as nix once it has been added there. See [Add sops to nix](../hosts/ci01-semaphore.md#sops), which is also where it is added again after `nix-data` has been emptied.

### One host for each run {#nix-memory}

Semaphore's container has a memory limit of 4 GB, from `SEMAPHORE_MEM_LIMIT` in the stack's `komodo.env`, in place of the 2 GB the other containers get from `GLOBAL_MEM_LIMIT`. Working out one host's configuration takes about 1 GB at its peak. The `nixos` stage installs and deploys one host at a time, even in a run against a group, so a run never works out two configurations at once.

The configuration is only worked out in Semaphore's container. It is built on the host that is being deployed to, which is what `nixos_build_on: remote` in the fleet-ansible repo sets.

## 8. Create the Template {#template}

Open *Task Templates*, click **New Template**, and choose the **Ansible Playbook** app.

| Field | Value |
| --- | --- |
| *Name* | `site` |
| *Playbook Filename* | `site.yml` |
| *Repository* | **fleet-ansible** |
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

Each run asks for *Target*. Answer with one host's name from the inventory. A group's name works too, within the limit in [step 7](#nix-memory).

Bootstrap mode is not a Survey Variable, for the same reason the identity values are not in the group. It stays in the inventory, where a host can differ from the fleet.

Do not run the Template yet. OpenTofu's state is still in the shell, and a run from Semaphore at this point would find an empty database.

## What's next

Move the state across, prove Semaphore with a run, and clean the shell. See [The handover](handover.md).

## Not yet confirmed {#unconfirmed}

- The whole page. Semaphore has not been set up on a ci01 that the run built, and the **site** Template has not run from it.
- The labels and the places in Semaphore's UI that the steps name.
- The flake's commands finding the fleet's SSH key in a run. They call `ssh` with no key named, so the key has to come from an agent that Semaphore starts for the run.
- nix reading Semaphore's clone of the private repo. The flake takes the private repo as a git repo and reads the files git tracks in it.
- nix and sops in a run, with the three values from [step 6](#environment-variables) and [step 7](#nix).
- `SOPS_AGE_KEY` holding the key's one line, entered as a masked value.
- The memory a run takes in Semaphore's container. One host's configuration took 0.94 GB at its peak when it was worked out on another machine.
- The run cloning fleet-nixos from the address in `nixos_repo_url`.
