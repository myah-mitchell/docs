For system-agent:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/system /opt/docker/volumes/system
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vmagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vlagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vector-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/system/dockns-data
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `5140/tcp` | The internal subnet |
| `5140/udp` | The internal subnet |
| `7007/tcp` | The internal subnet |
