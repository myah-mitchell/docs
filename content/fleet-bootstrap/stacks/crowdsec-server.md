# crowdsec-server

crowdsec-server is CrowdSec with its local API turned on: it reads logs, decides which addresses to block, and answers the agents and bouncers that ask it. No host lists it. CrowdSec was cut from the plan. See [Not in the plan](index.md#unused).

Cloudflare handles the web application firewall, denial-of-service protection, and rate limiting for the one public hostname, and UniFi CyberSecure covers intrusion detection on the network. Alert rules against the data VictoriaMetrics already holds cover the rest without another service that is always on.

The folder stays in the docker-stacks repo because the container definition still works. To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/crowdsec-server/services.md"

| Service | Does |
| --- | --- |
| `crowdsec-server` | Runs the local API and a log processor in one container |
| `socket-proxy` | Gives CrowdSec a filtered, read-only view of the Docker socket, which it reads container logs through |

The project is `crowdsec`, and the containers are `crowdsec-crowdsec-server` and `crowdsec-socket-proxy`.

The container installs CrowdSec's collections for Traefik, HTTP attacks, and the application firewall rules when it starts. Addresses in the private ranges are on its allowlist, so a machine on a private network is never blocked.

The local API is published on port 8080 of the host.

## Values it reads {#values}

--8<-- "generated/crowdsec-server/values.md"

The values under [CrowdSec](../concepts/variables-and-secrets.md#crowdsec) and [Traefik](../concepts/variables-and-secrets.md#traefik) that mention CrowdSec belong to the stacks that talk to this one. No page stages a real value for them, because no host runs CrowdSec. The Traefik stacks get the literal `unused` as the CrowdSec host, and their bouncer stays off.

Turning it on means three things, none of which a page in this section does:

- An agent on another host needs `GLOBAL_CROWDSEC_LAPI_URL`, the address of this stack's API. See [crowdsec-agent](crowdsec-agent.md#values).
- Traefik's bouncer needs `GLOBAL_CROWDSEC_LAPI_HOST` set to the same host in place of `unused`.
- Each agent and each bouncer needs a credential made on this server, with `cscli` inside the container.

## What the host needs {#host-setup}

--8<-- "generated/crowdsec-server/host-setup.md"

The stack has no route, so it needs no Traefik on the host.

The stack's `setup.yaml` holds no `firewall` entry for port 8080, so the host's firewall has no rule for it. The host's configuration takes a stack's ports from those entries alone, so an agent or a bouncer on another host needs one added in docker-stacks before it can reach the API. See [Firewall](../concepts/host-layout.md#firewall).

## Verify {#verify}

On the host, list the project's containers:

```bash
docker compose -p crowdsec ps
```

Both containers show `healthy` in the *STATUS* column. The check only asks CrowdSec for its version, so it says the container is up and nothing about the API.

Ask the server which agents and bouncers it knows:

```bash
docker exec crowdsec-crowdsec-server cscli machines list
docker exec crowdsec-crowdsec-server cscli bouncers list
```

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- Port 8080 from another host. Docker publishes a port through rules of its own, and whether the host's rule is what limits a published port has not been tried.
- Where it reads Traefik's access log from. The container mounts a `traefik` folder under its own project's log folder, `/opt/docker/logs/crowdsec`. Traefik writes to `/opt/docker/logs/traefik/traefik`, so the file CrowdSec is told to read would be missing.
