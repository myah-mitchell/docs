# How a host is built

Every VM in the fleet is built by one ansible run, `site.yml`, from what the private repo says about it. This page explains what that run does, what it needs, and what it leaves to you. Read it once before the first host page, and come back when a run stops somewhere unexpected.

## The five stages {#stages}

`site.yml` takes the hosts named in `target` through five stages, in order.

| Stage | Tag | What it does |
| --- | --- | --- |
| Create the VM | `vms` | Clones the cloud-init template through OpenTofu, from the host's entry in `opentofu/prod.tfvars` |
| Wait | `wait` | Waits for the VM to answer over SSH and for cloud-init to finish |
| Provision | each role's own | Runs `provision.yml` against the host: packages, users, SSH, firewall, Docker, the persistent disk, Periphery, Node Exporter, and the folders, files, and firewall rules its stacks need |
| Reboot | `reboot` | Reboots a new VM one time, if the package upgrade asks for it |
| Deploy | `komodo` | Runs Komodo's `fleet` Resource Sync for this host's Stacks, then waits until every one is running |

A host whose VM already exists skips nothing but the clone. OpenTofu plans no change, provisioning brings the host back in line with the inventory, and the sync redeploys only a Stack whose definition changed. Running it twice is safe, which is why every host page says to run it again after fixing a failure.

The reboot happens on a VM's first run only. The run leaves a marker at `/var/lib/ansible-site-first-run`, and a host that has the marker is never rebooted by a later run. unattended-upgrades handles later kernel updates overnight.

## Where the run starts from {#control-node}

Whatever runs `site.yml` is the control node. The fleet has two.

| Control node | Used for | Holds its secrets in |
| --- | --- | --- |
| A shell on your own machine | km01 and ci01, before Semaphore exists | An environment file, mode `0600`, deleted at the handover |
| Semaphore on ci01 | Every host after the handover, and every later run against km01 and ci01 | The Variable Group's secrets |

Both run the same playbook against the same private repo, so a host built from the shell does not differ from one built from Semaphore. See [The foundation](../foundation/index.md) for how the shell hands over, and [Running from a shell again](../foundation/handover.md#shell-runs) for the times a shell is needed afterwards.

Every connection the control node makes is outbound: the Proxmox API on port 8006, SSH to the VMs, and Komodo's API on port 9120. Nothing in the fleet has to reach the control node.

## What the run needs {#needs}

These come from the environment of the `ansible-playbook` process.

| Name | Holds |
| --- | --- |
| `TF_ENCRYPTION` | OpenTofu's state encryption block, with the passphrase |
| `TF_VAR_server_api_tokens` | A JSON object with one Proxmox API token per server in the tfvars file |
| `KOMODO_API_KEY`, `KOMODO_API_SECRET` | The Komodo service user's API key |
| `PG_CONN_STR` | The state database's connection string. The first run does without it, since the shell keeps state in a file until the handover |

With a single Proxmox server, its token can go in `PROXMOX_VE_API_TOKEN` instead of the JSON object.

One value is an ansible variable, passed with `-e` or held in Semaphore's secret *Extra Variables*: `komodo_onboarding_key`. Everything else comes from the private repo. See [The private repo](fleet-private.md).

The run asks for nothing under Semaphore, so an identity value missing from the inventory stops it. From a shell it asks one time for whatever the inventory leaves unset.

## What first boot does {#first-boot}

The template's cloud-init snippet is in minimal mode. A new clone installs and starts the guest agent, and creates the `ansible` login with the keys from `ansible_ssh_public_keys` and passwordless sudo. It does nothing else, so first boot takes a minute or two and never reboots.

`tofu apply` returns as soon as the guest agent reports an address, which is before cloud-init finishes. The wait stage covers the gap by running `cloud-init status --wait` on the VM. Exit code 2 counts as success there. Proxmox generates user data with a key cloud-init has deprecated, so every clone finishes as degraded with no real error.

A new VM's SSH host key is accepted on first contact and pinned afterwards. Set `site_accept_new_host_keys: false` to turn that off and accept keys yourself.

## How a host joins Komodo {#onboarding}

Periphery on each host dials out to Komodo Core on km01. Core never connects inward, so km01 is the only host with an inbound rule for port 9120.

A host proves itself to Core the first time with an onboarding key, the way a new SSH host key is accepted one time. Core creates the host's Server at that moment, and the two trust each other by their own keypairs from then on. One key, created with an expiry and not privileged, onboards every new host until it expires. See [the onboarding key](../foundation/komodo-setup.md#onboarding-key).

Periphery keeps its private key at `/srv/persist/host/komodo/periphery.key`, on the persistent disk. A rebuilt host that keeps its disk reconnects as the Server it already was and needs no key.

## What the run overwrites {#overwrites}

A Stack's *Environment* in Komodo comes from the committed file `komodo/stacks/<host>.toml`. An edit made in Komodo's UI is undone by the next sync. Put the value in the inventory's `komodo_stack_env`, or in a Komodo Variable or Secret the stack references.

A config file the run copies onto a host is never replaced when a copy is already there. Your edits to it survive every later run.

A Stack made by hand under the name the run would give it is taken over, not duplicated. Stacks that run on every VM carry the host name on the end, such as `system-agent-id01`, because Komodo wants Stack names unique. The rest keep their plain names.

## Seeing what a run would do {#check}

Add `--check` to the command, or tick *Dry Run* in Semaphore. OpenTofu stops at its plan, and the run confirms the committed Komodo file is current without running the sync.

For a VM that does not exist yet, check mode fails at the provision stage, because there is nothing to connect to. That failure is expected.

## Limits {#limits}

- The sync never deletes. A Stack a host no longer lists stays in Komodo until you delete it there, and so does a host's traefik-bootstrap Stack after the host leaves bootstrap mode.
- A reference to a Variable or Secret that does not exist reaches the container as the literal text. See [Variables and Secrets](variables-and-secrets.md#how).
- OpenTofu is given every VM in the tfvars file on every run, and refuses any plan that would destroy one. Removing a VM is a deliberate edit in the opentofu repo.
- Every run reads each Proxmox server's VM list. A node that is down is missing from that list, and a run that includes an unpinned VM on it fails.

## Not yet confirmed {#unconfirmed}

The run has been tested against a mocked Komodo API and a mocked Proxmox API, and OpenTofu's part against one real Proxmox node. These have not been run against the real fleet.

- The whole run, end to end, from a shell and from Semaphore.
- Running the sync for some of its Stacks, while the file also lists Stacks for a Server that is not in Komodo yet.
- The sync on km01, where Core redeploys the Stack it runs in. See [The first run](../foundation/first-run.md#unconfirmed).
- A clone pinned to a node other than the template node, which is migrated after cloning.
