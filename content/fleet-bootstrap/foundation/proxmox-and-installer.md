# Proxmox and the installer ISO

Every VM in the fleet is created blank and boots one [installer ISO](../../tools/glossary.md#installer-iso), which waits for the run to install NixOS over SSH. This page puts that ISO on a [Proxmox](../../tools/glossary.md#proxmox) host, and creates the API token [OpenTofu](../../tools/opentofu/index.md) creates the VMs with.

At the end the Proxmox host lists the ISO in its storage, has a deploy account the run can log in as, and the shell holds a token that can create VMs. The work is commands in the shell, edits to two files in the private repo, and a few commands as root on the Proxmox host. The slow part is step 3, which builds an ISO of about 1.4 GiB and copies it to the host.

Installing and hardening Proxmox itself is outside these pages. The fleet-ansible repo's pve role does more than this page uses, and its README covers a full run against a Proxmox host.

Status: written, not yet run.

## Prerequisites

- Proxmox VE is installed, on ZFS, so the storages `local` and `local-zfs` exist, and `local` accepts ISO images.
- The bridge `vmbr0` is VLAN aware and carries the fleet's VLANs. OpenTofu sets each VM's own.
- You can log in to the Proxmox host as root over SSH, with root's password.
- The shell is set up to the end of [The control shell](control-shell.md), with the tools open and `~/.config/fleet/env` loaded.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<token-secret>` | The secret Proxmox prints when the token is created in [step 4](#token) |
| `<vh01-ssh-host-key>` | The Proxmox host's SSH host key, from [step 1](#describe) |

## 1. Describe the Proxmox host {#describe}

In the private repo's `hosts.yml`, the [inventory](../../tools/glossary.md#inventory), give the host an entry in the `pve_host` group:

```yaml
pve_host:
  hosts:
    vh01:
      ansible_host: 172.16.0.11
      serverHostname: "vh01"
      pve_ssh_host_key: "<vh01-ssh-host-key>"
  vars:
    PVE: true
```

`pve_ssh_host_key` is the host's own SSH [host key](../../tools/glossary.md#host-key), the key a machine proves its identity with when you connect to it. Read it at the host's console, or in the Proxmox web UI under *vh01 > Shell*, not over SSH, and put **the whole line** in place of `<vh01-ssh-host-key>`:

```bash
cat /etc/ssh/ssh_host_ed25519_key.pub
```

Every install logs in to the host to read the new VM's installer key, and accepts no other key from it. A key read over SSH would be taken from the same connection it is meant to check, which is why it is read at the console.

In `opentofu/prod.tfvars`, the [tfvars](../../tools/glossary.md#tfvars) file, list the same host under `servers`. See [the Proxmox servers](../concepts/fleet-private.md#servers) for each key, and for a cluster.

```hcl
servers = {
  vh01 = {
    endpoint     = "https://172.16.0.11:8006/"
    insecure     = true
    default_node = "vh01"
  }
}
```

Log in to the host one time from the shell, accept its host key when it matches the line you just read, and log out:

```bash
ssh root@172.16.0.11
```

Ansible refuses a password login to a host whose key it has not seen, and step 3 logs in with a password.

## 2. Write the fleet's file {#fleet-file}

Add km01 and the `vars` of the `docker_host` group to `hosts.yml`. See [Komodo (km01)](../hosts/km01-komodo.md#describe) for both. Leave that page's entry in `opentofu/prod.tfvars` for the first run, which sends you to the same step.

km01 goes into the inventory here, ahead of its build, because of how the fleet's file is made. The installer accepts the SSH keys in `nixos/fleet.json`, a file the playbook `nixos-sync.yml` writes from the NixOS hosts in the inventory. While the inventory has no NixOS host, the playbook writes nothing. See [the generated files](../concepts/fleet-private.md#generated).

From `~/src/fleet-ansible`, write the file and commit it:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
git -C ../fleet-private add hosts.yml opentofu/ nixos/
git -C ../fleet-private commit -m "Describe vh01 and write the fleet's file"
git -C ../fleet-private push
```

The recap shows `failed=0` for km01. The commit holds two new files.

| File | Holds |
| --- | --- |
| `nixos/fleet.json` | The values every NixOS host shares, the two lists of SSH keys among them |
| `nixos/hosts/km01.json` | km01 as far as it is described. The first run writes it again |

The commit matters. The ISO is built from the files git tracks in the private repo, so a `fleet.json` that is not committed leaves the build with nothing to read.

## 3. Build the ISO and copy it to Proxmox {#installer-iso}

Build and copy the ISO, and create the deploy account on the Proxmox host, from `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml provision.yml \
  -e target=pve_host --tags pve-installer-iso,users -u root --ask-pass
```

Enter **root's password** when asked. The recap shows `failed=0` for each Proxmox host.

`provision.yml` is the fleet-ansible playbook that configures Proxmox hosts. The two tags limit it to the ISO and the accounts. This is the one run that logs in as root with a password, since the deploy account does not exist until it finishes.

| The run | Where |
| --- | --- |
| Builds the ISO from the fleet-nixos flake and `nixos/fleet.json` in the private repo | The shell, one time for the whole run |
| Copies it to `/var/lib/vz/template/iso/fleet-nixos-installer.iso` | Every Proxmox host in the inventory |
| Creates the deploy account `ansible`, with the keys in `ansible_ssh_public_keys` and sudo without a password, and the admin and client accounts | Every Proxmox host |
| Removes the package `nano` and packages nothing depends on | Every Proxmox host, as every run of `provision.yml` does at its end |

The ISO is about 1.4 GiB. The first build downloads what it is made of, and the copy takes as long as the link to the host allows. A later run builds nothing when the flake and the keys are unchanged.

<details>
<summary>Background: why one run builds the ISO and creates the account</summary>

The ISO holds no secret. It carries public SSH keys and nothing a stranger could use, so the copy on the Proxmox host needs no protection.

The cost of that is a host key the run cannot know in advance. The installer's sshd makes a new host key at every boot, so the run has no stored key to check a new VM against. `install-host` gets the key another way: it logs in to the Proxmox host and reads the key from inside the VM, through the VM's [guest agent](../../tools/glossary.md#guest-agent).

That login needs an account on the Proxmox host, which is the deploy account `ansible`. The ISO and the account are two halves of one arrangement, so one run makes both. See [what first boot does](../concepts/how-a-host-is-built.md#first-boot).

</details>

On the Proxmox host, check that the storage lists it:

```bash
pvesm list local --content iso
```

The output has a line for `local:iso/fleet-nixos-installer.iso`, which is the name OpenTofu puts in each VM's CD-ROM drive.

Run this step again after any change to `ansible_ssh_public_keys` or `admin_ssh_public_keys`, once `nixos-sync.yml` has written the change and it is committed. The ISO carries the keys as they were on the day it was built. See [the installer](../concepts/nixos-flake.md#installer) for what else is on it.

## 4. Create the API token {#token}

On the Proxmox host, as root, create a role, a user, and a token that can manage VMs and nothing else. An API token is a credential a program uses in place of a person's password, and OpenTofu sends it with every call to the Proxmox API.

```bash
pveum role add TofuVM --privs "Datastore.AllocateSpace Datastore.Audit SDN.Use Sys.Audit VM.Allocate VM.Audit VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.GuestAgent.Audit VM.Migrate VM.PowerMgmt"
pveum user add tofu@pve
pveum user token add tofu@pve tf --privsep 1
```

The last command prints the token's secret one time. Copy **the secret** now.

Grant the role to the user and to the token, on the four paths OpenTofu touches:

```bash
for path in /vms /storage/local-zfs /storage/local /sdn/zones/localnetwork; do
  pveum acl modify "$path" --users tofu@pve --roles TofuVM
  pveum acl modify "$path" --tokens 'tofu@pve!tf' --roles TofuVM
done
```

| Path | For |
| --- | --- |
| `/vms` | The VMs |
| `/storage/local-zfs` | The datastore the disks are created on |
| `/storage/local` | The storage that holds the installer ISO |
| `/sdn/zones/localnetwork` | The bridge |

A token with separated privileges can do only what both it and its user are granted, which is why each path is granted twice.

<details>
<summary>Background: why the token has these privileges</summary>

The token sits in the environment of every run, in the shell now and in Semaphore later. It is built to be worth as little as possible to someone who takes it, so it is not root's and it is not an administrator's.

A role in Proxmox is a named list of privileges, and a grant gives a role on one path. The role here lists what creating a blank VM takes.

| Privileges | Let OpenTofu |
| --- | --- |
| VM.Allocate, VM.Audit | Create a VM and read it back |
| The VM.Config group | Set its CPU, memory, disks, network, CD-ROM drive, cloud-init drive, and options |
| VM.PowerMgmt | Start it |
| VM.GuestAgent.Audit | Read the address the guest agent reports |
| VM.Migrate | Move a VM that a plan puts on another node |
| Datastore.AllocateSpace, Datastore.Audit | Create the disks, and see the storage that holds the ISO |
| SDN.Use | Attach the VM to the bridge |
| Sys.Audit | Read the node's status |

Nothing in the list changes the Proxmox host itself, its users, or its permissions, and the four paths leave out everything that is not a VM, one of the two storages, or the bridge. The token can still act on every VM under `/vms`, including one the fleet did not create. The fleet-opentofu repo's README describes a tighter setup that uses a pool.

</details>

Each standalone host and each cluster needs a user, role, and token of its own.

## 5. Give the token to the shell {#token-env}

Add one line to `~/.config/fleet/env`, with the secret from step 4 in place of `<token-secret>`:

```bash
export TF_VAR_server_api_tokens='{"vh01": "tofu@pve!tf=<token-secret>"}'
```

The key is the server's name under `servers` in the tfvars file. With more than one server, the object has one entry for each.

Load the file again with `source ~/.config/fleet/env`.

## What's next

Create the first VM. See [The first run](first-run.md).

## Not yet confirmed {#unconfirmed}

- The whole page. No step on it has run against a Proxmox host.
- The run in [step 3](#installer-iso) with a password login, and the time the build and the copy take. The flake evaluates the ISO from a private repo in the state step 2 leaves it in, and the ISO has been built at 1.4 GiB from the flake's own example.
- What `pvesm list` prints for the ISO.
- The `users` tag on a Proxmox host that has only root, and `sudo -n qm` working for the account it creates.
- The privileges in [step 4](#token) for a VM that is created blank, and `Datastore.Audit` on `local` being enough to put the ISO in a VM's drive.
