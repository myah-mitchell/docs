The project is `technitium`, so the stack's folders sit under `/opt/docker/volumes/technitium` and `/opt/docker/logs/technitium`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/technitium/technitium-data` | `101000:101000` | Default |

This stack opens no port on the host's firewall.
