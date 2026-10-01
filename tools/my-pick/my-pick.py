#!/usr/bin/env python3
"""Pick skills/agents/commands/rules from my library repo and symlink (or copy) them into a project.

Usage: my-pick [project] [--list] [--describe NAME] [--all] [--kind skills,agents] [--copy] [--dry-run]
       my-pick --scan-back [DIR ...]   # find real copies outside the repo; pick which to merge in
State = the filesystem: an item is "linked" if the project has a symlink into the repo.
"""
import argparse
import glob
import hashlib
import os
import re
import shutil
import sys

# This script lives at <repo>/tools/my-pick/, so the repo root is two levels up — no config needed.
REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# kind -> (repo dir, project dirs to link into). Add a target here to support another tool.
KINDS = {
    "skills": ("skills", [".agents/skills", ".claude/skills"]),
    "agents": (".claude/agents", [".claude/agents"]),
    "commands": (".claude/commands", [".claude/commands"]),
    "rules": (".claude/rules", [".claude/rules"]),
}


def describe(path, full=False):
    """One-line description from frontmatter `description:` (or first heading). full=True: whole multi-line block, no 5-line cap."""
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
                block = []
                for l in lines[i + 1:] if full else lines[i + 1:i + 6]:
                    if l.startswith(" "):
                        block.append(l.strip())
                    elif l.strip() or not full:
                        if full:
                            break  # next frontmatter key / closing ---
                    elif block:
                        block.append("")  # blank line inside block
                text = " ".join(block)
            return text.strip("\"'")
    return next((l.lstrip("# ").strip() for l in lines if l.startswith("#")), "")


def discover():
    """-> list of (kind, name, src_path, [project target dirs])"""
    items = []
    for kind, (sub, targets) in KINDS.items():
        base = os.path.join(REPO, sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            items.append((kind, name, os.path.join(base, name), targets))
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


def hash_path(path):
    """Content hash of a file, or a directory (names + contents, order-independent)."""
    h = hashlib.sha256()
    if os.path.isfile(path):
        h.update(open(path, "rb").read())
        return h.hexdigest()
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames.sort()
        for fn in sorted(filenames):
            fp = os.path.join(dirpath, fn)
            h.update(os.path.relpath(fp, path).encode())
            h.update(open(fp, "rb").read())
    return h.hexdigest()


def find_target_dirs(root, rel):
    """Real dirs under root ending in relative path `rel` (e.g. '.claude/skills'), skipping this repo, .git, node_modules."""
    hits = []
    for p in glob.glob(os.path.join(root, "**", rel), recursive=True):
        if not os.path.isdir(p) or os.path.realpath(p).startswith(REPO + os.sep) or os.path.realpath(p) == REPO:
            continue
        if "node_modules" in p.split(os.sep) or ".git" in p.split(os.sep):
            continue
        hits.append(p)
    return hits


def scan_back(roots=None):
    """-> list of ('new'|'drift', kind, name, path) for real copies outside the repo that aren't in it, or differ from it."""
    lib = {(k, n): src for k, n, src, _ in discover()}
    roots = roots or [os.path.expanduser("~/github_projs"), os.path.expanduser("~/.claude")]
    found = []
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        base = os.path.basename(root.rstrip(os.sep))
        is_global = base in (".claude", ".copilot")
        for kind, (_, targets) in KINDS.items():
            if base in KINDS:  # root is itself a kind dir, e.g. ~/.copilot/skills
                if kind != base:
                    continue
                dirs, skip = [root], set()
            elif is_global:
                dirs, skip = [os.path.join(root, kind)], ({"synced"} if kind == "skills" else set())
            else:
                dirs, skip = {d for t in targets for d in find_target_dirs(root, t)}, set()
            for d in dirs:
                if not os.path.isdir(d):
                    continue
                for name in sorted(os.listdir(d)):
                    p = os.path.join(d, name)
                    if name in skip or os.path.islink(p):
                        continue
                    key = (kind, name)
                    if key not in lib:
                        found.append(("new", kind, name, p))
                    elif hash_path(p) != hash_path(lib[key]):
                        found.append(("drift", kind, name, p))
    return found


def merge_back(finding, dry):
    """Copy a scan-back finding into the repo (overwriting a drifted copy)."""
    status, kind, name, path = finding
    dest = os.path.join(REPO, "skills", name) if kind == "skills" else os.path.join(REPO, ".claude", kind, name)
    print(f"  {'~' if status == 'drift' else '+'} {kind}/{name}")
    if dry:
        return
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    elif os.path.lexists(dest):
        os.remove(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isdir(path):
        shutil.copytree(path, dest)
    else:
        shutil.copy2(path, dest)


def choose_scan_back(findings):
    import questionary  # lazy: plain listing works without it
    choices = []
    for f in findings:
        status, kind, name, path = f
        desc = describe(path)
        title = f"[{'NEW' if status == 'new' else 'DRIFT'}] {kind}/{name}" + (f" — {desc[:60]}" if desc else "")
        choices.append(questionary.Choice(title, value=f))
    return questionary.checkbox("Space = toggle, Enter = merge selected into the lib", choices=choices).ask()


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
    ap.add_argument("--describe", metavar="NAME", help="print the full, untruncated description of one item (exact name, else substring matches) and exit")
    ap.add_argument("--all", action="store_true", help="link everything (incl. rules), no prompt")
    ap.add_argument("--kind", help="comma-separated kinds to limit to: skills,agents,commands,rules")
    ap.add_argument("--copy", action="store_true", help="copy instead of symlink (standalone project; not tracked as linked)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--scan-back", nargs="*", metavar="DIR",
                     help="report real (non-symlink) skills/agents/commands/rules under DIR(s) that are new or "
                          "drifted vs the lib (default: ~/github_projs + ~/.claude); no writes")
    a = ap.parse_args()

    if a.scan_back is not None:
        findings = scan_back(a.scan_back or None)
        if not findings:
            print("scan-back: nothing new or drifted")
            return
        for status, kind, name, p in findings:
            print(f"[{'NEW  ' if status == 'new' else 'DRIFT'}] {kind:<8} {name:<24} {p}")
        if not sys.stdin.isatty():
            return
        picks = choose_scan_back(findings)
        if not picks:
            return
        for f in picks:
            merge_back(f, a.dry_run)
        print("dry run, nothing changed" if a.dry_run
              else f"merged into {REPO} — review with `git status` there and commit")
        return

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

    if a.describe:
        hits = [i for i in items if i[1] == a.describe] or [i for i in items if a.describe.lower() in i[1].lower()]
        if not hits:
            sys.exit(f"no item matching '{a.describe}'; try --list")
        for i in hits:
            print(f"{i[0]}/{i[1]}\n  {describe(i[2], full=True) or '(no description)'}\n  {i[2]}\n")
        return

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
