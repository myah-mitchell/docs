#!/usr/bin/env python3
"""Generate the fleet bootstrap facts from a fleet-stacks checkout.

Reads every stack under stacks/ in fleet-stacks and writes:

  content/fleet-bootstrap/concepts/variables-and-secrets.md
      The register of every Komodo Variable and Secret a komodo.env file
      references, built from scripts/fleet-register.yaml and
      scripts/templates/variables-and-secrets.md.

  snippets/generated/<stack>/services.md
  snippets/generated/<stack>/values.md
  snippets/generated/<stack>/host-setup.md
  snippets/generated/<stack>/manual.md
      The facts each stack page includes: the services it runs, the
      Variables and Secrets it reads, and the folders, seed files, and open
      ports the host's NixOS configuration gives it. manual.md holds the
      folders and seed files as commands, and says where the ports come from,
      because the firewall of a NixOS host changes only through its
      configuration.

The output is committed. Run this again after fleet-stacks changes a
komodo.env, a setup.yaml, or a compose.yaml, and commit what it writes:

  python scripts/fleet_facts.py --fleet-stacks ../fleet-stacks

The run stops without writing anything when a komodo.env references a name
that fleet-register.yaml does not describe, when fleet-register.yaml
describes a name nothing references, or when the text it is about to write
holds a character the style guide bans. --check writes nothing and exits 1
when the committed output is out of date.
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REGISTER_META = ROOT / "scripts" / "fleet-register.yaml"
REGISTER_TEMPLATE = ROOT / "scripts" / "templates" / "variables-and-secrets.md"
REGISTER_PAGE = ROOT / "content" / "fleet-bootstrap" / "concepts" / "variables-and-secrets.md"
SNIPPETS_DIR = ROOT / "snippets" / "generated"

REGISTER_MARKER = "<!-- register -->"
REFERENCE = re.compile(r"\[\[([A-Z0-9_]+)\]\]")
ENV_LINE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*:(.*)$")

# Stacks under stacks/ that are not deployable and get no facts.
SKIPPED_STACKS = {"template"}

VOLUMES_DIR = "/opt/docker/volumes"
LOGS_DIR = "/opt/docker/logs"
# containerGroup in fleet-nixos's modules/stacks.nix, the containers' UID 1000
# as the host sees it under userns-remap.
PROJECT_GROUP = 101000
RAW_URL = "https://raw.githubusercontent.com/myah-mitchell/fleet-stacks/main"
# Where a host's folders, seed files, and ports are held, in the private repo.
HOST_FILE = "nixos/hosts/<host>.json"
HOST_LAYOUT = "../concepts/host-layout.md"

# Characters the style guide bans, by name. Descriptions and firewall comments
# come from other files, so the output is checked before it is written.
BANNED = {"\u2014": "an em-dash", "\u2013": "an en-dash"}


def fail(message):
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def load_services(compose_path, seen=None):
    """Return a stack's service names, included compose files first."""
    seen = seen if seen is not None else set()
    compose_path = compose_path.resolve()
    if compose_path in seen:
        return []
    seen.add(compose_path)

    compose = yaml.safe_load(compose_path.read_text()) or {}
    services = []
    for entry in compose.get("include") or []:
        path = entry["path"] if isinstance(entry, dict) else entry
        for name in load_services(compose_path.parent / path, seen):
            if name not in services:
                services.append(name)
    for name in compose.get("services") or {}:
        if name not in services:
            services.append(name)
    return services


def load_references(env_path):
    """Return the names a komodo.env references, in order, with their keys."""
    references = {}
    for line in env_path.read_text().splitlines():
        match = ENV_LINE.match(line)
        if not match:
            continue
        for name in REFERENCE.findall(match.group(2)):
            references.setdefault(name, []).append(match.group(1))
    return references


def load_stacks(fleet_stacks):
    stacks_dir = fleet_stacks / "stacks"
    if not stacks_dir.is_dir():
        fail(f"{stacks_dir} is not a folder. Pass --fleet-stacks.")

    stacks = {}
    for stack_dir in sorted(stacks_dir.iterdir()):
        if not stack_dir.is_dir() or stack_dir.name in SKIPPED_STACKS:
            continue
        setup_path = stack_dir / "setup.yaml"
        env_path = stack_dir / "komodo.env"
        if not setup_path.exists() or not env_path.exists():
            fail(f"{stack_dir} has no setup.yaml or komodo.env. Run scripts/build.py in fleet-stacks.")
        setup = yaml.safe_load(setup_path.read_text()) or {}
        stacks[stack_dir.name] = {
            "project": setup.get("project") or "",
            "folders": setup.get("folders") or [],
            "files": setup.get("files") or [],
            "firewall": setup.get("firewall") or [],
            "services": load_services(stack_dir / "compose.yaml"),
            "references": load_references(env_path),
        }
    return stacks


def load_register():
    register = yaml.safe_load(REGISTER_META.read_text())
    names = {}
    for group in register["groups"]:
        for name, entry in group["names"].items():
            if name in names:
                fail(f"{name} is in fleet-register.yaml twice.")
            if entry.get("kind") not in ("Variable", "Secret"):
                fail(f"{name} needs kind: Variable or kind: Secret in fleet-register.yaml.")
            if not entry.get("value"):
                fail(f"{name} needs a value in fleet-register.yaml.")
            names[name] = {**entry, "group": group["id"]}
    return register, names


def check_register(stacks, names):
    referenced = {name for stack in stacks.values() for name in stack["references"]}
    missing = sorted(referenced - names.keys())
    unused = sorted(names.keys() - referenced)
    if missing:
        fail("fleet-register.yaml does not describe: " + ", ".join(missing))
    if unused:
        fail("fleet-register.yaml describes names nothing references: " + ", ".join(unused))


def check_output(output):
    for path, text in output.items():
        for character, name in BANNED.items():
            for number, line in enumerate(text.splitlines(), start=1):
                if character in line:
                    fail(f"{path.relative_to(ROOT)} would hold {name} on line {number}. Reword the source.")


def allowed_from(rule):
    return "The internal subnet" if rule["allow_from"] == "internal" else "Anywhere"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def folder_path(project, folder):
    root = LOGS_DIR if folder["root"] == "logs" else VOLUMES_DIR
    return f"{root}/{project}/{folder['path']}"


def render_register(register, names, stacks):
    every_stack = len(stacks)
    sections = []
    for group in register["groups"]:
        rows = []
        for name, entry in group["names"].items():
            readers = [stack for stack, facts in stacks.items() if name in facts["references"]]
            if len(readers) == every_stack:
                read_by = "Every stack"
            else:
                read_by = ", ".join(f"[{stack}](../stacks/{stack}.md)" for stack in readers)
            rows.append([f"`{name}`", entry["kind"], entry["value"].strip(), read_by])
        section = [f"## {group['title']} {{#{group['id']}}}", "", group["intro"].strip(), ""]
        section.append(table(["Name", "Kind", "Value", "Read by"], rows))
        if group.get("notes"):
            section += ["", group["notes"].strip()]
        sections.append("\n".join(section))

    template = REGISTER_TEMPLATE.read_text()
    if REGISTER_MARKER not in template:
        fail(f"{REGISTER_TEMPLATE} has no {REGISTER_MARKER} line.")
    return template.replace(REGISTER_MARKER, "\n\n".join(sections))


def render_services(facts):
    return "```text\n" + "\n".join(facts["services"]) + "\n```\n"


def render_values(facts, register, names):
    groups = {group["id"]: group for group in register["groups"]}
    operational = [g for g in register["groups"] if g.get("every_stack")]
    operational_ids = {g["id"] for g in operational}

    rows = []
    for name, keys in facts["references"].items():
        entry = names[name]
        if entry["group"] in operational_ids:
            continue
        group = groups[entry["group"]]
        rows.append([
            ", ".join(f"`{key}`" for key in keys),
            f"`{name}`",
            entry["kind"],
            f"[{group['title']}](../concepts/variables-and-secrets.md#{group['id']})",
        ])

    lines = []
    if rows:
        lines += [table(["Key", "Reads", "Kind", "Described under"], rows), ""]
    else:
        lines += ["This stack reads no Variable or Secret of its own.", ""]
    for group in operational:
        lines.append(
            f"It also reads the {len(group['names'])} "
            f"[{group['title'].lower()}](../concepts/variables-and-secrets.md#{group['id']}), "
            "as every stack does."
        )
    return "\n".join(lines) + "\n"


def render_host_setup(facts):
    project = facts["project"]
    lines = [
        f"The project is `{project}`, so the stack's folders sit under "
        f"`{VOLUMES_DIR}/{project}` and `{LOGS_DIR}/{project}`. "
        f"Both are mode `0750`, owned by the admin account with group `{PROJECT_GROUP}`.",
        "",
    ]

    if facts["folders"]:
        rows = [
            [
                f"`{folder_path(project, folder)}`",
                f"`{folder['owner']}:{folder['group']}`",
                f"`{folder['mode']}`" if folder.get("mode") else "Default",
            ]
            for folder in facts["folders"]
        ]
        lines += [table(["Folder", "Owner", "Mode"], rows), ""]
    else:
        lines += ["No container in this stack has a folder of its own.", ""]

    if facts["files"]:
        rows = [
            [
                f"`{VOLUMES_DIR}/{project}/{item['path']}`",
                f"`{item['source']}`",
                f"`{item['owner']}:{item['group']}`",
                f"`{item['mode']}`" if item.get("mode") else "Default",
            ]
            for item in facts["files"]
        ]
        lines += [
            "These seed files come from fleet-stacks. "
            "Each is written only when nothing is at its path, "
            "so a copy already on the host is never replaced.",
            "",
            table(["File", "Copied from", "Owner", "Mode"], rows),
            "",
        ]

    if facts["firewall"]:
        rows = [
            [f"`{rule['port']}/{rule['proto']}`", allowed_from(rule), rule["comment"]]
            for rule in facts["firewall"]
        ]
        lines += [table(["Port", "Allowed from", "Comment"], rows), ""]
    else:
        lines += ["This stack opens no port on the host's firewall.", ""]

    work = "creates the folders"
    if facts["files"]:
        work += " and the seed files"
    if facts["firewall"]:
        work += ", and opens the ports," if facts["files"] else " and opens the ports"
    lines += [
        f"The host's NixOS configuration {work} when the host is deployed. "
        f"It reads them from the host's file in the private repo, `{HOST_FILE}`, "
        "which `nixos-sync.yml` writes from the stack's `setup.yaml`. "
        f"See [Host layout]({HOST_LAYOUT}#stack-folders).",
        "",
    ]

    return "\n".join(lines)


def render_manual(stack, facts):
    project = facts["project"]
    made = "folders and seed files" if facts["files"] else "folders"
    blocks = [
        f"A host deployed with the stack in its file has these {made} already. "
        "The commands make them on a host whose file does not list the stack."
    ]

    commands = [
        f"sudo install -d -o $USER -g {PROJECT_GROUP} -m 0750 \\",
        f"  {LOGS_DIR}/{project} {VOLUMES_DIR}/{project}",
    ]
    for folder in facts["folders"]:
        mode = f" -m {folder['mode']}" if folder.get("mode") else ""
        commands.append(
            f"sudo install -d -o {folder['owner']} -g {folder['group']}{mode} "
            f"{folder_path(project, folder)}"
        )
    blocks.append("```bash\n" + "\n".join(commands) + "\n```")

    if facts["files"]:
        commands = []
        for item in facts["files"]:
            dest = f"{VOLUMES_DIR}/{project}/{item['path']}"
            commands += [
                f"sudo test -e {dest} || sudo curl -fsSL \\",
                f"  -o {dest} \\",
                f"  {RAW_URL}/{item['source']}",
                f"sudo chown {item['owner']}:{item['group']} {dest}",
            ]
            if item.get("mode"):
                commands.append(f"sudo chmod {item['mode']} {dest}")
        blocks.append("```bash\n" + "\n".join(commands) + "\n```")

    # No command here. The firewall of a NixOS host is built from its
    # configuration, and a rule added on the host does not last.
    if facts["firewall"]:
        rows = [
            [f"`{rule['port']}/{rule['proto']}`", allowed_from(rule)]
            for rule in facts["firewall"]
        ]
        blocks += [
            "No command opens the stack's ports, "
            "because the firewall changes only through the host's configuration. "
            f"The ports below are open once the host's file, `{HOST_FILE}`, holds them: "
            "`nixos-sync.yml` writes that file in the private repo, "
            "and a deploy of the host applies it. "
            f"See [Host layout]({HOST_LAYOUT}#firewall).",
            table(["Port", "Allowed from"], rows),
        ]

    return f"For {stack}:\n\n" + "\n\n".join(blocks) + "\n"


def render_all(stacks, register, names):
    output = {REGISTER_PAGE: render_register(register, names, stacks)}
    for stack, facts in stacks.items():
        folder = SNIPPETS_DIR / stack
        output[folder / "services.md"] = render_services(facts)
        output[folder / "values.md"] = render_values(facts, register, names)
        output[folder / "host-setup.md"] = render_host_setup(facts)
        output[folder / "manual.md"] = render_manual(stack, facts)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--fleet-stacks",
        type=Path,
        default=ROOT.parent / "fleet-stacks",
        help="path to a fleet-stacks checkout (default: ../fleet-stacks)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="write nothing, and exit 1 when the committed output is out of date",
    )
    args = parser.parse_args()

    stacks = load_stacks(args.fleet_stacks)
    register, names = load_register()
    check_register(stacks, names)
    output = render_all(stacks, register, names)
    check_output(output)

    stale = [path for path, text in output.items() if not path.exists() or path.read_text() != text]
    expected = set(output)
    orphans = [path for path in SNIPPETS_DIR.rglob("*.md") if path not in expected] if SNIPPETS_DIR.exists() else []

    if args.check:
        for path in stale + orphans:
            print(f"Out of date: {path.relative_to(ROOT)}")
        sys.exit(1 if stale or orphans else 0)

    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output[path])
        print(f"Wrote {path.relative_to(ROOT)}")
    for path in orphans:
        path.unlink()
        print(f"Removed {path.relative_to(ROOT)}")
    if not stale and not orphans:
        print("Nothing to write.")


if __name__ == "__main__":
    main()
