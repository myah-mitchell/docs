# Applications (ap01)

ap01 is the host for whatever you want the fleet to run. Nothing in the plan depends on it, so it is built last, and this page is also the worked example of adding a host of your own.

The page puts two [stacks](../../tools/glossary.md#stack) on ap01. The first, [dozzle-server](../stacks/dozzle-server.md), exists in fleet-stacks already and only has to be listed. The second is one you write yourself, from the repo's template. Skip [step 3](#new-stack) when every stack you want exists.

Every step is the same for any host. Where the page says ap01, a host of your own has its own name, address, and stacks, and each step says what to change. At the end you have a VM that runs the stacks you listed, built by one run, and you have done every part of adding a host once.

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
| `<key-prefix>` | The image's name in upper case, which prefixes its keys, such as `VAULTWARDEN` |

## 1. Describe the host {#describe}

Pick **a name**, **an address**, and **a VMID**. The fleet names a host after its role, two letters and a number, and these pages build the VMID from the VLAN and the address's last part.

A host is described in two files of the [private repo](../../tools/glossary.md#private-repo). The [inventory](../../tools/glossary.md#inventory), `hosts.yml`, says what the host is called and which stacks it runs. OpenTofu's variables file, `opentofu/prod.tfvars`, says how big its VM is.

In `hosts.yml`, add ap01 to the `docker_host` group:

```yaml
    ap01:
      ansible_host: 172.16.7.151
      serverHostname: "ap01"
      docker_stacks:
        - system-agent
        - traefik-agent
```

Every VM lists system-agent. A VM that serves a web interface lists traefik-agent as well.

ap01 is on the internal network, so it takes the gateway the `docker_host` group sets. A host on another network sets `network_gateway` in its own entry, as [bh01](bh01-dmz-edge.md#describe) does.

ap01 is built after the fleet has left bootstrap mode, so the run deploys the list as it is written. For a host added earlier than that, see [Bootstrap mode](../concepts/bootstrap-mode.md).

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  ap01 = {
    server       = "vh01"
    vm_id        = 7151
    cores        = 2
    memory_mb    = 4096
    vlan_id      = 7
    ipv4_address = "172.16.7.151/24"
    ipv4_gateway = "172.16.7.1"
    dns_servers  = ["172.16.7.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
```

Two cores, 4 GB, and 20 GB are enough for the two stacks on this page. Size your own host for what it runs.

The persistent disk holds every stack's data and can grow later, but never shrink. See [Growing a disk](../procedures/grow-a-disk.md).

For a host of your own, change these and keep the rest as it is:

| In the example | For a host of your own |
| --- | --- |
| `ap01`, as the key in `hosts.yml`, in `serverHostname`, and as the key in `prod.tfvars` | The host's name, the same in all three places |
| `172.16.7.151`, in `ansible_host` and in `ipv4_address` | A free address on the host's network. The copy in `prod.tfvars` carries the prefix length |
| `vm_id` | A VMID that is free in Proxmox |
| `vlan_id`, `ipv4_gateway`, `dns_servers` | The VLAN, gateway, and DNS server of the host's network |
| `server` | The Proxmox server that holds the VM, by its name under `servers` |
| `cores`, `memory_mb`, `size_gb` | What the host's stacks need |
| `docker_stacks` | system-agent, traefik-agent for a host that serves a web interface, then the host's own stacks, which steps 2 and 3 add |

The address and the gateway are written in both files, and the run stops when the two disagree.

See [Describing a host](../concepts/fleet-private.md#describe) for every key in both entries, and [km01's page](km01-komodo.md#describe) for a walk through the common ones.

## 2. Add a stack that exists {#existing-stack}

Choose **the stack** from [Stacks](../stacks/index.md) and read its page before listing it. Two sections of the page decide what the host needs.

| Section of the stack page | What to check |
| --- | --- |
| Values it reads | Every Variable and Secret in the table exists in Komodo before the run |
| What the host needs | A stack that needs a Traefik on its host is why traefik-agent is in the list. A port open to the internal subnet only needs `docker_stacks_internal_subnet`, which the `docker_host` group sets already |

Add the stack to ap01's list by its folder name:

```yaml
      docker_stacks:
        - system-agent
        - traefik-agent
        - dozzle-server
```

dozzle-server reads no Variable or Secret of its own and opens no port. Traefik routes `dozzle.ap01.home.myah-mitchell.com` to it.

To set a key of the stack's `komodo.env` for this host, add `komodo_stack_env` to the entry. `komodo.env` is the file in a stack's folder that becomes the Stack's *Environment* in [Komodo](../../tools/komodo/index.md).

dozzle-server runs no agent of its own. It reads each host, ap01 included, from the Dozzle agent in that host's system-agent, and takes the list from `DOZZLE_REMOTE_AGENT`, as addresses with the port, separated by commas:

```yaml
      komodo_stack_env:
        dozzle-server:
          DOZZLE_REMOTE_AGENT: "172.16.7.151:7007,172.16.7.101:7007,172.16.7.121:7007"
        system-agent:
          DOCKNS_CF_API_KEY: ""
          DOCKNS_CF_ACCOUNT_ID: ""
          DOCKNS_CF_ZONE_ID: ""
          DOCKNS_WAN_IP: ""
```

A host's own `komodo_stack_env` replaces the one the `docker_host` group sets, and the two are not merged. That is why the `system-agent` block from [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md#inventory) is repeated here. See [Stack values](../concepts/fleet-private.md#stack-values) for the rules a value follows.

For a host of your own, list the stacks you chose in place of dozzle-server. Add a `komodo_stack_env` block only when a stack's page names a key that differs by host, and repeat the group's `system-agent` block in it when you do.

## 3. Add a stack of your own {#new-stack}

A stack is a folder under `stacks/` in fleet-stacks that holds one hand-written file, `compose.yaml`. Each service in it extends a container defined under `containers/`, and `scripts/build.py` generates the rest of the folder from those containers. See the [Docker Compose primer](../../tools/docker-compose/index.md#in-the-fleet) for how the two folders fit together.

This step is the same on any host, since a stack belongs to the repo and not to a host. Only [List it on the host](#list) names ap01. The example values in the placeholder table are for Vaultwarden, and every `<image>`, `<stack>`, `<project>`, and `<key-prefix>` below takes the names of your own application.

| File in `stacks/<stack>` | Written by | Holds |
| --- | --- | --- |
| `compose.yaml` | You | The project name, the networks, and one `extends` per service |
| `komodo.env` | `build.py` | The Stack's *Environment* in Komodo |
| `setup.yaml` | `build.py` | The folders, seed files, and open ports the host's configuration takes from the stack |
| `README.md` | `build.py` | The same host setup as tables, with commands for the folders and files |

`build.py` also writes a `.env` file with values for local testing. It is ignored by git and never reaches Komodo.

### Get a repo you can push to {#fork}

Skip this when you can push to the fleet-stacks repo the fleet uses.

On GitHub, open `myah-mitchell/fleet-stacks`, click **Fork**, and clone the fork. Then point the run and Komodo at it, in the `vars` of the `docker_host` group in `hosts.yml`:

```yaml
  vars:
    docker_stacks_repo_url: "https://github.com/<github-login>/fleet-stacks.git"
    komodo_stacks_repo: "<github-login>/fleet-stacks"
```

Keep the fork public. The repo holds no secret, and neither the run nor Komodo then needs a credential to read it.

Both values apply to every host in the group, so every host's Stacks move to the fork on its next run.

### Add the container {#container}

From the root of the fleet-stacks checkout, copy the container template to a folder named after the image:

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

The template's [route](../../tools/glossary.md#route) uses `chain-no-auth@file`, which never asks for a sign-in. For a service that Authentik should guard, use the line dozzle's container uses. See [the auth chain](../../tools/glossary.md#auth-chain) for what the two chains do.

```yaml
      - "traefik.http.routers.$PROJECT_NAME-rtr.middlewares=${TRAEFIK_AUTH_CHAIN:-chain-authentik@file}"
```

Then give the key a line in the container's `komodo.env`, so the run can fill it in:

```text
#= Stack Specific Settings
#== Traefik
TRAEFIK_AUTH_CHAIN:
```

In `setup.yaml`, list each folder the container mounts, with the owner as the host sees it. The container's UID 1000 is `101000` on the host. See [UID offsets](../concepts/host-layout.md#uid-offsets).

A container with Traefik labels also says that it needs a Traefik on its host:

```yaml
needs_host:
  - name: traefik
folders:
  - path: <image>-data
    owner: 101000
    group: 101000
```

A port the container publishes on the host gets an entry under `firewall` as well. A service reached through Traefik publishes none. The template's own `setup.yaml` shows every kind of entry, and `scripts/project-layout.md` in fleet-stacks describes every key.

### Add the stack {#stack}

Copy the stack template, and give the new stack its project name and its service:

```bash
cp -r stacks/template stacks/<stack>
```

In `stacks/<stack>/compose.yaml`, set the project name in the comment near the top. `build.py` reads the name from that line.

```yaml
# Project Name: "<project>"
```

Then add the service under the `services:` key:

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
<key-prefix>_HOSTNAME: <image>
<key-prefix>_ADMIN_PASSWORD: [[<key-prefix>_ADMIN_PASSWORD]]
```

Every secret is a reference, written as the name in double square brackets. Nothing secret is written in the repo, and a value that differs by host goes in the inventory's `komodo_stack_env`. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

The stacks in the repo name a value after the service that owns it, and start the name with `GLOBAL_` when more than one stack reads it. Keep a generated secret alphanumeric: 48 characters for a database password and 96 for any other.

### List it on the host {#list}

Add the stack to ap01's `docker_stacks`, after the ones from [step 2](#existing-stack). For a host of your own, this is that host's list:

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

This step is for whoever keeps a copy of this site. The tables on a stack page are generated from fleet-stacks. From the docs checkout, with fleet-stacks checked out next to it:

```bash
python scripts/fleet_facts.py --fleet-stacks ../fleet-stacks
```

The script writes four snippets under `snippets/generated/<stack>` and the register in [Variables and Secrets](../concepts/variables-and-secrets.md). It stops when the new `komodo.env` references a name that `scripts/fleet-register.yaml` does not describe. Add the name there, with its kind and what it holds, and run the script again.

Then write `stacks/<stack>.md` in the shape of the other stack pages, and add it to the site's navigation. The register links to that page for every value the stack reads.

## 4. Stage the values {#values}

Create every Variable and Secret the host's stacks read, in Komodo, before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks.

dozzle-server needs none. Your own stack needs one for each reference from [Give it its values](#new-values).

For a host of your own, go through the *Values it reads* table on the page of each stack it lists.

A value that is missing does not stop the run. It reaches the container as the literal text of the reference. See [How a stack gets its values](../concepts/variables-and-secrets.md#how).

Then generate ap01's files: its SSH host keys, its NixOS file, and its Komodo file. For a host of your own, put its name wherever the commands say `<host>`.

--8<-- "generate-fleet-files.md"

Both playbooks read each stack's `setup.yaml` from the repo's `main` branch as pushed. Push the commit from [step 3](#build) before you generate.

After a move to a fork, the diff also shows the new repo in every other host's Komodo file. Commit those with it.

## 5. Run the build {#run}

/// tab | Semaphore

In [Semaphore](../../tools/semaphore/index.md), run the **site** Template with *Target* set to `ap01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ap01
```

///

The run creates the VM, installs NixOS on it, deploys its configuration, and has Komodo deploy `system-agent-ap01`, `traefik-agent-ap01`, `dozzle-server`, and your own Stack.

For a host of your own, the only change is the target: the host's name in *Target*, or after `target=`. See [How a host is built](../concepts/how-a-host-is-built.md#stages) for what each stage of the run does.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/system-agent/manual.md"

--8<-- "generated/traefik-agent/manual.md"

--8<-- "generated/dozzle-server/manual.md"

For a stack of your own, the same commands are in the `README.md` that `build.py` wrote into its folder.

--8<-- "manual-stack-deploy.md"

</details>

## 6. Verify {#verify}

--8<-- "verify-run.md"

The `dozzle-server` Stack has one service:

--8<-- "generated/dozzle-server/services.md"

Open `https://dozzle.ap01.home.myah-mitchell.com` in a browser. The name needs a DNS record pointing at ap01, or an entry in your own hosts file.

Authentik asks for a sign-in first. Dozzle then lists ap01's containers, and those of every host named in `DOZZLE_REMOTE_AGENT`.

For a host of your own, the first check is the same for every host. After it, follow the *Verify* section on the page of each stack the host runs, and open the names under its *Hostnames*.

## What's next

ap01 is the last host in the [running order](../index.md#running-order).

For a further host, the short form of this page is [Adding a host](../procedures/add-a-host.md).

## Not yet confirmed {#unconfirmed}

- The whole page. ap01 has not been built by the run, and no stack has been added through these steps.
- dozzle-server reading its own host. It reaches ap01's agent at ap01's address and port 7007, from inside a Docker network, and whether the firewall rule for the internal subnet admits that has not been tried. Docker publishes the port with rules of its own, so the request may never pass the chain the host's rule is in. See [dozzle-server](../stacks/dozzle-server.md#unconfirmed).
- The sign-in in front of Dozzle. It depends on the chain that [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md) sets up, which has not been run.
- A run against a fork. `docker_stacks_repo_url` and `komodo_stacks_repo` are ordinary role defaults, and setting them in the inventory has not been tried.
- The format of `DOZZLE_REMOTE_AGENT`. It follows Dozzle's own documentation and has not been tried in this fleet.
