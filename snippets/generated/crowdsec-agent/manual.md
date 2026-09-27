For crowdsec-agent:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/crowdsec /opt/docker/volumes/crowdsec
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/crowdsec/crowdsec-data
sudo install -d -o 100000 -g 100000 /opt/docker/volumes/crowdsec/crowdsec-config
```
