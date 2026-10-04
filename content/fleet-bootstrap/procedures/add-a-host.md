# Adding a host

This page adds one more VM to a fleet that is already built. A new host is two entries in the [private repo](../../tools/glossary.md#private-repo), its SSH host keys, two generated files, and one run.

Use it when you want a host for a new job and every [stack](../../tools/glossary.md#stack) it runs exists already in fleet-stacks. It is the short form of every host page, with the steps and little of the reasoning. [Applications (ap01)](../hosts/ap01-applications.md) is the worked example: the same steps with real values, and a stack written from nothing.

The run touches no host but the new one. The one shared thing that changes is `secrets/fleet.yaml`, which [step 3](#host-key) encrypts again so the new host can read it.

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- A free address on the host's [VLAN](../../tools/glossary.md#vlan), and a free VMID on the [Proxmox](../../tools/glossary.md#proxmox) server. The VMID is the number Proxmox knows a VM by.
- The control shell, with the fleet-ansible repo, the private repo and fleet-nixos checked out next to each other, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. See [The control shell](../foundation/control-shell.md).

The [installer ISO](../../tools/glossary.md#installer-iso) on the Proxmox host serves every host, so a new host needs no new ISO.

`<host>` stands for the new host's name throughout.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add the host to the `docker_host` group, with its address, its hostname, and the stacks it runs. In `opentofu/prod.tfvars`, add its VM inside `vms`, under the same name.

The first file is the [inventory](../../tools/glossary.md#inventory), which says what the host is and runs. The second is the [tfvars file](../../tools/glossary.md#tfvars), which says how big its VM is and where it lives. See [Describing a host](../concepts/fleet-private.md#describe) for both entries and every key in them.

List the stacks the host runs once the fleet is finished. While the fleet is in bootstrap mode the generated files swap some of them, and the list stays as it is. See [Bootstrap mode](../concepts/fleet-private.md#bootstrap).

The address, the prefix length and the gateway in the tfvars entry have to match the inventory's `ansible_host`, `network_prefix_length` and `network_gateway`. When the entry has `dns_servers`, they have to match `network_dns`, which defaults to the gateway. The run stops when one differs.

## 2. Set what differs on this host {#stack-values}

Skip this step when every stack runs with the values fleet-stacks gives it.

To set a key of a stack's *Environment* for this host, add `komodo_stack_env` to its entry in `hosts.yml`. The *Environment* is the list of values [Komodo](../../tools/komodo/index.md) hands the stack when it deploys it. See [Stack values](../concepts/fleet-private.md#stack-values) for the form and the rules.

To drop a reference the host does not use, set the key to blank in the same place. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

## 3. Make the host's keys {#host-key}

Make the host's SSH host keys with `new-host-key`. From `~/src/fleet-ansible`:

```bash
nix run ../fleet-nixos#new-host-key -- --fleet ../fleet-private <host>
git -C ../fleet-private status --short
```

The status shows one new file, `secrets/host-keys/<host>.yaml`, and two changed ones, `.sops.yaml` and `secrets/fleet.yaml`.

Run the command once per host. A second run keeps the keys it finds and changes nothing, so the same command at the start of the next step is harmless.

<details>
<summary>Background: why the keys are made before the host exists</summary>

An SSH [host key](../../tools/glossary.md#host-key) is what a machine proves its identity with when you connect to it. Most systems make one at first boot, so the first connection has to accept a key nobody has seen.

The fleet makes the keys first and keeps them, encrypted, in the private repo. The install puts them on the host's [persistent disk](../../tools/glossary.md#persistent-disk), so the run already knows which key the new host must answer with, and refuses any other.

The same key does a second job. The host's [age key](../../tools/glossary.md#age-key) is derived from its ed25519 host key, which is how the host decrypts the fleet's secrets from its first boot. That is why the command also changes `.sops.yaml` and `secrets/fleet.yaml`: the new host joins the list of keys that file is encrypted for. See [Host keys](../concepts/secrets-with-sops.md#host-keys) and the [sops primer](../../tools/sops/index.md).

</details>

## 4. Generate the host's files {#generate}

--8<-- "generate-fleet-files.md"

The diff shows two new files beside the host's keys: `nixos/hosts/<host>.json`, and `komodo/stacks/<host>.toml` with a `[[stack]]` block for each Stack the run deploys.

## 5. Stage the values {#values}

Each stack's page lists the Variables and Secrets it reads. See [Stacks](../stacks/index.md).

Create the ones that do not exist yet, in Komodo, before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks, and [Variables and Secrets](../concepts/variables-and-secrets.md) for what each one holds.

The deploy does not stop for a missing one. A reference with nothing behind it reaches the container as literal text.

## 6. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to **the host's name**.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The run creates the VM, installs [NixOS](../../tools/nixos/index.md) on it, deploys its configuration, and has Komodo deploy its Stacks. See [How a host is built](../concepts/how-a-host-is-built.md) for each stage.

Running it again is safe. A stage that finds its work done changes nothing, so after fixing a failure, start the same run again.

## 7. Verify {#verify}

--8<-- "verify-run.md"

Each stack's page says how to check the stack itself.

## What's next

Give the host's names a DNS record, or an entry in your own hosts file, before opening a web interface on it.

A host added while the fleet is in bootstrap mode leaves it with the rest. See [Leaving bootstrap mode](leave-bootstrap-mode.md).

A host seldom stays as it was built. These pages cover what comes after.

| To | Read |
| --- | --- |
| Put another stack that exists on the host | [Adding a stack to a host](../../tools/komodo/add-a-stack-to-a-host.md) |
| Write a stack of your own | [Writing a new stack](../../tools/komodo/write-a-new-stack.md) |
| See both done with real values | [Applications (ap01)](../hosts/ap01-applications.md) |

## Not yet confirmed {#unconfirmed}

No host has been added by these steps. The commands were run against a copy of the private repo with placeholder secrets, and every host in it evaluates. Confirm these on the first real host and correct this page.

- The run from a blank VM to a deployed host, with the installer answering at the host's address.
- `new-host-key` in a private repo whose `.sops.yaml` already names other hosts, followed by a run of every host that shares `secrets/fleet.yaml`.
