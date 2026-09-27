For stalwart-server:

```bash
sudo install -d -o $USER -g 101000 -m 0750 \
  /opt/docker/logs/mail /opt/docker/volumes/mail
sudo install -d -o 102000 -g 102000 /opt/docker/volumes/mail/stalwart-config
sudo install -d -o 102000 -g 102000 /opt/docker/volumes/mail/stalwart-data
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/settings
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/admin
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/admin-state
sudo install -d -o 101001 -g 101001 /opt/docker/volumes/mail/bulwark-data/telemetry
```

```bash
sudo ufw allow 25/tcp comment 'Stalwart SMTP'
sudo ufw allow 465/tcp comment 'Stalwart submissions'
sudo ufw allow 587/tcp comment 'Stalwart submission'
sudo ufw allow 993/tcp comment 'Stalwart IMAPS'
```
