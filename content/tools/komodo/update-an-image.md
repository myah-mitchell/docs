# Updating a container image

This page moves one container to another version of its image. The version is a tag in the fleet-stacks repo, so the change is a commit there, followed by a deploy of each Stack that runs the container. Do it when an image has a release you want, or when Renovate has opened a pull request for one.

Status: written, not yet run.

The host's own software is not part of this. That includes Periphery, whose version is pinned in the fleet-nixos repo. See [Updating the fleet](../../fleet-bootstrap/procedures/update-the-fleet.md).

## Prerequisites

- A checkout of fleet-stacks that you can push to, or the right to merge a pull request in it.
- A login to Komodo that can deploy a [Stack](index.md#stack).
- The image's release notes read, for anything a new version asks of its data or its settings.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<container>` | The container's folder under `containers/`, such as `grafana` |
| `<host>` | A host that runs a stack with the container, such as `ci01` |

## How a version is pinned {#pins}

Each container's image and tag are one `image:` line in `containers/<container>/compose.yaml`. A stack's own compose file only extends that service, so every stack that uses the container gets the same version from the same line.

| Kind of tag | Example | What it follows |
| --- | --- | --- |
| A full version | `grafana/grafana:12.3.1` | That release and no other |
| A major version | `ghcr.io/moghtech/komodo-core:2` | The newest release of that major version, at the time the image is pulled |
| `latest` | `traefik:latest` | Whatever is newest at the time the image is pulled |

Only the first kind is a pin. A host keeps the image it pulled for the other two until something pulls again, so two hosts can run different versions under one tag.

List every container's tag, from the root of the checkout:

```bash
grep -h 'image:' containers/*/compose.yaml
```

## What Renovate does {#renovate}

Renovate is a bot that reads a repo for version numbers, checks each against its registry, and opens a pull request when a newer one exists. `renovate.json` in fleet-stacks configures it.

| Setting | Effect |
| --- | --- |
| The `docker-compose` file match | Renovate reads the `image:` lines in every `compose.yaml` under `containers/` and `stacks/` |
| `schedule` | Pull requests are opened before 6am on Monday, Chicago time |
| `prConcurrentLimit` | At most five are open at one time |
| The rule for major updates | A new major version waits for a tick in the repo's *Dependency Dashboard* issue before its pull request is opened |
| `labels` | Each pull request is labelled `dependencies`, and a major one `major-version` as well |

Renovate changes the repo and nothing else. A merged pull request is a new tag on `main`, which no host runs until its Stack is deployed. A `latest` tag has no version for Renovate to raise, so those containers get no pull requests.

The file also has a rule for keys that end in `_VERSION` in a `komodo.env`. No container uses one today.

## 1. Change the tag {#tag}

If Renovate opened a pull request for the image, read the release notes it links, check that the lint workflow passed, and merge it. Then skip to [step 3](#stacks).

Otherwise, edit the `image:` line in `containers/<container>/compose.yaml`:

```yaml
    image: grafana/grafana:12.3.1
```

## 2. Check, commit, and push {#push}

From the root of the checkout:

```bash
python3 scripts/build.py
git status --short
```

The status shows the one compose file you changed. A tag is in no generated file, so `build.py` writes nothing new.

```bash
git add containers/<container>/compose.yaml
git commit -m "Update <container>"
git push
```

The repo's lint workflow checks that every stack's compose file is still valid.

## 3. Find the Stacks that run it {#stacks}

From the root of the checkout:

```bash
grep -l 'containers:.*"<container>"' stacks/*/setup.yaml
```

Each file named is a stack that runs the container, through its own compose file or one it includes. The host that lists that stack in its `docker_stacks` runs it, and the Stack in Komodo has the stack's name. A stack every host runs has one Stack per host, such as `system-agent-<host>`. See [Stack](index.md#stack).

## 4. Deploy each Stack {#deploy}

1. In Komodo's UI, open *Resources > Stacks* and open the Stack.
2. Click **Deploy**, and watch the deploy log. The Stack shows as *Running* when the deploy finishes.

Repeat for each Stack from [step 3](#stacks). For a container every host runs, deploy one host's Stack first and check it before the rest.

Periphery pulls the repo, so the new tag reaches the host, and Compose replaces the one container whose image changed. See [Deploy](index.md#deploy).

> [!WARNING]
> Deploying `komodo-server` replaces Core's own container. The UI drops for up to a minute. Take a copy of the newest dump in `/opt/docker/volumes/komodo/postgres-backup-data` on km01 before a new version of Core.

<details>
<summary>Background: why the run is not the way to redeploy</summary>

The run's last stage has Komodo's [Resource Sync](index.md#resource-sync) deploy a Stack that is not running or whose definition changed. The definition is the host's TOML file in the private repo, which holds the repo, the branch, and the *Environment*. A new image tag changes none of them, so the sync may see nothing to do.

The comment in `renovate.json` says the sync redeploys after a merge. Whether Komodo counts a new commit in the Stack's repo as a change has not been checked, and the fleet's sync has no webhook that would run it on a push. Until that is settled, the **Deploy** button is the step that is known to fetch the repo.

</details>

## 5. Verify {#verify}

On the host:

```bash
docker ps --format '{{.Names}}  {{.Image}}  {{.Status}}'
```

The container's line shows the new tag, and its status says `healthy` once its health check has passed. A container with no health check shows `Up` and nothing more.

The stack's own page says how to check the service itself. See [Stacks](../../fleet-bootstrap/stacks/index.md).

## Going back {#rollback}

Set the `image:` line back to the old tag, or revert the commit, then push and repeat [step 4](#deploy). The container starts again from the old image.

A service that changed its data on the way up may not start on the old version. That is what the release notes and the backup are for.

## What's next

A page that states a version, such as the image tags on [semaphore-server](../../fleet-bootstrap/stacks/semaphore-server.md), needs the new one.

## Not yet confirmed {#unconfirmed}

- The whole page. No image has been updated on a running fleet.
- Whether Renovate is installed on the fleet-stacks repo on GitHub. The repo holds its configuration, which does nothing until the Renovate app is given access to the repo.
- Whether a run of `site.yml` redeploys a Stack after a commit that changes only an image tag. See the background block in [step 4](#deploy).
- Whether **Deploy** pulls a newer image for a tag that did not change, such as `latest` or `2`. If it does not, those containers move only when the image is pulled on the host by hand.
- The labels *Resources > Stacks*, **Deploy**, and *Running*. They are the ones the build guide uses, and have not been checked against the version of Komodo the fleet runs.
- The location and contents of the dump named in the warning in [step 4](#deploy), on a km01 that has run for a day.
