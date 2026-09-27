# Standards

Documentation standards shared across every repo: ansible, opentofu, fleet-private, docker-stacks, and this site. They exist so that a README in one repo and a runbook in another read like they were written by the same person on the same day.

- [Markdown style guide](markdown-style-guide.md): the full standard, plus a review checklist and a lint config.

## The short version

Three markers, three meanings, no overlap.

| Marker | Meaning | Examples |
| --- | --- | --- |
| `**bold**` | Something the reader does or supplies | **Sign Up**, **Deploy**, **Add Server** |
| `*italic*` | Something printed on the screen being described | *Settings > Variables*, *Public key*, *Name* |
| `` `code` `` | A string the reader acts on: copies, types, runs, or matches exactly | `qm start 101`, `/opt/docker/volumes`, `--full` |

So a step reads:

```markdown
1. Open *Settings > Variables* and click **New Variable**.
2. In *Name*, enter `GLOBAL_PUID`, and in *Value*, enter `1000`.
3. Leave **Is Secret** unticked, then click **Save**.
```

Everything else follows from protecting that. Bold never means "note this", so a reader can skim a page and see every action they have to take. Code marks strings the reader acts on, not technical nouns in general, so a name being described stays plain. Explanation always sits after the instruction it explains, never in front of it. Prose is not hard-wrapped. There are no em-dashes.

Examples use the real domain, `myah-mitchell.com`, with `home.` or `cloud.` as the sub-domain. A domain is not a secret, and `example.com` would only make the reader translate every hostname back. Addresses, keys, and tokens stay placeholders. See [placeholders and example values](markdown-style-guide.md#placeholders-and-example-values).

## Using this in another repo

Read [the guide](markdown-style-guide.md) in full once. After that, the [review checklist](markdown-style-guide.md#review-checklist) is the day-to-day reference, and [applying this to an existing repo](markdown-style-guide.md#applying-this-to-an-existing-repo) gives the order to convert existing docs in so the diffs stay reviewable.

To hold an agent to it, add this to that repo's `CLAUDE.md`:

```markdown
## Documentation

Markdown files follow the house standard at
https://myah-mitchell.github.io/docs/standards/markdown-style-guide/. In short: bold is what the reader does
(**Save**, **Deploy**), italic is what the screen says (*Username*,
*Settings > Variables*), code is a string the reader copies, types, runs
or matches exactly (`docker compose ps`, `--full`). A name being
described rather than reproduced stays plain: the ansible repo, km01 is
healthy. Never nest the markers, never use bold or italic for stress or
warnings, never hard-wrap prose, and never use em-dashes.

Examples use the real domain `myah-mitchell.com`, with `home.` or
`cloud.` as the sub-domain, never `example.com`. Real addresses, keys,
and tokens stay placeholders.
```

Copy the lint config from [the guide's linting section](markdown-style-guide.md#linting) into that repo's `.markdownlint.jsonc`. It catches the mechanical rules only. Emphasis semantics and density are review responsibilities, so a green lint run is not a passing document.
