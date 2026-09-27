# Applications (ap01)

ap01 is the host for whatever you want the fleet to run. Nothing in the plan depends on it, so it is built last, and this page is also the worked example of adding a host of your own.

The page puts two stacks on ap01. The first, [dozzle-server](../stacks/dozzle-server.md), exists in docker-stacks already and only has to be listed. The second is one you write yourself, from the repo's template. Skip [step 3](#new-stack) when every stack you want exists.

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- The fleet has left bootstrap mode. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).
- For [step 3](#new-stack), a GitHub account, and a machine with git, Python 3, PyYAML, and Docker Compose.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<github-login>` | Your GitHub username |
| `<image>` | The name of the image your stack runs, in lower case, such as `vaultwarden` |
| `<stack>` | The new stack's folder name, such as `vaultwarden-server` |
| `<project>` | The new stack's project name, which prefixes its containers and folders, such as `vaultwarden` |
| `<IMAGE>` | The image's name in upper case, which prefixes its keys, such as `VAULTWARDEN` |

## 1. Describe the host {#describe}

Pick a name, an address, and a VMID. The fleet names a host after its role, two letters and a number, and these pages build the VMID from the VLAN and the address's last part.

In the private repo's `hosts.yml`, add ap01 to the `docker_host` group:

```yaml
    ap01:
      ansible_host: 192.0.2.16
      serverHostname: "ap01"
      docker_stacks:
        - system-agent
        - traefik-agent
```

Every VM lists system-agent. A VM that serves a web interface lists traefik-agent as well.

ap01 is built after the fleet has left bootstrap mode, so the run deploys the list as it is written. For a host added earlier than that, see [Bootstrap mode](../concepts/bootstrap-mode.md).

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  ap01 = {
    server       = "vh01"
    vm_id        = 7016
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 7
    ipv4_address = "192.0.2.16/24"
    ipv4_gateway = "192.0.2.1"
    dns_servers  = ["192.0.2.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

Two cores, 4 GB, and 20 GB are enough for the two stacks on this page. Size your own host for what it runs. The persistent disk holds every stack's data and can grow later, but never shrink. See [Growing a disk](../procedures/grow-a-disk.md).

See [Describing a host](../concepts/fleet-private.md#describe) for every key in both entries.

## 2. Add a stack that exists {#existing-stack}

Choose the stack from [Stacks](../stacks/index.md) and read its page before listing it. Two sections of the page decide what the host needs.

| Section of the stack page | What to check |
| --- | --- |
| Values it reads | Every Variable and Secret in the table exists in Komodo before the run |
| What the host needs | A stack that needs a Traefik on its host is why traefik-agent is in the list. A firewall rule scoped to the internal subnet needs `docker_stacks_internal_subnet`, which the `docker_host` group sets already |

Add the stack to ap01's list by its folder name. dozzle-server also takes the place of system-agent, for the reason given below:

```yaml
      docker_stacks:
        - traefik-agent
        - dozzle-server
```

dozzle-server carries a Dozzle agent of its own, and so does system-agent. Both publish port 7007, so the two cannot run on one host as the repo stands. ap01 leaves system-agent out, and so sends no metrics or logs to ci01 until one of the two stacks changes in docker-stacks. See [Not yet confirmed](#unconfirmed). A stack that publishes no port of system-agent's goes in the list beside it, and the host keeps both.

dozzle-server reads no Variable or Secret of its own. It opens port 7007 to the internal subnet, and Traefik routes `dozzle.ap01.home.myah-mitchell.com` to it.

To set a key of the stack's `komodo.env` for this host, add `komodo_stack_env` to the entry. dozzle-server reads the other hosts' Dozzle agents from `DOZZLE_REMOTE_AGENT`, a comma-separated list of addresses with the port:

```yaml
      komodo_stack_env:
        dozzle-server:
          DOZZLE_REMOTE_AGENT: "192.0.2.11:7007,192.0.2.13:7007"
```

The agent on each of the other hosts is part of system-agent. ci01 does not run system-agent, so leave its address out of the list.

A host's own `komodo_stack_env` replaces the one the `docker_host` group sets, and the two are not merged. On a host that lists system-agent, repeat the group's `system-agent` block beside your own keys. See [Stack values](../concepts/fleet-private.md#stack-values) for the rules a value follows.

## 3. Add a stack of your own {#new-stack}

A stack is a folder under `stacks/` in docker-stacks that holds one hand-written file, `compose.yaml`. Each service in it extends a container defined under `containers/`, and `scripts/build.py` generates the rest of the folder from those containers.

| File in `stacks/<stack>` | Written by | Holds |
| --- | --- | --- |
| `compose.yaml` | You | The project name, the networks, and one `extends` per service |
| `komodo.env` | `build.py` | The Stack's *Environment* in Komodo |
| `setup.yaml` | `build.py` | The folders, files, and firewall rules the run creates on the host |
| `README.md` | `build.py` | The same host setup as commands |

`build.py` also writes a `.env` file with values for local testing. It is ignored by git and never reaches Komodo.

### Get a repo you can push to {#fork}

Skip this when you can push to the docker-stacks repo the fleet uses.

Fork `myah-mitchell/docker-stacks` on GitHub and clone the fork. Then point the run and Komodo at it, in the `vars` of the `docker_host` group in `hosts.yml`:

```yaml
  vars:
    docker_stacks_repo_url: "https://github.com/<github-login>/docker-stacks.git"
    komodo_stacks_repo: "<github-login>/docker-stacks"
```

Keep the fork public. The repo holds no secret, and neither the run nor Komodo then needs a credential to read it.

Both values apply to every host in the group, so every host's Stacks move to the fork on its next run.

### Add the container {#container}

From the root of the docker-stacks checkout, copy the container template to a folder named after the image:

```bash
cp -r containers/template containers/<image>
```

| File in `containers/<image>` | Edit it to hold |
| --- | --- |
| `compose.yaml` | One service, named with a leading dot, such as `.<image>` |
| `komodo.env` | The keys only this container reads |
| `setup.yaml` | What the container needs on the host |
| `stack-README.md`, `testing.env` | Text for the stack's README, and values for local testing |

In `compose.yaml`, replace `imageName` and `IMAGENAME` throughout, and set the image and the port Traefik forwards to. Delete what the container does not use: the command, the published port, the volumes, the `kop-public` labels, and the DockNS labels. Keep the block of defaults above the service as it is.

The template's route uses `chain-no-auth@file`, which never asks for a sign-in. For a service that Authentik should guard, use the line dozzle's container uses:

```yaml
      - "traefik.http.routers.$PROJECT_NAME-rtr.middlewares=${TRAEFIK_AUTH_CHAIN:-chain-authentik@file}"
```

Then give the key a line in the container's `komodo.env`, so the run can fill it in:

```text
#= Stack Specific Settings
#== Traefik
TRAEFIK_AUTH_CHAIN:
```

In `setup.yaml`, list each folder the container mounts, with the owner as the host sees it. The container's UID 1000 is `101000` on the host. A container with Traefik labels also says that it needs a Traefik on its host:

```yaml
needs_host:
  - name: traefik
folders:
  - path: <image>-data
    owner: 101000
    group: 101000
```

A port the container publishes on the host gets an entry under `firewall` as well. A service reached through Traefik publishes none. The template's own `setup.yaml` shows every kind of entry, and `scripts/project-layout.md` in docker-stacks describes every key.

### Add the stack {#stack}

Copy the stack template, and give the new stack its project name and its service:

```bash
cp -r stacks/template stacks/<stack>
```

In `stacks/<stack>/compose.yaml`, set the project name in the comment near the top. `build.py` reads the name from that line.

```yaml
# Project Name: "<project>"
```

Then add the service under `services:`

```yaml
  <image>:
    extends:
      file: ../../containers/<image>/compose.yaml
      service: .<image>
```

The template declares four networks: `proxy`, `frontend`, `backend`, and `socket_proxy`. Comment out the ones no service joins, as dozzle-server does with `backend`.

A stack with a database adds one more service that extends `containers/postgres`, and the application's container names it under `needs_stack` in its `setup.yaml`. authentik-server is the fullest example in the repo.

### Generate and check {#build}

Generate the stack's files:

```bash
python3 scripts/build.py
```

The output ends with `Build complete.` The script stops with a message when a `setup.yaml` has an unknown key, or when a container needs a service that nothing in the stack provides.

Check that Compose accepts the result:

```bash
docker compose --env-file stacks/<stack>/.env \
  -f stacks/<stack>/compose.yaml config -q
```

The command prints nothing when the stack is valid.

Commit the container folder and the stack folder together, generated files included, and push. The repo's CI fails when the committed files differ from what `build.py` generates.

### Give it its values {#new-values}

A line in a container's `komodo.env` takes a fixed value, stays blank, or references a Komodo Variable or Secret by name:

```text
#= Stack Specific Settings
#== <image>
<IMAGE>_HOSTNAME: <image>
<IMAGE>_ADMIN_PASSWORD: [[<IMAGE>_ADMIN_PASSWORD]]
```

Every secret is a reference. Nothing secret is written in the repo, and a value that differs by host goes in the inventory's `komodo_stack_env`. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

The stacks in the repo name a value after the service that owns it, and start the name with `GLOBAL_` when more than one stack reads it. Keep a generated secret alphanumeric: 48 characters for a database password and 96 for any other.

### List it on the host {#list}

Add the stack to ap01's `docker_stacks`, after the ones from step 2:

```yaml
        - dozzle-server
        - <stack>
```

A stack that runs on more than one host needs the host's name on the end of its Stack, since Komodo wants Stack names unique. Add it to `komodo_stacks_per_host` in the `docker_host` group's `vars`. The value replaces the role's default, so repeat the six names the default holds:

```yaml
    komodo_stacks_per_host:
      - system-agent
      - traefik-agent
      - traefik-bootstrap
      - crowdsec-agent
      - dozzle-agent
      - victoriametrics-agent
      - <stack>
```

### Add it to these pages {#docs}

This step is for whoever keeps a copy of this site. The tables on a stack page are generated from docker-stacks. From the docs checkout, with docker-stacks checked out next to it:

```bash
python scripts/fleet_facts.py --docker-stacks ../docker-stacks
```

The script writes four snippets under `snippets/generated/<stack>` and the register in [Variables and Secrets](../concepts/variables-and-secrets.md). It stops when the new `komodo.env` references a name that `scripts/fleet-register.yaml` does not describe. Add the name there, with its kind and what it holds, and run the script again.

Then write `stacks/<stack>.md` in the shape of the other stack pages, and add it to the site's navigation. The register links to that page for every value the stack reads.

## 4. Stage the values {#values}

Create every Variable and Secret the host's stacks read, in Komodo, before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

dozzle-server needs none. Your own stack needs one for each reference from [Give it its values](#new-values).

Then generate ap01's Komodo file.

--8<-- "generate-komodo-files.md"

After a move to a fork, the diff also shows the new repo in every other host's file. Commit those with it.

## 5. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `ap01`.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ap01 \
  -e komodo_onboarding_key="$KOMODO_ONBOARDING_KEY"
```

///

The run creates the VM, provisions it, and has Komodo deploy `traefik-agent-ap01`, `dozzle-server`, and your own Stack.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-provision.md"

--8<-- "generated/traefik-agent/manual.md"

--8<-- "generated/dozzle-server/manual.md"

For a stack of your own, the same commands are in the `README.md` that `build.py` wrote into its folder.

--8<-- "manual-stack-deploy.md"

</details>

## 6. Verify {#verify}

--8<-- "verify-run.md"

The `dozzle-server` Stack has three services:

--8<-- "generated/dozzle-server/services.md"

Open `https://dozzle.ap01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ap01, or an entry in your own hosts file.

Authentik asks for a sign-in first. Dozzle then lists ap01's containers, and those of every host named in `DOZZLE_REMOTE_AGENT`.

## What's next

ap01 is the last host in the [running order](../index.md#running-order).

For a further host, the short form of this page is [Adding a host](../procedures/add-a-host.md).

## Not yet confirmed {#unconfirmed}

- The whole page. ap01 has not been built by the run, and no stack has been added through these steps.
- dozzle-server beside system-agent. Both publish port 7007, so one of the two has to change in docker-stacks before a host can list both. Until then ap01 lists dozzle-server alone and ships no metrics or logs. No host in the plan lists dozzle-server, so the pair has never been deployed together.
- The sign-in in front of Dozzle. It depends on the chain that [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md) sets up, which has not been run.
- A run against a fork. `docker_stacks_repo_url` and `komodo_stacks_repo` are ordinary role defaults, and setting them in the inventory has not been tried.
- The format of `DOZZLE_REMOTE_AGENT`. It follows Dozzle's own documentation and has not been tried in this fleet.
