import argparse
import sys
from pathlib import Path

from . import tui
from .catalog import ResolveError, installed_keys, load_catalog, resolve_key
from .kinds import KINDS, Ctx
from .plan import make_plan
from .profiles import load_profiles, resolve
from .runner import build_actions, run

TOOL_DIR = Path(__file__).resolve().parents[1]
LIB = TOOL_DIR.parents[1]


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="skills-tui", description="Pick skills from the lib and install them via `npx skills`.")
    ap.add_argument("project", nargs="?", default=".", help="project dir (default .)")
    ap.add_argument("--profile", nargs="+", default=[], metavar="P", help="pre-tick these profiles")
    ap.add_argument("--pick", nargs="+", default=[], metavar="NAME", help="pre-tick these items (name or kind/name)")
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
    catalog = load_catalog(a.lib, KINDS)
    names = {i.key for i in catalog}
    have = installed_keys(project, KINDS)
    profiles = load_profiles(a.profiles_file)

    if a.list:
        for i in catalog:
            print(f"{'*' if i.key in have else ' '} {i.key:36} {i.origin:9} {i.description[:50]}")
        return 0

    try:
        pre = {resolve_key(t, names) for t in a.pick}
        for p in a.profile:
            pre |= resolve(p, profiles, names)
    except ResolveError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if a.no_tui:
        selected = have | pre
    else:
        chosen = [] if (a.profile or a.pick) else tui.pick_profiles(profiles)
        try:
            for p in chosen:
                pre |= resolve(p, profiles, names)
        except ResolveError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        selected = tui.pick_items(catalog, have, pre)
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
    ctx = Ctx(project, a.lib, a.agent, a.global_)
    return run(build_actions(plan, KINDS, ctx), a.dry_run)
