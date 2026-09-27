From the ansible checkout, with the private repo checked out next to it:

```bash
ansible-playbook -i ../fleet-private/hosts.yml komodo-sync.yml
git -C ../fleet-private diff komodo/
```

Read the diff. It shows the Stacks the next run deploys and every value in their *Environment*. Then commit and push:

```bash
git -C ../fleet-private add hosts.yml opentofu/ komodo/
git -C ../fleet-private commit -m "Describe <host>"
git -C ../fleet-private push
```

Komodo reads the pushed copy, and the run stops at a host whose committed file differs from what the inventory gives.
