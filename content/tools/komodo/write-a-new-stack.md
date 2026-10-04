# Writing a new stack

This page adds a stack to the fleet-stacks repo, for a service the repo does not have yet. You write a container definition and a short compose file, and `scripts/build.py` generates the files Komodo and the hosts read. Nothing is deployed here. A host gets the stack afterwards, from [Adding a stack to a host](add-a-stack-to-a-host.md).

Status: written, not yet run.

[Applications (ap01)](../../fleet-bootstrap/hosts/ap01-applications.md#new-stack) walks through the same work as part of building a host, with more detail on each file.

## Prerequisites

- A checkout of fleet-stacks that you can push to. To work from a fork, see [Get a repo you can push to](../../fleet-bootstrap/hosts/ap01-applications.md#fork).
- Python 3 with PyYAML, and Docker with Compose, on the machine that holds the checkout.
- [Conventions](https://github.com/myah-mitchell/fleet-stacks/blob/main/docs/conventions.md) read, for the naming and secrets rules.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<image>` | The image's name in lower case, such as `vaultwarden`. It names the container's folder and its service |
| `<IMAGE>` | The same name in upper case, as the prefix of the container's keys |
| `<stack>` | The stack's folder name, such as `vaultwarden-server` |
| `<project>` | The stack's project name, such as `vaultwarden`. Container names, network names, and the stack's folders on a host start with it |
| `<group-id>` | A short lower-case id for a new group in the register, used in [step 6](#docs) |

## Where each file goes {#layout}

A container folder defines one image. A stack folder combines containers into something Komodo deploys.

| File | Written by | Holds |
| --- | --- | --- |
| `containers/<image>/compose.yaml` | You | One service, named with a leading dot, and the shared defaults |
| `containers/<image>/komodo.env` | You | The keys only this container reads |
| `containers/<image>/setup.yaml` | You | The folders, seed files, and ports the container needs on a host |
| `containers/<image>/stack-README.md`, `testing.env` | You | Text for the stack's README, and values for local testing |
| `stacks/<stack>/compose.yaml` | You | The project name, the networks, and one `extends` per service |
| `stacks/<stack>/komodo.env` | `build.py` | The Stack's [Environment](index.md#environment) in Komodo |
| `stacks/<stack>/setup.yaml` | `build.py` | What the host's NixOS configuration takes from the stack |
| `stacks/<stack>/README.md` | `build.py` | The same host setup as tables |

`build.py` also writes `stacks/<stack>/.env` for local testing. Git ignores it, and it never reaches Komodo.

## 1. Add the container {#container}

Skip this step when every image the stack runs already has a folder under `containers/`.

From the root of the checkout:

```bash
cp -r containers/template containers/<image>
```

In `containers/<image>/compose.yaml`, replace `imageName` with `<image>` and `IMAGENAME` with `<IMAGE>` throughout. Set the `image:` line to the image and a version tag, and set the port in the `loadbalancer.server.port` label to the one the service listens on.

Delete what the container does not use: the command, the published port, the volumes, the `kop-public` labels, and the DockNS labels. Keep the block of defaults above `services:` as it is.

In `containers/<image>/setup.yaml`, list each folder the container mounts, with the owner as the host sees it. A container with Traefik labels also says it needs a Traefik on its host:

```yaml
needs_host:
  - name: traefik
folders:
  - path: <image>-data
    owner: 101000
    group: 101000
```

A port the container publishes on the host gets an entry under `firewall`. A service reached only through Traefik publishes none. The comments in the template's own `setup.yaml` show every kind of entry.

<details>
<summary>Background: why the owner is 101000</summary>

The fleet's hosts run Docker with user namespace remapping, so UID 1000 inside a container is UID 101000 on the host. A folder the container writes to has to belong to the number the host sees. See [Why 100000 and 101000](../../fleet-bootstrap/concepts/host-layout.md#uid-offsets).

</details>

## 2. Give the container its values {#values}

In `containers/<image>/komodo.env`, add one line for each key the container's compose file reads. A line takes a fixed value, stays blank, or refers to a Komodo [Variable or Secret](index.md#variables-and-secrets) by name:

```text
#= Stack Specific Settings
#== <image>
<IMAGE>_HOSTNAME: <image>
<IMAGE>_SERVICE_NAME: <image>
<IMAGE>_ADMIN_PASSWORD: [[<IMAGE>_ADMIN_PASSWORD]]
```

Every secret is a reference. The repo is public and holds the names of secrets, never their values. A value that differs by host stays blank here and is set in the inventory. See [How a stack gets its values](../../fleet-bootstrap/concepts/variables-and-secrets.md#how).

Leave out the keys every stack shares, such as `SERVER_NAME`, `TZ`, and the resource limits. `build.py` adds them to each stack from `scripts/base-komodo.env`.

## 3. Add the stack {#stack}

```bash
cp -r stacks/template stacks/<stack>
```

In `stacks/<stack>/compose.yaml`, set the project name in the comment near the top. `build.py` reads the name from this line, and the run stops at a stack that has none:

```yaml
# Project Name: "<project>"
```

Add one service under `services:` for each container the stack runs:

```yaml
  <image>:
    extends:
      file: ../../containers/<image>/compose.yaml
      service: .<image>
```

The template declares four networks: `proxy`, `frontend`, `backend`, and `socket_proxy`. Comment out the ones no service joins, as `stacks/dozzle-server/compose.yaml` does.

A stack with a database adds a service that extends `containers/postgres`, and the application's container names it under `needs_stack` in its own `setup.yaml`. authentik-server is the fullest example in the repo.

## 4. Generate and check {#build}

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

## 5. Commit and push {#push}

```bash
git add containers/<image> stacks/<stack>
git status --short
git commit -m "Add the <stack> stack"
git push
```

The status lists the container's files and the stack's `compose.yaml`, `komodo.env`, `setup.yaml`, and `README.md`. The repo's lint workflow runs `build.py` again and fails when the committed files differ from what it generates.

The stack has to be on `main` before a host can list it. The playbooks that generate a host's files, and Komodo, both read fleet-stacks from GitHub and not from your checkout.

## 6. Add it to the docs site {#docs}

This step is for whoever keeps a copy of this site. The tables on a stack's page are generated from fleet-stacks by `scripts/fleet_facts.py` in the docs repo.

The script stops when a `komodo.env` refers to a name the register does not describe. For each new reference from [step 2](#values), add the name to a group in `scripts/fleet-register.yaml`, with its kind and what it holds. A new group needs an `id`, a `title`, and an `intro`:

```yaml
  - id: <group-id>
    title: <stack>
    intro: >-
      Read by the <stack> stack only.
    names:
      <IMAGE>_ADMIN_PASSWORD: {kind: Secret, value: "A generated password, 48 alphanumeric characters"}
```

Then, from the docs checkout, with fleet-stacks checked out next to it:

```bash
python scripts/fleet_facts.py --fleet-stacks ../fleet-stacks
```

The script prints a `Wrote` line for each of four files under `snippets/generated/<stack>`, and one for the register page. It picks the stack up by its folder under `stacks/`, with no list to add it to.

| Snippet | Holds |
| --- | --- |
| `services.md` | The stack's services |
| `values.md` | The Variables and Secrets it reads |
| `host-setup.md` | Its folders, seed files, and ports |
| `manual.md` | The same folders and files as commands |

Write `content/fleet-bootstrap/stacks/<stack>.md` in the shape of the other stack pages, include the snippets in it, and add the page to the site's navigation. Commit the generated files with it.

## What's next

Put the stack on a host. See [Adding a stack to a host](add-a-stack-to-a-host.md).

## Not yet confirmed {#unconfirmed}

- The whole page. No stack has been written by these steps and then deployed.
- `build.py` and the Compose check against a container made from the template. The repo's lint workflow runs both against the stacks the repo has.
- `fleet_facts.py` against a stack that is not one of the nineteen it has snippets for now.
