The project is `victoriametrics`, so the stack's folders sit under `/opt/docker/volumes/victoriametrics` and `/opt/docker/logs/victoriametrics`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/victoriametrics/vlagent-data` | `101000:101000` | Default |
| `/opt/docker/volumes/victoriametrics/vmagent-data` | `101000:101000` | Default |
| `/opt/docker/volumes/victoriametrics/vector-data` | `101000:101000` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `5140/tcp` | The internal subnet | Vector syslog |
| `5140/udp` | The internal subnet | Vector syslog |

The host's NixOS configuration creates the folders and opens the ports when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
