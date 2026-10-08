#!/usr/bin/env python3
"""Scan a tree for .claude/skills and .agents/skills; emit JSON of unique skills per project.

Usage: skill-inventory.py [ROOT] [-o FILE] [--skip DIR ...]
"""
import argparse
import json
import os
import sys

SKILL_DIRS = (".claude/skills", ".agents/skills")
DEFAULT_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "build", "dist"}


def is_skills_dir(path):
    norm = path.replace(os.sep, "/")
    return any(norm.endswith("/" + s) for s in SKILL_DIRS)


def read_skills(skills_dir):
    """Yield (name, is_symlink, broken) for each skill entry in a skills dir."""
    for name in sorted(os.listdir(skills_dir)):
        entry = os.path.join(skills_dir, name)
        link = os.path.islink(entry)
        if link and not os.path.exists(entry):
            yield name, True, True
        elif os.path.isfile(os.path.join(entry, "SKILL.md")):
            yield name, link, False


def scan(root, skip):
    projects = {}
    for dirpath, dirnames, _ in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for sub in SKILL_DIRS:
            parts = sub.split("/")
            if os.path.basename(dirpath) != parts[0] or parts[1] not in dirnames:
                continue
            skills_dir = os.path.join(dirpath, parts[1])
            project = os.path.relpath(os.path.dirname(dirpath), root)
            by_name = projects.setdefault(project, {})
            for name, link, broken in read_skills(skills_dir):
                item = by_name.setdefault(name, {"name": name, "locations": [], "symlink": False, "broken": False})
                item["locations"].append(sub)
                item["symlink"] |= link
                item["broken"] |= broken
            if parts[1] in dirnames:
                dirnames.remove(parts[1])  # don't descend into skills dir itself
    return {p: sorted(s.values(), key=lambda i: i["name"]) for p, s in sorted(projects.items())}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=".", help="directory to scan (default .)")
    ap.add_argument("-o", "--output", help="write JSON here (default stdout)")
    ap.add_argument("--skip", nargs="*", default=[], help="extra directory names to skip")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    projects = scan(root, DEFAULT_SKIP | set(args.skip))

    all_skills = {}
    for project, skills in projects.items():
        for s in skills:
            all_skills.setdefault(s["name"], []).append(project)

    result = {
        "root": root,
        "projects": {p: {"skills": s} for p, s in projects.items()},
        "all_skills": {n: {"count": len(ps), "projects": ps} for n, ps in sorted(all_skills.items())},
    }
    out = json.dumps(result, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(out + "\n")
        print(f"wrote {args.output}: {len(projects)} projects, {len(all_skills)} unique skills", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
