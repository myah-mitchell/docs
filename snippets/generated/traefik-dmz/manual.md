For traefik-dmz:

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
  https://raw.githubusercontent.com/myah-mitchell/docker-stacks/main/containers/cloudflared/config/config.yml.example
sudo chown 101000:101000 /opt/docker/volumes/traefik/cloudflared-config/config.yml
```

```bash
sudo ufw allow 80/tcp comment 'Traefik HTTP'
sudo ufw allow 443/tcp comment 'Traefik HTTPS'
sudo ufw allow 8443/tcp comment 'Traefik HTTPS (alt)'
```
