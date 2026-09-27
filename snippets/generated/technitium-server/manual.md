For technitium-server:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/technitium /opt/docker/volumes/technitium
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/technitium/technitium-data
```
