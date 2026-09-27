# Adding a host

A new host is two entries in the private repo, its SSH host keys, two generated files, and one run. This page is the short form, for a host whose stacks exist already. For the worked example, and for writing a stack of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- A free address on the host's VLAN, and a free VMID on the Proxmox server.
- The control shell, with the ansible repo, the private repo and nixos-fleet checked out next to each other, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. See [The control shell](../foundation/control-shell.md).

The installer ISO on the Proxmox host serves every host, so a new host needs no new ISO.

`<host>` stands for the new host's name throughout.

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add the host to the `docker_host` group, with its address, its hostname, and the stacks it runs. In `opentofu/prod.tfvars`, add its VM inside `vms`, under the same name.

See [Describing a host](../concepts/fleet-private.md#describe) for both entries and every key in them.

List the stacks the host runs once the fleet is finished. While the fleet is in bootstrap mode the generated files swap some of them, and the list stays as it is. See [Bootstrap mode](../concepts/fleet-private.md#bootstrap).

The address, the prefix length and the gateway in the tfvars entry have to match the inventory's `ansible_host`, `network_prefix_length` and `network_gateway`. The run stops when one differs.

## 2. Set what differs on this host {#stack-values}

Skip this step when every stack runs with the values docker-stacks gives it.

To set a key of a stack's *Environment* for this host, add `komodo_stack_env` to its entry in `hosts.yml`. See [Stack values](../concepts/fleet-private.md#stack-values) for the form and the rules.

To drop a reference the host does not use, set the key to blank in the same place. See [Blanking a reference](../concepts/variables-and-secrets.md#blanking).

## 3. Make the host's keys {#host-key}

A host's SSH host keys are made before the host exists, and the install puts them on its persistent disk. The host's age key is derived from its ed25519 host key, which is how the host decrypts the fleet's secrets from its first boot.

From `~/src/ansible`:

```bash
nix run ../nixos-fleet#new-host-key -- --fleet ../fleet-private <host>
git -C ../fleet-private status --short
```

The status shows one new file, `secrets/host-keys/<host>.yaml`, and two changed ones, `.sops.yaml` and `secrets/fleet.yaml`. See [Host keys](../concepts/secrets-with-sops.md#host-keys).

Run the command once per host. A second run keeps the keys it finds and changes nothing.

## 4. Generate the host's files {#generate}

--8<-- "generate-fleet-files.md"

The diff shows two new files beside the host's keys: `nixos/hosts/<host>.json`, and `komodo/stacks/<host>.toml` with a `[[stack]]` block for each Stack the run deploys.

## 5. Stage the values {#values}

Each stack's page lists the Variables and Secrets it reads. See [Stacks](../stacks/index.md).

Create the ones that do not exist yet, in Komodo, before the run. See [Creating one](../concepts/variables-and-secrets.md#create) for the clicks, and [Variables and Secrets](../concepts/variables-and-secrets.md) for what each one holds.

## 6. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The run creates the VM, installs NixOS on it, deploys its configuration, and has Komodo deploy its Stacks. See [How a host is built](../concepts/how-a-host-is-built.md) for each stage.

## 7. Verify {#verify}

--8<-- "verify-run.md"

Each stack's page says how to check the stack itself.

## What's next

Give the host's names a DNS record, or an entry in your own hosts file, before opening a web interface on it.

A host added while the fleet is in bootstrap mode leaves it with the rest. See [Leaving bootstrap mode](leave-bootstrap-mode.md).

## Not yet confirmed {#unconfirmed}

No host has been added by these steps. The commands were run against a copy of the private repo with placeholder secrets, and every host in it evaluates. Confirm these on the first real host and correct this page.

- The run from a blank VM to a deployed host, with the installer answering at the host's address.
- `new-host-key` in a private repo whose `.sops.yaml` already names other hosts, followed by a run of every host that shares `secrets/fleet.yaml`.
