The project is `dozzle`, so the stack's folders sit under `/opt/docker/volumes/dozzle` and `/opt/docker/logs/dozzle`. Both are mode `0750`, owned by the admin account with group `101000`.

No container in this stack has a folder of its own.

This stack opens no port on the host's firewall.

The host's NixOS configuration creates the folders when the host is deployed. It reads them from the host's file in the private repo, `nixos/hosts/<host>.json`, which `nixos-sync.yml` writes from the stack's `setup.yaml`. See [Host layout](../concepts/host-layout.md#stack-folders).
