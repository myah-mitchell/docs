For step-ca-server:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/step-ca /opt/docker/volumes/step-ca
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/step-ca/step-ca-data
sudo install -d -o 101000 -g 101000 -m 0700 /opt/docker/volumes/step-ca/step-ca-secrets
```
