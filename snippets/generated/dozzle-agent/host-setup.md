The project is `dozzle`, so the stack's folders sit under `/opt/docker/volumes/dozzle` and `/opt/docker/logs/dozzle`. Both are mode `0750`, owned by the admin account with group `101000`.

No container in this stack has a folder of its own.

| Port | Allowed from | Comment |
| --- | --- | --- |
| `7007/tcp` | The internal subnet | Dozzle agent |
