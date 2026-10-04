# dozzle-server

dozzle-server is Dozzle, a web interface for reading container logs live, across every VM in the fleet. No host lists it, because none has been chosen for it. See [Not in the plan](index.md#unused).

The fleet does not depend on it. Logs reach VictoriaLogs on ci01 through [system-agent](system-agent.md) whether Dozzle runs or not.

To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/dozzle-server/services.md"

| Service | Does |
| --- | --- |
| `dozzle-server` | Serves the web interface, on port 8080 inside the `proxy` network |

The server touches no Docker socket and runs no agent of its own. It reads a host, its own included, only through an agent named in `DOZZLE_REMOTE_AGENT`. Every VM runs that agent as part of [system-agent](system-agent.md).

The [project](../../tools/glossary.md#project) is `dozzle`, and the server's container is `dozzle-dozzle-server`.

## Values it reads {#values}

--8<-- "generated/dozzle-server/values.md"

One key in the stack's file is blank and has to be set for the server to show anything: `DOZZLE_REMOTE_AGENT`. It is the list of agents the server connects to, each as a host and port 7007, separated by commas. Set it in the host's inventory entry, under `komodo_stack_env`. See [Stack values](../concepts/fleet-private.md#stack-values).

## What the host needs {#host-setup}

--8<-- "generated/dozzle-server/host-setup.md"

The stack also needs a Traefik on the same host.

Each agent's port 7007 is open to the internal subnet, as part of system-agent's host setup, so the server reaches any agent on that subnet.

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

In Komodo, the `dozzle-server` Stack shows as running with one service.

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p dozzle-server ps
```

The container shows `healthy` in the *STATUS* column.

Open the interface at the host's name, such as `https://dozzle.ap01.home.myah-mitchell.com`. Each agent in `DOZZLE_REMOTE_AGENT` appears as a host in the list on the left.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed.
- Whether the server starts with `DOZZLE_REMOTE_AGENT` blank. It has no Docker socket to fall back on.
- Reading its own host. The server reaches the agent on its own host at the host's address and port 7007, from inside a Docker network. The host opens the port to the internal subnet, and whether that admits traffic from a Docker network has not been tried.
- An agent on the DMZ. A host opens port 7007 to the internal subnet only, so a server on the internal network may not reach bh01 or mx01.
