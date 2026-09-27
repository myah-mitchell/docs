The project is `komodo`, so the stack's folders sit under `/opt/docker/volumes/komodo` and `/opt/docker/logs/komodo`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/komodo/ferretdb-data` | `101000:101000` | Default |
| `/opt/docker/volumes/komodo/postgres-data` | `100000:100000` | Default |
| `/opt/docker/volumes/komodo/postgres-backup-data` | `100000:100000` | Default |
| `/opt/docker/volumes/komodo/komodo-keys` | `101000:101000` | Default |
| `/opt/docker/volumes/komodo/komodo-backups` | `101000:101000` | Default |
| `/opt/docker/volumes/komodo/komodo-sync` | `101000:101000` | Default |
| `/opt/docker/volumes/komodo/komodo-cache` | `101000:101000` | Default |
| `/opt/docker/volumes/komodo/komodo-secrets` | `101000:101000` | `0700` |

These files are copied from docker-stacks when they are missing. A copy already on the host is never replaced.

| File | Copied from | Owner | Mode |
| --- | --- | --- | --- |
| `/opt/docker/volumes/komodo/komodo-secrets/core.config.toml` | `containers/komodo/config/core.config.toml.example` | `101000:101000` | `0600` |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `9120/tcp` | Anywhere | Komodo Core |
