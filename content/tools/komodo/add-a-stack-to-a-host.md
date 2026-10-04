# Adding a stack to a host

This page gives a host that is already built one more stack from the fleet-stacks repo. You make the change in the private repo's inventory, and the next run of the host carries it to the host and to Komodo.

Status: written, not yet run.

For a host that does not exist yet, see [Adding a host](../../fleet-bootstrap/procedures/add-a-host.md). For a stack that does not exist yet, see [Writing a new stack](write-a-new-stack.md) first.

## Prerequisites

- The host is built and shows as a connected [Server](index.md#server) in Komodo.
- The stack has a folder under `stacks/` on the `main` branch of fleet-stacks, with its generated `komodo.env` and `setup.yaml`.
- The control shell, with fleet-ansible, the private repo, and fleet-nixos checked out next to each other, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host's name in the inventory, such as `ap01` |
| `<stack>` | The stack's folder name in fleet-stacks, such as `dozzle-server` |
| `<key>` | A key that has a line in the stack's `komodo.env`. Only [step 2](#stack-values) uses it |
| `<value>` | What this host gives that key |

## 1. List the stack {#list}

In the private repo's `hosts.yml`, add the stack to the host's `docker_stacks`:

```yaml
    <host>:
      docker_stacks:
        - system-agent
        - traefik-agent
        - <stack>
```

The list holds what the host runs once the fleet is finished. While the host is in bootstrap mode, the run leaves out a stack that needs a service elsewhere in the fleet. See [Bootstrap mode](../../fleet-bootstrap/concepts/bootstrap-mode.md#changes).

If the stack already runs on another host, Komodo needs a different [Stack](index.md#stack) name for each one. See [List it on the host](../../fleet-bootstrap/hosts/ap01-applications.md#list) for `komodo_stacks_per_host`.

## 2. Set what differs on this host {#stack-values}

Skip this step when the stack runs with the values fleet-stacks gives it.

To set a key of the stack's [Environment](index.md#environment) for this host, add it under `komodo_stack_env` in the host's entry:

```yaml
    <host>:
      komodo_stack_env:
        <stack>:
          <key>: "<value>"
```

A key with no line in the stack's `komodo.env` stops the run. A secret never goes here. See [Stack values](../../fleet-bootstrap/concepts/fleet-private.md#stack-values) for the rules.

## 3. Stage the values {#values}

The stack's `komodo.env` is in fleet-stacks, which the foundation never has you clone to your own machine. Clone it if you have no checkout:

```bash
git clone https://github.com/myah-mitchell/fleet-stacks ~/src/fleet-stacks
```

List the references in the file, from `~/src/fleet-stacks`:

```bash
grep -o '\[\[[A-Z0-9_]*\]\]' stacks/<stack>/komodo.env | sort -u
```

In Komodo, create each [Variable or Secret](index.md#variables-and-secrets) in that list that does not exist yet. See [Creating one](../../fleet-bootstrap/concepts/variables-and-secrets.md#create) for the clicks, and the stack's own page under [Stacks](../../fleet-bootstrap/stacks/index.md) for what each one holds.

> [!WARNING]
> A reference with nothing behind it does not stop the deploy. The container gets the literal text `[[NAME]]`, and fails later in a way that does not name the cause.

## 4. Generate the host's files {#generate}

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
ansible-playbook -i ../fleet-private/hosts.yml komodo-sync.yml
git -C ../fleet-private add hosts.yml nixos/ komodo/
git -C ../fleet-private diff --cached
```

The diff of `komodo/stacks/<host>.toml` shows a new `[[stack]]` block for the stack. The diff of `nixos/hosts/<host>.json` shows the folders, seed files, and ports the stack needs on the host.

Either playbook stops when the stack needs a service on its own host that no listed stack provides, such as a Traefik. Add the stack that provides it to the list.

Commit and push:

```bash
git -C ../fleet-private commit -m "Add <stack> to <host>"
git -C ../fleet-private push
```

<details>
<summary>Background: why two files change for one stack</summary>

A stack needs things from two systems. Komodo needs the Stack's definition, which is the TOML file its [Resource Sync](index.md#resource-sync) reads. The host needs the stack's folders, its seed files, and its open ports before the first deploy, and those are part of the host's NixOS configuration, which is built from the JSON file.

Both are generated from the same list, so they cannot disagree. Komodo reads the pushed copy of the private repo, and the run stops at a host whose committed files differ from what the inventory gives. That is why the push comes before the run.

</details>

## 5. Run the host {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `<host>`.

///

/// tab | Command line

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

OpenTofu finds nothing to change. The NixOS stage makes the stack's folders and opens its ports, and the last stage has Komodo create the Stack and deploy it. See [From the repo to running containers](index.md#flow).

## 6. Verify {#verify}

--8<-- "verify-run.md"

The stack's own page says how to check its services. See [Stacks](../../fleet-bootstrap/stacks/index.md).

## Taking a stack off a host {#remove}

Remove the stack from `docker_stacks`, then repeat [step 4](#generate) and [step 5](#run). The sync never deletes, so the Stack stays in Komodo and its containers keep running.

To stop them, open the Stack in Komodo and destroy it, then delete the Stack. The stack's folders under `/opt/docker/volumes` stay on the host until you remove them.

## What's next

Give each of the stack's hostnames a DNS record, or an entry in your own hosts file, before opening its web interface.

## Not yet confirmed {#unconfirmed}

- The whole page. No stack has been added to a built host by these steps.
- A run against a built host that changes only its stacks: that the NixOS stage adds the folders and ports without restarting anything else.
- The controls in Komodo's UI for stopping and deleting a Stack, in [Taking a stack off a host](#remove). Their labels have not been checked against the version the fleet runs.
- The `grep` in [step 3](#values) lists every reference. It was run against the `komodo.env` files in fleet-stacks, and matches what the register page lists for them.
