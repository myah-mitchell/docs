The project is `crowdsec`, so the stack's folders sit under `/opt/docker/volumes/crowdsec` and `/opt/docker/logs/crowdsec`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/crowdsec/crowdsec-data` | `100000:100000` | Default |
| `/opt/docker/volumes/crowdsec/crowdsec-config` | `100000:100000` | Default |

This stack opens no port on the host's firewall.
