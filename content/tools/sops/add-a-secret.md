# Adding a secret for the hosts

This page adds a new secret that a host's operating system reads, such as a password for a systemd service. You do it when a module in the fleet-nixos repo needs a value that must not be in the repo in the clear. A value a container reads is a Komodo Secret instead. See [Which store a secret belongs in](index.md#which-store).

Status: written, not yet run. See [Not yet confirmed](#unconfirmed).

The change is made in two repos. The value goes into a [sops file](index.md#sops-file) in the private repo, and a module in fleet-nixos declares the secret so that [sops-nix](index.md#sops-nix) decrypts it on the host. A deploy of each host carries both there.

To change the value of a secret that already exists, see [Changing a secret](../../fleet-bootstrap/concepts/secrets-with-sops.md#edit).

## Prerequisites

- The control shell, with checkouts of the private repo and of fleet-nixos, and the right to push to both. See [The control shell](../../fleet-bootstrap/foundation/control-shell.md#checkouts).
- The admin key or the deploy key in `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE`. See [Three kinds of key](../../fleet-bootstrap/concepts/secrets-with-sops.md#keys).
- The module that will read the secret, written or planned. Without one, the secret is never decrypted on a host.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<fleet-dir>` | Absolute path of the private repo's checkout, such as `$HOME/src/fleet-private` |
| `<flake>` | Path of the fleet-nixos checkout, such as `$HOME/src/fleet-nixos` |
| `<secret-name>` | The secret's name, in lower case with hyphens, as `komodo-onboarding-key` is |
| `<module>` | The file under `modules/` in fleet-nixos that uses the secret |
| `<host>` | A host that reads the secret |

## 1. Add the value {#value}

From the private repo, open the file every host reads:

```bash
cd <fleet-dir>
sops secrets/fleet.yaml
```

sops decrypts the file into your editor. Add a line with `<secret-name>` as the key and the secret as its value, beside the two entries already there, then save and close. sops encrypts the file again as it closes.

Check that the new entry decrypts:

```bash
sops decrypt --extract '["<secret-name>"]' secrets/fleet.yaml
```

The command prints the value you entered.

For a secret one host alone may read, use that host's own file. See [A secret for one host](#one-host).

## 2. Commit the file {#commit-value}

Commit the file and push it:

```bash
git -C <fleet-dir> add secrets/fleet.yaml
git -C <fleet-dir> commit -m "Add <secret-name>"
git -C <fleet-dir> push
```

`git diff` shows the new entry and a changed `mac` and `lastmodified`. The other entries are untouched.

The value goes in before the module does. A configuration that declares a secret the file lacks does not build.

## 3. Declare the secret {#declare}

In `<flake>/modules/<module>`, declare the secret, and give its path to whatever reads it:

```nix
sops.secrets.<secret-name> = { };
```

The path is `config.sops.secrets.<secret-name>.path`, which is `/run/secrets/<secret-name>` on the host. The file is owned by root and readable by root alone unless the declaration sets `owner`, `group`, or `mode`.

<details>
<summary>Background: how the modules that exist read their secrets</summary>

The two secrets a host reads today show the two usual shapes.

`modules/users.nix` hands a path to an option that wants a file. The account's password hash is read from the decrypted file when the accounts are made. In short form:

```nix
sops.secrets.server-password-hash.neededForUsers = true;
users.users.root.hashedPasswordFile = config.sops.secrets.server-password-hash.path;
```

`modules/komodo-periphery.nix` needs the secret as an environment variable, so it has sops-nix write a small file around it. The placeholder is replaced with the secret at activation, and the systemd service names the result as its `EnvironmentFile`:

```nix
sops.secrets.komodo-onboarding-key = { };
sops.templates."komodo-periphery.env" = {
  owner = "komodo";
  content = ''
    PERIPHERY_ONBOARDING_KEY=${config.sops.placeholder.komodo-onboarding-key}
  '';
};
```

Neither puts the secret in the configuration itself. Everything in a NixOS configuration ends up in the nix store, which every account on the host can read, so a module passes the path and never the value.

</details>

## 4. Check the flake {#check}

From `<flake>`, format the file and run the flake's checks against the private repo:

```bash
cd <flake>
nix fmt
nix flake check --override-input fleet git+file://<fleet-dir> --no-write-lock-file
```

The command ends without an error. Its `hosts` check builds every host's list of secrets against the sops file each one names, so a name that differs between the module and the file stops it here.

## 5. Commit the module {#commit-module}

Commit the module and push it:

```bash
git -C <flake> add modules/<module>
git -C <flake> commit -m "Read <secret-name> on the hosts"
git -C <flake> push
```

The run builds from the pushed `main` of fleet-nixos, so a module that is not pushed reaches no host through the run.

## 6. Run the hosts {#run}

Deploy each host that reads the secret, one run for each. See [Deploy to a host](../../fleet-bootstrap/procedures/update-the-fleet.md#deploy).

/// tab | Semaphore

In Semaphore, run the **site** Template with *Target* set to `<host>`.

///

/// tab | Command line

From `~/src/fleet-ansible`, in a shell prepared for runs after the handover. See [Running from a shell again](../../fleet-bootstrap/foundation/handover.md#shell-runs).

```bash
ansible-playbook -i ../fleet-private/hosts.yml site.yml \
  -e target=<host> \
  --tags nixos
```

///

The recap line for the host shows `failed=0` and `unreachable=0`.

On the host, check that the secret was decrypted:

```bash
sudo ls -l /run/secrets/<secret-name>
```

The listing shows the file with the owner and mode the declaration gave it.

## A secret for one host {#one-host}

A secret in `secrets/fleet.yaml` can be decrypted by every host. For one that only `<host>` may read, three things differ.

In [step 1](#value), edit the host's own file. Its [creation rule](index.md#creation-rules) was written by `new-host-key`, so the file is encrypted for the admin key, the deploy key, and that host:

```bash
cd <fleet-dir>
mkdir -p secrets/hosts
sops secrets/hosts/<host>.yaml
```

In [step 2](#commit-value), add `secrets/hosts/<host>.yaml` in place of `secrets/fleet.yaml`.

In [step 3](#declare), name the host's file in the declaration:

```nix
sops.secrets.<secret-name> = {
  sopsFile = config.fleet.hostSecretsFile;
};
```

`fleet.hostSecretsFile` is null on a host that has no file of its own. The modules are the same for every host, so put the declaration behind a condition that is true on `<host>` alone, such as one of the host's `features`.

## What's next

Nothing more is needed. The secret is decrypted again at every boot and every deploy, and a later change to its value reaches a host with the next deploy. See [Changing a secret](../../fleet-bootstrap/concepts/secrets-with-sops.md#edit).

## Not yet confirmed {#unconfirmed}

The steps follow from `modules/secrets.nix`, the two modules that declare a secret, and the flake's checks. None of them has been run.

- `nix flake check` with `--override-input fleet`, against a private repo. The checks pass against the example fleet inside fleet-nixos.
- The `hosts` check stopping on a secret that a module declares and the file lacks.
- A new secret appearing under `/run/secrets` on a host after a deploy.
- A declaration with `sopsFile = config.fleet.hostSecretsFile`. The option exists and no module uses it yet.
- Whether a service that reads the secret restarts by itself when the value changes. sops-nix has a `restartUnits` option for a declared secret, and no module in the flake sets it.
