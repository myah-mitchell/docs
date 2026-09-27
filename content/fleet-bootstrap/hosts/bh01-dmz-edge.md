# DMZ edge (bh01)

bh01 is the fleet's edge, and the only host that carries web traffic from the internet. It reaches Cloudflare through a tunnel it opens outward, so no port is forwarded to it and no public address points at it.

Its own stack is [traefik-dmz](../stacks/traefik-dmz.md): a Traefik, a Redis that copies the one on tf01, and cloudflared, the tunnel's connector. bh01 sits on the DMZ VLAN, so it is the first host whose traffic to the rest of the fleet crosses your router's firewall.

Status: written, not yet run.

## Prerequisites

- tf01 is built, because bh01's Redis copies tf01's. See [Traefik hub (tf01)](tf01-traefik-hub.md).
- A Cloudflare account that holds the zone for your domain.
- An admin machine with the `cloudflared` CLI installed. It must not be bh01, and the machine the control shell runs on will do.
- A DMZ VLAN on the router, carried by the Proxmox bridge the VMs use, with firewall rules you control.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `<abbr_name>admin` |
| `<fleet-subnet>` | A range in CIDR form, from your own addressing plan, that holds both the internal subnet and the DMZ |
| `<tunnel-id>` | The tunnel's ID, printed in [step 4](#tunnel) |
| `<hostname>` | A public name to publish, such as `ntfy.myah-mitchell.com` |

## 1. Describe the host {#describe}

In the private repo's `hosts.yml`, add bh01 to the `docker_host` group:

```yaml
    bh01:
      ansible_host: 198.51.100.11
      network_gateway: "198.51.100.1"
      serverHostname: "bh01"
      komodo_stacks_manage: false
      docker_stacks:
        - system-agent
        - traefik-dmz
```

`network_gateway` is the DMZ's gateway. The `docker_host` group sets the internal network's gateway, so a host on the DMZ sets its own. Its DNS server is the same address unless `network_dns` names another. See [the group's values](km01-komodo.md#describe).

traefik-dmz includes traefik-agent, so the list does not name it.

While `docker_stacks_bootstrap: true` is set, the run leaves out system-agent and deploys traefik-dmz alone. traefik-dmz is a Traefik itself, so the run adds no traefik-bootstrap. See [Bootstrap mode](../concepts/bootstrap-mode.md#changes).

`komodo_stacks_manage: false` turns off the run's last stage for this host, so the first run builds bh01 and deploys nothing. cloudflared cannot start before its credentials are on the host, and [step 7](#deploy) takes the line out again once they are.

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  bh01 = {
    server       = "vh01"
    vm_id        = 8011
    cores        = 4
    memory_mb    = 8192
    vlan_id      = 8
    ipv4_address = "198.51.100.11/24"
    ipv4_gateway = "198.51.100.1"
    dns_servers  = ["198.51.100.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 10 }
    }
  }
```

The VLAN, the address, the gateway, and the DNS server all come from the DMZ. bh01 is the first host where they differ from the internal ones. The run stops when the address or the gateway here differs from the one in `hosts.yml`.

Every request from the internet passes through this Traefik, and the four cores and 8 GB leave room for that. The persistent disk holds certificates and the tunnel's two files, so 10 GB is more than enough.

Then generate bh01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 2. Open the path across the boundary {#boundary}

Allow these on the router, between the DMZ and the internal VLAN. The run itself needs the first two.

| From | To | Port | Used for |
| --- | --- | --- | --- |
| The control node, ci01 at `192.0.2.12` | bh01 | `22/tcp` | The run installs and deploys over SSH |
| bh01 | km01, `192.0.2.11` | `9120/tcp` | Periphery dials Komodo Core |
| bh01 | tf01, `192.0.2.15` | `6379/tcp` | The Redis copy, and bh01's own route publisher |
| bh01 | Every internal host that serves a web interface | `443/tcp` | Published routes, the sign-in on id01, and telemetry to ci01 |

A run from a shell needs the first rule for the shell's own address.

bh01 also needs the internet, outbound only. Ports 80 and 443 carry NixOS packages, images, the docker-stacks repo, Let's Encrypt, and Cloudflare's API. Port 7844, over both TCP and UDP, carries the tunnel.

Allow nothing else from the DMZ inward. A host in the DMZ that is taken over can reach whatever these rules leave open.

The DMZ's DNS server has to resolve the fleet's internal names. bh01 finds tf01 by the value of `TRAEFIK_KOP_REDIS_SERVER`, which is `tf01.home.myah-mitchell.com` in these pages. Nothing writes DNS records in bootstrap mode, so add the record by hand.

### Admit the DMZ on tf01 {#boundary-tf01}

tf01's own firewall opens its Redis port to `docker_stacks_internal_subnet` only, and bh01 is outside that subnet. The rule is part of tf01's configuration, so it changes in the inventory. A rule added on tf01 by hand is gone after the next deploy or reboot.

In `hosts.yml`, give tf01 a range of its own:

```yaml
    tf01:
      ansible_host: 192.0.2.15
      serverHostname: "tf01"
      docker_stacks_internal_subnet: "<fleet-subnet>"
      docker_stacks:
        - system-agent
        - traefik-server
```

The value is a single range, and tf01 opens every port marked for the internal subnet to it. Once the fleet has left bootstrap mode, that includes system-agent's ports on tf01.

From `~/src/ansible`, write tf01's file again, then commit and push:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
git -C ../fleet-private add hosts.yml nixos/
git -C ../fleet-private commit -m "Open tf01's Redis to the DMZ"
git -C ../fleet-private push
```

Run tf01 again, the same way as in [its own build](tf01-traefik-hub.md#run). Then log in to tf01 and read the rule:

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport 6379 '
```

The line names `<fleet-subnet>` after `-s` and ends in `-j nixos-fw-accept`.

## 3. Stage the values {#values}

Nothing new is needed. traefik-dmz reads seven values, and all seven exist already, from [Setting up Komodo](../foundation/komodo-setup.md#traefik).

This Traefik uses the Cloudflare token and the Let's Encrypt address for real certificates, in bootstrap mode too. tf01 was the first host to use them, so a tf01 with a trusted certificate has proven both.

The tunnel's credentials are a file on bh01's disk, not a value in Komodo. The next step creates them.

## 4. Create the tunnel {#tunnel}

On the admin machine, sign in to Cloudflare and create the tunnel:

```bash
cloudflared tunnel login
cloudflared tunnel create home-edge
```

The first command opens a browser, where you authorise the zone for your domain. The second prints the tunnel's ID and writes the credentials to `~/.cloudflared/<tunnel-id>.json`.

`home-edge` names this site's edge. A second site would get a tunnel of its own.

Confirm the tunnel exists:

```bash
cloudflared tunnel list
```

The list includes `home-edge` with the same ID.

> [!WARNING]
> Anything that holds the credentials file can serve traffic for your hostnames. Keep it out of every repo, and delete every copy but the one on bh01 and the one in your password manager.

## 5. Run the build {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `bh01`.

///

/// tab | Command line

From `~/src/ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=bh01
```

///

The run creates the VM, installs NixOS on it, and deploys its configuration, which makes the folders its stack needs and puts cloudflared's example config in place. It ends there, with no Stack deployed.

The recap line for bh01 shows `failed=0` and `unreachable=0`. In Komodo's UI, under *Resources > Servers*, bh01 shows as connected, which proves Periphery reached km01 across the boundary.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/traefik-dmz/manual.md"

</details>

## 6. Install the tunnel's files {#tunnel-files}

From the admin machine, copy the credentials to bh01:

```bash
scp ~/.cloudflared/<tunnel-id>.json <admin>@198.51.100.11:
```

Log in to bh01 and move the file into place:

```bash
sudo install -o 101000 -g 101000 -m 0600 ~/<tunnel-id>.json \
  /opt/docker/volumes/traefik/cloudflared-secrets/<tunnel-id>.json
rm ~/<tunnel-id>.json
```

Open the config the run put in place:

```bash
sudoedit /opt/docker/volumes/traefik/cloudflared-config/config.yml
```

Put the tunnel's ID in the first two lines, and remove the example rule for `vault.myah-mitchell.com`. The file then reads:

```yaml
tunnel: <tunnel-id>
credentials-file: /etc/cloudflared/secrets/<tunnel-id>.json

ingress:
  - service: http_status:404
```

The last rule answers any hostname no other rule matches. It stays, and it stays last, because cloudflared reads the rules in order.

Give the file back to the container's user, in case the editor changed its owner:

```bash
sudo chown 101000:101000 \
  /opt/docker/volumes/traefik/cloudflared-config/config.yml
```

Check both files:

```bash
sudo ls -ln /opt/docker/volumes/traefik/cloudflared-secrets \
  /opt/docker/volumes/traefik/cloudflared-config
```

Each folder holds one file owned by `101000`, and the credentials show mode `-rw-------`.

A host's configuration puts the example there only when no file is in its place, so these edits survive every later run and a rebuild of bh01.

## 7. Deploy the edge {#deploy}

In `hosts.yml`, remove the `komodo_stacks_manage: false` line from bh01. Commit and push the change:

```bash
git -C ../fleet-private add hosts.yml
git -C ../fleet-private commit -m "Deploy bh01's stacks"
git -C ../fleet-private push
```

`komodo_stacks_manage` is in neither of bh01's generated files, so there is nothing to generate again.

Run the build a second time, the same way as in [step 5](#run). This time the run has Komodo deploy one Stack, `traefik-dmz`.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-stack-deploy.md"

</details>

## 8. Verify {#verify}

--8<-- "verify-run.md"

The `traefik-dmz` Stack has eight services:

--8<-- "generated/traefik-dmz/services.md"

On bh01, confirm the Redis copy is in step with tf01:

```bash
docker exec traefik-redis redis-cli info replication
```

The output includes `role:slave` and `master_link_status:up`. A copy that cannot reach tf01 reports `down` and keeps serving what it last had, so check this now.

Confirm the tunnel is connected:

```bash
docker ps --filter name=traefik-cloudflared --format '{{.Status}}'
```

The status ends with `(healthy)`. cloudflared's health check passes only once the tunnel has a connection to Cloudflare.

Confirm the firewall:

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport (80|443|8443) '
```

Three rules show, one for each of Traefik's ports. None names a source address after `-s`, and each ends in `-j nixos-fw-accept`.

## 9. Open the dashboard {#first-access}

Open `https://traefik.bh01.home.myah-mitchell.com:8443` in a browser. The name needs a DNS record pointing at bh01, or an entry in your own hosts file.

The certificate is from Let's Encrypt, so the browser shows no warning.

The dashboard opens with no sign-in while the fleet is in bootstrap mode. Nothing on the internet can reach port 8443 on bh01, since nothing forwards to it, but every machine in the DMZ can.

## While the fleet is in bootstrap mode {#bootstrap}

| Part of bh01 | In bootstrap mode | After it |
| --- | --- | --- |
| Certificate | Let's Encrypt, trusted | The same |
| Tunnel | Connected, with no hostname on it | Carries each published hostname |
| Redis copy | In step with tf01, which holds no routes | Holds every published route |
| Dashboard | No sign-in | Authentik first |
| Metrics and logs | Not shipped. system-agent is left out | Shipped to ci01 |

bh01 can prove the tunnel and the copy in bootstrap mode, and it cannot publish anything. A route reaches bh01 only when the route publisher on the service's own host writes it to tf01's Redis. The publisher is part of traefik-agent, and a host in bootstrap mode runs traefik-bootstrap in its place.

## Publishing a hostname {#publish}

Do this after the fleet has left bootstrap mode, one time for each public name.

A service can be published only when its container carries `kop-public` labels. In docker-stacks today those are ntfy, Stalwart, and Bulwark.

On the admin machine, create the public DNS record:

```bash
cloudflared tunnel route dns home-edge <hostname>
```

On bh01, add a rule for the name to `config.yml`, above the catch-all:

```yaml
ingress:
  - hostname: <hostname>
    service: http://traefik-traefik:80

  - service: http_status:404
```

Every rule points at bh01's own Traefik, which decides where the request goes. `traefik-traefik` is that container's name, because every Traefik stack uses the project name `traefik`.

Restart cloudflared so that it reads the file:

```bash
docker restart traefik-cloudflared
```

Open `https://<hostname>` from outside your network, such as from a phone with Wi-Fi off. The service answers.

> [!WARNING]
> A hostname on the tunnel is on the internet from the moment its DNS record exists. Publish only a service that signs its users in itself, or one whose route uses the Authentik chain.

A public name has no sub-domain in it. `ntfy.myah-mitchell.com` is public, and `ntfy.home.myah-mitchell.com` is the internal name for the same service.

## What's next

Every host the fleet was waiting for is up. Leave bootstrap mode next. See [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

mx01 is the host after that, and it is optional. See [Mail (mx01)](mx01-mail.md).

## Not yet confirmed {#unconfirmed}

- The whole page. bh01 has not been built by the run.
- Whether tf01's firewall filters the Redis port at all. Docker publishes a container's port through rules of its own, which a packet can reach without passing the host's `nixos-fw` chain. If so, the range in [step 2](#boundary-tf01) changes nothing for Redis, and the router's rules are the only limit on that port.
- The rule on tf01 with a range of its own. The inventory value reaches tf01's file and the rule the flake writes from it, and both have been read in the code and not deployed.
- The Redis provider on bh01. Traefik sends the Redis password to the local copy, and the copy is started with no password of its own. Redis may refuse that login.
- Ingress rules that point at port 80. Traefik's entrypoint there redirects to HTTPS, and no published route listens on it. The rules may have to point at port 443 instead.
- The address the route publisher writes for a published service. The page assumes the service's own host, on port 443.
- Port 7844 for the tunnel, which comes from Cloudflare's documentation.
- Publishing Authentik. `auth.myah-mitchell.com` is its public name, and authentik-server carries no `kop-public` labels, so bh01 has no route for it yet.
