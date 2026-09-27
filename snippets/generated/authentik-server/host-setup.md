The project is `authentik`, so the stack's folders sit under `/opt/docker/volumes/authentik` and `/opt/docker/logs/authentik`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/authentik/authentik-media` | `101000:101000` | Default |
| `/opt/docker/volumes/authentik/authentik-templates` | `101000:101000` | Default |
| `/opt/docker/volumes/authentik/authentik-certs` | `101000:101000` | Default |
| `/opt/docker/volumes/authentik/postgres-data` | `100000:100000` | Default |
| `/opt/docker/volumes/authentik/postgres-backup-data` | `100000:100000` | Default |
| `/opt/docker/volumes/authentik/geoip-data` | `101000:101000` | Default |

This stack opens no port on the host's firewall.

The host's NixOS configuration creates the folders when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
