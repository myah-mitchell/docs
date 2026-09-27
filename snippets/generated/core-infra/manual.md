For core-infra:

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

`<internal-subnet>` is the inventory's `docker_stacks_internal_subnet`, for example `192.0.2.0/24`.

```bash
sudo ufw allow from <internal-subnet> to any port 8025 proto tcp comment 'Mailrise SMTP'
sudo ufw allow from <internal-subnet> to any port 25 proto tcp comment 'Postfix SMTP'
```
