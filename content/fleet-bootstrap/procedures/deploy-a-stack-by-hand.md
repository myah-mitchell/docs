# Deploying a stack by hand

The run deploys a host's stacks in its last stage, through [Komodo](../../tools/komodo/index.md)'s `fleet` [Resource Sync](../../tools/glossary.md#resource-sync). This page creates and deploys one [Stack](../../tools/glossary.md#stack) in Komodo's UI instead, for the times the run is not an option or you want to see each piece. It also covers running only one part of the run from a shell.

The usual way to give a host a stack is the run. See [Adding a stack to a host](../../tools/komodo/add-a-stack-to-a-host.md). Come here when Semaphore or the sync is what is broken, or to learn what the sync does for you.

Nothing here touches a stack's data. The risks are a Stack made under the wrong name, which ends up beside the run's own and fights it for container names, and an edit made in the UI, which the next run undoes. See [What the run does with a Stack made by hand](#takeover).

Status: written, not yet run.

## Prerequisites

- The host runs NixOS and shows as a connected Server in Komodo. See [How a host joins Komodo](../concepts/how-a-host-is-built.md#onboarding).
- Every Variable and Secret the stack reads exists in Komodo. The stack's page lists them. See [Stacks](../stacks/index.md).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host's name in the inventory, such as `id01` |
| `<stack>` | The stack's folder name in fleet-stacks, such as `authentik-server` |
| `<stack-name>` | The Stack's name in Komodo, from [step 2](#create) |

## 1. Prepare the host for the stack {#prepare}

Add the stack to the host's `docker_stacks` list in the private repo's `hosts.yml`. See [Describing a host](../concepts/fleet-private.md#describe).

A stack expects its folders, its seeded config files, and its open ports on the host before the first deploy. All three are part of the host's [NixOS](../../tools/nixos/index.md) configuration, which makes them for every stack in that list. Komodo makes none of them.

Generate the host's files again, commit them, and push. See [After a change](../concepts/fleet-private.md#after-a-change).

Then deploy the host's configuration. From `~/src/fleet-ansible`, in a shell prepared as [Running from a shell again](../foundation/handover.md#shell-runs) describes:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  --tags nixos
```

The recap line for the host shows `failed=0`.

To make the folders without a deploy, use the commands on the host's page, in the collapsed block of its run step. A port has no command of its own. The firewall opens only what the host's configuration lists, and a rule added by hand is lost at the next deploy or reboot.

## 2. Create the Stack {#create}

In Komodo's UI, open *Resources > Stacks* and create a Stack named `<stack-name>`.

The name decides whether the run later takes the Stack over. A stack that runs on every VM carries the host's name on the end. The rest keep their folder name.

| Stack | Name in Komodo |
| --- | --- |
| system-agent, traefik-agent, traefik-bootstrap | `<stack>-<host>`, such as `traefik-bootstrap-id01` |
| crowdsec-agent, dozzle-agent, victoriametrics-agent | `<stack>-<host>` |
| Any other | `<stack>`, such as `authentik-server` |

Set *Server* to **the host's Server**. Under *Choose Mode*, choose **Git Repo**, and fill in the rest:

| Field | Value |
| --- | --- |
| *Git Provider* | `github.com` |
| *Repo* | `myah-mitchell/fleet-stacks` |
| *Branch* | `main` |
| *Run Directory* | `stacks/<stack>` |
| *File Paths* | `compose.yaml`, which is relative to the run directory |

The repo is public, so the provider needs no account. The *Run Directory* is the stack's folder in the repo, where Komodo runs Docker Compose after it has cloned the repo onto the host.

## 3. Fill in the Environment {#environment}

The Stack's *Environment* is the stack's `komodo.env` with this host's values set. The private repo has it ready when the host's Komodo file has been generated.

Open `komodo/stacks/<host>.toml` in the private repo and find the block whose `name` is `<stack-name>`. Copy the text between the two `'''` lines of its `environment` key, and paste it into *Environment*.

Without a generated file, paste the contents of `stacks/<stack>/komodo.env` from fleet-stacks, and set the keys the run would have set:

| Key | Value |
| --- | --- |
| `SERVER_NAME` | The host's name in lower case, such as `id01` |
| `SUB_DOMAIN_NAME` | The sub-domain with its trailing dot, such as `home.` |
| `DOMAIN_NAME` | The domain, such as `myah-mitchell.com` |
| `TRAEFIK_AUTH_CHAIN` | `chain-no-auth@file` in bootstrap mode, blank otherwise |

A stack's file has only the keys the stack uses, so some of the four may be missing. Set the keys the host's `komodo_stack_env` names as well, when it has any.

Leave every `[[NAME]]` reference as it is. Komodo fills those in at deploy time, from the Variable or Secret of that name. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

## 4. Deploy {#deploy}

Click **Save**, then click **Deploy**, and watch the deploy log.

The Stack shows as *Running* when the deploy finishes. The stack's own page lists its services and how to check them.

A reference that reached a container as literal `[[NAME]]` text means the Variable or Secret does not exist. Create it, then click **Deploy** again.

## What's next

Go back to the page that sent you here.

## Running only the last stage {#komodo-stage}

The `komodo` tag runs the deploy stage of `site.yml` and skips the rest. Use it after changing a stack's values, when nothing about the VM or the host has changed. See [The four stages](../concepts/how-a-host-is-built.md#stages) for the tags.

From `~/src/fleet-ansible`, in a shell prepared as [Running from a shell again](../foundation/handover.md#shell-runs) describes:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  --tags komodo
```

OpenTofu does not run, so the shell needs neither the tunnel to the state database nor the state passphrase. It needs `KOMODO_API_KEY` and `KOMODO_API_SECRET`, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`, because the inventory holds an encrypted file.

The stage never connects to the host. It talks to Komodo's API only: it waits for the host's Server to show as connected, runs the sync for the host's Stacks, and waits for them to run.

The stage stops when the committed Komodo file differs from what the inventory gives. Generate the file again, commit it, and push. See [After a change](../concepts/fleet-private.md#after-a-change).

In Semaphore, the `site` Template runs every stage. A run against a host that is built already changes nothing in the earlier stages, so running the whole Template comes to the same result.

## What the run does with a Stack made by hand {#takeover}

The Resource Sync matches Stacks by name. A Stack made by hand under the name from [step 2](#create) is taken over by the next run against the host: its settings and its *Environment* become what the generated file holds.

An edit made to a Stack's *Environment* in the UI lasts until that run. Put a value that should stay in the inventory's `komodo_stack_env`, or in a Variable or Secret the stack references. See [What the run overwrites](../concepts/how-a-host-is-built.md#overwrites).

A Stack made under any other name is left alone, and the run creates its own beside it. Both then claim the same container names on the host. Delete the one made by hand, in Komodo, before the run.

The sync never deletes a Stack. One that a host no longer lists stays in Komodo until you delete it there.

## Not yet confirmed {#unconfirmed}

- The labels in Komodo's UI. They have not been checked against the version of Komodo the fleet runs. The values match the generated file's `server`, `git_provider`, `repo`, `branch`, `run_directory`, and `file_paths`.
- The takeover of a Stack made by hand. The sync has been tested against a mocked Komodo API only.
- A run with `--tags nixos` alone, or with `--tags komodo` alone, against a real host.
