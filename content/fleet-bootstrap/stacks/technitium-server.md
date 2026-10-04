# technitium-server

technitium-server is [Technitium](../../tools/technitium/index.md), a DNS server with a web console. No host lists it. It was cut from the plan. See [Not in the plan](index.md#unused).

dockns, part of [system-agent](system-agent.md), writes the fleet's records straight into the network's own DNS on the UniFi gateway. With Technitium running beside it, hosts had two resolvers that disagreed.

The folder stays in the fleet-stacks repo because the container definition still works. To run it on a host of your own, see [Applications (ap01)](../hosts/ap01-applications.md).

## What it runs {#services}

--8<-- "generated/technitium-server/services.md"

| Service | Does |
| --- | --- |
| `technitium` | Answers DNS queries, and serves the web console on port 5380 inside the `proxy` network |

The [project](../../tools/glossary.md#project) is `technitium`, and the container is `technitium-technitium`.

The container publishes one port on the host, port 53 for DNS, over both UDP and TCP. It is bound to one address of the host, the value of `TECHNITIUM_BIND_IP`.

The compose file holds three more port lines, each commented out because nothing listens behind it as the stack stands:

| Port | Used for | Take the comment off when |
| --- | --- | --- |
| `853/tcp` | DNS over TLS | The protocol is turned on in the console |
| `853/udp` | DNS over QUIC | The protocol is turned on in the console |
| `53443/tcp` | The web console over HTTPS, without Traefik | The console has a certificate |

The two lines for port 853 bind to `TECHNITIUM_BIND_IP` as well. The line for port 53443 names no address, so it publishes on every address of the host once it is on.

## Values it reads {#values}

--8<-- "generated/technitium-server/values.md"

Two keys in the stack's file are blank and have to be set in the host's inventory entry, under `komodo_stack_env`. See [Stack values](../concepts/fleet-private.md#stack-values).

| Key | Value |
| --- | --- |
| `TECHNITIUM_NS_NAME` | The server's own name, without the domain, such as `ns1` |
| `TECHNITIUM_BIND_IP` | The host's address that DNS listens on, such as `172.16.7.151` |

## What the host needs {#host-setup}

--8<-- "generated/technitium-server/host-setup.md"

The stack also needs a Traefik on the same host, for the web console.

The stack's `setup.yaml` holds no `firewall` entry for port 53, so the host's firewall has no rule for it. The host's configuration takes a stack's ports from those entries alone, so add one in fleet-stacks for port 53, and for any of the other three you turn on. See [Firewall](../concepts/host-layout.md#firewall) and [Not yet confirmed](#unconfirmed).

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

On the host, list the Stack's containers. Komodo names the Compose project after the Stack, not after `PROJECT_NAME`:

```bash
docker compose -p technitium-server ps
```

The container shows `healthy` in the *STATUS* column. Its check resolves the fleet's domain through the server itself, so `healthy` means DNS is answering inside the container.

From another machine on the network, ask the server for a name:

```bash
dig @172.16.7.151 myah-mitchell.com
```

The answer's header shows `status: NOERROR`.

## Not yet confirmed {#unconfirmed}

- The stack has not been deployed on any host.
- The firewall. The host has no rule for port 53, the one port the container publishes, and the query from another machine has not been tried. Docker publishes a port through rules of its own, and whether the host's rule is what limits a published port has not been tried.
- Turning on the console's HTTPS port, DNS over TLS, and DNS over QUIC. Their port lines are commented out in the compose file. The image's documentation has a variable for the console's HTTPS and none for the other two, and the console's settings for them have not been seen.
- A blank `TECHNITIUM_BIND_IP`. The port lines then start with a colon, and what Compose makes of that has not been tried.
