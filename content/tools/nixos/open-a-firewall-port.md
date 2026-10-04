# Opening a firewall port

This page opens a port in a host's firewall. A port is open because the host's configuration lists it, so the change is made in a repo and carried to the host by a run. Use it when a container starts listening on a port of its host, or when a host outside the internal network needs to reach one port that is closed to it.

Status: written, not yet run.

No command on the host opens a port for good. A rule added with `iptables` is gone after the next deploy or restart. See [The firewall](../../fleet-bootstrap/concepts/host-layout.md#firewall) for the rules every host starts with.

## Prerequisites

- The control shell, with fleet-ansible, fleet-nixos, fleet-stacks, and the private repo checked out next to each other under `~/src`. See [The control shell](../../fleet-bootstrap/foundation/control-shell.md).
- The right to push to the fleet-stacks repo the fleet uses, for a new port. See [Get a repo you can push to](../../fleet-bootstrap/hosts/ap01-applications.md#fork).
- The host is built, healthy, and has `FIREWALL: true` in the inventory.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<host>` | The host's name in the inventory, such as `tf01` |
| `<address>` | The host's address, `ansible_host` in the inventory |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
| `<container>` | The container's folder under `containers/` in fleet-stacks, such as `mailrise` |
| `<port>` | The port number |

## 1. Choose the case {#case}

| You want | Do |
| --- | --- |
| A port that a container publishes on its host, and that no rule lists yet | [Step 2](#stack-port), then steps 4 to 6 |
| An address outside the internal subnet to reach a port that is open to the internal subnet only | [Step 3](#port-sources), then steps 4 to 6 |
| A port for a service of the host itself, not a container | A module in fleet-nixos that sets `networking.firewall.allowedTCPPorts`. See [Adding a module to the flake](add-a-module.md) |

A service reached through Traefik needs no port of its own. Traefik's ports 80 and 443 are already open on every host that runs it, and Traefik reaches the container over the Docker network.

<details>
<summary>Background: where a host's rules come from</summary>

Each container in fleet-stacks declares the ports it needs in its `setup.yaml`. The script `build.py` rolls those up into each stack's own `setup.yaml`, and `nixos-sync.yml` copies the entries of every stack a host runs into the host's file, `nixos/hosts/<host>.json`. The flake's stacks module turns each entry into a firewall rule. The module names no stack and no port itself.

An entry marked `any` is open to every address. An entry marked `internal` is open to `docker_stacks_internal_subnet` and to nothing else. Docker hands a published port straight to its container, past the host's own firewall chain, so the module also closes each `internal` port to outside addresses in Docker's `DOCKER-USER` chain. See [Modules and options](index.md#modules).

</details>

## 2. Declare a container's port {#stack-port}

If the port is already listed for the stack and only the allowed addresses are wrong, skip to [step 3](#port-sources).

In `~/src/fleet-stacks`, add the port under `firewall` in `containers/<container>/setup.yaml`. This is the entry the mailrise container declares for its SMTP port:

```yaml
firewall:
  - port: 8025
    proto: tcp
    allow_from: internal
    comment: Mailrise SMTP
```

| Key | Holds |
| --- | --- |
| `port` | The port on the host, as the container's `compose.yaml` publishes it |
| `proto` | `tcp` or `udp`. A port used with both gets two entries |
| `allow_from` | `internal` for the internal subnet only, or `any` for every address |
| `comment` | What listens on the port. It travels with the rule into the host's file |

Use `internal` unless the port has to be reached from outside the fleet's internal network. The entry opens the firewall and does nothing else: the container's `compose.yaml` still has to publish the port under `ports`.

Generate the stacks' files, then commit and push:

```bash
python3 scripts/build.py
git add containers/ stacks/
git commit -m "Open <port> for <container>"
git push
```

The output of `build.py` ends with `Build complete.` The commit holds your edit and the regenerated `setup.yaml` and `README.md` of every stack that uses the container. `nixos-sync.yml` reads fleet-stacks from the pushed `main`, so a change that is not pushed reaches no host.

## 3. Admit another address to an internal port {#port-sources}

If every address that needs the port is inside `docker_stacks_internal_subnet`, skip to [step 4](#generate).

In `~/src/fleet-private/hosts.yml`, add `docker_stacks_port_sources` to the host that owns the port. This example lets bh01, in the DMZ, reach Redis on tf01:

```yaml
    tf01:
      ansible_host: 172.16.7.111
      serverHostname: "tf01"
      docker_stacks_port_sources:
        - port: 6379
          proto: tcp
          sources: ["172.16.8.111/32"]
```

Each entry names one port and protocol that a stack on the host opens as `internal`, and the IPv4 addresses or subnets that may also connect. Every other internal port stays closed to those addresses. An entry that matches no such port stops the build with a message naming the port, so a typo does not pass unnoticed.

[Admit the DMZ on tf01](../../fleet-bootstrap/hosts/bh01-dmz-edge.md#boundary-tf01) is this step as the build guide runs it.

## 4. Generate the host's file {#generate}

From `~/src/fleet-ansible`:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
git -C ../fleet-private add hosts.yml nixos/
git -C ../fleet-private diff --cached
```

The diff of `nixos/hosts/<host>.json` shows the new entry under `stacks.firewall`, or under `portSources`. A new port shows in the file of every host that runs the stack.

Check what the host's firewall will hold before anything reaches the host. From `~/src/fleet-nixos`:

```bash
nix eval --json .#nixosConfigurations.<host>.config.fleet.stacks.firewall \
  --override-input fleet git+file://$HOME/src/fleet-private \
  --no-write-lock-file
```

The output lists every port of the host's stacks, the new one among them. Then commit and push, from `~/src/fleet-ansible`:

```bash
git -C ../fleet-private commit -m "Open <port> on <host>"
git -C ../fleet-private push
```

## 5. Run the host {#run}

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to the host's name.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host>
```

///

The run ends with `failed=0` and `unreachable=0` for the host. Its NixOS stage switches the host to a system with the new rule, and its last stage redeploys the Stack if the stack's files changed. Run every host whose file changed in step 4, one per run.

## 6. Verify the rule {#verify}

Log in to the host and read the rules for the port:

```bash
ssh <admin>@<address>
```

```bash
sudo iptables -S nixos-fw | grep -E -e '--dport <port> '
sudo iptables -S DOCKER-USER | grep -E -e '--ctorigdstport <port> '
```

| The port is | `nixos-fw` shows | `DOCKER-USER` shows |
| --- | --- | --- |
| `any` | One line that ends in `-j nixos-fw-accept` | Nothing |
| `internal` | One line for the internal subnet that ends in `-j nixos-fw-accept` | One line that ends in `-j DROP` for every address outside the subnet |
| `internal`, with more sources | One more accept line for each source | One line that ends in `-j RETURN` for each source, above the drop |

Then connect to the port from a machine that should reach it, and from one that should not.

## What's next

To close a port again, remove its entry and follow the same steps. The next deploy builds the firewall without the rule.

## Not yet confirmed {#unconfirmed}

The entries, the generated file, and the rules the module writes were read from fleet-stacks, fleet-ansible, and the flake's `modules/stacks.nix`. No rule has been loaded on a host.

- The rules on a host as `iptables -S` prints them, for each of the three cases in step 6. A port marked `any` goes through NixOS's `allowedTCPPorts` or `allowedUDPPorts`, and its line is expected to accept from every address.
- That a switch reloads the firewall with the new rule and leaves established connections alone.
- That the run's last stage redeploys a Stack whose compose file changed in the same push.
- A module that opens a port for a service of the host itself. No module in the flake does so through `allowedTCPPorts` today, apart from the stacks module.
