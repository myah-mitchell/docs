# The private repo

Everything that describes your fleet, as opposed to anyone's, lives in one private git repo. These pages call it fleet-private. This page explains what each file in it holds and how to describe a host, for anyone about to add or change one.

The ansible, docker-stacks, and opentofu repos are public and hold no address, key, or name of yours. The run reads the private repo next to them, so nothing is copied between the two.

## The four kinds of file {#files}

```text
fleet-private/
  hosts.yml
  group_vars/all/private.yml
  opentofu/prod.tfvars
  komodo/stacks/<host>.toml
```

| File | Holds | Written by |
| --- | --- | --- |
| `hosts.yml` | What each host is: its address, its roles, and the stacks it runs | You |
| `group_vars/all/private.yml` | Values every host shares: SSH public keys, Core's address and public key, the sub-domain | You |
| `opentofu/prod.tfvars` | Each host's VM: the Proxmox server, size, disks, VLAN, and address | You |
| `komodo/stacks/<host>.toml` | Each host's Komodo Stacks | `komodo-sync.yml`, from the first file and docker-stacks |

The host's name links them. It is the key in `hosts.yml`, the key in the tfvars file in lower case, and the name of the generated file.

Start the repo from `private-repo.example/` in the ansible repo, which has every file with example values and a comment on each key.

> [!WARNING]
> No secret goes in this repo. API tokens, the onboarding key, the state passphrase, and `server_password` live in the control node's environment file or in Semaphore's secrets. What this repo holds is private, not secret.

## Describing a host {#describe}

A host is two entries. The first is in `hosts.yml`:

```yaml
docker_host:
  hosts:
    id01:
      ansible_host: 192.0.2.13
      serverHostname: "id01"
      docker_stacks:
        - system-agent
        - traefik-agent
        - authentik-server
```

| Key | Holds |
| --- | --- |
| `ansible_host` | The address ansible connects to |
| `serverHostname` | The hostname the host is given, and its Server name in Komodo in lower case |
| `docker_stacks` | The stacks the host runs once the fleet is finished, by their folder name in docker-stacks |

The `docker_host` group's own `vars` turn on the roles every Docker VM gets, and set `docker_stacks_internal_subnet`, the subnet a firewall rule is scoped to when a stack opens a port to the internal network only.

The second entry is in `opentofu/prod.tfvars`:

```hcl
vms = {
  id01 = {
    server       = "vh01"
    vm_id        = 7013
    cores        = 4
    memory_mb    = 8192
    vlan_id      = 7
    ipv4_address = "192.0.2.13/24"
    ipv4_gateway = "192.0.2.1"
    dns_servers  = ["192.0.2.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 20 }
    }
  }
}
```

| Key | Holds |
| --- | --- |
| `server` | Which entry under `servers` the VM lives on |
| `vm_id` | The VMID. These pages use the VLAN followed by the address's last part in three digits. It applies only when the VM is created |
| `cores`, `memory_mb` | The VM's size. Each host page gives the numbers and what drives them |
| `vlan_id` | `7` for the internal VLAN and `8` for the DMZ in these pages |
| `ipv4_address` | The address with its prefix. It must match `ansible_host`, and the run stops when the two differ |
| `extra_disks` | The persistent disk, always on `scsi2`. See [Host layout](host-layout.md#disks) |

Add `node_name` to pin a VM to one node of a cluster. A pinned VM that is moved in Proxmox is migrated back by the next run that includes it. Without the key, a VM is created on the template node and then left wherever you or HA move it.

`envs/prod/terraform.tfvars.example` and `variables.tf` in the opentofu repo list every key.

## The Proxmox servers {#servers}

The tfvars file opens with the servers the VMs live on:

```hcl
servers = {
  vh01 = {
    endpoint       = "https://203.0.113.11:8006/"
    insecure       = true
    template_node  = "vh01"
    template_vm_id = 2604001
  }
}
```

A standalone Proxmox host is a server of its own. A cluster is one server, reached through any node, with `template_node` naming the node that holds the cloud-init template. `insecure` skips the certificate check while the API certificate is self-signed.

## Identity values {#identity}

`provision.yml` names things after four values. Set them in `hosts.yml` under `all: vars:`, so every control node reads the same ones:

```yaml
all:
  vars:
    short_name: "MYMI"
    abbr_name: "mm"
    location_abbr: "h"
    domain_name: "myah-mitchell.com"
```

A group or a host can set its own. A value passed with `-e`, or held in Semaphore's *Extra Variables*, beats all of them, so keep these four out of there.

## Bootstrap mode {#bootstrap}

`docker_stacks_bootstrap: true` on a host, or in a group's `vars`, puts it in bootstrap mode. The `docker_stacks` list does not change. See [Bootstrap mode](bootstrap-mode.md).

## Stack values {#stack-values}

The run fills in four keys of every stack's *Environment* wherever the stack's `komodo.env` has them.

| Key | Value |
| --- | --- |
| `SERVER_NAME` | The host's `serverHostname`, in lower case |
| `SUB_DOMAIN_NAME` | `komodo_stacks_sub_domain_name` from `private.yml`, with its trailing dot, such as `home.` |
| `DOMAIN_NAME` | `domain_name` |
| `TRAEFIK_AUTH_CHAIN` | `chain-no-auth@file` in bootstrap mode, blank otherwise |

Set any other key with `komodo_stack_env`, keyed by the stack's folder name:

```yaml
    ci01:
      komodo_stack_env:
        core-infra:
          POSTFIX_RELAYHOST: "[smtp.myah-mitchell.com]:587"
          POSTFIX_RELAYHOST_USERNAME: "relay@myah-mitchell.com"
```

- Every key must already have a line in that stack's `komodo.env`. A misspelt key stops the run, and is not silently dropped.
- A value can be a literal, a blank, or a reference to a Variable or Secret of your own, such as `"[[DOCKNS_WAN_IP_DMZ]]"`.
- A secret never goes here. Create a Komodo Secret and reference it.
- A host's `komodo_stack_env` replaces a group's. Ansible does not merge the two, so a host that sets its own lists every stack and key it needs.

## After a change {#after-a-change}

Generate the Komodo files again and commit them after any of these:

- A host's `docker_stacks`, `docker_stacks_bootstrap`, or `komodo_stack_env` changes.
- A host is added, or stops running stacks.
- A stack's `komodo.env` changes in docker-stacks.

--8<-- "generate-komodo-files.md"

The generated files are never edited by hand. The playbook connects to no host, so it is safe to run at any time.
