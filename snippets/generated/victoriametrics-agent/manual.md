For victoriametrics-agent:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/victoriametrics /opt/docker/volumes/victoriametrics
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vlagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vmagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/victoriametrics/vector-data
```

`<internal-subnet>` is the inventory's `docker_stacks_internal_subnet`, for example `192.0.2.0/24`.

```bash
sudo ufw allow from <internal-subnet> to any port 5140 proto tcp comment 'Vector syslog'
sudo ufw allow from <internal-subnet> to any port 5140 proto udp comment 'Vector syslog'
```
