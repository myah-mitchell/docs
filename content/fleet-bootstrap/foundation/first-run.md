# The first run

This page builds km01 and ci01 from the shell. km01 is created and provisioned by the run, Komodo Core is started on it by hand one time, and the next run hands Core's stack over to Komodo. ci01 is then built the way every later host is.

Status: written, not yet run. The by-hand start of Core follows the steps the real km01 was built with. See [Not yet confirmed](#unconfirmed) for the rest.

## Prerequisites

- The shell is a control node, from [The control shell](control-shell.md).
- The template exists and the shell holds the Proxmox token, from [Proxmox and the template](proxmox-and-template.md).
- `~/.config/fleet/env` is loaded in the shell you run from.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `<abbr_name>admin`. With `abbr_name` set to `mm` it is `mmadmin` |
| `<db-username>` | A username for Komodo's database, for example `komodo-admin` |

## 1. Describe km01 {#describe}

Add km01 to `hosts.yml` and to `opentofu/prod.tfvars` in the private repo. See [Komodo (km01)](../hosts/km01-komodo.md#describe) for both entries.

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

Then generate km01's Komodo file.

--8<-- "generate-komodo-files.md"

## 2. Create km01 {#km01-vm}

From `~/src/ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=km01 \
  -e vms_backend=local \
  --skip-tags komodo
```

Enter the admin account's password at the prompt, twice. The run ends with `failed=0` for km01.

| Option | Why it is here |
| --- | --- |
| `vms_backend=local` | OpenTofu keeps its state in a file in the shell. The state database is on ci01, which does not exist yet |
| `--skip-tags komodo` | The last stage asks Komodo to deploy km01's Stacks, and Komodo is not running yet |

The state file is `~/.local/state/ansible-opentofu/prod.tfstate`, encrypted with the passphrase in `TF_ENCRYPTION`. It is the only record of which VMs OpenTofu made, until the handover moves it.

Check the host. Log in as the admin account and run:

```bash
ssh <admin>@192.0.2.11
```

```bash
docker version
findmnt /srv/persist
sudo ufw status
ls /opt/docker/volumes
```

Docker answers, the persistent disk is mounted, port `9120/tcp` is allowed with the comment `Komodo Core`, and the folders `komodo` and `traefik` exist.

Periphery is installed and cannot reach Core yet. Step 5 fixes that.

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

Generate the file's contents:

```bash
cd ~/docker-stacks
python3 scripts/build.py
```

Every blank password in the file now holds 48 random characters. Leave `KOMODO_DB_PASSWORD` and `POSTGRES_PASSWORD` as generated.

Open `stacks/komodo-server/.env` in an editor and set these keys:

| Key | Value |
| --- | --- |
| `SERVER_NAME` | `km01` |
| `SUB_DOMAIN_NAME` | `home.`, with the trailing dot |
| `DOMAIN_NAME` | `myah-mitchell.com` |
| `KOMODO_DB_USERNAME` | `<db-username>` |

Run the build again, so the username reaches `POSTGRES_USER`, then start the stack:

```bash
python3 scripts/build.py
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
> `/opt/docker/volumes/komodo/komodo-keys` now holds Core's keypair. Losing that folder breaks trust with every host in the fleet, and each one has to be onboarded again.

## 4. Set Komodo up {#komodo-setup}

Open `http://192.0.2.11:9120` in a browser and follow [Setting up Komodo](komodo-setup.md) to its end. Then come back here.

That page creates the admin account, the keys the run needs, the Resource Sync, and the first Variables and Secrets. It also has you commit Core's public key to the private repo.

## 5. Run km01 in full {#km01-full}

From `~/src/ansible`, with the environment file loaded again so the new values apply:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=km01 \
  -e vms_backend=local \
  -e komodo_onboarding_key="$KOMODO_ONBOARDING_KEY"
```

OpenTofu and provisioning find nothing to change, except Periphery. It gets Core's public key and the onboarding key, connects, and km01 appears in Komodo as a Server.

The last stage then runs the Resource Sync for km01. Komodo creates the Stacks `komodo-server` and `traefik-bootstrap-km01` and deploys both. Core is one of the containers it replaces, so the UI drops for up to a minute while the run waits.

--8<-- "verify-run.md"

On km01, confirm that Komodo now owns Core's containers:

```bash
docker compose ls
```

`komodo-server` and `traefik-bootstrap-km01` are both listed as running. The config file shown for `komodo-server` is under `/opt/docker/stacks/komodo-server`, which is Periphery's checkout and no longer yours.

Remove your checkout. Keep the environment file:

```bash
rm -rf ~/docker-stacks
```

Komodo is now also reachable through Traefik at `https://komodo.km01.home.myah-mitchell.com`, once that name has a DNS record pointing at km01.

--8<-- "certificate-warning.md"

### If the handover fails {#handover-fails}

Read the deploy log of the `komodo-server` Stack in Komodo, under *Resources > Stacks*. If Core is down, start it again the way step 3 did, from a fresh checkout and the same environment file.

A failed handover does not block ci01. Every other host's Stacks deploy the same way whether km01's own Stack is healthy or not, so carry on and come back to it.

## 6. Build ci01 {#ci01}

Follow [Automation and monitoring (ci01)](../hosts/ci01-automation.md) from its first step to its last. Use the **Command line** tab where the page runs the build, with one option added:

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=ci01 \
  -e vms_backend=local \
  -e komodo_onboarding_key="$KOMODO_ONBOARDING_KEY"
```

ci01's pages have you create the Secrets its three stacks read before the run. Do not skip them. A missing Secret reaches the container as literal text and the stack fails to start.

## What's next

Semaphore is running on ci01 with nothing in it. Configure it to run the same playbook the shell has been running. See [The Semaphore project](semaphore-project.md).

## Not yet confirmed {#unconfirmed}

None of these has been run against a real host.

- Komodo redeploying the Stack that Core runs in. Periphery runs under systemd on the host and carries out the deploy, which is the arrangement that should let it finish after Core's container stops.
- Komodo using the Stack's name as the Compose project name, which is what the `-p komodo-server` in step 3 relies on.
- The run's wait for km01's Stacks while Core restarts. The run polls Core's API, and the poll has to survive Core being away for part of it.
- Periphery installed in step 2 with no public key and no onboarding key, then corrected by step 5. The docker role rewrites both values on every run.
- The reboot in step 2, if the first package upgrade asks for one.
