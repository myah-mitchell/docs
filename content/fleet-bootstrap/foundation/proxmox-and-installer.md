# Proxmox and the installer ISO

Every VM in the fleet is created blank and boots one installer ISO, which waits for the run to install NixOS over SSH. This page puts that ISO on a Proxmox host, and creates the API token OpenTofu creates the VMs with.

Installing and hardening Proxmox itself is outside these pages. The ansible repo's pve role does more than this page uses, and its README covers a full run against a Proxmox host.

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

## 1. Describe the Proxmox host {#describe}

In the private repo's `hosts.yml`, give the host an entry in the `pve_host` group:

```yaml
pve_host:
  hosts:
    vh01:
      ansible_host: 203.0.113.11
      serverHostname: "vh01"
  vars:
    PVE: true
```

In `opentofu/prod.tfvars`, list the same host under `servers`. See [the Proxmox servers](../concepts/fleet-private.md#servers) for each key, and for a cluster.

```hcl
servers = {
  vh01 = {
    endpoint     = "https://203.0.113.11:8006/"
    insecure     = true
    default_node = "vh01"
  }
}
```

Log in to the host one time from the shell, accept its host key, and log out:

```bash
ssh root@203.0.113.11
```

Ansible refuses a password login to a host whose key it has not seen, and step 3 logs in with a password.

## 2. Write the fleet's file {#fleet-file}

The installer accepts the SSH keys in `nixos/fleet.json`, a file `nixos-sync.yml` writes from the NixOS hosts in the inventory. While the inventory has no NixOS host, the playbook writes nothing. km01 therefore goes into the inventory here, ahead of its build.

Add km01 and the `vars` of the `docker_host` group to `hosts.yml`. See [Komodo (km01)](../hosts/km01-komodo.md#describe) for both. Leave that page's entry in `opentofu/prod.tfvars` for the first run, which sends you to the same step.

From `~/src/ansible`, write the file and commit it:

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

The ISO has an SSH host key of its own, the same at every boot. `install-host` sends a host its private keys only to a machine that answers with that key. Make it once, from `~/src/ansible`, and commit it:

```bash
nix run ../nixos-fleet#new-installer-key -- --fleet ../fleet-private
git -C ../fleet-private add .sops.yaml secrets/installer.yaml
git -C ../fleet-private commit -m "Add the installer's host key"
git -C ../fleet-private push
```

The command prints `made secrets/installer.yaml`, and adds a rule for the file to `.sops.yaml` the first time. A second run keeps the key and prints `kept the key in secrets/installer.yaml`.

Then build and copy the ISO, from the same folder:

```bash
ansible-playbook -i ../fleet-private/hosts.yml provision.yml \
  -e target=pve_host --tags pve-installer-iso -u root --ask-pass
```

Enter root's password when asked. The recap shows `failed=0` for each Proxmox host.

| The run | Where |
| --- | --- |
| Builds the ISO from the nixos-fleet flake and the private repo, with the installer's host key from `secrets/installer.yaml` | The shell, one time for the whole run |
| Copies it to `/var/lib/vz/template/iso/nixos-fleet-installer.iso` | Every Proxmox host in the inventory |
| Removes the package `nano` and packages nothing depends on | Every Proxmox host, as every run of `provision.yml` does at its end |

The ISO is about 1.4 GiB. The first build downloads what it is made of, and the copy takes as long as the link to the host allows. A later run builds nothing when the flake and the keys are unchanged. The installer's private key ends up in the shell's Nix store, where every account on the machine can read it, and in the ISO.

On the Proxmox host, check that the storage lists it:

```bash
pvesm list local --content iso
```

The output has a line for `local:iso/nixos-fleet-installer.iso`, which is the name OpenTofu puts in each VM's CD-ROM drive.

Run this step again after any change to `ansible_ssh_public_keys` or `admin_ssh_public_keys`, once `nixos-sync.yml` has written the change and it is committed. The ISO carries the keys as they were on the day it was built. See [the installer](../concepts/nixos-flake.md#installer) for what else is on it.

## 4. Create the API token {#token}

On the Proxmox host, as root, create a role, a user, and a token that can manage VMs and nothing else:

```bash
pveum role add TofuVM --privs "Datastore.AllocateSpace Datastore.Audit SDN.Use Sys.Audit VM.Allocate VM.Audit VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.GuestAgent.Audit VM.Migrate VM.PowerMgmt"
pveum user add tofu@pve
pveum user token add tofu@pve tf --privsep 1
```

The last command prints the token's secret one time. Copy it now.

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

Each standalone host and each cluster needs a user, role, and token of its own.

## 5. Give the token to the shell {#token-env}

Add one line to `~/.config/fleet/env`:

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
- The privileges in [step 4](#token) for a VM that is created blank, and `Datastore.Audit` on `local` being enough to put the ISO in a VM's drive.
