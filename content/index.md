# Documentation, How-Tos, and Ramblings

Documentation that spans more than one repo, standalone how-tos, and the occasional post. Documentation that belongs to a single repo stays in that repo's README.

If the fleet's tools are new to you, start with [The fleet at a glance](fleet-bootstrap/concepts/the-fleet-at-a-glance.md).

| Section | What it covers |
| --- | --- |
| [Fleet bootstrap](fleet-bootstrap/index.md) | Building the self-hosted fleet from nothing: the order hosts come up in, the procedures they share, and each host's runbook |
| [Tools](tools/index.md) | A primer for each tool the fleet is built from, how-tos for common changes, and a glossary |
| [How-tos](how-tos/index.md) | Standalone guides that are not part of the fleet runbooks |
| [Standards](standards/index.md) | The Markdown style guide every repo here follows |
| [Ramblings](blog/index.md) | Posts |

## The repos

| Repo | Holds | Visibility |
| --- | --- | --- |
| [fleet-stacks](https://github.com/myah-mitchell/fleet-stacks) | Every container and stack definition, deployed through Komodo | Public |
| [fleet-ansible](https://github.com/myah-mitchell/fleet-ansible) | The run that builds a VM from nothing to running stacks, plus the roles that configure the Proxmox hosts | Public |
| [fleet-opentofu](https://github.com/myah-mitchell/fleet-opentofu) | The OpenTofu configuration that creates each VM, blank, with the installer ISO in its CD drive | Public |
| [fleet-nixos](https://github.com/myah-mitchell/fleet-nixos) | The flake that holds every VM's NixOS configuration, the installer ISO, and the commands that install and deploy a host | Public |
| fleet-private | The real inventory, the private values, and the encrypted secrets the public repos run against | Private |
| [docs](https://github.com/myah-mitchell/docs) | This site | Public |
