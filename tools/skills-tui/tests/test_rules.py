import pytest

from skills_tui import cli
from skills_tui.kinds import Ctx
from skills_tui.kinds.rules import RulesKind


@pytest.fixture
def rlib(lib):
    r = lib / ".claude/rules"
    r.mkdir(parents=True)
    (r / "style.md").write_text("# Code Style\n\nuse tabs\n")
    (r / "naming.md").write_text("no heading here\n")
    return lib


def test_given_lib_when_catalog_then_rules_with_heading_description(rlib):
    items = {i.name: i for i in RulesKind().catalog(rlib)}
    assert set(items) == {"style", "naming"}
    assert items["style"].description == "Code Style" and items["style"].key == "rules/style"


def test_given_no_rules_dir_when_catalog_then_empty(lib):
    assert RulesKind().catalog(lib) == []


def test_given_add_when_run_then_real_file_copied_not_symlink(rlib, tmp_path):
    ctx = Ctx(tmp_path / "proj", rlib)
    for a in RulesKind().add(("style",), ctx):
        assert a.run() == 0
    dest = tmp_path / "proj/.claude/rules/style.md"
    assert dest.is_file() and not dest.is_symlink()
    assert dest.read_text() == "# Code Style\n\nuse tabs\n"
    assert RulesKind().installed(tmp_path / "proj") == {"style"}


def test_given_installed_when_remove_then_deleted_and_lib_untouched(rlib, tmp_path):
    ctx = Ctx(tmp_path, rlib)
    for a in RulesKind().add(("style",), ctx):
        a.run()
    for a in RulesKind().remove(("style",), ctx):
        assert a.run() == 0
    assert RulesKind().installed(tmp_path) == set()
    assert (rlib / ".claude/rules/style.md").exists()


def test_given_global_when_add_then_error(rlib, tmp_path):
    with pytest.raises(ValueError, match="project-only"):
        RulesKind().add(("style",), Ctx(tmp_path, rlib, global_=True))


def test_given_cli_pick_rule_when_run_then_copied(rlib, tmp_path):
    rc = cli.main([str(tmp_path), "--lib", str(rlib), "--no-tui", "--pick", "rules/style"])
    assert rc == 0 and (tmp_path / ".claude/rules/style.md").is_file()
