For semaphore-server:

A host deployed with the stack in its file has these folders and seed files already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/semaphore /opt/docker/volumes/semaphore
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/semaphore/semaphore-data
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/semaphore/semaphore-config
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/semaphore/semaphore-tmp
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/semaphore/nix-data
sudo install -d -o 100000 -g 100000 -m 0755 /opt/docker/volumes/semaphore/postgres-initdb
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/semaphore/postgres-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/semaphore/postgres-backup-data
```

```bash
sudo test -e /opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh || sudo curl -fsSL \
  -o /opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh \
  https://raw.githubusercontent.com/myah-mitchell/fleet-stacks/main/containers/semaphore/config/postgres-initdb/10-tofu-state.sh
sudo chown 100000:100000 /opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh
sudo chmod 0755 /opt/docker/volumes/semaphore/postgres-initdb/10-tofu-state.sh
```
