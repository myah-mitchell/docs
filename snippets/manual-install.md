### Install NixOS without the rest of the run

The run's second and third stages wait for the VM's SSH port, install NixOS when the VM answers as the installer, and deploy the host's configuration. The same three commands of the flake do it from a shell.

From `~/src/ansible`, with the host's files committed in the private repo, the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`, and the fleet's SSH key in the SSH agent. See [The fleet's SSH key](../foundation/control-shell.md#ssh-key).

Ask the VM what it runs:

```bash
nix run ../nixos-fleet#host-state -- <address>
```

It prints `installer` for a VM that booted the ISO. Then install:

```bash
nix run ../nixos-fleet#install-host -- --fleet ../fleet-private <host> <address>
```

> [!WARNING]
> The install wipes `scsi0` and `scsi1`. It formats `scsi2` only when the disk is blank, and it refuses any machine that is not the installer.

The last line reads `install-host: <host> is installed and is rebooting`. Repeat the `host-state` command until it prints `installed`, then deploy the configuration:

```bash
nix run ../nixos-fleet#deploy-host -- --fleet ../fleet-private <host> <address>
```

`<host>` is the host's name in the inventory, and `<address>` is its `ansible_host`. The configuration is the whole base build: accounts, SSH, the firewall, Docker, the persistent disk, Periphery, Node Exporter, and the folders, seed files and ports of every stack in the host's file. See [The commands](../concepts/nixos-flake.md#commands).
