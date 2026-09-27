For victoriametrics-server:

A host deployed with the stack in its file has these folders already. The commands make them on a host whose file does not list the stack.

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/victoriametrics /opt/docker/volumes/victoriametrics
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/victoriametrics-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/victorialogs-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/victoriatraces-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/grafana-data
```
