# crowdsec-agent

crowdsec-agent is CrowdSec with its local API turned off: a log processor that reads one host's logs and reports to a CrowdSec server elsewhere. No host lists it. CrowdSec was cut from the plan, for the reasons on [crowdsec-server](crowdsec-server.md). See [Not in the plan](index.md#unused).

The folder stays in the docker-stacks repo because the container definition still works. To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/crowdsec-agent/services.md"

| Service | Does |
| --- | --- |
| `crowdsec-agent` | Reads the host's container logs and Traefik's access log, and sends what it finds to the server |
| `socket-proxy` | Gives the agent a filtered, read-only view of the Docker socket |

The project is `crowdsec`, and the containers are `crowdsec-crowdsec-agent` and `crowdsec-socket-proxy`.

crowdsec-server uses the same project and runs a log processor of its own. The host with the server on it does not take this stack as well.

## Values it reads {#values}

--8<-- "generated/crowdsec-agent/values.md"

`GLOBAL_CROWDSEC_LAPI_URL` is the one value in the register that no page stages. CrowdSec is not in the plan, so nothing in the fleet reads it, and the register lists it only because this stack's file still references it. See [CrowdSec](../concepts/variables-and-secrets.md#crowdsec).

A host that runs the agent needs two things that are not there by default:

| Value | Where it goes |
| --- | --- |
| `GLOBAL_CROWDSEC_LAPI_URL` | A Komodo Variable, holding the URL of the server's API on port 8080 |
| `CROWDSEC_AGENT_PASSWORD` | The host's `komodo_stack_env`, as a reference to a Komodo Secret of your own |

The second key is blank in the stack's file. The password is a secret, so the inventory holds a reference such as `"[[CROWDSEC_AGENT_PASSWORD]]"` and never the value. See [Stack values](../concepts/fleet-private.md#stack-values).

The agent signs in to the server under the name `crowdsec.`, the host, the sub-domain, and the domain, such as `crowdsec.ap01.home.myah-mitchell.com`. The server has to hold a machine of that name with the same password.

## What the host needs {#host-setup}

--8<-- "generated/crowdsec-agent/host-setup.md"

The stack has no route, so it needs no Traefik on the host. Every connection it makes is outbound, to the server.

## Verify {#verify}

On the host, list the project's containers:

```bash
docker compose -p crowdsec ps
```

Both containers show `healthy` in the *STATUS* column. The check only asks CrowdSec for its version, so it says the container is up and nothing about the link to the server.

Ask the agent whether it can reach the server:

```bash
docker exec crowdsec-crowdsec-agent cscli lapi status
```

The output includes `You can successfully interact with Local API (LAPI)`.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed since it was cut from the plan.
- Where it reads Traefik's access log from. See the same item on [crowdsec-server](crowdsec-server.md#unconfirmed).
