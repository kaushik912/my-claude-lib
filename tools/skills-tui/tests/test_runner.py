from pathlib import Path
from types import SimpleNamespace

from skills_tui.kinds import Action, Ctx
from skills_tui.kinds.skills import SkillsKind
from skills_tui.plan import Plan
from skills_tui.runner import build_actions, run

CTX = Ctx(Path("/proj"), Path("/lib"))


def test_given_plan_when_build_then_add_and_remove_labels():
    a = build_actions(Plan(("skills/a", "skills/b"), ("skills/c",)), [SkillsKind()], CTX)
    assert a[0].label == "npx --yes skills add /lib -s a b -a claude-code codex -y"
    assert a[1].label == "npx --yes skills remove c -a claude-code codex -y"


def test_given_global_when_build_then_flag_appended():
    ctx = Ctx(Path("/proj"), Path("/lib"), global_=True)
    (a,) = build_actions(Plan(("skills/a",), ()), [SkillsKind()], ctx)
    assert a.label.endswith("-a claude-code codex -y -g")


def test_given_action_when_run_then_executes_in_project_dir():
    calls = []
    ctx = Ctx(Path("/proj"), Path("/lib"), exec_=lambda cmd, cwd: calls.append((cmd[3], cwd)) or SimpleNamespace(returncode=0))
    (a,) = build_actions(Plan(("skills/a",), ()), [SkillsKind()], ctx)
    assert run([a]) == 0
    assert calls == [("add", Path("/proj"))]


def test_given_dry_run_when_run_then_nothing_executed():
    hit = []
    assert run([Action("x", lambda: hit.append(1) or 0)], dry_run=True) == 0
    assert not hit


def test_given_failure_when_run_then_stops_and_returns_rc():
    hit = []
    acts = [Action("a", lambda: hit.append("a") or 3), Action("b", lambda: hit.append("b") or 0)]
    assert run(acts) == 3
    assert hit == ["a"]
