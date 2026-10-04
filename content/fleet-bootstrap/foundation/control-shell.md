# The control shell

This page turns a shell on your own machine into the fleet's first control node. It gets the tools, the checkouts, the fleet's SSH key, the keys that decrypt the fleet's secrets, and the first contents of the private repo. Any Linux shell that can reach the Proxmox hosts and the fleet's VLANs works, WSL included.

Status: written, not yet run.

## Prerequisites

- A Linux shell with sudo, on a machine that can open connections to the Proxmox API on port 8006, to the Proxmox hosts and the fleet's VMs on port 22, and to km01 on port 9120. Nothing has to connect back to it.
- A GitHub account that can create a private repo.
- A password manager, or another encrypted store.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<fleet-key>` | The public half of the fleet's SSH key, from [step 3](#ssh-key) |
| `<your-key>` | Your own SSH public key, the one you log in to hosts with |
| `<your-login>` | The username you want for your own login on each host |
| `<admin-public-key>` | The public key `age-keygen` prints for the admin key in [step 4](#age-keys) |
| `<deploy-public-key>` | The public key it prints for the deploy key |
| `<state-passphrase>` | The passphrase OpenTofu encrypts its state with, generated in [step 5](#environment) |

## 1. Get the tools {#tools}

Every tool comes from nix, so nix is the one thing to install. Use the installer from [nixos.org](https://nixos.org/download/):

```bash
sh <(curl --proto '=https' --tlsv1.2 -L https://nixos.org/nix/install) --daemon
```

Turn on the flake commands. Add this line to `~/.config/nix/nix.conf`, and create the file if it does not exist:

```ini
experimental-features = nix-command flakes
```

Open a new terminal, then open a shell that has the tools:

```bash
nix shell nixpkgs#git nixpkgs#ansible nixpkgs#opentofu nixpkgs#sops nixpkgs#age \
  nixpkgs#sshpass nixpkgs#mkpasswd
```

The first time, nix downloads the tools. After that the command returns at once. Nothing is installed, so the tools are gone when the shell is closed.

Run every command on these pages inside that shell. In a new terminal, open it again first.

| Tool | Used for |
| --- | --- |
| ansible | The run, and the two playbooks that write the generated files |
| OpenTofu | Creating the VMs |
| sops and age | Encrypting and decrypting the fleet's secrets |
| sshpass | The one login to the Proxmox host that uses a password |
| mkpasswd | Hashing the admin password |

The playbooks need ansible-core 2.15 or later, and the fleet-opentofu repo needs OpenTofu 1.9.0 or later. Check with `ansible --version` and `tofu version`.

## 2. Check out the repos {#checkouts}

Three checkouts sit next to each other, so every command on these pages can reach the inventory at `../fleet-private/hosts.yml` and the flake at `../fleet-nixos`:

```bash
mkdir -p ~/src
git clone https://github.com/myah-mitchell/fleet-ansible ~/src/fleet-ansible
git clone https://github.com/myah-mitchell/fleet-nixos ~/src/fleet-nixos
cd ~/src/fleet-ansible
ansible-galaxy install -r requirements.yml
```

If the private repo exists already, clone it to `~/src/fleet-private` and go to step 3.

To start one, create an empty private repo named `fleet-private` on GitHub, then fill it from the skeleton:

```bash
git clone git@github.com:myah-mitchell/fleet-private.git ~/src/fleet-private
cp -r ~/src/fleet-ansible/private-repo.example/. ~/src/fleet-private/
cd ~/src/fleet-private
rm -r README.md nixos group_vars/all/secrets.sops.yaml.example
```

The files removed are the skeleton's own examples. See [The private repo](../concepts/fleet-private.md) for what each of the others holds.

The run keeps checkouts of its own, and updates them at the start of every run. They need no attention.

| Repo | Checked out by | Where |
| --- | --- | --- |
| fleet-ansible | You | `~/src/fleet-ansible` |
| fleet-private | You | `~/src/fleet-private` |
| fleet-nixos | You, for the commands you run yourself | `~/src/fleet-nixos` |
| fleet-nixos | The run | `/tmp/ansible-fleet-nixos-checkout` |
| fleet-opentofu | The run | `/tmp/ansible-fleet-opentofu-checkout` |
| fleet-stacks | The run, and the two sync playbooks | `/tmp/ansible-fleet-stacks-checkout` |

Run every `ansible-playbook` command on these pages from `~/src/fleet-ansible`.

## 3. Create the fleet's SSH key {#ssh-key}

Generate the key the run reaches every host with:

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

| List | Who gets it |
| --- | --- |
| `ansible_ssh_public_keys` | The `ansible` account on every host, which has passwordless sudo and no password |
| `admin_ssh_public_keys` | The admin account and your own login, for your sessions |
| Both | Root on the installer, which is how a new VM is reached before NixOS is on it |

The flake's commands call `ssh` themselves and pass it no key, so SSH has to find the fleet's key on its own. Add this to `~/.ssh/config`:

```text
Match user ansible,root host 192.0.2.*,198.51.100.*
    IdentityFile ~/.ssh/fleet-ansible
    IdentitiesOnly yes
```

The two patterns are the fleet's networks. A login as `ansible` or as root to an address in them uses the fleet's key, and every other login is left as it was.

The private half moves into Semaphore's Key Store later, and the handover deletes it from the shell.

> [!WARNING]
> This key is passwordless root on every host in the fleet. It never goes in a repo, a chat, or a backup that is not encrypted.

## 4. Create the age keys {#age-keys}

The fleet's secrets are encrypted with sops, to age keys. Two keys are made by hand. See [the keys](../concepts/secrets-with-sops.md#keys) for what each one can read, and for the third kind, which each host has for itself.

```bash
install -d -m 0700 ~/.config/fleet
age-keygen -o ~/.config/fleet/admin.key
age-keygen -o ~/.config/fleet/deploy.key
```

Each command prints the key's public half, a line that starts with `Public key: age1`. Note both. `age-keygen -y` with a key file prints its public half again.

The admin key is yours. Store the contents of `admin.key` in your password manager, then delete the file:

```bash
rm ~/.config/fleet/admin.key
```

The deploy key stays in the shell, where the run reads it. Store a copy of `deploy.key` in your password manager as well. It moves into Semaphore later.

> [!WARNING]
> Either key decrypts every secret in the private repo. Neither file ever goes into a repo.

## 5. Write the environment file {#environment}

The run reads its secrets from the environment. Keep them in one private file, so they are never typed on a command line:

```bash
install -m 0600 /dev/null ~/.config/fleet/env
```

Generate the state passphrase, and store a copy in your password manager:

```bash
tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 48; echo
```

Open `~/.config/fleet/env` in an editor and add:

```bash
export SOPS_AGE_KEY_FILE="$HOME/.config/fleet/deploy.key"
export TF_ENCRYPTION='key_provider "pbkdf2" "main" { passphrase = "<state-passphrase>" }
method "aes_gcm" "main" { keys = key_provider.pbkdf2.main }
state { method = method.aes_gcm.main }
plan  { method = method.aes_gcm.main }'
```

Later pages add three more lines to this file as the values come into existence: the Proxmox API token, and Komodo's API key and secret.

Load the file in every new shell before running anything:

```bash
source ~/.config/fleet/env
```

The passphrase outlives the shell. Semaphore needs the same one to read the state after the handover, and a state nobody can decrypt means importing every VM again.

## 6. Set the fleet-wide values {#fleet-values}

The skeleton's inventory and its VMs are examples. Start both files empty, so that the fleet holds only the hosts these pages describe.

Replace the contents of `hosts.yml` in the private repo with the four identity values. See [identity values](../concepts/fleet-private.md#identity) for what each one names.

```yaml
all:
  vars:
    short_name: "MYMI"
    abbr_name: "mm"
    location_abbr: "h"
    domain_name: "myah-mitchell.com"
```

Replace the contents of `opentofu/prod.tfvars` with two empty maps:

```hcl
servers = {}

vms = {}
```

In `group_vars/all/private.yml`, set these two and leave the rest as the skeleton has them:

```yaml
komodo_stacks_sub_domain_name: "home."
client_account: "<your-login>"
```

| Key | Holds |
| --- | --- |
| `komodo_stacks_sub_domain_name` | The sub-domain every stack's hostnames sit under, with its trailing dot |
| `client_account` | The name of your own day-to-day login on each host |

## 7. Write the secrets {#secrets}

Open `.sops.yaml` in the private repo. Replace the placeholder after `&admin` with `<admin-public-key>` and the one after `&deploy` with `<deploy-public-key>`. Remove the example host: the line `&ex01`, the rule for `secrets/hosts/ex01.yaml`, and `*ex01` in the rule for `secrets/fleet.yaml`. The file then reads:

```yaml
keys:
  - &admin <admin-public-key>
  - &deploy <deploy-public-key>

creation_rules:
  - path_regex: ^group_vars/all/secrets\.sops\.yaml$
    key_groups:
      - age: [*admin, *deploy]

  - path_regex: ^secrets/fleet\.yaml$
    key_groups:
      - age: [*admin, *deploy]

  - path_regex: ^secrets/host-keys/[^/]+\.yaml$
    key_groups:
      - age: [*admin, *deploy]
```

Hosts are never added to this file by hand. The command that makes a host's keys adds the host. See [Host keys](../concepts/secrets-with-sops.md#host-keys).

Hash the password of the admin account. The command asks for the password and prints the hash, which starts with `$y$`:

```bash
mkpasswd -m yescrypt
```

Write the two secrets files from the private repo's folder, where sops finds `.sops.yaml`. Each command opens the editor named in `EDITOR` on an example, and encrypts what you save:

```bash
cd ~/src/fleet-private
mkdir -p secrets
sops group_vars/all/secrets.sops.yaml
sops secrets/fleet.yaml
```

Replace the example in each with these keys and nothing else.

| File | Key | Value |
| --- | --- | --- |
| `group_vars/all/secrets.sops.yaml` | `server_password` | The password ansible sets for root and the admin account on a Proxmox host. Empty leaves every password as it is |
| `secrets/fleet.yaml` | `server-password-hash` | The hash `mkpasswd` printed |
| `secrets/fleet.yaml` | `komodo-onboarding-key` | The text `placeholder` |

```yaml
server-password-hash: "$y$..."
komodo-onboarding-key: "placeholder"
```

The onboarding key does not exist until Komodo runs, and a host's configuration cannot be built without the entry. [Setting up Komodo](komodo-setup.md#onboarding-key) replaces the placeholder with the real key.

Commit and push the private repo:

```bash
git add -A
git commit -m "Set the fleet's values and its first secrets"
git push
```

From here on, every playbook run against this inventory decrypts `secrets.sops.yaml`, so it needs the environment file loaded.

> [!WARNING]
> Never commit a secrets file that sops has not encrypted. In an encrypted file every value starts with `ENC[`.

## 8. Verify {#verify}

From `~/src/fleet-ansible`, with the environment file loaded:

```bash
ansible-inventory -i ../fleet-private/hosts.yml --graph
sops decrypt --extract '["komodo-onboarding-key"]' ../fleet-private/secrets/fleet.yaml
nix run ../fleet-nixos#host-state -- 192.0.2.11
```

| Command | Prints |
| --- | --- |
| `ansible-inventory` | The inventory's groups, with no error about the file or its variables |
| `sops` | `placeholder`, which shows that the deploy key decrypts the file |
| `host-state` | `unreachable` after about five seconds, since km01 does not exist yet |

The first `nix run` of a command builds it, which takes a minute or two.

## Notes for WSL {#wsl}

Keep the checkouts, the keys, and the environment file on the Linux filesystem, under your home folder. Under `/mnt/c` file modes do not hold, so SSH refuses the private key and ansible ignores the `ansible.cfg` in a folder it sees as world-writable.

The nix installer's `--daemon` mode needs systemd, which a current WSL2 distribution runs. Without systemd, install with `--no-daemon`.

WSL2's default networking handles every connection the run makes, since all of them are outbound.

## What's next

Put the installer ISO on the Proxmox host, and create the API token the run reaches Proxmox with. See [Proxmox and the installer ISO](proxmox-and-installer.md).

## Not yet confirmed {#unconfirmed}

- The nix installer on a machine that has no nix. The commands after it were run with nix 2.34.7, which gave ansible-core 2.21.3, OpenTofu 1.12.6, sops 3.13.3, and age 1.3.2.
- The `Match` block against a real host. `ssh -G` shows that a login as `ansible` or root to an address in the two networks takes the fleet's key.
- Installing nix under WSL, with and without systemd.
