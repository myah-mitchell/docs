# dozzle-agent

dozzle-agent is the part of Dozzle that reads a host's container logs and serves them to a Dozzle server elsewhere. No host lists it, and no stack includes it. See [Not in the plan](index.md#unused).

Every VM already runs the same agent inside [system-agent](system-agent.md), so a host in the plan never needs this stack.

To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/dozzle-agent/services.md"

| Service | Does |
| --- | --- |
| `dozzle-agent` | Serves the host's container logs to a Dozzle server, on port 7007 |
| `socket-proxy` | Gives the agent a filtered, read-only view of the Docker socket |

The project is `dozzle`, and the containers are `dozzle-dozzle-agent` and `dozzle-socket-proxy`.

The agent keeps nothing on disk.

## Values it reads {#values}

--8<-- "generated/dozzle-agent/values.md"

## What the host needs {#host-setup}

--8<-- "generated/dozzle-agent/host-setup.md"

The stack has no route, so it needs no Traefik on the host.

The agent in system-agent publishes port 7007 as well. A host runs one or the other.

## Verify {#verify}

On the host, list the project's containers:

```bash
docker compose -p dozzle ps
```

Both containers show `healthy` in the *STATUS* column.

The agent has no interface of its own. Its logs appear in a Dozzle server that names the host as a remote agent. See [dozzle-server](dozzle-server.md#values).
