The project is `victoriametrics`, so the stack's folders sit under `/opt/docker/volumes/victoriametrics` and `/opt/docker/logs/victoriametrics`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/victoriametrics/victoriametrics-data` | `101000:101000` | Default |
| `/opt/docker/volumes/victoriametrics/victorialogs-data` | `101000:101000` | Default |
| `/opt/docker/volumes/victoriametrics/victoriatraces-data` | `101000:101000` | Default |
| `/opt/docker/volumes/victoriametrics/grafana-data` | `101000:101000` | Default |

This stack opens no port on the host's firewall.

The host's NixOS configuration creates the folders when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
