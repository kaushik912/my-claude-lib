import shutil
from types import SimpleNamespace

from skills_tui import cli
from skills_tui.doctor_flow import run_doctor
from skills_tui.kinds import Ctx
from tests.test_doctor import installed


def make(lib, tmp_path):
    """alpha outdated (rec update), beta modified (no rec), gamma orphan (rec delete)."""
    for n in ("alpha", "beta", "gamma"):
        installed(tmp_path, lib, n)
    (lib / "skills/alpha/SKILL.md").write_text("new")
    (tmp_path / ".claude/skills/beta/SKILL.md").write_text("mine")
    shutil.rmtree(lib / "skills/gamma")
    calls = []
    ctx = Ctx(tmp_path, lib, exec_=lambda cmd, cwd: calls.append(cmd) or SimpleNamespace(returncode=0))
    return ctx, calls


def test_given_yes_when_doctor_then_only_recommended_applied(lib, tmp_path):
    ctx, calls = make(lib, tmp_path)
    assert run_doctor(tmp_path, lib, ctx, yes=True) == 0
    assert [c[3:7] for c in calls] == [["add", str(lib), "-s", "alpha"], ["remove", "gamma", "-a", "claude-code"]]


def test_given_choices_when_doctor_then_each_decision_honoured(lib, tmp_path):
    ctx, calls = make(lib, tmp_path)
    choose = lambda issues: {"alpha": "keep", "beta": "update", "gamma": "keep"}  # noqa: E731
    assert run_doctor(tmp_path, lib, ctx, choose=choose, confirm=lambda: True) == 0
    assert len(calls) == 1 and calls[0][3:7] == ["add", str(lib), "-s", "beta"]


def test_given_all_keep_when_doctor_then_nothing_runs(lib, tmp_path):
    ctx, calls = make(lib, tmp_path)
    assert run_doctor(tmp_path, lib, ctx, choose=lambda i: {x.name: "keep" for x in i}) == 0
    assert not calls


def test_given_decline_or_cancel_when_doctor_then_nothing_runs(lib, tmp_path):
    ctx, calls = make(lib, tmp_path)
    assert run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "update"}, confirm=lambda: False) == 1
    assert run_doctor(tmp_path, lib, ctx, choose=lambda i: None) == 1
    assert not calls


def test_given_dry_run_when_doctor_then_nothing_runs(lib, tmp_path, capsys):
    ctx, calls = make(lib, tmp_path)
    assert run_doctor(tmp_path, lib, ctx, yes=True, dry_run=True) == 0
    assert not calls and "npx --yes skills add" in capsys.readouterr().out


def test_given_healthy_when_doctor_then_message(lib, tmp_path, capsys):
    installed(tmp_path, lib, "alpha")
    assert run_doctor(tmp_path, lib, Ctx(tmp_path, lib)) == 0
    assert "healthy" in capsys.readouterr().out


def test_cli_doctor_flag_dry_run_and_global_rejected(lib, tmp_path, capsys):
    make(lib, tmp_path)
    base = [str(tmp_path), "--lib", str(lib)]
    assert cli.main([*base, "--doctor", "--yes", "--dry-run"]) == 0
    assert "outdated" in capsys.readouterr().out
    assert cli.main([*base, "--doctor", "--global"]) == 2


def test_cli_doctor_without_terminal_or_yes_fails_fast(lib, tmp_path):
    make(lib, tmp_path)  # pytest stdin is not a tty
    assert cli.main([str(tmp_path), "--lib", str(lib), "--doctor"]) == 2
