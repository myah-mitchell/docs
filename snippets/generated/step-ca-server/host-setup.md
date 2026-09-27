The project is `step-ca`, so the stack's folders sit under `/opt/docker/volumes/step-ca` and `/opt/docker/logs/step-ca`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/step-ca/step-ca-data` | `101000:101000` | Default |
| `/opt/docker/volumes/step-ca/step-ca-secrets` | `101000:101000` | `0700` |

This stack opens no port on the host's firewall.
