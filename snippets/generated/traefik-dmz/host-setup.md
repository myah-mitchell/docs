The project is `traefik`, so the stack's folders sit under `/opt/docker/volumes/traefik` and `/opt/docker/logs/traefik`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/logs/traefik/traefik` | `101000:101000` | `0755` |
| `/opt/docker/volumes/traefik/traefik-certs` | `101000:101000` | Default |
| `/opt/docker/volumes/traefik/traefik-plugins` | `101000:101000` | Default |
| `/opt/docker/volumes/traefik/cloudflared-config` | `101000:101000` | Default |
| `/opt/docker/volumes/traefik/cloudflared-secrets` | `101000:101000` | `0700` |

These seed files come from docker-stacks. Each is written only when nothing is at its path, so a copy already on the host is never replaced.

| File | Copied from | Owner | Mode |
| --- | --- | --- | --- |
| `/opt/docker/volumes/traefik/cloudflared-config/config.yml` | `containers/cloudflared/config/config.yml.example` | `101000:101000` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `80/tcp` | Anywhere | Traefik HTTP |
| `443/tcp` | Anywhere | Traefik HTTPS |
| `8443/tcp` | Anywhere | Traefik HTTPS (alt) |

The host's NixOS configuration creates the folders and the seed files, and opens the ports, when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
