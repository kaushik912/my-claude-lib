from pathlib import Path
from types import SimpleNamespace

from skills_tui.plan import Plan
from skills_tui.runner import build_commands, run

LIB = Path("/lib")


def test_given_plan_when_build_then_add_and_remove_argv():
    cmds = build_commands(Plan(("a", "b"), ("c",)), LIB)
    assert cmds[0] == ["npx", "--yes", "skills", "add", "/lib", "-s", "a", "b", "-a", "claude-code", "-y"]
    assert cmds[1] == ["npx", "--yes", "skills", "remove", "c", "-a", "claude-code", "-y"]


def test_given_global_and_agent_when_build_then_flags():
    (cmd,) = build_commands(Plan(("a",), ()), LIB, agent="codex", global_=True)
    assert cmd[-4:] == ["-a", "codex", "-y", "-g"]


def test_given_dry_run_when_run_then_nothing_executed(tmp_path):
    calls = []
    assert run([["x"]], tmp_path, dry_run=True, exec_=lambda *a, **k: calls.append(a)) == 0
    assert not calls


def test_given_failure_when_run_then_stops_and_returns_rc(tmp_path):
    calls = []

    def fake(cmd, cwd):
        calls.append(cmd)
        return SimpleNamespace(returncode=3)

    assert run([["a"], ["b"]], tmp_path, exec_=fake) == 3
    assert calls == [["a"]]
