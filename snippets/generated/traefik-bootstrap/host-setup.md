The project is `traefik`, so the stack's folders sit under `/opt/docker/volumes/traefik` and `/opt/docker/logs/traefik`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/logs/traefik/traefik` | `101000:101000` | `0755` |
| `/opt/docker/volumes/traefik/traefik-certs` | `101000:101000` | Default |
| `/opt/docker/volumes/traefik/traefik-plugins` | `101000:101000` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `80/tcp` | Anywhere | Traefik HTTP |
| `443/tcp` | Anywhere | Traefik HTTPS |
| `8443/tcp` | Anywhere | Traefik HTTPS (alt) |
