### Create the VM by hand

The run's first stage creates the VM through OpenTofu, from the host's entry in `opentofu/prod.tfvars`. By hand, on the Proxmox host, with the values from that same entry:

```bash
qm clone <template-vmid> <vmid> --name <host> --full
qm set <vmid> --cores <cores> --memory <memory>
qm set <vmid> --ipconfig0 ip=<ip>/24,gw=<gateway-ip>
qm set <vmid> --scsi2 <vm-storage>:<data-size>,discard=on,ssd=1,iothread=1
qm start <vmid>
```

| Placeholder | Value |
| --- | --- |
| `<template-vmid>` | The template's VMID, `template_vm_id` under `servers`. Ubuntu 26.04 gives `2604001` |
| `<vmid>` | The entry's `vm_id` |
| `<cores>`, `<memory>` | The entry's `cores` and `memory_mb` |
| `<ip>`, `<gateway-ip>` | The entry's `ipv4_address` and `ipv4_gateway` |
| `<vm-storage>` | The Proxmox storage that holds VM disks, `local-zfs` with the pve role's defaults |
| `<data-size>` | The persist disk's `size_gb` |

Add the `--scsi2` disk before the first start. It becomes `/srv/persist`, and the docker role stops when it cannot find it.

The template carries the internal VLAN's tag. For a host on another VLAN, set the tag as well, with the network device's other settings kept as `qm config <vmid>` shows them.

A VM made this way is not in OpenTofu's state. Leave its entry out of `opentofu/prod.tfvars`, or a later run tries to create a second VM under the same name and address.
