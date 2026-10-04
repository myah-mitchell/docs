# Adding a Task Template

A [Task Template](index.md#task-template) describes one kind of run. The fleet starts with one, `site`, which takes a host through every stage of `site.yml`. Add another when you start the same run with the same options often enough that it deserves a button of its own.

This page adds a Template named `stacks`, which runs only the last stage of `site.yml`. It redeploys a host's Stacks through Komodo and skips the VM and NixOS stages, which is all a host needs after a change in the fleet-stacks repo that touches no folder, file, or port. The same steps fit any other Template.

Status: written, not yet run.

The change is made in Semaphore's UI and stored in Semaphore's database on ci01. No repo changes, and nothing is carried to a host until the Template is run.

## Prerequisites

- Semaphore has its Project, from [The Semaphore project](../../fleet-bootstrap/foundation/semaphore-project.md), and the `site` Template has run, from [The handover](../../fleet-bootstrap/foundation/handover.md#prove).
- You can sign in to Semaphore with an account that may edit the Project.

## 1. Decide what the Template runs {#decide}

Pick the playbook and its options before opening the form. Not every playbook in the fleet-ansible repo suits a Template.

| Playbook | As a Template |
| --- | --- |
| `site.yml`, every stage | The `site` Template, which exists |
| `site.yml`, limited by tag | A good fit. This page's example |
| `nixos-sync.yml`, `komodo-sync.yml` | Not a fit. Run them from a shell |
| `provision.yml` | Not covered. It configures Proxmox hosts and needs tools that have not been checked in Semaphore's container |

The two sync playbooks write files into the private repo for you to review and commit. A [Task](index.md#task) works in Semaphore's own clone and pushes nothing, so files written there never reach the repo. See [After a change](../../fleet-bootstrap/concepts/fleet-private.md#after-a-change).

`site.yml` gives each stage a tag of the same name: `vms`, `wait`, `nixos`, and `komodo`. A run limited to `komodo` checks that the host's committed Komodo file is current, runs the sync for the host's Stacks, and waits until each one is running. See [The four stages](../../fleet-bootstrap/concepts/how-a-host-is-built.md#stages).

## 2. Create the Template {#create}

Open *Task Templates*, click **New Template**, and choose the **Ansible Playbook** app.

| Field | Value |
| --- | --- |
| *Name* | `stacks` |
| *Playbook Filename* | `site.yml` |
| *Repository* | **fleet-ansible** |
| *Inventory* | **ansible-fleet** |
| *Variable Groups* | **fleet-private** |
| *Tags* | `komodo` |

Click **Create**. The Template appears in the *Task Templates* list with no last Task.

<details>
<summary>Background: why it reuses the same three pieces</summary>

A Template owns nothing but its own options. The [Repository](index.md#repository), the [Inventory](index.md#inventory), and the [Variable Group](index.md#variable-group) are shared, so a second Template that names them gets the same playbooks, the same hosts, and the same secrets as `site` with nothing copied. A key replaced in the Variable Group later is replaced for both.

The `komodo` stage reads only `KOMODO_API_KEY` and `KOMODO_API_SECRET` from the group. Giving it the whole group is simpler than keeping a second, smaller one in step, and it grants nothing new: anyone who may run this Template may also run `site`.

</details>

## 3. Add the Target prompt {#target}

Open the **stacks** Template's *Survey Variables* tab and add one entry:

| Field | Value |
| --- | --- |
| *Name* | `target` |
| *Title* | `Target` |
| *Type* | **String** |
| *Required* | **Yes** |

Save the Template. A [Survey Variable](index.md#survey-variable) belongs to one Template, so the one on `site` does not carry over. Without it the run has no `target`, and `site.yml` stops at its first play because it does not know which hosts to run against.

## 4. Try it as a dry run {#dry-run}

In *Task Templates*, open **stacks** and click **Run**. In *Target*, enter `km01`, tick **Dry Run**, and start the Task.

The log shows the first three plays with no tasks under them, since the tag leaves them out. The last play, `Deploy the stacks through Komodo`, confirms km01's committed Komodo file is current and stops there. The recap line for km01 ends with `unreachable=0` and `failed=0`.

A [dry run](index.md#dry-run) proves the Template is wired up: the repos cloned, the inventory was read, and the tag was applied. It does not contact Komodo.

If the Task fails, see [Reading a task's log](read-a-task-log.md).

## 5. Run it {#run}

Click **Run** again, enter `km01` in *Target*, leave **Dry Run** unticked, and start the Task.

The run ends with `failed=0` for km01, after Komodo reports every one of km01's Stacks as running. A Stack whose files did not change is left running as it is.

## What's next

Use the `stacks` Template after a change in the fleet-stacks repo that only Komodo has to pick up, such as a new image version. Use `site` for everything else. A change to a host's list of stacks, or to a stack's folders, files, or ports, changes the host's NixOS configuration too, and only `site` deploys that.

## Not yet confirmed {#unconfirmed}

- The whole page. No Template has been created on a real Semaphore.
- The labels. The form's labels follow [The Semaphore project](../../fleet-bootstrap/foundation/semaphore-project.md#template), which has not been checked against Semaphore v2.13.13, the version in the fleet-stacks repo. Semaphore's current documentation calls the filename field *Playbook / Script filename* and the button for a prompt *Add Survey Variable*.
- Where the form takes *Tags*, and in what format. The current documentation describes tags mainly as a prompt on the form that starts a Task, turned on in the Template under *Ansible Prompts*. If the Template's form has no *Tags* field, put `["--tags", "komodo"]` in *CLI args*.
- The label *Create* on the form's button, and whether a Survey Variable is saved with its own button or with the Template.
- Where *Dry Run* is ticked. The build guide's pages place it on the form that starts a Task.
- What the log shows for the three plays the tag leaves out.
- That a Task's clone of the private repo is not pushed anywhere. It follows from Semaphore having only a read token for that repo.
