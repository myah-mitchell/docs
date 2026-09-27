# Proxmox and the template

Every VM in the fleet is a clone of one cloud-init template. This page puts the template and its first-boot snippet on a Proxmox host, and creates the API token OpenTofu clones with.

Installing and hardening Proxmox itself is outside these pages. The ansible repo's pve role does more than this page uses, and its README covers a full run against a Proxmox host.

Status: written, not yet run. OpenTofu has cloned a template built this way, with a token scoped this way, on one real Proxmox node. The commands on this page have not been followed as written.

## Prerequisites

- Proxmox VE is installed, on ZFS, so the storages `local` and `local-zfs` exist.
- The bridge `vmbr0` is VLAN aware and carries the fleet's VLANs. The template is built on VLAN 7, and OpenTofu sets each VM's own.
- You can log in to the Proxmox host as root over SSH.
- The shell is set up as far as [the control shell](control-shell.md#fleet-values).

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

Nodes of one cluster share a `pve_cluster_name`. The first node of a cluster in this file is the one that builds the template. A standalone host leaves the key unset.

In `opentofu/prod.tfvars`, list the same host under `servers`. See [the Proxmox servers](../concepts/fleet-private.md#servers).

Commit and push the private repo.

## 2. Install the snippet and the template script {#snippet}

From `~/src/ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml provision.yml \
  -e target=pve_host --tags pve-cloudinit -u root --ask-pass
```

Enter root's password when asked, and press Enter at the admin password prompt. The recap shows `failed=0` for each Proxmox host.

The run does three things on the host.

| It writes | Which is |
| --- | --- |
| `/var/lib/vz/snippets/cloudinit-vendor.yml` | What a clone does on first boot. In minimal mode: start the guest agent and create the `ansible` login |
| `/usr/local/bin/create-cloud-init-template.sh` | The script that builds the template |
| A cron entry | A rebuild of the template every Wednesday at 20:00, so clones start from a current image |

Run this step again after any change to `ansible_ssh_public_keys` or `admin_ssh_public_keys`. Both files carry the keys as they were on the day of the run.

## 3. Build the template {#template}

On the Proxmox host, as root, run the script one time. The cron entry handles every later build:

```bash
/usr/local/bin/create-cloud-init-template.sh
```

It downloads the Ubuntu cloud image and builds the template from it. Check the result:

```bash
qm config 2604001 | grep -E '^(name|template|cicustom|scsi1)'
```

The output has four lines: the name `ubuntu-server-2604`, `template: 1`, a `cicustom` line that names `cloudinit-vendor.yml`, and a 40 GB `scsi1` disk.

The VMID and the name follow the Ubuntu version, so 26.04 gives `2604001` and `ubuntu-server-2604`. That VMID is the `template_vm_id` in the tfvars file.

The template has two disks, the root disk and the Docker disk. A VM's persistent disk is added per VM. See [Host layout](../concepts/host-layout.md#disks).

## 4. Create the API token {#token}

On the Proxmox host, as root, create a role, a user, and a token that can manage VMs and nothing else:

```bash
pveum role add TofuVM --privs "Datastore.AllocateSpace Datastore.Audit SDN.Use Sys.Audit VM.Allocate VM.Audit VM.Clone VM.Config.CDROM VM.Config.CPU VM.Config.Cloudinit VM.Config.Disk VM.Config.HWType VM.Config.Memory VM.Config.Network VM.Config.Options VM.GuestAgent.Audit VM.Migrate VM.PowerMgmt"
pveum user add tofu@pve
pveum user token add tofu@pve tf --privsep 1
```

The last command prints the token's secret one time. Copy it now.

Grant the role to the user and to the token, on the three paths OpenTofu touches:

```bash
for path in /vms /storage/local-zfs /sdn/zones/localnetwork; do
  pveum acl modify "$path" --users tofu@pve --roles TofuVM
  pveum acl modify "$path" --tokens 'tofu@pve!tf' --roles TofuVM
done
```

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
