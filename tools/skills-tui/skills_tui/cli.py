import argparse
import sys
from pathlib import Path

from . import tui
from .catalog import load_catalog
from .installed import installed_skills
from .plan import make_plan
from .profiles import ProfileError, load_profiles, resolve
from .runner import build_commands, run

TOOL_DIR = Path(__file__).resolve().parents[1]
LIB = TOOL_DIR.parents[1]


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="skills-tui", description="Pick skills from the lib and install them via `npx skills`.")
    ap.add_argument("project", nargs="?", default=".", help="project dir (default .)")
    ap.add_argument("--profile", nargs="+", default=[], metavar="P", help="pre-tick these profiles")
    ap.add_argument("--pick", nargs="+", default=[], metavar="NAME", help="pre-tick these skills")
    ap.add_argument("--no-tui", action="store_true", help="additive install of --profile/--pick, no prompt")
    ap.add_argument("--list", action="store_true", help="print catalog with installed marks and exit")
    ap.add_argument("--agent", default="claude-code")
    ap.add_argument("--global", dest="global_", action="store_true", help="user-level instead of project")
    ap.add_argument("--yes", action="store_true", help="skip confirmation")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--lib", type=Path, default=LIB, help=argparse.SUPPRESS)
    ap.add_argument("--profiles-file", type=Path, default=TOOL_DIR / "profiles.json", help=argparse.SUPPRESS)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    a = parse_args(argv)
    project = Path(a.project).resolve()
    catalog = load_catalog(a.lib)
    names = {s.name for s in catalog}
    have = installed_skills(project)
    profiles = load_profiles(a.profiles_file)

    if a.list:
        for s in catalog:
            print(f"{'*' if s.name in have else ' '} {s.name:24} {s.origin:9} {s.description[:60]}")
        return 0

    try:
        pre = set(a.pick)
        for p in a.profile:
            pre |= resolve(p, profiles, names)
    except ProfileError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if pre - names:
        print(f"error: unknown skills: {', '.join(sorted(pre - names))}", file=sys.stderr)
        return 2

    if a.no_tui:
        selected = have | pre
    else:
        chosen = [] if (a.profile or a.pick) else tui.pick_profiles(profiles)
        try:
            for p in chosen:
                pre |= resolve(p, profiles, names)
        except ProfileError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        selected = tui.pick_skills(catalog, have, pre)
        if selected is None:
            return 130

    plan = make_plan(selected, have, names)
    if not plan:
        print("nothing to do")
        return 0
    print(f"add: {', '.join(plan.to_add) or '-'}\nremove: {', '.join(plan.to_remove) or '-'}")
    if not (a.yes or a.dry_run or a.no_tui):
        if input("Apply? [y/N] ").strip().lower() != "y":
            return 1
    return run(build_commands(plan, a.lib, a.agent, a.global_), project, a.dry_run)
