The project is `semaphore`, so the stack's folders sit under `/opt/docker/volumes/semaphore` and `/opt/docker/logs/semaphore`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/semaphore/semaphore-data` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/semaphore-config` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/semaphore-tmp` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/postgres-initdb` | `100000:100000` | `0755` |
| `/opt/docker/volumes/semaphore/postgres-data` | `100000:100000` | Default |
| `/opt/docker/volumes/semaphore/postgres-backup-data` | `100000:100000` | Default |

These files are copied from docker-stacks when they are missing. A copy already on the host is never replaced.

| File | Copied from | Owner | Mode |
| --- | --- | --- | --- |
| `/opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh` | `containers/semaphore/config/postgres-initdb/10-tofu-state.sh` | `100000:100000` | `0755` |

This stack opens no port on the host's firewall.
