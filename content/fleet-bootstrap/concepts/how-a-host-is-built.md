# How a host is built

Every VM in the fleet is built by one ansible run, `site.yml`, from what the private repo says about it. This page explains what that run does, what it needs, and what it leaves to you. Read it once before the first host page, and come back when a run stops somewhere unexpected.

Status: written, not yet run. See [Not yet confirmed](#unconfirmed).

## The four stages {#stages}

`site.yml` takes the hosts named in `target` through four stages, in order.

| Stage | Tag | What it does |
| --- | --- | --- |
| Create the VM | `vms` | OpenTofu creates a blank VM from the host's entry in `opentofu/prod.tfvars`. Its disk is empty, so it boots the installer ISO |
| Wait | `wait` | Waits for the host to answer on its SSH port |
| NixOS | `nixos` | Stops if the host's committed files under `nixos/` are out of date. Asks the host what it runs, installs NixOS when the answer is the installer, then deploys the host's configuration |
| Deploy the stacks | `komodo` | Runs Komodo's `fleet` Resource Sync for this host's Stacks, then waits until every one is running |

Ansible runs nothing on the host itself. Every task runs on the control node, which calls OpenTofu, the commands of [the NixOS flake](nixos-flake.md#commands), and Komodo's API. A host has no Python and needs none.

A host that is already built goes through the same four stages. OpenTofu plans no change, the host answers as installed and is not installed again, the deploy activates whatever changed in its configuration, and the sync redeploys a Stack that changed or is not running. Running it twice is safe, which is why every host page says to run it again after fixing a failure.

The run never reboots a built host. A deploy that brings a new kernel takes effect at the next reboot, which is yours to do. See [Updating the fleet](../procedures/update-the-fleet.md#reboot).

## Where the run starts from {#control-node}

Whatever runs `site.yml` is the control node. The fleet has two.

| Control node | Used for | Holds its secrets in |
| --- | --- | --- |
| A shell on your own machine | km01 and ci01, before Semaphore exists | An environment file, mode `0600`, deleted at the handover |
| Semaphore on ci01 | Every host after the handover, and every later run against km01 and ci01 | The Variable Group's secrets |

Both run the same playbook against the same private repo, so a host built from the shell does not differ from one built from Semaphore. See [The foundation](../foundation/index.md) for how the shell hands over, and [Running from a shell again](../foundation/handover.md#shell-runs) for the times a shell is needed afterwards.

Every connection the control node makes is outbound: the Proxmox API on port 8006, SSH to the VMs, Komodo's API on port 9120, and GitHub for the repos it clones. Nothing in the fleet has to reach the control node.

## What the run needs {#needs}

The control node needs nix with flakes enabled, ansible with the collections in the fleet-ansible repo's `requirements.yml`, OpenTofu, sops, and age. See [The control shell](../foundation/control-shell.md#tools) for the shell, and [The Semaphore project](../foundation/semaphore-project.md#nix) for Semaphore.

These come from the environment of the `ansible-playbook` process.

| Name | Holds |
| --- | --- |
| `TF_ENCRYPTION` | OpenTofu's state encryption block, with the passphrase |
| `TF_VAR_server_api_tokens` | A JSON object with one Proxmox API token per server in the tfvars file |
| `KOMODO_API_KEY`, `KOMODO_API_SECRET` | The Komodo service user's API key |
| `PG_CONN_STR` | The state database's connection string. The runs from the shell do without it, since they pass `-e vms_backend=local` and keep state in a file until the handover |
| `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE` | The deploy key, which decrypts the private repo's secrets. See [Secrets with sops](secrets-with-sops.md#keys) |

With a single Proxmox server, its token can go in `PROXMOX_VE_API_TOKEN` in place of the JSON object.

The control node also holds the SSH private key whose public half is in `ansible_ssh_public_keys`. The installer, every built host, and the deploy account on each Proxmox host accept that key.

Everything else comes from the private repo. See [The private repo](fleet-private.md). The run never asks a question, so a value missing from the inventory stops it with a message that says what is missing.

## What first boot does {#first-boot}

A new VM has three blank disks, the installer ISO in its CD drive, and a cloud-init drive that carries its address. Its boot order is the OS disk and then the CD drive, so an empty OS disk sends it to the installer.

The installer runs from memory and changes nothing on the disks by itself. It takes the VM's address from the cloud-init drive, starts the guest agent, and accepts the fleet's admin and deploy SSH keys for root. Its sshd makes a new host key at every boot. See [The installer](nixos-flake.md#installer).

`tofu apply` returns when the guest agent reports an address, and the wait stage then waits for the SSH port. The NixOS stage asks the host what it runs with `host-state`, gets `installer`, and runs `install-host`. That command partitions the OS and Docker disks, prepares the persistent disk, writes the host's SSH host keys onto it, installs the host's configuration, and reboots. The OS disk holds a system after that, so the VM boots NixOS and never the installer again.

`install-host` reads the installer's host key through Proxmox, from the VM itself by its guest agent, and checks the installer against that key before it sends the host's keys. The keys go to the VM OpenTofu made for the host, or nowhere. The host takes its SSH host keys from the persistent disk at its first boot, so it answers with the keys the private repo holds for it. The deploy that follows checks the host against that key and refuses any other. Nothing that carries a secret accepts a host key on first contact. See [The host's SSH keys](secrets-with-sops.md#host-keys).

## How a host joins Komodo {#onboarding}

Periphery is a systemd service on each host, and it dials out to Komodo Core on km01. Core never connects inward, so km01 is the only host that opens port 9120.

A host proves itself to Core the first time with an onboarding key. Core creates the host's Server at that moment, and the two trust each other by their own keypairs from then on. One key, created with an expiry and not privileged, onboards every new host until it expires. See [the onboarding key](../foundation/komodo-setup.md#onboarding-key).

The onboarding key is the entry `komodo-onboarding-key` in the private repo's `secrets/fleet.yaml`, encrypted with sops. A host decrypts it with its own key when its configuration is activated, and Periphery reads it from there. It is not an ansible variable, and it is never passed on a command line.

Periphery keeps its private key at `/srv/persist/host/komodo/periphery.key`, on the persistent disk. A rebuilt host that keeps its disk reconnects as the Server it already was and needs no onboarding key.

## What the run overwrites {#overwrites}

A host's operating system is built from its configuration, so a change made by hand to a file the configuration owns is undone by the next deploy or reboot. That covers the firewall, the accounts and their keys, the services, and everything under `/etc`. Change the inventory, generate the host's files again, and run the host. See [After a change](fleet-private.md#after-a-change).

A Stack's *Environment* in Komodo comes from the committed file `komodo/stacks/<host>.toml`. An edit made in Komodo's UI is undone by the next sync. Put the value in the inventory's `komodo_stack_env`, or in a Komodo Variable or Secret the stack references.

A config file that a deploy copies into a stack's folder is never replaced when a copy is already there. Your edits to it survive every later run.

A Stack made by hand under the name the run would give it is taken over, not duplicated. Stacks that run on every VM carry the host name on the end, such as `system-agent-id01`, because Komodo wants Stack names unique. The rest keep their plain names.

## Seeing what a run would do {#check}

Add `--check` to the command, or tick *Dry Run* in Semaphore.

| Stage | In check mode |
| --- | --- |
| Create the VM | OpenTofu stops at its plan |
| Wait | Skipped |
| NixOS | Confirms the committed files are current, and evaluates the host's configuration on the control node with `deploy-host --action dry-build`, which lists what would be built. Nothing reaches the host |
| Deploy the stacks | Confirms the committed Komodo file is current, and stops there |

Check mode works the same for a host that has never been built, since no stage reaches the host. It does not list which services a deploy would restart. For that, run `deploy-host --action dry-activate` by hand, which builds the system on the host. See [The commands](nixos-flake.md#commands).

## Limits {#limits}

- The sync never deletes. A Stack a host no longer lists stays in Komodo until you delete it there, and so does a host's traefik-bootstrap Stack after the host leaves bootstrap mode.
- A reference to a Variable or Secret that does not exist reaches the container as the literal text. See [Variables and Secrets](variables-and-secrets.md#how).
- OpenTofu is given only the VMs of the hosts in `target`, and refuses any plan that would destroy one. Removing a VM is a deliberate edit in the fleet-opentofu repo.
- Every run reads each Proxmox server's VM list. A node that is down is missing from that list, and a run that includes an unpinned VM on it fails.
- The flake reads only the files git tracks in the private repo. A generated file that is not committed, or at least added, does not reach a host. See [After a change](fleet-private.md#after-a-change).
- The run stops when a VM's address, prefix length, or gateway in the tfvars file differs from the inventory.
- A host's configuration is built on the host, which downloads what it lacks from the public NixOS cache. A host with no route to the internet cannot be installed or deployed this way.

## Not yet confirmed {#unconfirmed}

The run has been checked against the playbooks, the flake's commands, and an evaluation of each example host. None of it has run against a real Proxmox host.

- The whole run, end to end, from a shell and from Semaphore.
- A blank VM booting the installer, the installer taking its address from the cloud-init drive, and its guest agent reporting that address to OpenTofu.
- `install-host` from start to end on a VM, and the first boot into NixOS with the host keys from the persistent disk.
- `install-host` reading the installer's key through `qm guest exec` on a real Proxmox host. It was tried against the ISO in QEMU on a workstation, with a stand-in for the Proxmox host.
- Periphery onboarding from the secret in `secrets/fleet.yaml`, and reconnecting after a rebuild with the key it kept.
- Running the sync for some of its Stacks, while the file also lists Stacks for a Server that is not in Komodo yet.
- The sync on km01, where Core redeploys the Stack it runs in. See [The first run](../foundation/first-run.md#unconfirmed).
- A VM pinned to a node other than the server's default node.
