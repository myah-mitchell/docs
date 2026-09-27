For stalwart-server:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/mail /opt/docker/volumes/mail
sudo install -d -o 102000 -g 102000 /opt/docker/volumes/mail/stalwart-config
sudo install -d -o 102000 -g 102000 /opt/docker/volumes/mail/stalwart-data
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/settings
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/admin
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/admin-state
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/telemetry
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `25/tcp` | Anywhere |
| `465/tcp` | Anywhere |
| `587/tcp` | Anywhere |
| `993/tcp` | Anywhere |
