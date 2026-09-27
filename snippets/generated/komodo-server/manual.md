For komodo-server:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/komodo /opt/docker/volumes/komodo
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/komodo/ferretdb-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/komodo/postgres-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/komodo/postgres-backup-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/komodo/komodo-keys
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/komodo/komodo-backups
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/komodo/komodo-sync
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/komodo/komodo-cache
sudo install -d -o 101000 -g 101000 -m 0700 /opt/docker/volumes/komodo/komodo-secrets
```

```bash
sudo test -e /opt/docker/volumes/komodo/komodo-secrets/core.config.toml || sudo curl -fsSL \
  -o /opt/docker/volumes/komodo/komodo-secrets/core.config.toml \
  https://raw.githubusercontent.com/myah-mitchell/docker-stacks/main/containers/komodo/config/core.config.toml.example
sudo chown 101000:101000 /opt/docker/volumes/komodo/komodo-secrets/core.config.toml
sudo chmod 0600 /opt/docker/volumes/komodo/komodo-secrets/core.config.toml
```

```bash
sudo ufw allow 9120/tcp comment 'Komodo Core'
```
