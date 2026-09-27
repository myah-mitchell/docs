For system-agent:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/system /opt/docker/volumes/system
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vmagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vlagent-data
sudo install -d -o 101000 -g 101000 /opt/docker/volumes/system/vector-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/system/dockns-data
```

`<internal-subnet>` is the inventory's `docker_stacks_internal_subnet`, for example `192.0.2.0/24`.

```bash
sudo ufw allow from <internal-subnet> to any port 5140 proto tcp comment 'Vector syslog'
sudo ufw allow from <internal-subnet> to any port 5140 proto udp comment 'Vector syslog'
sudo ufw allow from <internal-subnet> to any port 7007 proto tcp comment 'Dozzle agent'
```
