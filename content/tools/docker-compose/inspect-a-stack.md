# Looking inside a stack on a host

This page signs you in to a host and reads what one of its stacks is doing: its containers, their health, their logs, and its files on disk. Use it when Komodo shows a Stack as unhealthy or down and you want the detail, or when a stack's page sends you to the host to check something. Every command here reads and none changes anything.

Status: written, not yet run. See [Not yet confirmed](#unconfirmed).

The terms are explained in the [Docker Compose primer](index.md#ideas).

## Prerequisites

- The host is built and answers on SSH.
- Your SSH key is one of the keys in `admin_ssh_public_keys`. See [Accounts](../../fleet-bootstrap/concepts/host-layout.md#accounts).

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<admin>` | The admin account, `abbr_name` followed by `admin`, such as `mmadmin` |
| `<address>` | The host's `ansible_host` in `hosts.yml`, such as `172.16.7.111` for tf01 |
| `<stack>` | The Compose project's name, from the list in [Find the project](#find), such as `traefik-agent-id01` |
| `<service>` | A service's name, from the *SERVICE* column in [List its containers](#ps), such as `traefik` |
| `<container>` | A container's name, from the *NAME* column in [List its containers](#ps), such as `traefik-traefik` |
| `<project>` | The stack's `PROJECT_NAME`, which is the first part of every container name, such as `traefik` |

## 1. Sign in to the host {#sign-in}

```bash
ssh <admin>@<address>
```

Sign in as the admin account and not as `ansible`, which is the account the run uses. The admin is in the `docker` group, so the commands below need no `sudo`.

## 2. Find the project {#find}

List every Compose project on the host:

```bash
docker compose ls
```

Each line is one project, with its status and the compose file it was started from:

```text
NAME                 STATUS       CONFIG FILES
system-agent-id01    running(7)   /opt/docker/stacks/system-agent-id01/stacks/system-agent/compose.yaml
```

The name is the name of the Stack in Komodo. It is not the stack's `PROJECT_NAME`, which names the containers and folders. See [Two names for one stack](index.md#two-names).

The number after `running` counts the containers that are up. A status such as `running(6), restarting(1)` or `exited(2)` says which stack to look at.

## 3. List its containers {#ps}

```bash
docker compose -p <stack> ps -a
```

`-a` includes containers that have stopped, which the command otherwise leaves out. The columns to read are *NAME*, *SERVICE*, *STATUS*, and *PORTS*.

| *STATUS* reads | Means |
| --- | --- |
| `Up 2 hours (healthy)` | Running, and its health check passes |
| `Up 2 hours` | Running. The service has no health check |
| `Up 20 seconds (health: starting)` | Running, and no check has passed yet |
| `Up 2 hours (unhealthy)` | Running, and its health check keeps failing |
| `Restarting (1) 5 seconds ago` | The program exits at start, and Docker keeps starting it again. The number in parentheses is its exit code |
| `Exited (0) 2 hours ago` | Stopped. An exit code of `0` is a container that finished its job, and any other is a failure |

Compare the list with the services on the stack's page, under [Stacks](../../fleet-bootstrap/stacks/index.md). A service that is missing from the list was never created, which usually means a service it depends on is not healthy.

## 4. Read a health status {#health}

The *STATUS* column gives the verdict. For the reason, ask Docker for the container's health record:

```bash
docker inspect --format '{{json .State.Health}}' <container>
```

The output is one line of JSON. `Status` is `starting`, `healthy`, or `unhealthy`, `FailingStreak` is the number of failures in a row, and `Log` holds the last few runs of the check, each with its `ExitCode` and what the check command printed in `Output`.

An exit code of `0` is a pass. The text in `Output` is the check's own error, such as a refused connection, and is often all you need.

Docker does not restart an unhealthy container. It stays up and unhealthy until its program recovers or something redeploys it. See [Health checks](index.md#health-checks).

## 5. Read the logs {#logs}

Show the last 50 lines one service printed:

```bash
docker compose -p <stack> logs --tail 50 <service>
```

Leave out `<service>` for every service in the stack, with each line marked by its container. Add `-f` to follow new lines as they arrive, and press Ctrl+C to stop following. That stops the command and not the container.

For a container in a restart loop, read the lines from just before each exit:

```bash
docker logs --tail 50 <container>
```

Some programs also write log files. Those are on the host under `/opt/docker/logs/<project>`, in a folder for each container that has any:

```bash
ls /opt/docker/logs/<project>
```

## 6. Look inside a container {#exec}

Run one command in a running container:

```bash
docker compose -p <stack> exec <service> env
```

`env` prints the environment the program was started with, which is the way to confirm that a value from Komodo arrived. A value that reads `[[NAME]]` is a reference to a Variable or Secret that does not exist. See [How a stack gets its values](../../fleet-bootstrap/concepts/variables-and-secrets.md#how).

The output can include passwords. Do not paste it anywhere.

For a shell, replace `env` with `sh`. Not every image has one: an image that holds a single program, as Dozzle's does, has no shell and no `env`, and the command fails with a message that the executable was not found. Anything you change in a shell is lost when the container is next replaced.

## 7. Find its files {#files}

The stack's folders are named for its `PROJECT_NAME`:

```bash
ls -ln /opt/docker/volumes/<project>
```

Each folder is `<container>-data`, `<container>-config`, or `<container>-secrets`. The owner shown is a number such as `101000`, which is the container's user as the host sees it. See [Stack folders](../../fleet-bootstrap/concepts/host-layout.md#stack-folders).

You can list the project's folder as the admin. Reading inside one of its folders needs `sudo`, because they belong to the container's user:

```bash
sudo ls -l /opt/docker/volumes/<project>/<container>-config
```

To see which host folder is mounted where in a container:

```bash
docker inspect --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' <container>
```

The compose file the stack was deployed from is the path in the *CONFIG FILES* column in [Find the project](#find). It is in Periphery's checkout of fleet-stacks, and the container definitions it extends are in the `containers` folder of the same checkout.

## What not to change by hand {#hands-off}

Everything on a host is put there from a repo or from Komodo, and is put back the next time the host is run. A fix made on the host works until then and is gone afterwards, with no record that it was ever made. See [What the run overwrites](../../fleet-bootstrap/concepts/how-a-host-is-built.md#overwrites).

| Do not | Because | Change it in |
| --- | --- | --- |
| Edit a file under `/opt/docker/stacks` | Periphery replaces its checkout when it redeploys the Stack | The fleet-stacks repo |
| Run `docker compose up`, `down`, or `stop` | The next sync redeploys a Stack that changed or is not running, and Komodo's view of the Stack is wrong until it does | Komodo, or a run of the host |
| Edit the env file in the checkout, or the Stack's *Environment* in Komodo | The sync writes the *Environment* again from the committed file | The inventory's `komodo_stack_env`, or a Komodo Variable or Secret |
| Change a file inside a container | The container is replaced on the next deploy | The stack's folder under `/opt/docker/volumes`, or its definition |
| Create a network, open a port, or change a folder's owner | The host's configuration owns them, and the next deploy or reboot puts them back | The stack's `setup.yaml` in fleet-stacks, then a run of the host |

The files under `/opt/docker/volumes` are the exception. They belong to the stacks, a deploy never replaces one that is already there, and a stack's page tells you when to edit one.

## What's next

- To redeploy or restart a Stack, use Komodo. See the [Komodo primer](../komodo/index.md).
- To change what a stack runs, see [Making changes](index.md#changes).
- To check a route into the stack, see the [Traefik primer](../traefik/index.md).

## Not yet confirmed {#unconfirmed}

No host has been built, so no command on this page has been run against one.

- The names `docker compose ls` shows. Komodo is expected to pass the Stack's name as the project, as [The first run](../../fleet-bootstrap/foundation/first-run.md#km01-full) describes. Komodo's documentation says the project name defaults to the Stack's name, and the stack pages' *Verify* sections follow that. Take the name from `docker compose ls` if a command lists nothing, and correct the pages.
- The path in the *CONFIG FILES* column, and the layout of Periphery's checkout under `/opt/docker/stacks`.
- Where Periphery writes the env file it gives to Compose, and under which name.
- `docker compose -p <stack>` commands run with no compose file in the current folder. Compose finds the project's containers by their labels, and this has not been tried on a host with `DOCKER_CONTENT_TRUST=1` set in the shell.
- The exact wording of the *STATUS* column for each state.
- Which folders under `/opt/docker/volumes/<project>` the admin can read without `sudo`.
