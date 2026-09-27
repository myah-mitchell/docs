For traefik-server:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/traefik /opt/docker/volumes/traefik
sudo install -d -o 101000 -g 101000 -m 0755 /opt/docker/logs/traefik/traefik
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/traefik/traefik-certs
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/traefik/traefik-plugins
```

`<internal-subnet>` is the inventory's `docker_stacks_internal_subnet`, for example `192.0.2.0/24`.

```bash
sudo ufw allow 80/tcp comment 'Traefik HTTP'
sudo ufw allow 443/tcp comment 'Traefik HTTPS'
sudo ufw allow 8443/tcp comment 'Traefik HTTPS (alt)'
sudo ufw allow from <internal-subnet> to any port 6379 proto tcp comment 'traefik-kop Redis'
```
