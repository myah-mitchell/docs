# step-ca-server

step-ca-server is step-ca, the fleet's internal certificate authority. It is the smallest stack in the repo: one service and no database. It runs on one host, pk01. See [Certificates (pk01)](../hosts/pk01-certificates.md) for the build.

## What it runs {#services}

--8<-- "generated/step-ca-server/services.md"

| Service | Does |
| --- | --- |
| `step-ca` | Issues certificates over ACME and with its own provisioners, and holds an SSH certificate authority |

The project is `step-ca`, so the container is `step-ca-step-ca`. It joins `proxy` and no other network.

step-ca sets itself up on the first start of an empty data folder. It generates a root key, an intermediate key, and the SSH authority's keys, and turns on its ACME provisioner. Its own certificate carries its name on the host, the sub-domain, and a wildcard under the sub-domain.

The SSH authority is on from that first start, before anything uses it. Its keys are made during setup, and adding them to a working authority later is harder than having them from the start.

## Values it reads {#values}

--8<-- "generated/step-ca-server/values.md"

Two keys in the stack's environment are settings with a committed value. Change one in the inventory, before the first start. See [Stack values](../concepts/fleet-private.md#stack-values).

| Key | Holds |
| --- | --- |
| `STEPCA_CA_NAME` | The name the authority gives itself in every certificate it issues |
| `STEPCA_PROVISIONER_NAME` | The name of the first provisioner, `admin` as committed |

## What the host needs {#host-setup}

--8<-- "generated/step-ca-server/host-setup.md"

The stack also needs a Traefik on the same host, since it publishes no port of its own.

The run does not create the password file, and the stack cannot start without it:

```text
/opt/docker/volumes/step-ca/step-ca-secrets/password
```

The file holds the password that encrypts the root and intermediate keys on disk. It is mounted read-only into the container, and it has to exist before the first deploy. When it is missing, Docker makes a folder under that name and step-ca fails to start. The host page creates it.

## Hostnames {#hostnames}

Traefik routes two names to step-ca. With the host `pk01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, they are:

| Hostname | Comes from |
| --- | --- |
| `pki.home.myah-mitchell.com` | `STEPCA_SERVICE_NAME` on the sub-domain |
| `step-ca.pk01.home.myah-mitchell.com` | `STEPCA_HOSTNAME` on the host |

The route uses `chain-no-auth` in both modes. Each provisioner does its own authentication, and an ACME client cannot follow a redirect to Authentik.

step-ca serves TLS itself, so Traefik connects to it over HTTPS on port 9000.

## Verify {#verify}

In Komodo, the `step-ca-server` Stack shows as running with one service.

On the host, ask the authority for its health:

```bash
docker exec step-ca-step-ca \
  step ca health --ca-url https://127.0.0.1:9000
```

The command prints `ok`. It is the check the container runs on itself, so a container that shows `healthy` has passed it.

## Data worth keeping {#data}

| Path under `/opt/docker/volumes/step-ca` | Holds |
| --- | --- |
| `step-ca-data` | The whole authority: its config, its record of issued certificates, and its keys |
| `step-ca-secrets/password` | The password those keys are encrypted with |

Both are on the persistent disk, so they survive a rebuild of the VM.

After the first start the root key is in `step-ca-data/secrets`, beside the intermediate key. The host page takes it offline. The authority issues from the intermediate key alone.

## Not yet confirmed {#unconfirmed}

- Anything asking this authority for a certificate. The Traefik service in fleet-stacks defines no resolver for it, so every Traefik gets its certificates from Let's Encrypt. See [Certificates from Let's Encrypt](../concepts/bootstrap-mode.md#certificates).
- The SSH authority in use. It exists from the first start, and no host is set to trust it yet.
