### Create the VM by hand

The run's first stage creates the VM through OpenTofu, from the host's entry in `opentofu/prod.tfvars`. By hand, on the Proxmox host, with the values from that same entry:

```bash
qm create <vmid> --name <host> --ostype l26 \
  --cpu x86-64-v2-AES --cores <cores> --numa 1 \
  --memory <memory> --balloon 0 \
  --scsihw virtio-scsi-single \
  --scsi0 <vm-storage>:<os-size>,discard=on,ssd=1,iothread=1 \
  --scsi1 <vm-storage>:<docker-size>,discard=on,ssd=1,iothread=1 \
  --scsi2 <vm-storage>:<persist-size>,discard=on,ssd=1,iothread=1 \
  --ide2 local:iso/fleet-nixos-installer.iso,media=cdrom \
  --ide0 <vm-storage>:cloudinit \
  --ipconfig0 ip=<address>,gw=<gateway> \
  --nameserver <dns-server> \
  --net0 virtio,bridge=vmbr0,tag=<vlan-id> \
  --boot 'order=scsi0;ide2' \
  --serial0 socket --vga serial0 \
  --agent enabled=1 --onboot 1 \
  --tags 'nixos;<tags>'
qm start <vmid>
```

| Placeholder | Value |
| --- | --- |
| `<vmid>` | The entry's `vm_id` |
| `<host>` | The entry's name, which is the host's name in the inventory |
| `<cores>`, `<memory>` | The entry's `cores` and `memory_mb` |
| `<vm-storage>` | The Proxmox storage that holds VM disks, `local-zfs` unless the server's entry sets `datastore_id` |
| `<os-size>`, `<docker-size>` | The entry's `os_disk_gb` and `docker_disk_gb` in GB, `20` and `40` when it sets neither |
| `<persist-size>` | The persist disk's `size_gb` |
| `<address>`, `<gateway>` | The entry's `ipv4_address`, with its prefix length, and `ipv4_gateway` |
| `<dns-server>` | The entry's `dns_servers`, separated by spaces inside one pair of quotes when there are several |
| `<vlan-id>` | The entry's `vlan_id` |
| `<tags>` | The entry's `tags`, separated by semicolons |

An entry with no `dns_servers` takes no `--nameserver` option, and one with no `vlan_id` takes no `,tag=` part.

The three disks are blank. The VM finds nothing to boot on `scsi0`, so it boots the installer ISO on `ide2`, and the installer takes its address from the cloud-init drive on `ide0`.

The ISO has to be on the Proxmox host first. See [The installer ISO](../foundation/proxmox-and-installer.md#installer-iso).

Create all three disks before the first start. The install partitions `scsi0` and `scsi1` and formats `scsi2`, and it stops when one is missing.

A VM made this way is not in OpenTofu's state, and it does not carry the `tofu` tag that marks the VMs OpenTofu manages. Leave its entry out of `opentofu/prod.tfvars`, or a later run tries to create a second VM under the same name and address.
