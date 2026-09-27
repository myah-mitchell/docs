For core-infra:

A host deployed with the stack in its file has these folders and seed files already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/core /opt/docker/volumes/core
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/core/ntfy-data
sudo install -d -o 101000 -g 101000 -m 0700 /opt/docker/volumes/core/mailrise-secrets
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/core/postfix-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/core/mailpit-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/core/blackbox-exporter-config
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/core/uptime-kuma-data
```

```bash
sudo test -e /opt/docker/volumes/core/mailrise-secrets/mailrise.conf || sudo curl -fsSL \
  -o /opt/docker/volumes/core/mailrise-secrets/mailrise.conf \
  https://raw.githubusercontent.com/myah-mitchell/docker-stacks/main/containers/mailrise/config/mailrise.conf.example
sudo chown 101000:101000 /opt/docker/volumes/core/mailrise-secrets/mailrise.conf
sudo chmod 0600 /opt/docker/volumes/core/mailrise-secrets/mailrise.conf
sudo test -e /opt/docker/volumes/core/blackbox-exporter-config/blackbox.yml || sudo curl -fsSL \
  -o /opt/docker/volumes/core/blackbox-exporter-config/blackbox.yml \
  https://raw.githubusercontent.com/myah-mitchell/docker-stacks/main/containers/blackbox-exporter/config/blackbox.yml.example
sudo chown 101000:101000 /opt/docker/volumes/core/blackbox-exporter-config/blackbox.yml
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `8025/tcp` | The internal subnet |
| `25/tcp` | The internal subnet |
