# Documentation, How-Tos, and Ramblings

Documentation that spans more than one repo, standalone how-tos, and the occasional post. Documentation that belongs to a single repo stays in that repo's README.

| Section | What it covers |
| --- | --- |
| [Fleet bootstrap](fleet-bootstrap/index.md) | Building the self-hosted fleet from nothing: the order hosts come up in, the procedures they share, and each host's runbook |
| [How-tos](how-tos/index.md) | Standalone guides that are not part of the fleet runbooks |
| [Standards](standards/index.md) | The Markdown style guide every repo here follows |
| [Ramblings](blog/index.md) | Posts |

## The repos

| Repo | Holds | Visibility |
| --- | --- | --- |
| [docker-stacks](https://github.com/myah-mitchell/docker-stacks) | Every container and stack definition, deployed through Komodo | Public |
| [ansible](https://github.com/myah-mitchell/ansible) | The run that builds a VM from nothing to running stacks, plus the roles that configure the Proxmox hosts | Public |
| [opentofu](https://github.com/myah-mitchell/opentofu) | The OpenTofu configuration that creates each VM, blank, with the installer ISO in its CD drive | Public |
| [nixos-fleet](https://github.com/myah-mitchell/nixos-fleet) | The flake that holds every VM's NixOS configuration, the installer ISO, and the commands that install and deploy a host | Public |
| fleet-private | The real inventory, the private values, and the encrypted secrets the public repos run against | Private |
| [docs](https://github.com/myah-mitchell/docs) | This site | Public |
