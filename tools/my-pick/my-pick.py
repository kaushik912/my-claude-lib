#!/usr/bin/env python3
"""Pick skills/agents/commands/rules from my library repo and symlink (or copy) them into a project.

Usage: my-pick [project] [--list] [--describe NAME] [--all] [--kind skills,agents] [--copy] [--dry-run]
       my-pick [project] --prune [--yes]   # remove dangling links into the lib (asks first)
       my-pick [project] --pick NAME... [--preset P...] [--remove NAME...]   # non-interactive, additive
       my-pick --scan-back [DIR ...]   # find real copies outside the repo; pick which to merge in
       my-pick sync [project]          # recreate links/copies listed in the project's .my-pick.json
       my-pick [project] --update      # bump the ref pinned in .my-pick.json to the lib's latest
State = the filesystem: an item is "linked" if the project has a symlink into the repo.
Picks are also recorded in <project>/.my-pick.json (commit it; links themselves are gitignored).
"""
import argparse
import difflib
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

# This script lives at <repo>/tools/my-pick/, so the repo root is two levels up — no config needed.
REPO = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CACHE = os.path.expanduser("~/.cache/my-pick/lib")  # fallback lib clone for `sync` when REPO isn't the manifest's lib
MANIFEST = ".my-pick.json"

PRESETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets.json")

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


def is_lib_path(p):
    """True if resolved path p lives inside the lib checkout (REPO or the sync cache clone)."""
    return any(p.startswith(r + os.sep) for r in (REPO, os.path.realpath(CACHE)))


def discover(root=None):
    """-> list of (kind, name, src_path, [project target dirs])"""
    items = []
    for kind, (sub, targets) in KINDS.items():
        base = os.path.join(root or REPO, sub)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            items.append((kind, name, os.path.join(base, name), targets))
    return items


def resolve(items, names):
    """Map NAME or KIND/NAME tokens to items. Exact match only; exits (nothing linked) on any miss/ambiguity."""
    out, errs = [], []
    for tok in names:
        kind, _, name = tok.rpartition("/")
        hits = [i for i in items if i[1] == name and (not kind or i[0] == kind)]
        if len(hits) == 1:
            out.append(hits[0])
        elif hits:
            errs.append(f"'{tok}' is ambiguous ({', '.join(f'{i[0]}/{i[1]}' for i in hits)}); use KIND/NAME or --kind")
        else:
            near = difflib.get_close_matches(name, [i[1] for i in items], n=3)
            errs.append(f"no item '{tok}'" + (f"; did you mean: {', '.join(near)}?" if near else ""))
    if errs:
        sys.exit("\n".join(errs) + "\nnothing changed")
    return out


def preset_names(presets):
    """Expand preset names to item tokens (deduped, order kept); exits on unknown preset."""
    try:
        with open(PRESETS) as f:
            known = json.load(f)
    except FileNotFoundError:
        known = {}
    except json.JSONDecodeError as e:
        sys.exit(f"bad {PRESETS}: {e}")
    toks = []
    for p in presets:
        if p not in known:
            sys.exit(f"unknown preset '{p}'; available: {', '.join(sorted(known)) or '(none)'}")
        toks += [t for t in known[p] if t not in toks]
    return toks


def link_state(project, item):
    """True if any of the item's targets is a symlink pointing at its source."""
    _, name, src, targets = item
    return any(
        os.path.islink(p := os.path.join(project, t, name)) and os.path.realpath(p) == os.path.realpath(src)
        for t in targets
    )


def make_link(src, dest):
    """Symlink dest -> src, relative to dest's real dir so the link survives moving both trees together."""
    try:
        target = os.path.relpath(os.path.realpath(src), os.path.realpath(os.path.dirname(dest)))
    except ValueError:  # different drives on Windows
        target = os.path.realpath(src)
    try:
        os.symlink(target, dest, target_is_directory=os.path.isdir(src))
    except (OSError, NotImplementedError) as e:
        if os.name == "nt" or getattr(e, "winerror", None):
            sys.exit(f"can't create symlink {dest}: {e}\n"
                     "Windows needs Developer Mode on (Settings > For developers) or an admin shell; "
                     "or re-run with --copy to copy files instead")
        raise


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
                make_link(src, dest)
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
        if os.path.islink(dest) and is_lib_path(os.path.realpath(dest)):
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


def git_unexclude(project, rels, dry):
    """Drop exclude lines git_exclude added for links that no longer exist."""
    path = os.path.join(project, ".git", "info", "exclude")
    if dry or not rels or not os.path.exists(path):
        return
    drop = {f"/{r}" for r in rels}
    lines = open(path).read().splitlines()
    keep = [l for l in lines if l not in drop]
    if len(keep) != len(lines):
        with open(path, "w") as f:
            f.write("\n".join(keep) + ("\n" if keep else ""))


def find_dead(project):
    """-> [(rel, old_target)] dangling symlinks in our link dirs that pointed into the lib."""
    dead = []
    for d in sorted({t for _, targets in KINDS.values() for t in targets}):
        base = os.path.join(project, d)
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if os.path.islink(p) and not os.path.exists(p):
                target = os.path.normpath(os.path.join(os.path.realpath(base), os.readlink(p)))
                if is_lib_path(target):
                    dead.append((os.path.join(d, name), target))
    return dead


def git_out(root, *args):
    """stdout of `git -C root ...`, or None on any failure."""
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def lib_slug():
    """'owner/repo' of REPO's origin remote (the lib id recorded in manifests)."""
    url = git_out(REPO, "remote", "get-url", "origin") or ""
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def load_manifest(project):
    path = os.path.join(project, MANIFEST)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f"bad {path}: {e}")


def save_manifest(project, m):
    m["items"] = {k: sorted(set(v)) for k, v in sorted(m["items"].items()) if v}
    m["copies"] = dict(sorted(m.get("copies", {}).items()))
    if not m["copies"]:
        del m["copies"]
    with open(os.path.join(project, MANIFEST), "w") as f:
        json.dump(m, f, indent=2)
        f.write("\n")


def in_manifest(m, item):
    return bool(m) and item[1] in m["items"].get(item[0], [])


def present(project, item, copy):
    """True if the item really exists in project in the requested mode (link, or real copy)."""
    if not copy:
        return link_state(project, item)
    return any(os.path.lexists(p := os.path.join(project, t, item[1])) and not os.path.islink(p) for t in item[3])


def record(project, add, drop, copy, dry):
    """Update <project>/.my-pick.json after a pick/remove. Skipped for dry runs and for the lib itself."""
    if dry or os.path.realpath(project) == REPO or not (add or drop):
        return
    m = load_manifest(project) or {"lib": lib_slug(), "ref": git_out(REPO, "rev-parse", "HEAD"), "items": {}}
    m.setdefault("copies", {})
    for i in add:
        names = m["items"].setdefault(i[0], [])
        if i[1] not in names:
            names.append(i[1])
        if copy:  # provenance: which lib commit + content the copy came from
            m["copies"][f"{i[0]}/{i[1]}"] = {"ref": git_out(REPO, "rev-parse", "HEAD"), "hash": hash_path(i[2])}
        else:
            m["copies"].pop(f"{i[0]}/{i[1]}", None)
    for i in drop:
        if i[1] in m["items"].get(i[0], []):
            m["items"][i[0]].remove(i[1])
        m["copies"].pop(f"{i[0]}/{i[1]}", None)
    save_manifest(project, m)


def offer_gitignore(project, yes):
    """Ask to add our symlink paths (one line each, never whole dirs) to the project's .gitignore, no duplicates."""
    m = load_manifest(project)
    if not m or not os.path.isdir(os.path.join(project, ".git")) or os.path.realpath(project) == REPO:
        return
    rels = [f"/{t}/{name}" for kind, names in m["items"].items() for name in names
            if f"{kind}/{name}" not in m.get("copies", {})
            for t in KINDS[kind][1] if os.path.islink(os.path.join(project, t, name))]
    path = os.path.join(project, ".gitignore")
    text = open(path).read() if os.path.exists(path) else ""
    have = set(text.splitlines())
    new = [r for r in rels if r not in have]
    if not new:
        return
    if not yes:
        if not sys.stdin.isatty():
            print(f"note: {len(new)} link path(s) not in .gitignore; re-run on a terminal or with --yes")
            return
        if input(f"Add {len(new)} link path(s) to .gitignore? [y/N] ").strip().lower() not in ("y", "yes"):
            return
    header = "# my-pick symlinks (recreate with `my-pick sync`)"
    with open(path, "a") as f:
        if text and not text.endswith("\n"):
            f.write("\n")
        if header not in have:
            f.write(header + "\n")
        f.write("\n".join(new) + "\n")
    print(f"  .gitignore: +{len(new)}")


def get_lib(m):
    """Lib checkout for sync: REPO if it is the manifest's lib, else a clone in CACHE checked out at the pinned ref."""
    slug, ref = m.get("lib"), m.get("ref")
    if slug and slug == lib_slug():
        head = git_out(REPO, "rev-parse", "HEAD")
        if ref and head and head != ref:
            print(f"warning: local lib at {head[:8]}, manifest pins {ref[:8]}; using local (`my-pick --update` repins)",
                  file=sys.stderr)
        return REPO
    if not slug:
        sys.exit(f"{MANIFEST} has no 'lib'")
    if not os.path.isdir(os.path.join(CACHE, ".git")):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        print(f"cloning {slug} -> {CACHE}")
        if subprocess.run(["git", "clone", "-q", f"https://github.com/{slug}.git", CACHE]).returncode:
            sys.exit(f"clone of {slug} failed")
    if ref:
        if subprocess.run(["git", "-C", CACHE, "cat-file", "-e", f"{ref}^{{commit}}"], capture_output=True).returncode:
            subprocess.run(["git", "-C", CACHE, "fetch", "-q", "origin"])
        if subprocess.run(["git", "-C", CACHE, "checkout", "-q", "--detach", ref]).returncode:
            sys.exit(f"can't check out pinned ref {ref} in {CACHE}")
    return os.path.realpath(CACHE)


def sync(project, dry):
    """Recreate every item in the manifest (links, or copies where recorded). Idempotent."""
    m = load_manifest(project)
    if not m:
        sys.exit(f"no {MANIFEST} in {project}; pick something first")
    lib = get_lib(m)
    items = {(i[0], i[1]): i for i in discover(lib)}
    links, missing = [], 0
    for kind, names in m["items"].items():
        for name in names:
            item = items.get((kind, name))
            if not item:
                print(f"  ! {kind}/{name} not in lib at {(m.get('ref') or 'HEAD')[:8]}")
                missing += 1
                continue
            copy = f"{kind}/{name}" in m.get("copies", {})
            added = link(project, item, dry, copy)
            if not copy:
                links += added
    git_exclude(project, links, dry)
    print("sync: dry run" if dry else "sync: done")
    if missing:
        sys.exit(f"{missing} manifest item(s) missing from lib")


def update_ref(project, dry):
    """Bump the manifest's pinned ref to the lib remote's HEAD."""
    m = load_manifest(project)
    if not m:
        sys.exit(f"no {MANIFEST} in {project}")
    slug = m.get("lib")
    remote = "origin" if slug == lib_slug() else f"https://github.com/{slug}.git"
    out = git_out(REPO, "ls-remote", remote, "HEAD")
    if not out:
        sys.exit(f"can't read HEAD of {slug} (offline?)")
    latest = out.split()[0]
    if latest == m.get("ref"):
        print(f"update: already at {latest[:8]}")
        return
    print(f"update: {(m.get('ref') or 'none')[:8]} -> {latest[:8]}")
    if not dry:
        m["ref"] = latest
        save_manifest(project, m)
    head = git_out(REPO, "rev-parse", "HEAD")
    if slug == lib_slug() and head != latest:
        print(f"note: local lib at {(head or '?')[:8]}; `git pull` there to match")


def choose_prune(dead):
    import questionary  # lazy: --yes works without it
    choices = [questionary.Choice(f"{rel}  ->  {tgt}", value=rel, checked=True) for rel, tgt in dead]
    return questionary.checkbox("Dead links. Space = toggle, Enter = delete selected", choices=choices).ask()


def prune(project, dry, yes):
    dead = find_dead(project)
    if not dead:
        print("prune: no dead links")
        return
    if yes or dry:  # a dry run deletes nothing, so no confirmation needed
        rels = [r for r, _ in dead]
    elif sys.stdin.isatty():
        rels = choose_prune(dead)
        if not rels:
            print("prune: nothing selected")
            return
    else:
        sys.exit("prune needs a terminal to confirm; use --yes")
    for rel in rels:
        print(f"  - {rel}")
        if not dry:
            os.remove(os.path.join(project, rel))
    git_unexclude(project, rels, dry)
    m = None if dry or os.path.realpath(project) == REPO else load_manifest(project)
    if m:  # drop manifest entries whose every target is now gone
        gone = [(k, n) for k, names in m["items"].items() for n in names
                if not any(os.path.lexists(os.path.join(project, t, n)) for t in KINDS[k][1])]
        for k, n in gone:
            m["items"][k].remove(n)
            m.get("copies", {}).pop(f"{k}/{n}", None)
        if gone:
            save_manifest(project, m)
    print(f"prune: dry run, {len(rels)} would be removed" if dry else f"prune: removed {len(rels)}")


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


def choose(project, items, m=None):
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
            choices.append(questionary.Choice(title, value=i, checked=link_state(project, i) or in_manifest(m, i)))
    return questionary.checkbox("Space = toggle, Enter = apply", choices=choices).ask()


def finish(project, want, drop, copy, added, dry, yes):
    """Shared tail of every pick run: manifest, local git exclude, optional .gitignore."""
    record(project, [i for i in want if present(project, i, copy)], drop, copy, dry)
    if not copy:
        git_exclude(project, added, dry)
    if not dry:
        offer_gitignore(project, yes)
    print("dry run, nothing changed" if dry else f"done: {project}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="*", metavar="[sync] [project]", help="project dir (default .); 'sync' first = run sync")
    ap.add_argument("--update", action="store_true", help="bump the ref pinned in .my-pick.json to the lib remote's HEAD")
    ap.add_argument("--list", action="store_true", help="print everything available (+ linked status) and exit")
    ap.add_argument("--describe", metavar="NAME", help="print the full, untruncated description of one item (exact name, else substring matches) and exit")
    ap.add_argument("--all", action="store_true", help="link everything (incl. rules), no prompt")
    ap.add_argument("--pick", nargs="+", metavar="NAME", help="non-interactive: link these items (NAME or KIND/NAME), additive; nothing else is unlinked")
    ap.add_argument("--preset", nargs="+", metavar="P", help=f"non-interactive: link every item in the named preset(s) from {os.path.basename(PRESETS)}")
    ap.add_argument("--remove", nargs="+", metavar="NAME", help="non-interactive: unlink these items (only links into this repo)")
    ap.add_argument("--prune", action="store_true", help="remove dangling symlinks that point into this lib (asks first; combine with --pick/--preset to relink after)")
    ap.add_argument("--yes", action="store_true", help="auto-accept prompts: --prune confirmation, .gitignore edit (needed when not on a terminal)")
    ap.add_argument("--kind", help="comma-separated kinds to limit to: skills,agents,commands,rules")
    ap.add_argument("--copy", action="store_true", help="copy real files instead of symlinks (zero-tooling repos: CI/cloud/collaborators); provenance goes in .my-pick.json")
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

    do_sync = bool(a.target) and a.target[0] == "sync"
    rest = a.target[1:] if do_sync else a.target
    if len(rest) > 1:
        sys.exit("at most one project dir")
    proj_arg = rest[0] if rest else "."
    project = os.path.abspath(proj_arg)
    if not os.path.isdir(project):
        sys.exit(f"not a directory: {project}")
    if do_sync:
        return sync(project, a.dry_run)
    if a.update:
        return update_ref(project, a.dry_run)
    if a.prune:
        prune(project, a.dry_run, a.yes)
        if not (a.pick or a.preset or a.remove or a.all or a.list):
            return
    elif not a.describe:
        n = len(find_dead(project))
        if n:
            print(f"warning: {n} dead link(s) in {project}; run `my-pick {proj_arg} --prune`", file=sys.stderr)
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

    if a.pick or a.preset or a.remove:
        if a.all:
            sys.exit("--all can't combine with --pick/--preset/--remove")
        want = resolve(items, (a.pick or []) + (preset_names(a.preset) if a.preset else []))
        drop = resolve(items, a.remove or [])
        clash = {(i[0], i[1]) for i in want} & {(i[0], i[1]) for i in drop}
        if clash:
            sys.exit(f"both picked and removed: {', '.join(f'{k}/{n}' for k, n in sorted(clash))}")
        added = []
        for i in want:
            if link_state(project, i) and not a.copy:
                print(f"  = {i[1]} already linked")
            else:
                added += link(project, i, a.dry_run, a.copy)
        for i in drop:
            unlink(project, i, a.dry_run)
        finish(project, want, drop, a.copy, added, a.dry_run, a.yes)
        return

    if a.all:
        picks = items
    else:
        if not sys.stdin.isatty():
            sys.exit("interactive only; use --pick/--preset, --all or --list")
        picks = choose(project, items, load_manifest(project))
        if picks is None:
            sys.exit("cancelled")

    picked = {(i[0], i[1]) for i in picks}
    m = load_manifest(project)
    added, drop = [], []
    for i in items:
        linked, want = link_state(project, i), (i[0], i[1]) in picked
        if want:
            added += link(project, i, a.dry_run, a.copy)
        elif (linked or in_manifest(m, i)) and not a.all:
            unlink(project, i, a.dry_run)
            drop.append(i)
    finish(project, [i for i in items if (i[0], i[1]) in picked], drop, a.copy, added, a.dry_run, a.yes)


if __name__ == "__main__":
    main()
