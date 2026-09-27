For dozzle-agent:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/dozzle /opt/docker/volumes/dozzle
```

`<internal-subnet>` is the inventory's `docker_stacks_internal_subnet`, for example `192.0.2.0/24`.

```bash
sudo ufw allow from <internal-subnet> to any port 7007 proto tcp comment 'Dozzle agent'
```
