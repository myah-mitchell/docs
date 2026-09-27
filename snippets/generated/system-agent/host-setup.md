The project is `system`, so the stack's folders sit under `/opt/docker/volumes/system` and `/opt/docker/logs/system`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/system/vmagent-data` | `101000:101000` | Default |
| `/opt/docker/volumes/system/vlagent-data` | `101000:101000` | Default |
| `/opt/docker/volumes/system/vector-data` | `101000:101000` | Default |
| `/opt/docker/volumes/system/dockns-data` | `100000:100000` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `5140/tcp` | The internal subnet | Vector syslog |
| `5140/udp` | The internal subnet | Vector syslog |
| `7007/tcp` | The internal subnet | Dozzle agent |
