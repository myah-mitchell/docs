### Provision it without the rest of the run

The run's second and third stages wait for the first boot, then run `provision.yml` against the host. That playbook is the whole base build: packages, users, SSH, the firewall, Docker, the persistent disk, Periphery, and Node Exporter. It has no by-hand equivalent short of reading the roles, so the manual path runs it alone.

From the ansible checkout, once the VM answers over SSH:

```bash
ansible-playbook -i ../fleet-private/hosts.yml provision.yml \
  -e target=<host> \
  -e komodo_onboarding_key=<onboarding-key>
```

`<onboarding-key>` is the key from [Setting up Komodo](../foundation/komodo-setup.md#onboarding-key). A host that was onboarded before needs none.

The `stacks` tag of the same playbook prepares the host for its stacks. The commands below do that part by hand.
