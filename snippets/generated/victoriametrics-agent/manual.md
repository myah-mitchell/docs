For victoriametrics-agent:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/victoriametrics /opt/docker/volumes/victoriametrics
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vlagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vmagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vector-data
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `5140/tcp` | The internal subnet |
| `5140/udp` | The internal subnet |
