# dozzle-server

dozzle-server is Dozzle, a web interface for reading container logs live, across every VM in the fleet. No host lists it, because none has been chosen for it. See [Not in the plan](index.md#unused).

The fleet does not depend on it. Logs reach VictoriaLogs on ci01 through [system-agent](system-agent.md) whether Dozzle runs or not.

To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/dozzle-server/services.md"

| Service | Does |
| --- | --- |
| `dozzle-server` | Serves the web interface, on port 8080 inside the `proxy` network |
| `dozzle-agent` | Reads the logs of the host the server is on |
| `socket-proxy` | Gives the agent a filtered, read-only view of the Docker socket |

The agent and the socket proxy come from [dozzle-agent](dozzle-agent.md), which this stack includes. The server touches no Docker socket. It reads a host only through an agent named in `DOZZLE_REMOTE_AGENT`.

The project is `dozzle`, and the server's container is `dozzle-dozzle-server`.

## Values it reads {#values}

--8<-- "generated/dozzle-server/values.md"

One key in the stack's file is blank and has to be set for the server to show anything: `DOZZLE_REMOTE_AGENT`. It is the list of agents the server connects to, each as a host and port 7007, separated by commas. Set it in the host's inventory entry, under `komodo_stack_env`. See [Stack values](../concepts/fleet-private.md#stack-values).

## What the host needs {#host-setup}

--8<-- "generated/dozzle-server/host-setup.md"

The stack also needs a Traefik on the same host.

Its agent publishes port 7007, and so does the one in system-agent. Every VM in the plan runs system-agent, so the two collide on any of them. See [Not yet confirmed](#unconfirmed).

## Hostnames {#hostnames}

With the host `ap01`, the sub-domain `home.`, and the domain `myah-mitchell.com`, Traefik routes these names to the server:

| Hostname | Comes from |
| --- | --- |
| `dozzle.myah-mitchell.com` | `DOZZLE_HOSTNAME` on the domain |
| `dozzle.home.myah-mitchell.com` | `DOZZLE_HOSTNAME` on the sub-domain |
| `dozzle.ap01.home.myah-mitchell.com` | `DOZZLE_HOSTNAME` on the host |

A fourth name is the project on the host, which here is the same as the third.

The route asks for a sign-in through Authentik, and uses no sign-in while the host is in bootstrap mode. Anyone who can open it can read every container's logs, so take it out of bootstrap mode before relying on it. See [Bootstrap mode](../concepts/bootstrap-mode.md#effects).

## Verify {#verify}

In Komodo, the `dozzle-server` Stack shows as running with three services.

On the host, list the project's containers:

```bash
docker compose -p dozzle ps
```

Every container shows `healthy` in the *STATUS* column.

Open the interface at the host's name, such as `https://dozzle.ap01.home.myah-mitchell.com`. Each agent in `DOZZLE_REMOTE_AGENT` appears as a host in the list on the left.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed.
- How it shares a host with system-agent. Both publish port 7007, so the second one to start fails to bind it. The stack needs its own agent removed, or a host that does not run system-agent, before it can go on a VM in the plan.
