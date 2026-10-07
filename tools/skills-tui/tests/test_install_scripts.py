import os
import subprocess
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1]


def sh(script, bin_dir):
    env = {**os.environ, "BIN_DIR": str(bin_dir), "SKIP_DEPS": "1"}
    return subprocess.run(["bash", str(TOOL / script)], env=env, capture_output=True, text=True)


def test_given_install_then_uninstall_when_run_then_link_added_and_removed(tmp_path):
    assert sh("install.sh", tmp_path).returncode == 0
    link = tmp_path / "skills-tui"
    assert link.is_symlink() and link.resolve() == TOOL / "skills-tui"
    assert sh("install.sh", tmp_path).returncode == 0  # idempotent
    assert sh("uninstall.sh", tmp_path).returncode == 0
    assert not link.exists()


def test_given_foreign_link_when_uninstall_then_refuses(tmp_path):
    (tmp_path / "skills-tui").symlink_to("/bin/true")
    assert sh("uninstall.sh", tmp_path).returncode == 1
    assert (tmp_path / "skills-tui").is_symlink()
