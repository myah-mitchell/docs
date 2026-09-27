The project is `semaphore`, so the stack's folders sit under `/opt/docker/volumes/semaphore` and `/opt/docker/logs/semaphore`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/semaphore/semaphore-data` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/semaphore-config` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/semaphore-tmp` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/nix-data` | `101001:101001` | Default |
| `/opt/docker/volumes/semaphore/postgres-initdb` | `100000:100000` | `0755` |
| `/opt/docker/volumes/semaphore/postgres-data` | `100000:100000` | Default |
| `/opt/docker/volumes/semaphore/postgres-backup-data` | `100000:100000` | Default |

These seed files come from docker-stacks. Each is written only when nothing is at its path, so a copy already on the host is never replaced.

| File | Copied from | Owner | Mode |
| --- | --- | --- | --- |
| `/opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh` | `containers/semaphore/config/postgres-initdb/10-tofu-state.sh` | `100000:100000` | `0755` |

This stack opens no port on the host's firewall.

The host's NixOS configuration creates the folders and the seed files when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
