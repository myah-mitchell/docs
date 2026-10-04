# Reading a task's log

Every run Semaphore starts is a [Task](index.md#task), and every Task keeps a log. This page finds a Task, works out which stage of `site.yml` it reached, and reads the lines that say why it stopped. Use it when a host page's run does not end the way the page says, or to see what someone else's run did.

Status: written, not yet run.

Nothing here changes anything. The log is read in Semaphore's UI, and it is kept in Semaphore's database on ci01.

## Prerequisites

- Semaphore has its Project and at least one Task has run, from [The handover](../../fleet-bootstrap/foundation/handover.md#prove).
- You know roughly what `site.yml` does. See [The four stages](../../fleet-bootstrap/concepts/how-a-host-is-built.md#stages).

## 1. Open the Task {#open}

Open *Dashboard > History*. The list shows every Task in the Project, newest first, each with its Template, its status, the user who started it, and when.

Click the Task. It opens on its *Log* tab. A Task that is still running adds lines as they are printed, so the log can be watched live.

| Status | Means |
| --- | --- |
| *Waiting* | The Task is queued and has not started |
| *Running* | `ansible-playbook` is running |
| *Success* | The command ended with no failed host |
| *Failed* | The command ended with an error, or never started |
| *Stopped* | Someone stopped the Task by hand |

To see one Template's Tasks only, open *Task Templates*, click the Template, and open its *Tasks* tab.

## 2. Read the top {#top}

The first lines are Semaphore's own, printed before Ansible starts. They show the repositories being cloned or updated, the commit each one is at, and the collections from the fleet-ansible repo's `requirements.yml` being installed.

A Task that fails here never reached the playbook. The cause is in Semaphore's Project and not in the fleet: a [Repository](index.md#repository) address or branch, an expired token in the [Key Store](index.md#key-store), or no route to GitHub.

The commit is worth a glance on a Task that passed, too. It tells you which version of the playbooks ran.

## 3. Find the stage {#stage}

Ansible prints a line that starts with `PLAY` for each play, and a line that starts with `TASK` for each task inside it. `site.yml` has four plays, one for each stage. Search the log for `PLAY [` and note the last one that has tasks under it.

| Line in the log | Stage |
| --- | --- |
| `PLAY [Create missing VMs]` | `vms` |
| `PLAY [Wait for the hosts to answer]` | `wait` |
| `PLAY [Install and deploy NixOS]` | `nixos` |
| `PLAY [Deploy the stacks through Komodo]` | `komodo` |

A `TASK` line names the role and then the task, such as `TASK [nixos : Check the committed files match the inventory]`. The word before the colon is the role, so it names the stage as well.

<details>
<summary>Background: why almost every task says localhost</summary>

Ansible normally logs in to each host and runs its tasks there. `site.yml` does not. Every task runs on the control node, which is Semaphore's container, and the commands those tasks call do the connecting.

The log still prints each result under the host's name, because the play is about that host. A result written as `km01 -> localhost` means the task was about km01 and ran in Semaphore's container. See [Ansible](../ansible/index.md) for plays, tasks, and delegation.

</details>

## 4. Read the recap {#recap}

Go to the end of the log. A run that got as far as Ansible ends with `PLAY RECAP` and one line for each host:

```text
km01 : ok=41 changed=3 unreachable=0 failed=0 skipped=12 rescued=0 ignored=0
```

The numbers above are an illustration. Yours differ.

| Count | Means |
| --- | --- |
| `ok` | Tasks that ran without error, changed or not |
| `changed` | Tasks that reported a change |
| `unreachable` | Tasks that could not connect |
| `failed` | Tasks that ended in an error. The run stops for that host at the first one |
| `skipped` | Tasks whose condition was not met |

`failed=0` and `unreachable=0` mean every stage finished for that host. `changed` is never zero on a full run, since the `nixos` stage reports a change each time it deploys and the `komodo` stage each time it syncs. See [Prove Semaphore](../../fleet-bootstrap/foundation/handover.md#prove).

A log with no recap at all means the command was killed or never started. Go back to [the top](#top), then check the container's memory. See [One host for each run](../../fleet-bootstrap/foundation/semaphore-project.md#nix-memory).

## 5. Read the failure {#failure}

If `failed` is not zero, search the log for `fatal:`. The line starts the failed task's result, and the `TASK` line above it says which task it was.

The result is printed as one block of JSON. Three keys in it carry the reason:

| Key | Holds |
| --- | --- |
| `msg` | Ansible's own description, or the message the playbook wrote for this failure |
| `stderr` | What the command printed as its error, for a task that ran a command |
| `stdout` | What the command printed otherwise. OpenTofu's plan and nix's output land here |

The fleet's playbooks check before they act, and each check writes a `msg` that says what to do. The two you are most likely to meet:

| The message says | Do this |
| --- | --- |
| A file under `nixos/` does not match the inventory, and names `nixos-sync.yml` | Generate the files again, commit, and push. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change) |
| A file under `komodo/stacks/` does not match, and names `komodo-sync.yml` | The same |

For these two, the lines just above `fatal:` show a diff between the committed file and what the inventory now gives.

For anything else, the primer lists the first place to look for each symptom. See [When it goes wrong](index.md#troubleshooting).

## 6. Run it again {#again}

Fix the cause, then start the Template again with the same *Target*. Every stage is safe to repeat, and a stage that already finished finds nothing to do. See [The four stages](../../fleet-bootstrap/concepts/how-a-host-is-built.md#stages).

The failed Task stays in the history with its log, so the two can be compared later.

## What's next

To see what a run would do before it does it, start it with **Dry Run** ticked and read its log the same way. See [Seeing what a run would do](../../fleet-bootstrap/concepts/how-a-host-is-built.md#check).

## Not yet confirmed {#unconfirmed}

- The whole page. No Task has run on a real Semaphore in this fleet.
- The labels *Dashboard > History*, *Log*, and *Tasks*, and the status names. They come from Semaphore's current documentation, which describes a newer version than v2.13.13, the one in the fleet-stacks repo. That documentation lists more statuses than the five above.
- The columns of the history list, and that it names the user who started each Task.
- What Semaphore prints before Ansible starts: the wording of the clone lines, whether the commit is shown, and whether it installs the collections from a `requirements.yml` in the repo's root.
- How a result is written for the fleet's delegated tasks, and the form `km01 -> localhost`.
- What the log looks like when the container runs out of memory.
- Whether a secret from the [Variable Group](index.md#variable-group) can appear in a log. Treat a log as readable by everyone with access to the Project, and do not paste one into a public place without reading it.
