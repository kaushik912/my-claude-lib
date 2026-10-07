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


# ---- push to lib ----

def push_env(lib, tmp_path):
    import subprocess

    subprocess.run(["git", "init", "-q", str(lib)], check=True)
    installed(tmp_path, lib, "alpha")
    (tmp_path / ".agents/skills/alpha/SKILL.md").write_text("better prompt")
    calls = []
    ctx = Ctx(tmp_path, lib, exec_=lambda cmd, cwd: calls.append(cmd) or SimpleNamespace(returncode=0))
    return ctx, calls


def test_given_push_decision_when_confirmed_then_lib_updated_and_no_npx(lib, tmp_path, capsys):
    ctx, calls = push_env(lib, tmp_path)
    rc = run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "push"}, confirm=lambda: True)
    assert rc == 0 and not calls
    assert (lib / "skills/alpha/SKILL.md").read_text() == "better prompt"
    assert "nothing committed" in capsys.readouterr().out


def test_given_push_then_second_doctor_when_run_then_lock_stale_update_refreshes(lib, tmp_path):
    from skills_tui.doctor import LOCK_STALE, diagnose

    ctx, calls = push_env(lib, tmp_path)
    run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "push"}, confirm=lambda: True)
    (issue,) = diagnose(tmp_path, lib)
    assert issue.state == LOCK_STALE and issue.recommended == "update"
    assert run_doctor(tmp_path, lib, ctx, yes=True) == 0
    assert calls and calls[0][3:7] == ["add", str(lib), "-s", "alpha"]


def test_given_push_when_declined_or_dry_run_then_lib_untouched(lib, tmp_path):
    ctx, calls = push_env(lib, tmp_path)
    before = (lib / "skills/alpha/SKILL.md").read_text()
    assert run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "push"}, confirm=lambda: False) == 1
    assert run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "push"}, dry_run=True) == 0
    assert (lib / "skills/alpha/SKILL.md").read_text() == before


def test_given_yes_when_doctor_then_push_is_never_applied(lib, tmp_path):
    ctx, calls = push_env(lib, tmp_path)
    before = (lib / "skills/alpha/SKILL.md").read_text()
    run_doctor(tmp_path, lib, ctx, yes=True)
    assert (lib / "skills/alpha/SKILL.md").read_text() == before


def test_given_push_error_when_doctor_then_rc_1_and_other_decisions_still_run(lib, tmp_path):
    ctx, calls = push_env(lib, tmp_path)
    shutil.rmtree(lib / ".git")  # lib no longer a git repo -> push refuses
    installed(tmp_path, lib, "beta")
    (lib / "skills/beta/SKILL.md").write_text("new")  # beta outdated
    rc = run_doctor(tmp_path, lib, ctx, choose=lambda i: {"alpha": "push", "beta": "update"}, confirm=lambda: True)
    assert rc == 1 and any("beta" in c for c in calls)
    assert (lib / "skills/alpha/SKILL.md").read_text() != "better prompt"
