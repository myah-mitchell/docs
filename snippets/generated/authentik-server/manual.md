For authentik-server:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/authentik /opt/docker/volumes/authentik
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/authentik/authentik-media
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/authentik/authentik-templates
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/authentik/authentik-certs
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/authentik/postgres-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/authentik/postgres-backup-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/authentik/geoip-data
```
