The project is `mail`, so the stack's folders sit under `/opt/docker/volumes/mail` and `/opt/docker/logs/mail`. Both are mode `0750`, owned by the admin account with group `101000`.

| Folder | Owner | Mode |
| --- | --- | --- |
| `/opt/docker/volumes/mail/stalwart-config` | `102000:102000` | Default |
| `/opt/docker/volumes/mail/stalwart-data` | `102000:102000` | Default |
| `/opt/docker/volumes/mail/bulwark-data` | `101001:101001` | Default |
| `/opt/docker/volumes/mail/bulwark-data/settings` | `101001:101001` | Default |
| `/opt/docker/volumes/mail/bulwark-data/admin` | `101001:101001` | Default |
| `/opt/docker/volumes/mail/bulwark-data/admin-state` | `101001:101001` | Default |
| `/opt/docker/volumes/mail/bulwark-data/telemetry` | `101001:101001` | Default |

| Port | Allowed from | Comment |
| --- | --- | --- |
| `25/tcp` | Anywhere | Stalwart SMTP |
| `465/tcp` | Anywhere | Stalwart submissions |
| `587/tcp` | Anywhere | Stalwart submission |
| `993/tcp` | Anywhere | Stalwart IMAPS |
