# Certificates (pk01)

pk01 runs [step-ca](../../tools/step-ca/index.md), the fleet's internal certificate authority (CA). A CA signs certificates for the fleet's own names, and a machine that trusts the CA's root certificate accepts every certificate it signs. pk01 is built now so that the CA's root key is made, backed up, and taken offline before anything depends on it.

At the end of this page the CA is running, its root key exists only in two encrypted backups that you hold, and every host trusts its root certificate.

Its own [stack](../../tools/glossary.md#stack) is [step-ca-server](../stacks/step-ca-server.md), the smallest in the fleet: one service and no database. pk01 is also the one host built in two runs. The CA reads its password from a file on the host, and the file has to be there before the first start, so the first run stops short of the deploy.

Nothing in the fleet asks this CA for a certificate yet. [Traefik](../../tools/traefik/index.md) gets its certificates from Let's Encrypt, and the hosts' SSH keys are static. See [Certificates from Let's Encrypt](../concepts/bootstrap-mode.md#certificates).

Status: written, not yet run.

## Prerequisites

- The foundation is finished, through [The handover](../foundation/handover.md).
- Two durable places to keep the root key's backup, physically apart from each other, such as an encrypted USB stick at home and a second one elsewhere.
- A machine outside the fleet with `age` and the `step` command line installed, to test the backup on.
- Time to go from [step 5](#deploy) to [step 7](#root-key) in one sitting. The root key sits on a running host between the two.

## 1. Describe the host {#describe}

In the [private repo](../../tools/glossary.md#private-repo)'s `hosts.yml`, add pk01 to the `docker_host` group:

```yaml
    pk01:
      ansible_host: 172.16.7.141
      serverHostname: "pk01"
      komodo_stacks_manage: false
      docker_stacks:
        - system-agent
        - traefik-agent
        - step-ca-server
      komodo_stack_env:
        step-ca-server:
          STEPCA_CA_NAME: "Home Internal CA"
```

--8<-- "bootstrap-mode-stacks.md"

The first three keys are the ones every host has. See [km01's entry](km01-komodo.md#describe) for those. Two keys are new on this page.

`komodo_stacks_manage: false` turns off the run's last stage for this host, the one where [Komodo](../../tools/komodo/index.md) deploys the stacks. The first run then builds pk01 and deploys nothing. [Step 5](#deploy) takes the line out again.

`komodo_stack_env` sets a value in a stack's environment for this host alone. See [Stack values](../concepts/fleet-private.md#stack-values).

`STEPCA_CA_NAME` is the name the CA puts in every certificate it issues. Choose **your CA's name** now. Changing it later means a new CA and new certificates everywhere.

In `opentofu/prod.tfvars`, add its VM inside `vms`:

```hcl
  pk01 = {
    server       = "vh01"
    vm_id        = 7141
    cores        = 2
    memory_mb    = 2048
    vlan_id      = 7
    ipv4_address = "172.16.7.141/24"
    ipv4_gateway = "172.16.7.1"
    dns_servers  = ["172.16.7.1"]
    tags         = ["docker"]
    extra_disks = {
      persist = { interface = "scsi2", size_gb = 10 }
    }
  }
```

The fields are the same as for every VM, and [the OpenTofu primer](../../tools/opentofu/index.md#in-the-fleet) explains them. Only the name, the VMID, the address, and the sizes differ from km01's.

One service with no database needs little, so pk01 is the smallest VM in the fleet. The CA's whole state is its configuration, its keys, and its record of what it issued, and 10 GB holds them.

pk01 is on the internal VLAN, and nothing publishes it to the internet. A CA for internal names has no reason to answer from outside.

Then generate pk01's files: its SSH host keys, its NixOS file, and its Komodo file.

--8<-- "generate-fleet-files.md"

## 2. Stage the values {#values}

step-ca-server reads no Variable or Secret of its own, so there is nothing to create in Komodo.

The one secret it needs is the CA password, which is a file on pk01 and never passes through Komodo. [Step 4](#password) creates it.

## 3. Run the build {#run}

/// tab | Semaphore

In [Semaphore](../../tools/semaphore/index.md), run the **site** Template with *Target* set to `pk01`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=pk01
```

///

The run creates the VM, installs NixOS on it, and deploys its configuration, which makes the folders its stacks need. It ends there, with no Stack deployed.

The recap line for pk01 shows `failed=0` and `unreachable=0`. In Komodo's UI, under *Resources > Servers*, pk01 shows as connected, and no Stack is attached to it.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-vm.md"

--8<-- "manual-install.md"

--8<-- "generated/traefik-bootstrap/manual.md"

--8<-- "generated/step-ca-server/manual.md"

</details>

## 4. Create the CA password {#password}

Log in to pk01 as the admin account and write 32 random bytes to the password file:

```bash
head -c32 /dev/urandom | base64 \
  | sudo tee /opt/docker/volumes/step-ca/step-ca-secrets/password > /dev/null
sudo chown 101000:101000 /opt/docker/volumes/step-ca/step-ca-secrets/password
sudo chmod 600 /opt/docker/volumes/step-ca/step-ca-secrets/password
```

Check the file and its owner:

```bash
sudo ls -ln /opt/docker/volumes/step-ca/step-ca-secrets
```

The listing shows one file, `password`, owned by `101000` with mode `-rw-------`. `101000` is the container's own user as the host sees it. See [UID offsets](../concepts/host-layout.md#uid-offsets).

Copy the password into your password manager, and keep a second copy on paper or on a disk of its own, beside the root key's backup:

```bash
sudo cat /opt/docker/volumes/step-ca/step-ca-secrets/password
```

> [!WARNING]
> This password encrypts the root key and the intermediate key. Once the root key is offline, a lost password means the backup can never be opened.

The file is on the host because the container mounts it read-only from there. When the file is missing, Docker puts an empty folder in its place, and step-ca fails to start.

## 5. Deploy the CA {#deploy}

In `hosts.yml`, remove the `komodo_stacks_manage: false` line from pk01. Commit and push the change:

```bash
git -C ../fleet-private add hosts.yml
git -C ../fleet-private commit -m "Deploy pk01's stacks"
git -C ../fleet-private push
```

`komodo_stacks_manage` is in neither of pk01's generated files, so there is nothing to generate again.

Run the build a second time, the same way as in [step 3](#run). This time the run has Komodo deploy two Stacks: `traefik-bootstrap-pk01` and `step-ca-server`.

On its first start step-ca creates a root key, an intermediate key, and the SSH certificate authority's keys, all encrypted with the password from [step 4](#password). It also turns on its [ACME](../../tools/glossary.md#acme) endpoint, the interface a program such as Traefik uses to ask for a certificate unattended.

<details>
<summary>Manual steps, instead of site.yml</summary>

--8<-- "manual-stack-deploy.md"

</details>

## 6. Verify {#verify}

--8<-- "verify-run.md"

The `step-ca-server` Stack has one service:

--8<-- "generated/step-ca-server/services.md"

On pk01, ask the CA for its health:

```bash
docker exec step-ca-step-ca step ca health --ca-url https://127.0.0.1:9000
```

The command prints `ok`. It is the same check the container's own health check runs.

Ask again through Traefik, from a machine on the internal network:

```bash
curl -k https://step-ca.pk01.home.myah-mitchell.com/health
```

The reply is `{"status":"ok"}`. The name needs a DNS record pointing at pk01, or an entry in your own hosts file. `-k` is needed while pk01 is in bootstrap mode, because Traefik serves its own self-signed certificate.

The CA's [route](../../tools/glossary.md#route) never asks for a sign-in, in either mode. step-ca checks each request itself, and the clients that renew certificates unattended could not pass a sign-in page.

## 7. Take the root key offline {#root-key}

Move the root key off pk01 in one sitting, through the five parts below: copy it out, encrypt it, store two copies, remove it from the host, and test a copy.

The root key and the intermediate key are both on pk01 now. The CA only needs the intermediate to issue certificates. The root signs a new intermediate when one is needed, so it belongs somewhere no running host can reach.

<details>
<summary>Background: why the CA has two keys, and what losing each one costs</summary>

Every host is told to trust one thing, the root certificate. A certificate is accepted when a chain of signatures leads from it back to that root, so whoever holds the root key can make a certificate for any name, and the whole fleet accepts it. The only cure for a stolen root key is a new CA, with a new root certificate on every host.

The root key is therefore used for one job. It signs the intermediate's certificate, and is then put away. The intermediate key does the daily signing, so it has to stay on pk01, where the password file unlocks it each time the CA starts.

That split limits what a break-in on pk01 costs. A stolen intermediate is replaced by signing a new one with the root key from the backup, and the root certificate on every host stays as it is. With the root key still on pk01, the same break-in would cost the whole CA.

The [step-ca primer](../../tools/step-ca/index.md#ideas) explains certificate chains in general.

</details>

### Copy the key out {#root-key-copy}

On pk01, copy the key and the root certificate out of the container into a folder only you can read:

```bash
mkdir -m 700 ~/root-key && cd ~/root-key
docker cp step-ca-step-ca:/home/step/secrets/root_ca_key .
docker cp step-ca-step-ca:/home/step/certs/root_ca.crt .
```

Print the root certificate's fingerprint, and store it with the backup:

```bash
docker exec step-ca-step-ca \
  step certificate fingerprint /home/step/certs/root_ca.crt
```

### Encrypt it a second time {#root-key-encrypt}

Encrypt the key under a passphrase with `age`. pk01 has no `age` of its own, so run it out of nixpkgs:

```bash
nix shell nixpkgs#age -c age -p -o root_ca_key.age root_ca_key
```

The command downloads `age` the first time it runs, and installs nothing on pk01.

`age` asks for the passphrase twice. Use **a new passphrase**, different from the CA password, and write it down somewhere that does not depend on the fleet being up.

The key file is already encrypted under the CA password. With a passphrase of its own on top, a backup stays closed to someone who finds it together with only one of the two.

### Store two copies {#root-key-store}

Copy `root_ca_key.age` and `root_ca.crt` to both places from the prerequisites. Either copy alone is enough to recover from.

`root_ca.crt` is public. Keep a copy within reach as well, for [step 8](#trust).

### Remove it from pk01 {#root-key-remove}

Delete the working copies, then the key inside the container:

```bash
shred -u ~/root-key/root_ca_key ~/root-key/root_ca_key.age
docker exec step-ca-step-ca rm /home/step/secrets/root_ca_key
```

Restart the CA and check that it runs on the intermediate alone:

```bash
docker restart step-ca-step-ca
docker exec step-ca-step-ca step ca health --ca-url https://127.0.0.1:9000
```

The command prints `ok`.

### Test the backup {#root-key-test}

On the machine outside the fleet, with one of the two copies, decrypt the key and sign a throwaway intermediate with it. Signing an intermediate is the one job the root key has, so this is the test that counts:

```bash
age -d -o root_ca_key root_ca_key.age
step certificate create "Test intermediate" test.crt test.key \
  --ca ./root_ca.crt --ca-key ./root_ca_key --profile intermediate-ca
```

`age` asks for the passphrase, and `step` asks for the CA password, then for a new password for the test key. A certificate written to `test.crt` proves the backup, the passphrase, and the CA password all work.

Delete what the test made:

```bash
shred -u root_ca_key test.crt test.key
```

## 8. Give the fleet the root certificate {#trust}

In the private repo's `group_vars/all/private.yml`, add the root certificate to `ca_certificates`. This is what makes the hosts accept certificates the CA signs:

```yaml
ca_certificates:
  - name: Home_Internal_CA
    content: |
      -----BEGIN CERTIFICATE-----
      ...
      -----END CERTIFICATE-----
```

Paste the contents of `root_ca.crt` in place of the three dots.

The certificate reaches the hosts through `nixos/fleet.json`. From `~/src/fleet-ansible`, write that file again, then commit and push:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
git -C ../fleet-private add group_vars/all/private.yml nixos/
git -C ../fleet-private commit -m "Trust the internal CA"
git -C ../fleet-private push
```

A host has the certificate in its own trust store from its next deploy. Run each host that is already built one more time, as in [step 3](#run) with that host as the target. A host built from here on has the certificate from its first boot. See [After a change](../concepts/fleet-private.md#after-a-change).

A trust store is the list of root certificates the programs on a machine accept. This step covers the programs running on the host. A container has a trust store of its own and is not changed.

## What's next

Build tf01, the Traefik hub. See [Traefik hub (tf01)](tf01-traefik-hub.md).

Two later pieces of work depend on this CA, and neither is part of the bootstrap: a Traefik resolver that gets certificates for internal names from it, and SSH certificates in place of the fleet's static key. For the key, see [Leaving bootstrap mode](../procedures/leave-bootstrap-mode.md).

## Not yet confirmed {#unconfirmed}

- The whole page. pk01 has not been built by the run.
- The first start. step-ca's image has not been started with the password mounted read-only at the path the image keeps its own copy in. If the container stops one time after creating the CA and then restarts cleanly, that is the cause.
- The run with `komodo_stacks_manage: false`. The role skips its tasks when the value is false, and that has been read in the code and not run.
- `age` through `nix shell` on pk01. The command needs pk01 to reach the NixOS binary cache, and it has not been run on a host.
- The root certificate in a host's trust store. The list reaches the host's configuration through `nixos/fleet.json`, which has been evaluated and not deployed.
- The ACME endpoint and the SSH certificate authority. Both are turned on at first start, and nothing has asked either for a certificate.
- The root certificate inside containers. The trust step reaches the host only.
