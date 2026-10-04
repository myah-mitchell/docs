For traefik-dmz:

A host deployed with the stack in its file has these folders and seed files already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/traefik /opt/docker/volumes/traefik
sudo install -d -o 101000 -g 101000 -m 0755 /opt/docker/logs/traefik/traefik
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/traefik/traefik-certs
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/traefik/traefik-plugins
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/traefik/cloudflared-config
sudo install -d -o 101000 -g 101000 -m 0700 /opt/docker/volumes/traefik/cloudflared-secrets
```

```bash
sudo test -e /opt/docker/volumes/traefik/cloudflared-config/config.yml || sudo curl -fsSL \
  -o /opt/docker/volumes/traefik/cloudflared-config/config.yml \
  https://raw.githubusercontent.com/myah-mitchell/fleet-stacks/main/containers/cloudflared/config/config.yml.example
sudo chown 101000:101000 /opt/docker/volumes/traefik/cloudflared-config/config.yml
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `80/tcp` | Anywhere |
| `443/tcp` | Anywhere |
| `8443/tcp` | Anywhere |
