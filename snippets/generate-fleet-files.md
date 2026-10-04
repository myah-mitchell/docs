From `~/src/fleet-ansible`, with the private repo and fleet-nixos checked out next to it, and the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`.

A host with no file under `secrets/host-keys/` in the private repo gets its SSH host keys first:

```bash
nix run ../fleet-nixos#new-host-key -- --fleet ../fleet-private <host>
```

The command writes `secrets/host-keys/<host>.yaml`, adds the host to `.sops.yaml`, and encrypts `secrets/fleet.yaml` again so that the host can read it. For a host that has its keys already, it changes nothing. See [Host keys](../concepts/secrets-with-sops.md#host-keys).

Then write the NixOS files and the Komodo files:

```bash
ansible-playbook -i ../fleet-private/hosts.yml nixos-sync.yml
ansible-playbook -i ../fleet-private/hosts.yml komodo-sync.yml
```

Add what changed, and read the diff before it is committed:

```bash
git -C ../fleet-private add hosts.yml group_vars/ opentofu/ komodo/ nixos/ secrets/ .sops.yaml
git -C ../fleet-private diff --cached
```

The diff of `nixos/hosts/<host>.json` shows the host's network, its features, and the folders, seed files and ports its stacks need. The diff of `komodo/stacks/<host>.toml` shows the Stacks the next run deploys and every value in their *Environment*. The files under `secrets/` are encrypted, so their diff shows that a value changed and not what it changed to.

Then commit and push:

```bash
git -C ../fleet-private commit -m "Describe <host>"
git -C ../fleet-private push
```

The run builds the host from the files git tracks in the private repo, and Komodo reads the pushed copy. The run stops at a host whose committed files differ from what the inventory gives.
