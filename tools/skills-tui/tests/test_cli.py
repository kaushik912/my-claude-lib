from skills_tui import cli
from tests.conftest import write_skill


def run_cli(lib, project, *args):
    return cli.main([str(project), "--lib", str(lib), "--profiles-file", str(lib / "p.json"), *args])


def test_given_no_tui_pick_when_dry_run_then_prints_add(lib, tmp_path, capsys):
    assert run_cli(lib, tmp_path, "--no-tui", "--pick", "alpha", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "add: skills/alpha" in out and f"skills add {lib} -s alpha" in out


def test_given_installed_when_no_tui_then_additive_only(lib, tmp_path, capsys):
    write_skill(tmp_path / ".agents/skills", "beta")
    run_cli(lib, tmp_path, "--no-tui", "--pick", "alpha", "--dry-run")
    assert "remove: -" in capsys.readouterr().out


def test_given_unknown_skill_when_pick_then_exit_2(lib, tmp_path):
    assert run_cli(lib, tmp_path, "--no-tui", "--pick", "nope") == 2


def test_given_profile_when_no_tui_then_installs_its_skills(lib, tmp_path, capsys):
    (lib / "p.json").write_text('{"x": {"skills": ["alpha", "beta"]}}')
    run_cli(lib, tmp_path, "--no-tui", "--profile", "x", "--dry-run")
    assert "add: skills/alpha, skills/beta" in capsys.readouterr().out


def test_given_installed_when_list_then_marked(lib, tmp_path, capsys):
    write_skill(tmp_path / ".agents/skills", "beta")
    run_cli(lib, tmp_path, "--list")
    lines = {l[2:].split()[0]: l[0] for l in capsys.readouterr().out.splitlines()}
    assert lines["skills/beta"] == "*" and lines["skills/alpha"] == " "


def test_given_everything_installed_when_run_then_nothing_to_do(lib, tmp_path, capsys):
    write_skill(tmp_path / ".agents/skills", "alpha")
    assert run_cli(lib, tmp_path, "--no-tui", "--pick", "alpha") == 0
    assert "nothing to do" in capsys.readouterr().out
