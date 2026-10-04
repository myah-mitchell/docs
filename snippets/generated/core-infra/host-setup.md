The project is `core`, so the stack's folders sit under `/opt/docker/volumes/core` and `/opt/docker/logs/core`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/core/ntfy-data` | `101000:101000` | Default |
| `/opt/docker/volumes/core/mailrise-secrets` | `101000:101000` | `0700` |
| `/opt/docker/volumes/core/postfix-data` | `100000:100000` | Default |
| `/opt/docker/volumes/core/mailpit-data` | `101000:101000` | Default |
| `/opt/docker/volumes/core/blackbox-exporter-config` | `101000:101000` | Default |
| `/opt/docker/volumes/core/uptime-kuma-data` | `101000:101000` | Default |

These seed files come from fleet-stacks. Each is written only when nothing is at its path, so a copy already on the host is never replaced.

| File | Copied from | Owner | Mode |
| --- | --- | --- | --- |
| `/opt/docker/volumes/core/mailrise-secrets/mailrise.conf` | `containers/mailrise/config/mailrise.conf.example` | `101000:101000` | `0600` |
| `/opt/docker/volumes/core/blackbox-exporter-config/blackbox.yml` | `containers/blackbox-exporter/config/blackbox.yml.example` | `101000:101000` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `8025/tcp` | The internal subnet | Mailrise SMTP |
| `25/tcp` | The internal subnet | Postfix SMTP |

The host's NixOS configuration creates the folders and the seed files, and opens the ports, when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
