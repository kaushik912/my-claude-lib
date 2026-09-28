#!/usr/bin/env python3
"""Pick skills/agents/commands/rules from my library repo and symlink (or copy) them into a project.

Usage: my-pick [project] [--list] [--all] [--kind skills,agents] [--copy] [--dry-run]
State = the filesystem: an item is "linked" if the project has a symlink into the repo.
"""
import argparse
import os
import re
import shutil
import sys

# This script lives at <repo>/tools/my-pick/, so the repo root is two levels up — no config needed.
REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# kind -> (repo dir, project dirs to link into). Add a target here to support another tool.
KINDS = {
    "skills": (".agents/skills", [".agents/skills", ".claude/skills"]),
    "agents": (".claude/agents", [".claude/agents"]),
    "commands": (".claude/commands", [".claude/commands"]),
    "rules": (".claude/rules", [".claude/rules"]),
}
# Claude-only skills that live as real dirs in the repo's .claude/skills (not symlinks to .agents)
CLAUDE_ONLY_SKILLS = (".claude/skills", [".claude/skills"])


def describe(path):
    """One-line description from frontmatter `description:` (or first heading)."""
    f = os.path.join(path, "SKILL.md") if os.path.isdir(path) else path
    try:
        lines = open(f, encoding="utf-8").read().splitlines()
    except OSError:
        return ""
    for i, line in enumerate(lines):
        m = re.match(r"description:\s*(.*)", line)
        if m:
            text = m.group(1).strip()
            if text in (">", ">-", "|", "|-", ""):  # multi-line YAML: join indented lines
                text = " ".join(l.strip() for l in lines[i + 1:i + 6] if l.startswith(" "))
            return text.strip("\"'")
    return next((l.lstrip("# ").strip() for l in lines if l.startswith("#")), "")


def discover():
    """-> list of (kind, name, src_path, [project target dirs])"""
    items, seen = [], set()
    sources = [(k, d, t) for k, (d, t) in KINDS.items()]
    sources.append(("skills", *CLAUDE_ONLY_SKILLS))
    for kind, sub, targets in sources:
        base = os.path.join(REPO, sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            src = os.path.join(base, name)
            if kind == "skills" and (name in seen or os.path.islink(src)):
                continue  # .claude/skills symlinks just mirror .agents/skills
            if kind == "skills":
                seen.add(name)
            items.append((kind, name, src, targets))
    return items


def link_state(project, item):
    """True if any of the item's targets is a symlink pointing at its source."""
    _, name, src, targets = item
    return any(
        os.path.islink(p := os.path.join(project, t, name)) and os.path.realpath(p) == os.path.realpath(src)
        for t in targets
    )


def link(project, item, dry, copy=False):
    _, name, src, targets = item
    added = []
    for t in targets:
        dest = os.path.join(project, t, name)
        rel = os.path.join(t, name)
        if os.path.islink(dest) and os.path.realpath(dest) == os.path.realpath(src):
            continue
        if os.path.islink(dest) and not os.path.exists(dest):  # dangling (e.g. repo moved): repair
            if not dry:
                os.remove(dest)
        elif os.path.lexists(dest):
            print(f"  skip {rel}: exists and is not our link")
            continue
        print(f"  {'cp' if copy else '+'} {rel}")
        if not dry:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not copy:
                os.symlink(src, dest)
            elif os.path.isdir(src):
                shutil.copytree(src, dest, symlinks=True)
            else:
                shutil.copy2(src, dest)
        added.append(rel)
    return added


def unlink(project, item, dry):
    _, name, src, targets = item
    for t in targets:
        dest = os.path.join(project, t, name)
        if os.path.islink(dest) and os.path.realpath(dest).startswith(REPO + os.sep):
            print(f"  - {os.path.join(t, name)}")
            if not dry:
                os.remove(dest)


def git_exclude(project, rels, dry):
    """Hide our symlinks from the project's git status (local only, no .gitignore edits)."""
    info = os.path.join(project, ".git", "info")
    if dry or not rels or not os.path.isdir(os.path.join(project, ".git")):
        return
    os.makedirs(info, exist_ok=True)
    path = os.path.join(info, "exclude")
    have = open(path).read().splitlines() if os.path.exists(path) else []
    new = [f"/{r}" for r in rels if f"/{r}" not in have]
    if new:
        with open(path, "a") as f:
            f.write("\n".join(new) + "\n")


def choose(project, items):
    import questionary  # lazy: --list and --all work without it
    choices = []
    for kind in KINDS:
        group = [i for i in items if i[0] == kind]
        if not group:
            continue
        choices.append(questionary.Separator(f"── {kind} ──"))
        for i in group:
            desc = describe(i[2])
            title = f"{i[1]} — {desc[:80]}" if desc else i[1]
            choices.append(questionary.Choice(title, value=i, checked=link_state(project, i)))
    return questionary.checkbox("Space = toggle, Enter = apply", choices=choices).ask()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", nargs="?", default=".")
    ap.add_argument("--list", action="store_true", help="print everything available (+ linked status) and exit")
    ap.add_argument("--all", action="store_true", help="link everything (incl. rules), no prompt")
    ap.add_argument("--kind", help="comma-separated kinds to limit to: skills,agents,commands,rules")
    ap.add_argument("--copy", action="store_true", help="copy instead of symlink (standalone project; not tracked as linked)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    project = os.path.abspath(a.project)
    if not os.path.isdir(project):
        sys.exit(f"not a directory: {project}")
    items = discover()
    if a.kind:
        kinds = {k.strip() for k in a.kind.split(",")}
        bad = kinds - set(KINDS)
        if bad:
            sys.exit(f"unknown kind(s): {', '.join(sorted(bad))}; choose from {', '.join(KINDS)}")
        items = [i for i in items if i[0] in kinds]

    if a.list:
        for i in items:
            mark = "✓" if link_state(project, i) else " "
            print(f"[{mark}] {i[0]:<8} {i[1]:<24} {describe(i[2])[:80]}")
        return

    if a.all:
        picks = items
    else:
        if not sys.stdin.isatty():
            sys.exit("interactive only; use --all or --list")
        picks = choose(project, items)
        if picks is None:
            sys.exit("cancelled")

    picked = {(i[0], i[1]) for i in picks}
    added = []
    for i in items:
        linked, want = link_state(project, i), (i[0], i[1]) in picked
        if want:
            added += link(project, i, a.dry_run, a.copy)
        elif linked and not a.all:
            unlink(project, i, a.dry_run)
    if not a.copy:
        git_exclude(project, added, a.dry_run)
    print("dry run, nothing changed" if a.dry_run else f"done: {project}")


if __name__ == "__main__":
    main()
