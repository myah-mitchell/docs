# The first run

This page builds km01 and ci01 from the shell. The run creates km01 and installs NixOS on it, Komodo Core is started on it by hand one time, and a second run hands Core's stack over to Komodo. ci01 is then built the way every later host is.

Status: written, not yet run.

## Prerequisites

- The shell is a control node, and the private repo holds the fleet's values and its first secrets, from [The control shell](control-shell.md).
- The installer ISO is on the Proxmox host and the shell holds the Proxmox token, from [Proxmox and the installer ISO](proxmox-and-installer.md).
- The tools are open and `~/.config/fleet/env` is loaded in the shell you run from.
- km01 can reach the internet. The install downloads the system, and Docker pulls the images.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `<abbr_name>admin`. With `abbr_name` set to `mm` it is `mmadmin` |
| `<db-username>` | A username for Komodo's database, for example `komodo-admin` |

## 1. Describe km01 {#describe}

km01 is in `hosts.yml` since [the fleet's file was written](proxmox-and-installer.md#fleet-file). Add its VM to `opentofu/prod.tfvars` in the private repo. See [Komodo (km01)](../hosts/km01-komodo.md#describe) for the entry.

Put the whole fleet in bootstrap mode, in the `docker_host` group's `vars` in `hosts.yml`:

```yaml
docker_host:
  vars:
    docker_stacks_bootstrap: true
```

Set Core's address in `group_vars/all/private.yml`. Leave `komodo_core_public_key` empty, since Core has no key until it has started:

```yaml
komodo_core_address: "http://192.0.2.11:9120"
```

Add that file to the next commit, which the commands below make from the other files:

```bash
git -C ~/src/fleet-private add group_vars/
```

Then generate km01's files: its SSH host keys, its NixOS file, and its Komodo file. In the commands below, `<host>` is `km01`.

--8<-- "generate-fleet-files.md"

## 2. Create km01 {#km01-vm}

From `~/src/ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=km01 \
  -e vms_backend=local \
  --skip-tags komodo
```

The run asks for nothing. It ends with `failed=0` for km01.

| Option | Why it is here |
| --- | --- |
| `vms_backend=local` | OpenTofu keeps its state in a file in the shell. The state database is on ci01, which does not exist yet |
| `--skip-tags komodo` | The last stage asks Komodo to deploy km01's Stacks, and Komodo is not running yet |

| Stage | What it does on this run |
| --- | --- |
| `vms` | Creates the VM, which finds its disk empty and boots the installer ISO |
| `wait` | Waits for the installer to answer on port 22 |
| `nixos` | Installs NixOS, waits for km01 to boot from its disk, and deploys its configuration |

The install builds the system on km01 itself, from what it downloads. See [How a host is built](../concepts/how-a-host-is-built.md#stages) for each stage in full.

The state file is `~/.local/state/ansible-opentofu/prod.tfstate`, encrypted with the passphrase in `TF_ENCRYPTION`. It is the only record of which VMs OpenTofu made, until the handover moves it.

Check the host. km01 has the host key that was made for it in step 1, so print that key's fingerprint before the first login:

```bash
sops decrypt --extract '["ssh_host_ed25519_key.pub"]' \
  ../fleet-private/secrets/host-keys/km01.yaml | ssh-keygen -lf -
```

Log in as the admin account, and accept the host key when the fingerprint SSH shows is the same:

```bash
ssh <admin>@192.0.2.11
```

```bash
cat /etc/fleet-host
docker version
findmnt /srv/persist
sudo iptables -S nixos-fw | grep 9120
ls /opt/docker/volumes
```

| Command | Shows |
| --- | --- |
| `cat /etc/fleet-host` | `km01` |
| `docker version` | A client and a server, so Docker answers |
| `findmnt` | The persistent disk, mounted |
| `iptables` | One rule that accepts TCP port 9120, which is Komodo Core's |
| `ls` | The folders `komodo` and `traefik` |

Periphery is running and cannot join Core yet. Its configuration has no public key of Core's, and its onboarding key is the placeholder. It keeps trying, and [step 5](#km01-full) gives it both.

## 3. Start Komodo Core {#start-core}

Do this on km01, as the admin account. Every other stack in the fleet is started by Komodo, and this is the one time Komodo cannot.

Check out docker-stacks, and create the file that holds Core's database credentials:

```bash
git clone https://github.com/myah-mitchell/docker-stacks ~/docker-stacks
envFile=/opt/docker/volumes/komodo/komodo-server.env
[ -e $envFile ] || install -m 600 /dev/null $envFile
ln -sfn $envFile ~/docker-stacks/stacks/komodo-server/.env
```

The file lives on the persistent disk, so a rebuilt km01 finds it and starts Core with the same credentials. The checkout only holds a link to it.

Generate the file's contents. A host has no Python, so nix provides one for this command alone, with the YAML library the script reads the stacks with:

```bash
cd ~/docker-stacks
nix-shell -p 'python3.withPackages (p: [ p.pyyaml ])' --run 'python3 scripts/build.py'
```

The output ends with `Build complete.` Every blank password in the file holds 48 random characters. Leave `KOMODO_DB_PASSWORD` and `POSTGRES_PASSWORD` as generated.

Open `stacks/komodo-server/.env` in an editor and set these keys:

| Key | Value |
| --- | --- |
| `SERVER_NAME` | `km01` |
| `SUB_DOMAIN_NAME` | `home.`, with the trailing dot |
| `DOMAIN_NAME` | `myah-mitchell.com` |
| `KOMODO_DB_USERNAME` | `<db-username>` |

Run the build again, so the username reaches `POSTGRES_USER`, then start the stack:

```bash
nix-shell -p 'python3.withPackages (p: [ p.pyyaml ])' --run 'python3 scripts/build.py'
cd stacks/komodo-server
docker compose -p komodo-server up -d
docker compose -p komodo-server ps
```

Four services show as running:

```text
ferretdb
postgres
postgres-backup
komodo
```

`-p komodo-server` gives the Compose project the name Komodo will use for its Stack. With the same name, Komodo's first deploy updates these containers. With any other name it would try to create a second set under container names that are taken.

> [!WARNING]
> `/opt/docker/volumes/komodo/komodo-keys` holds Core's keypair. Losing that folder breaks trust with every host in the fleet, and each one has to be onboarded again.

## 4. Set Komodo up {#komodo-setup}

Open `http://192.0.2.11:9120` in a browser and follow [Setting up Komodo](komodo-setup.md) to its end. Then come back here.

That page creates the admin account, the keys the run needs, the Resource Sync, and the first Variables and Secrets. It also has you write Core's public key and the onboarding key into the private repo, and leaves both changes for the next step to commit.

## 5. Run km01 in full {#km01-full}

The private repo holds two changes that are not committed: Core's public key in `group_vars/all/private.yml`, and the onboarding key in `secrets/fleet.yaml`. The first of them is one of the values in `nixos/fleet.json`, so write the generated files again. From `~/src/ansible`, with the environment file loaded again so that Komodo's API key applies:

```bash
source ~/.config/fleet/env
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
ansible-playbook -i ../fleet-private/hosts.yml komodo-sync.yml
git -C ../fleet-private add group_vars/ nixos/ komodo/ secrets/
git -C ../fleet-private diff --cached --stat
```

The list names `group_vars/all/private.yml`, `nixos/fleet.json`, and `secrets/fleet.yaml`. Commit and push:

```bash
git -C ../fleet-private commit -m "Give the hosts Core's key and the onboarding key"
git -C ../fleet-private push
```

Then run km01 with every stage:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=km01 \
  -e vms_backend=local
```

OpenTofu finds nothing to change, and km01 is not installed again. The deploy gives Periphery Core's public key and the onboarding key and restarts it. Periphery connects, and km01 appears in Komodo as a Server.

The last stage then runs the Resource Sync for km01. Komodo creates the Stacks `komodo-server` and `traefik-bootstrap-km01` and deploys both. Core is one of the containers it replaces, so the UI drops for up to a minute while the run waits.

--8<-- "verify-run.md"

On km01, confirm that Komodo owns Core's containers:

```bash
docker compose ls
```

`komodo-server` and `traefik-bootstrap-km01` are both listed as running. The config file shown for `komodo-server` is under `/opt/docker/stacks/komodo-server`, which is Periphery's checkout and not yours.

Remove your checkout. Keep the environment file:

```bash
rm -rf ~/docker-stacks
```

Komodo is also reachable through Traefik at `https://komodo.km01.home.myah-mitchell.com`, once that name has a DNS record pointing at km01.

--8<-- "certificate-warning.md"

### If the handover fails {#handover-fails}

Read the deploy log of the `komodo-server` Stack in Komodo, under *Resources > Stacks*. If Core is down, start it again the way step 3 did, from a fresh checkout and the same environment file.

If the run stops because km01's Periphery has not connected, read Periphery's log on km01:

```bash
sudo journalctl -u komodo-periphery -n 50
```

A failed handover does not block ci01. Every other host's Stacks deploy the same way whether km01's own Stack is healthy or not, so carry on and come back to it.

## 6. Build ci01 {#ci01}

Follow [Automation and monitoring (ci01)](../hosts/ci01-automation.md) from its first step to its last. Use the **Command line** tab where the page runs the build, with one option added:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ci01 \
  -e vms_backend=local
```

ci01's pages have you create the Secrets its three stacks read before the run. Do not skip them. A missing Secret reaches the container as literal text and the stack fails to start.

ci01 gets the real onboarding key and Core's public key with its first configuration, so one run builds it and deploys its Stacks.

## What's next

Semaphore is running on ci01 with nothing in it. Configure it to run the same playbook the shell has been running. See [The Semaphore project](semaphore-project.md).

## Not yet confirmed {#unconfirmed}

None of these has been run against a real host.

- The run itself: a VM created blank that boots the installer, the install, and the first deploy.
- The checks in [step 2](#km01-vm), and what each prints.
- Periphery on a host whose configuration names Core and has no public key of Core's, with a placeholder as its onboarding key. The unit restarts Periphery whenever it exits, which is the arrangement that should keep it trying.
- The `nix-shell` command in [step 3](#start-core) on a host. It was run on another machine with `NIX_PATH` set the way a host's configuration sets it, and the host needs the internet for it.
- `docker compose` typed by hand on a host. A host sets `DOCKER_CONTENT_TRUST=1` for commands typed in a shell, and whether Compose then pulls the four images has not been tried.
- The state of postgres-backup after the start by hand. The file `build.py` writes leaves the database and the user of the backup empty.
- Komodo using the Stack's name as the Compose project name, which is what the `-p komodo-server` in step 3 relies on.
- The deploy in [step 5](#km01-full) restarting Periphery with both new values. The public key changes Periphery's configuration file, which restarts the unit. The onboarding key is read from a file that the same deploy writes again.
- Komodo redeploying the Stack that Core runs in. Periphery runs under systemd on the host and carries out the deploy, which is the arrangement that should let it finish after Core's container stops.
- The run's wait for km01's Stacks while Core restarts. The run polls Core's API, and the poll has to survive Core being away for part of it.
