# technitium-server

technitium-server is Technitium, a DNS server with a web console. No host lists it. It was cut from the plan. See [Not in the plan](index.md#unused).

dockns, part of [system-agent](system-agent.md), writes the fleet's records straight into the network's own DNS on the UniFi gateway. With Technitium running beside it, hosts had two resolvers that disagreed.

The folder stays in the docker-stacks repo because the container definition still works. To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/technitium-server/services.md"

| Service | Does |
| --- | --- |
| `technitium` | Answers DNS queries, and serves the web console on port 5380 inside the `proxy` network |

The project is `technitium`, and the container is `technitium-technitium`.

The container publishes these ports on the host:

| Port | Used for |
| --- | --- |
| `53/tcp`, `53/udp` | DNS |
| `853/tcp` | DNS over TLS |
| `853/udp` | DNS over QUIC |
| `53443/tcp` | The web console over HTTPS, without Traefik |

Ports 53 and 853 are bound to one address of the host, the value of `TECHNITIUM_BIND_IP`.

## Values it reads {#values}

--8<-- "generated/technitium-server/values.md"

Two keys in the stack's file are blank and have to be set in the host's inventory entry, under `komodo_stack_env`. See [Stack values](../concepts/fleet-private.md#stack-values).

| Key | Value |
| --- | --- |
| `TECHNITIUM_NS_NAME` | The server's own name, without the domain, such as `ns1` |
| `TECHNITIUM_BIND_IP` | The host's address that DNS listens on, such as `192.0.2.16` |

## What the host needs {#host-setup}

--8<-- "generated/technitium-server/host-setup.md"

The stack also needs a Traefik on the same host, for the web console.

No rule covers ports 53, 853, or 53443. Add the ones you want reachable by hand. See [Not yet confirmed](#unconfirmed).

## Hostnames {#hostnames}

Traefik routes seven names to the web console. With the host `ap01`, the sub-domain `home.`, the domain `myah-mitchell.com`, and `ns1` as the server's name, they are:

| Hostname | Comes from |
| --- | --- |
| `ns1.myah-mitchell.com` | `TECHNITIUM_NS_NAME` on the domain |
| `ns1.home.myah-mitchell.com` | `TECHNITIUM_NS_NAME` on the sub-domain |
| `ns1.ap01.home.myah-mitchell.com` | `TECHNITIUM_NS_NAME` on the host |
| `dns.myah-mitchell.com` | `TECHNITIUM_SERVICE_NAME` on the domain |
| `dns.home.myah-mitchell.com` | `TECHNITIUM_SERVICE_NAME` on the sub-domain |
| `dns.ap01.home.myah-mitchell.com` | `TECHNITIUM_SERVICE_NAME` on the host |
| `technitium.ap01.home.myah-mitchell.com` | The project name on the host |

The route asks for a sign-in through Authentik, and uses no sign-in while the host is in bootstrap mode. The console has a login of its own in both.

## Verify {#verify}

In Komodo, the `technitium-server` Stack shows as running with one service.

On the host, list the project's containers:

```bash
docker compose -p technitium ps
```

The container shows `healthy` in the *STATUS* column. Its check resolves the fleet's domain through the server itself, so `healthy` means DNS is answering inside the container.

From another machine on the network, ask the server for a name:

```bash
dig @192.0.2.16 myah-mitchell.com
```

The answer's header shows `status: NOERROR`.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed since it was cut from the plan.
- The firewall. The stack's setup file holds no rule for the ports the container publishes, and the query from another machine has not been tried.
- A blank `TECHNITIUM_BIND_IP`. The port lines then start with a colon, and what Compose makes of that has not been tried.
