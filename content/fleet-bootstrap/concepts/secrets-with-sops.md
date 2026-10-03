# Secrets with sops

The secrets a host and the run need are files in the private repo, encrypted with sops so that they can be committed like any other file. This page explains which keys decrypt which file, how to change a secret, and what to do when a key is replaced or lost.

Status: written, not yet run. The commands were tried against a copy of the example fleet. See [Not yet confirmed](#unconfirmed).

sops holds only what a host's operating system and ansible need. A stack's values are Komodo Variables and Secrets. See [Variables and Secrets](variables-and-secrets.md).

## Placeholders {#placeholders}

| Placeholder | Value |
| --- | --- |
| `<flake>` | Path of a checkout of nixos-fleet, such as `$HOME/src/nixos-fleet` |
| `<fleet-dir>` | Absolute path of the private repo's checkout, such as `$HOME/src/fleet-private` |
| `<host>` | The host's name in the inventory |
| `<address>` | The host's IPv4 address |
| `<admin-public-key>`, `<deploy-public-key>` | The public halves of the admin key and the deploy key |
| `<id01-public-key>` | The age key `new-host-key` writes for a host, here id01 |
| `<onboarding-key>` | The key Komodo shows one time when you create it. See [the onboarding key](../foundation/komodo-setup.md#onboarding-key) |
| `<new-key-file>` | Where the new private key is written, outside every repo |
| `<new-public-key>` | The public key `age-keygen` prints for the new key. It starts with `age1` |

The commands on this page run on the control node, with `sops` and `age-keygen` from [the control shell's tools](../foundation/control-shell.md#tools). Each one that reads a secret needs `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE` set to a key that decrypts the file.

## Three kinds of key {#keys}

Every key is an age key pair. The public half is in `.sops.yaml` in the private repo, and the private half is what decrypts.

| Key | Whose | Private half is kept | Decrypts |
| --- | --- | --- | --- |
| `admin` | A person | In a password manager | Every file |
| `deploy` | The control node and Semaphore | In `SOPS_AGE_KEY` or `SOPS_AGE_KEY_FILE` | Every file |
| One per host | The host | Nowhere. It follows from the host's ed25519 SSH host key | `secrets/fleet.yaml` and the host's own file |

The admin key is for people and the deploy key is for automation, so either can be replaced without the other. See [The age keys](../foundation/control-shell.md#age-keys) for making the first two.

The deploy key decrypts every host's SSH host keys too, since an install from Semaphore puts them on the new host. That gives whoever holds it little more than they have already: the same run logs in to every host as root, and to the Proxmox host. Treat the deploy key, and Semaphore, as able to take over the whole fleet. To keep host keys from Semaphore, encrypt `secrets/host-keys/` to `admin` only and install hosts from the control shell.

> [!WARNING]
> Never commit a private age key, or a secrets file that sops has not encrypted. The repo being private makes neither one safe.

## The files {#files}

| File | Holds | Read by | Encrypted for |
| --- | --- | --- | --- |
| `secrets/fleet.yaml` | `server-password-hash` and `komodo-onboarding-key` | Every host | `admin`, `deploy`, every host |
| `secrets/hosts/<host>.yaml` | One host's own secrets. Optional | That host | `admin`, `deploy`, that host |
| `secrets/host-keys/<host>.yaml` | The host's SSH host keys, ed25519 and RSA | `install-host` and `deploy-host` | `admin`, `deploy` |
| `group_vars/all/secrets.sops.yaml` | `server_password`, for the Proxmox hosts | ansible, on the control node | `admin`, `deploy` |

`server-password-hash` is the password of root, the admin account, and the client account, stored as a hash. `komodo-onboarding-key` is what a new host's Periphery shows Komodo Core the first time. See [How a host joins Komodo](how-a-host-is-built.md#onboarding).

A host never reads `secrets/host-keys/`, its own file included. `install-host` decrypts the keys on the control node and writes them to the host's persistent disk.

`.sops.yaml` says who can decrypt what. It names each key one time under `keys`, and each rule lists the keys for the files its `path_regex` matches:

```yaml
keys:
  - &admin <admin-public-key>
  - &deploy <deploy-public-key>
  - &id01 <id01-public-key>

creation_rules:
  - path_regex: ^group_vars/all/secrets\.sops\.yaml$
    key_groups:
      - age: [*admin, *deploy]

  - path_regex: ^secrets/fleet\.yaml$
    key_groups:
      - age: [*admin, *deploy, *id01]

  - path_regex: ^secrets/hosts/id01\.yaml$
    key_groups:
      - age: [*admin, *deploy, *id01]

  - path_regex: ^secrets/host-keys/[^/]+\.yaml$
    key_groups:
      - age: [*admin, *deploy]
```

You write the first two keys and the rules that name no host. `new-host-key` writes every host's key and the rules that name it, so a host's entry is never written by hand.

Once `group_vars/all/secrets.sops.yaml` exists, ansible decrypts it whenever it loads the inventory. Every playbook run against the private repo then needs sops and a key, the two sync playbooks included.

## Changing a secret {#edit}

sops finds `.sops.yaml` from the folder it runs in, so run it from the private repo.

1. **Open** the file. sops decrypts it into your editor and encrypts it again when you save:

    ```bash
    cd <fleet-dir>
    sops secrets/fleet.yaml
    ```

    A file that does not exist yet is created, encrypted for the keys its rule names. Create the folder `secrets/hosts` first for a host's own file.

2. **Commit** the file and push.

3. **Run** every host that reads the file. A host decrypts its secrets when its configuration is activated, so a changed secret reaches it with the next deploy.

To set one value without an editor, or to read one back:

```bash
sops set secrets/fleet.yaml '["komodo-onboarding-key"]' '"<onboarding-key>"'
sops decrypt --extract '["komodo-onboarding-key"]' secrets/fleet.yaml
```

Make a value for `server-password-hash` with `mkpasswd`, which asks for the password and prints its hash:

```bash
nix shell nixpkgs#mkpasswd -c mkpasswd -m yescrypt
```

A changed `server-password-hash` replaces the password of all three accounts on every host it is deployed to. See [Accounts](host-layout.md#accounts).

## The host's SSH keys {#host-keys}

A host's SSH host keys are made on the control node before the host exists. The host's age key follows from its ed25519 key, so the fleet's secrets can be encrypted for a host that has never booted.

```bash
nix run <flake>#new-host-key -- --fleet <fleet-dir> <host>
```

```text
new-host-key: made secrets/host-keys/<host>.yaml
new-host-key: <host> is in .sops.yaml as age1...
new-host-key: encrypted secrets/fleet.yaml again, for the keys .sops.yaml names
```

| Step | Changes |
| --- | --- |
| Makes an ed25519 and an RSA key pair | `secrets/host-keys/<host>.yaml`, which is new |
| Adds the host's age key | `.sops.yaml`: the key, the rule for `secrets/fleet.yaml`, and a rule for the host's own file |
| Encrypts again, for the keys the rules name | `secrets/fleet.yaml`, and `secrets/hosts/<host>.yaml` when there is one |

Commit all of it. Run the command one time per host, as part of describing the host. See [Adding a host](../procedures/add-a-host.md#host-key).

A second run for the same host keeps its keys and changes nothing. The command changes nothing either when the key in your environment cannot decrypt the files it would encrypt again.

The keys reach the host at install, on its persistent disk, and sshd reads them from there. `deploy-host` checks every host against the ed25519 key in this file, and refuses a machine that answers with another. A host that is rebuilt answers with the same keys, so nothing that knows the host has to forget it.

## Replacing a key {#new-key}

### The admin key or the deploy key

Use these steps when a person joins or leaves, or when a key may have been read by someone else. They need a key that still decrypts every file.

1. **Make** the new key. The command prints the public half:

    ```bash
    age-keygen -o <new-key-file>
    ```

2. **Replace** the key's value under `keys` in `<fleet-dir>/.sops.yaml` with `<new-public-key>`. To add a second person, add a key with a name of its own, and add that name to every rule.

3. **Encrypt** every file again for the keys the rules name. `updatekeys` changes who can read the file's data key, and `rotate` replaces that data key, so an old key that once read it reads nothing written from now on:

    ```bash
    cd <fleet-dir>
    for file in group_vars/all/secrets.sops.yaml secrets/fleet.yaml secrets/hosts/*.yaml secrets/host-keys/*.yaml; do
      if [ -f "$file" ]; then sops updatekeys --yes "$file" && sops rotate --in-place "$file"; fi
    done
    ```

4. **Check** that the new key decrypts, then commit and push:

    ```bash
    SOPS_AGE_KEY_FILE=<new-key-file> sops decrypt --extract '["server-password-hash"]' secrets/fleet.yaml
    ```

5. **Put** a new deploy key where the run reads it: the control shell's environment, and `SOPS_AGE_KEY` in Semaphore's Variable Group. See [The age keys](../foundation/control-shell.md#age-keys) and [The Semaphore project](../foundation/semaphore-project.md#nix).

No host needs a deploy for this. A host decrypts with its own key, which has not changed.

> [!WARNING]
> The old key still decrypts every earlier commit of these files. When a key may have been read by someone else, replace the key and then change each secret it could read.

### A host's key

A host's keys are replaced by making new ones and installing the host again, since the install is what writes them to the host.

1. **Delete** `secrets/host-keys/<host>.yaml` in the private repo.
2. **Run** `new-host-key` for the host, as in [The host's SSH keys](#host-keys). It makes new keys, replaces the host's age key in `.sops.yaml`, and encrypts the host's files again.
3. **Commit** and push.
4. **Rebuild** the host. See [Rebuilding a VM](../procedures/rebuild-a-vm.md#reset).

Your own machine remembers the host's old key, and SSH warns you about the new one. Remove the old entry with `ssh-keygen -R <address>`.

## A lost key {#lost-key}

What you can still do depends on which keys are left.

| Lost | What still decrypts | Recover by |
| --- | --- | --- |
| The admin key | The deploy key | [Replacing the admin key](#new-key), with the deploy key in your environment |
| The deploy key | The admin key | [Replacing the deploy key](#new-key), with the admin key in your environment |
| A host's persistent disk, and the keys on it | The admin and deploy keys | Installing the host again. Its keys are in `secrets/host-keys/<host>.yaml` and the install writes them to the new disk |
| The admin key and the deploy key | Nothing a person holds | Starting the secrets over, below |

With both keys gone, nobody can read the files or encrypt them for a new key. The running hosts keep working, since each holds its own key, and none can be deployed to or installed. Start over:

1. **Make** a new admin key and a new deploy key, and put their public halves in `.sops.yaml`.
2. **Delete** the files under `secrets/` and `group_vars/all/secrets.sops.yaml`, and remove every host's key and rules from `.sops.yaml`.
3. **Write** `secrets/fleet.yaml` and `group_vars/all/secrets.sops.yaml` again, with a new password hash and a new onboarding key from Komodo. See [The first secrets](../foundation/control-shell.md#secrets).
4. **Run** `new-host-key` for every host. See [The host's SSH keys](#host-keys).
5. **Commit**, and rebuild each host in turn. The installer ISO holds no secret and needs no change.

Keep the admin key in a password manager, apart from anything that holds the deploy key, so that losing both takes two separate accidents.

## Not yet confirmed {#unconfirmed}

Tried with sops 3.13.3 against a copy of the example fleet: editing and setting a value, `new-host-key` for a new host and for a host whose keys were deleted, replacing the admin key with `sops updatekeys`, and the old key failing afterwards. `sops rotate` was tried on every file of the example fleet, which still decrypted afterwards. No host was involved.

- A host decrypting `secrets/fleet.yaml` at activation with the key on its persistent disk.
- A changed `server-password-hash` taking effect on a host at the next deploy.
- A host whose keys were replaced, after its rebuild: that `deploy-host` accepts it and that Periphery reconnects as the same Server.
- ansible decrypting `group_vars/all/secrets.sops.yaml` from Semaphore, with the key in the Variable Group.
- Starting the secrets over after losing both keys. The steps follow from how the files are made, and nobody has followed them.
