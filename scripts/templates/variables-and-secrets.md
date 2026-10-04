# Variables and Secrets

Every [Komodo](../../tools/komodo/index.md) Variable and Secret the fleet's stacks read, what each one holds, and which stacks read it. Come here from a host page to see what a value is for, or before a deploy to check that nothing is missing.

This page is generated from the `komodo.env` files in fleet-stacks by `scripts/fleet_facts.py` in this repo. Change a description in `scripts/fleet-register.yaml` and run the script again. An edit made here is lost on the next run.

## How a stack gets its values {#how}

A container is configured through environment variables, and a [stack](../../tools/glossary.md#stack) collects the ones its containers read in one place. Each stack in fleet-stacks has a `komodo.env` file, which becomes the Stack's *Environment* in Komodo. A line in it takes its value one of three ways.

| The line reads | Where the value comes from |
| --- | --- |
| `KEY: [[NAME]]` | The Komodo Variable or Secret called `NAME`, filled in by Komodo at deploy time |
| `KEY: value` | fleet-stacks, the same on every host |
| `KEY:` | Nothing. The stack's own default applies, unless the inventory sets the key |

The [inventory](../../tools/glossary.md#inventory) can set any key for one host or for all of them, through `komodo_stack_env`. It also fills in `SERVER_NAME`, `SUB_DOMAIN_NAME`, `DOMAIN_NAME`, and `TRAEFIK_AUTH_CHAIN` by itself. See [The private repo](fleet-private.md#stack-values).

A Secret is a Variable created with **Is Secret** ticked. Komodo hides its value in the UI and in deploy logs. The two resolve the same way, so the *Kind* column below says only how to create each one.

<details>
<summary>Background: why a value is a reference and not written in the file</summary>

fleet-stacks is public, and `komodo.env` is a file in it. A password written there would be published.

A reference keeps the value out of every repo. The file says only that the stack wants the Variable called `NAME`, and the value is typed into Komodo once, where its database holds it. Komodo puts the value in place of the reference as it deploys, so it exists on the host and in Komodo and nowhere else.

A Variable also gives a value one home. A dozen stacks can reference `GLOBAL_PUID`, and changing it is one edit in Komodo followed by a redeploy of the stacks that read it.

</details>

> [!WARNING]
> A reference with nothing behind it reaches the container as the literal text `[[NAME]]`. Komodo does not stop the deploy, and the failure usually surfaces as a type error or a failed login. Create every value a stack reads before the run that deploys it.

## Creating one {#create}

1. In Komodo's UI, open *Settings > Variables* and click **New Variable**.
2. In *Name*, enter **the name** exactly as the table gives it.
3. In *Value*, enter **the value**.
4. Tick **Is Secret** when the table's *Kind* is Secret.
5. Click **Save**. The name appears in the list.

Make a secret in these stacks alphanumeric only: 48 characters for a database password, 96 for any other generated secret. Several stacks put a password straight into a connection URL, where a symbol breaks the URL.

## Blanking a reference {#blanking}

When a host does not use a value its stack references, set that key to blank in the inventory. The reference is then gone from that host's Stack, and no Variable has to exist for it:

```yaml
komodo_stack_env:
  authentik-server:
    AUTHENTIK_EMAIL__USERNAME: ""
    AUTHENTIK_EMAIL__PASSWORD: ""
```

Where a table below gives `unused` as the value, the stack reads the reference on every host and ignores what it holds. Create it with that value once, which costs less than blanking the key on every host.

A host's `komodo_stack_env` replaces a group's. Ansible does not merge the two, so a host that sets its own lists every stack and key it needs. See [The private repo](fleet-private.md#stack-values).

## What Komodo does not hold {#elsewhere}

Komodo holds the values a stack reads and nothing else. The secrets a host's own configuration reads, such as the hash of the account password and the Komodo onboarding key, are in files in the private repo that are encrypted with [sops](../../tools/sops/index.md), and so are the secrets Ansible reads. See [Secrets with sops](secrets-with-sops.md#files).

<!-- register -->
