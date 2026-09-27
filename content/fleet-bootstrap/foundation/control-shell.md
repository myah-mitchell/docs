# The control shell

This page turns a shell on your own machine into the fleet's first control node: the tools, the checkouts, the fleet's SSH key, and the file that holds the run's secrets. Any Linux shell that can reach the Proxmox hosts and the fleet's VLANs works, WSL included.

Status: written, not yet run.

## Prerequisites

- A Linux shell with sudo, on a machine that can open connections to the Proxmox API on port 8006, to the fleet's VMs on port 22, and to km01 on port 9120. Nothing has to connect back to it.
- A GitHub account that owns a fork or copy of the private repo, or can create one.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<fleet-key>` | The public half of the fleet's SSH key, from [step 3](#ssh-key) |
| `<your-key>` | Your own SSH public key, the one you log in to hosts with |
| `<your-login>` | The username you want for your own login on each host |
| `<state-passphrase>` | The passphrase OpenTofu encrypts its state with, generated in [step 4](#environment) |

## 1. Install the tools {#tools}

Install ansible and what its roles need on the control node:

```bash
sudo apt update
sudo apt install git ansible python3-netaddr python3-jmespath sshpass figlet
```

The playbooks need ansible-core 2.15 or later. Check with `ansible --version`.

Install OpenTofu from its own package repository:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://get.opentofu.org/install-opentofu.sh \
  -o install-opentofu.sh
chmod +x install-opentofu.sh
./install-opentofu.sh --install-method deb
rm -f install-opentofu.sh
```

`tofu version` prints 1.9.0 or later. Semaphore's image ships 1.9.0, and the opentofu repo supports every version from there up.

## 2. Check out the repos {#checkouts}

The ansible repo and the private repo sit next to each other, so every command on these pages can reach the inventory at `../fleet-private/hosts.yml`:

```bash
mkdir -p ~/src
git clone https://github.com/myah-mitchell/ansible ~/src/ansible
cd ~/src/ansible
ansible-galaxy install -r requirements.yml
```

If the private repo exists already, clone it to `~/src/fleet-private` and skip to step 3.

To start one, create an empty private repo named `fleet-private` on GitHub, then fill it from the skeleton:

```bash
git clone git@github.com:myah-mitchell/fleet-private.git ~/src/fleet-private
cp -r ~/src/ansible/private-repo.example/. ~/src/fleet-private/
rm ~/src/fleet-private/README.md
```

The skeleton's hosts and addresses are examples. Later pages replace them as each host is described. See [The private repo](../concepts/fleet-private.md) for what each file holds.

Run every `ansible-playbook` command on these pages from `~/src/ansible`.

## 3. Create the fleet's SSH key {#ssh-key}

Generate the key ansible reaches every host with:

```bash
ssh-keygen -t ed25519 -C "fleet-ansible" -f ~/.ssh/fleet-ansible -N ""
```

Open `group_vars/all/private.yml` in the private repo. Add the contents of `~/.ssh/fleet-ansible.pub` to `ansible_ssh_public_keys`, and your own public key to `admin_ssh_public_keys`:

```yaml
ansible_ssh_public_keys:
  - "ssh-ed25519 <fleet-key> fleet-ansible"
admin_ssh_public_keys:
  - "ssh-ed25519 <your-key> you@your-machine"
```

Each new VM gives the first list to its `ansible` login, which has passwordless sudo. The second list goes to the admin account and to root, for your own sessions.

The private half moves into Semaphore's Key Store later, and the handover deletes it from the shell.

> [!WARNING]
> This key is passwordless root on every host in the fleet. It never goes in a repo, a chat, or a backup that is not encrypted.

## 4. Write the environment file {#environment}

The run reads its secrets from the environment. Keep them in one private file, so they are never typed on a command line:

```bash
install -d -m 0700 ~/.config/fleet
install -m 0600 /dev/null ~/.config/fleet/env
```

Generate the state passphrase, and store a copy in your password manager:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48; echo
```

Open `~/.config/fleet/env` in an editor and add:

```bash
export ANSIBLE_REMOTE_USER="ansible"
export ANSIBLE_PRIVATE_KEY_FILE="$HOME/.ssh/fleet-ansible"
export TF_ENCRYPTION='key_provider "pbkdf2" "main" { passphrase = "<state-passphrase>" }
method "aes_gcm" "main" { keys = key_provider.pbkdf2.main }
state { method = method.aes_gcm.main }
plan  { method = method.aes_gcm.main }'
```

Later pages add four more lines to this file as the values come into existence: the Proxmox API token, Komodo's API key and secret, and the onboarding key.

Load the file in every new shell before running anything:

```bash
source ~/.config/fleet/env
```

The passphrase outlives the shell. Semaphore needs the same one to read the state after the handover, and a state nobody can decrypt means importing every VM again.

## 5. Set the fleet-wide values {#fleet-values}

Open the private repo and set the values every host shares.

In `hosts.yml`, under `all: vars:`, set the four identity values. See [identity values](../concepts/fleet-private.md#identity).

In `group_vars/all/private.yml`, set these:

```yaml
pve_cloudinit_mode: "minimal"
komodo_stacks_sub_domain_name: "home."
client_account: "<your-login>"
```

| Key | Holds |
| --- | --- |
| `pve_cloudinit_mode` | `minimal`, so a new VM waits for the run and does not provision itself |
| `komodo_stacks_sub_domain_name` | The sub-domain every stack's hostnames sit under, with its trailing dot |
| `client_account` | The name of your own day-to-day login on each host |

Commit and push the private repo.

## 6. Verify {#verify}

From `~/src/ansible`:

```bash
ansible-inventory -i ../fleet-private/hosts.yml --graph
```

The output lists the inventory's groups and hosts, with no error about the file or its variables.

## Notes for WSL {#wsl}

Keep the checkouts, the key, and the environment file on the Linux filesystem, under your home folder. Under `/mnt/c` file modes do not hold, so SSH refuses the private key and ansible ignores the `ansible.cfg` in a folder it sees as world-writable.

WSL2's default networking handles every connection the run makes, since all of them are outbound.

## What's next

Prepare the Proxmox host the VMs are cloned on. See [Proxmox and the template](proxmox-and-template.md).
