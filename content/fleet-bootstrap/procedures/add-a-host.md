# Adding a host

A new host is two entries in the private repo, a generated file, and one run. This page is the short form, for a host whose stacks exist already. For the worked example, and for writing a stack of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- A free address on the host's VLAN, and a free VMID on the Proxmox server.
- A checkout of the ansible repo with the private repo next to it, to generate the Komodo file from. It needs no secret.

`<host>` stands for the new host's name throughout.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add the host to the `docker_host` group, with its address, its hostname, and the stacks it runs. In `opentofu/prod.tfvars`, add its VM inside `vms`, under the same name.

See [Describing a host](../concepts/fleet-private.md#describe) for both entries and every key in them.

List the stacks the host runs once the fleet is finished. While the fleet is in bootstrap mode the run swaps some of them by itself, and the list stays as it is. See [Bootstrap mode](../concepts/fleet-private.md#bootstrap).

The address in the tfvars entry has to match `ansible_host`. The run stops when the two differ.

## 2. Set what differs on this host {#stack-values}

Skip this step when every stack runs with the values docker-stacks gives it.

To set a key of a stack's *Environment* for this host, add `komodo_stack_env` to its entry in `hosts.yml`. See [Stack values](../concepts/fleet-private.md#stack-values) for the form and the rules.

To drop a reference the host does not use, set the key to blank in the same place. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

## 3. Generate the Komodo file {#generate}

--8<-- "generate-komodo-files.md"

The diff shows one new file, `komodo/stacks/<host>.toml`, with a `[[stack]]` block for each Stack the run deploys.

## 4. Stage the values {#values}

Each stack's page lists the Variables and Secrets it reads. See [Stacks](../stacks/index.md).

Create the ones that do not exist yet, in Komodo, before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks, and [Variables and Secrets](../concepts/variables-and-secrets.md) for what each one holds.

## 5. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  -e komodo_onboarding_key="$KOMODO_ONBOARDING_KEY"
```

///

The run creates the VM, provisions it, and has Komodo deploy its Stacks. See [How a host is built](../concepts/how-a-host-is-built.md) for each stage.

## 6. Verify {#verify}

--8<-- "verify-run.md"

Each stack's page says how to check the stack itself.

## What's next

Give the host's names a DNS record, or an entry in your own hosts file, before opening a web interface on it.

A host added while the fleet is in bootstrap mode leaves it with the rest. See [Leaving bootstrap mode](leave-bootstrap-mode.md).
