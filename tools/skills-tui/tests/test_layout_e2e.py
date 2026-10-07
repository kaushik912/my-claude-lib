"""Real `npx skills` end to end: the open-source layout (real files .agents/skills, symlinks .claude/skills)."""
import shutil

import pytest

from skills_tui import cli

pytestmark = pytest.mark.skipif(not shutil.which("npx"), reason="npx not installed")


def run(proj, *args):
    return cli.main([str(proj), *args])


def test_given_fresh_install_when_run_then_real_files_in_agents_and_symlinks_in_claude_and_doctor_healthy(tmp_path):
    if run(tmp_path, "--pick", "skills/karpathy-guidelines", "--no-tui") != 0:
        pytest.skip("npx skills unavailable")
    real, link = tmp_path / ".agents/skills/karpathy-guidelines", tmp_path / ".claude/skills/karpathy-guidelines"
    assert real.is_dir() and not real.is_symlink()
    assert link.is_symlink() and link.resolve() == real.resolve()
    assert run(tmp_path, "--doctor", "--yes") == 0
    assert run(tmp_path, "--list") == 0


def test_given_missing_link_when_doctor_yes_then_relinked(tmp_path):
    if run(tmp_path, "--pick", "skills/karpathy-guidelines", "--no-tui") != 0:
        pytest.skip("npx skills unavailable")
    (tmp_path / ".claude/skills/karpathy-guidelines").unlink()
    assert run(tmp_path, "--doctor", "--yes") == 0
    assert (tmp_path / ".claude/skills/karpathy-guidelines").is_symlink()
    assert run(tmp_path, "--doctor", "--yes") == 0
