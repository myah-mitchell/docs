# Running part of a run

A run of `site.yml` normally takes a host through all four stages. This page narrows a run: to some hosts, to some stages, or to a report of what it would do with nothing changed. Use it after a change that touches one stage only, or before a run you want to see the effect of first.

Status: written, not yet run.

The stages and what each does are in [The four stages](../../fleet-bootstrap/concepts/how-a-host-is-built.md#stages). The ideas used here are [tags](index.md#tags), [extra vars](index.md#extra-vars), and [check mode](index.md#check-mode).

## Prerequisites

- The host's files in the private repo are generated, committed, and pushed. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).
- For a run from Semaphore, the **site** Template exists. See [The Semaphore project](../../fleet-bootstrap/foundation/semaphore-project.md#template).
- For a run from a shell, the shell is prepared as [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs) describes. Before the handover, it is the shell from [The control shell](../../fleet-bootstrap/foundation/control-shell.md).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<target>` | The hosts to run, chosen in [step 1](#target) |
| `<tags>` | The tags of the stages to run, chosen in [step 2](#stages) |

## 1. Choose the hosts {#target}

Every play in `site.yml` runs for the hosts in the variable `target`, and the run stops at once without it. Give it one of these:

| Form | Example | Runs |
| --- | --- | --- |
| A host's name in the inventory | `id01` | That host |
| Several names, with commas | `id01,pk01` | Each of them |
| A group's name | `docker_host` | Every host in the group |

A run against several hosts creates their VMs in one OpenTofu apply, then installs and deploys them one at a time. See [One host for each run](../../fleet-bootstrap/foundation/semaphore-project.md#nix-memory) for why Semaphore is given one host.

## 2. Choose the stages {#stages}

Each stage has a tag. Without `--tags`, all four run.

| Tag | Runs | The control node needs |
| --- | --- | --- |
| `vms` | OpenTofu, then the wait | The state passphrase, the Proxmox tokens, and the state database or file |
| `wait` | The wait for the SSH port | Nothing more |
| `nixos` | The check of the committed files, an install if the host runs the installer, and the deploy | nix, and the fleet's SSH key |
| `komodo` | The check of the committed Komodo file, the sync, and the wait for the Stacks | `KOMODO_API_KEY` and `KOMODO_API_SECRET` |

Every combination also needs the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`, because the inventory holds an encrypted file that Ansible decrypts before any task. See [What the run needs](../../fleet-bootstrap/concepts/how-a-host-is-built.md#needs) for each value.

These are the options the build guide uses:

| Option | Use it when | Used in |
| --- | --- | --- |
| `--tags nixos` | The host's configuration changed and its VM and Stacks did not | [Updating the fleet](../../fleet-bootstrap/procedures/update-the-fleet.md) |
| `--tags komodo` | A stack's values changed and the host did not | [Running only the last stage](../../fleet-bootstrap/procedures/deploy-a-stack-by-hand.md#komodo-stage) |
| `--skip-tags komodo` | Komodo Core is not up to deploy anything | [The first run](../../fleet-bootstrap/foundation/first-run.md#km01-vm) and [Rebuilding km01](../../fleet-bootstrap/procedures/rebuild-a-vm.md#km01) |

`--skip-tags` is the reverse of `--tags`: it leaves out the stages named and runs the rest.

A host that runs the installer cannot be installed without the `vms` stage in the same run. The install needs the VM's Proxmox node and VMID, which the `vms` stage reads from OpenTofu, and the `nixos` stage stops with a message that says so. A host that is already built has no such need.

## 3. See what it would do {#check}

Do a check run first when the change is one you have not made before. Nothing is created, installed, deployed, or synced.

/// tab | Semaphore

Run the **site** Template with *Target* set to `<target>`, and tick **Dry Run**.

///

/// tab | Command line

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<target> \
  --check
```

///

The recap line for each host shows `failed=0`. A check run stops, as a real run does, at committed files that are out of date and at a host's configuration that does not evaluate.

What each stage does in a check run is in [Seeing what a run would do](../../fleet-bootstrap/concepts/how-a-host-is-built.md#check). On the command line, `--check` combines with `--tags`, so a check of one stage is the command in step 4 with `--check` added.

## 4. Run it {#run}

From a shell, in `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<target> \
  --tags <tags>
```

Name several stages with commas and no spaces, as in `--tags nixos,komodo`. The recap line for each host shows `failed=0`.

In Semaphore, the **site** Template passes no tags, so a run from it goes through every stage. For a host that is already built, that comes to the same result: OpenTofu plans no change, the host is not installed again, and the later stages do what they would have done alone. Run the Template with *Target* set to `<target>`.

<details>
<summary>Background: why a whole run is safe where a part would do</summary>

Each stage is idempotent in the sense the primer gives the word. OpenTofu compares the VM it knows with the tfvars file and changes only what differs. The `nixos` stage asks the host what it runs before it installs anything, and a deploy of an unchanged configuration activates nothing new. The Resource Sync redeploys a Stack only when it changed or is not running.

A part of a run saves time and saves the control node from needing every secret. It is never needed for safety. See [Idempotence](index.md#idempotence).

</details>

## What's next

When a run stops, see [Reading a failed run](read-a-failed-run.md).

## Not yet confirmed {#unconfirmed}

- A run with `--tags` or `--skip-tags` against a real host. The combinations come from the tags in `site.yml` and from the pages that use them.
- A run with a group or a list of hosts in `target`.
- The *Dry Run* label in Semaphore, and whether the Template's form can pass tags for one run. The **site** Template as [The Semaphore project](../../fleet-bootstrap/foundation/semaphore-project.md#template) creates it leaves *Tags* empty.
- What a check run prints for the `nixos` stage. The stage runs the flake's `deploy-host` with `dry-build` through Ansible's command module, which shows a command's output only when the run is given `-v`.
