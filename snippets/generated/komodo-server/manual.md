For komodo-server:

A host deployed with the stack in its file has these folders and seed files already. The commands make them on a host whose file does not list the stack.

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
  https://raw.githubusercontent.com/myah-mitchell/fleet-stacks/main/containers/komodo/config/core.config.toml.example
sudo chown 101000:101000 /opt/docker/volumes/komodo/komodo-secrets/core.config.toml
sudo chmod 0600 /opt/docker/volumes/komodo/komodo-secrets/core.config.toml
```

No command opens the stack's ports, because the firewall changes only through the host's configuration. The ports below are open once the host's file, `nixos/hosts/<host>.json`, holds them: `nixos-sync.yml` writes that file in the private repo, and a deploy of the host applies it. See [Host layout](../concepts/host-layout.md#firewall).

| Port | Allowed from |
| --- | --- |
| `9120/tcp` | Anywhere |
