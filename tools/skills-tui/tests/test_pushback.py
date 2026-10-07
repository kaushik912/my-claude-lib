import subprocess

import pytest

from skills_tui.pushback import PushError, apply_push, plan_push


@pytest.fixture
def glib(lib):
    """lib as a git repo that ignores credential files."""
    subprocess.run(["git", "init", "-q", str(lib)], check=True)
    (lib / ".gitignore").write_text("*.cnf\n")
    return lib


@pytest.fixture
def proj(glib, tmp_path):
    p = tmp_path / "proj"
    d = p / ".agents/skills/alpha"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("alpha desc improved")   # changed
    return p


def test_given_changed_and_added_when_plan_then_copy_both_and_apply_writes_lib(glib, proj):
    (proj / ".agents/skills/alpha/refs").mkdir()
    (proj / ".agents/skills/alpha/refs/new.md").write_text("new")
    plan = plan_push(proj, glib, "alpha")
    assert set(plan.copy) == {"SKILL.md", "refs/new.md"} and plan.added == ("refs/new.md",)
    apply_push(plan)
    assert (glib / "skills/alpha/SKILL.md").read_text() == "alpha desc improved"
    assert (glib / "skills/alpha/refs/new.md").read_text() == "new"
    assert not list((glib / "skills/alpha").rglob("*push-tmp"))


def test_given_file_deleted_in_project_when_push_then_not_propagated(glib, proj):
    (glib / "skills/alpha/extra.md").write_text("keep me")
    plan = plan_push(proj, glib, "alpha")
    assert plan.not_propagated == ("extra.md",)
    apply_push(plan)
    assert (glib / "skills/alpha/extra.md").read_text() == "keep me"


def test_given_gitignored_credentials_when_push_then_skipped_and_never_copied(glib, proj):
    (proj / ".agents/skills/alpha/db.cnf").write_text("password=secret")
    plan = plan_push(proj, glib, "alpha")
    assert "db.cnf" not in plan.copy and ("db.cnf", "ignored by the lib's .gitignore") in plan.skipped
    apply_push(plan)
    assert not (glib / "skills/alpha/db.cnf").exists()


def test_given_symlink_in_project_skill_when_push_then_skipped(glib, proj, tmp_path):
    (tmp_path / "outside.txt").write_text("outside")
    (proj / ".agents/skills/alpha/link.md").symlink_to(tmp_path / "outside.txt")
    plan = plan_push(proj, glib, "alpha")
    assert ("link.md", "symlink") in plan.skipped and "link.md" not in plan.copy


def test_given_only_skipped_files_when_push_then_error(glib, proj):
    (proj / ".agents/skills/alpha/SKILL.md").write_bytes((glib / "skills/alpha/SKILL.md").read_bytes())  # identical
    (proj / ".agents/skills/alpha/db.cnf").write_text("x")  # ignored
    with pytest.raises(PushError, match="nothing to push"):
        plan_push(proj, glib, "alpha")


def test_given_lib_not_a_git_repo_when_push_then_error_instead_of_copying_blindly(lib, tmp_path):
    p = tmp_path / "proj/.agents/skills/alpha"
    p.mkdir(parents=True)
    (p / "SKILL.md").write_text("changed")
    with pytest.raises(PushError, match="git repo"):
        plan_push(tmp_path / "proj", lib, "alpha")


def test_given_executable_when_push_then_mode_preserved(glib, proj):
    run = proj / ".agents/skills/alpha/run.sh"
    run.write_text("#!/bin/sh")
    run.chmod(0o755)
    apply_push(plan_push(proj, glib, "alpha"))
    assert (glib / "skills/alpha/run.sh").stat().st_mode & 0o111
