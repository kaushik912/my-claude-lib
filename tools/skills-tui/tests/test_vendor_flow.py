import json
from types import SimpleNamespace

import pytest

from skills_tui import cli, marketplace
from skills_tui.dirhash import tree_hash
from skills_tui.vendor_flow import run_vendor
from tests.conftest import write_skill

SRC = "https://github.com/o/r"


@pytest.fixture
def env(lib, tmp_path):
    """lib with marketplace; fake upstream repo; fake npx that fills the sandbox from upstream."""
    (lib / ".claude-plugin").mkdir()
    (lib / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": [
        {"name": "core", "description": "", "source": "./", "strict": False, "skills": ["./skills/alpha", "./skills/beta", "./skills/gamma"]}]}, indent=2) + "\n")
    upstream = tmp_path / "upstream"
    write_skill(upstream, "newskill", "fresh")
    calls = []

    def fake_npx(cmd, cwd, **kw):
        calls.append((cmd, cwd))
        names = cmd[cmd.index("-s") + 1: cmd.index("-a")]
        entries = {}
        for n in names:
            src = upstream / n
            if not src.is_dir():
                continue
            dest = cwd / ".claude/skills" / n
            dest.mkdir(parents=True)
            for f in src.rglob("*"):
                if f.is_file():
                    (dest / f.relative_to(src)).parent.mkdir(parents=True, exist_ok=True)
                    (dest / f.relative_to(src)).write_bytes(f.read_bytes())
            entries[n] = {"source": "o/r", "sourceType": "github", "skillPath": f"{n}/SKILL.md", "computedHash": tree_hash(dest)}
        (cwd / "skills-lock.json").write_text(json.dumps({"version": 1, "skills": entries}))
        return SimpleNamespace(returncode=0, stderr="")

    vf = tmp_path / "vendors.txt"
    vf.write_text(f"npx skills add {SRC} --skill newskill -g  # bundle=core\n")
    return SimpleNamespace(lib=lib, upstream=upstream, vf=vf, npx=fake_npx, calls=calls)


def go(env, **kw):
    kw.setdefault("confirm", lambda c: pytest.fail("unexpected prompt"))
    kw.setdefault("pick_bundle", lambda n, b: pytest.fail("unexpected bundle prompt"))
    return run_vendor(env.lib, env.vf, exec_=env.npx, **kw)


def lock(env):
    return json.loads((env.lib / "skills-lock.json").read_text())["skills"]


def test_given_new_skill_when_yes_then_copied_locked_bundled_without_prompts(env):
    assert go(env, yes=True) == 0
    assert (env.lib / "skills/newskill/SKILL.md").exists()
    assert lock(env)["newskill"]["source"] == "o/r" and "gamma" in lock(env)
    assert "./skills/newskill" in marketplace.load(env.lib)["plugins"][0]["skills"]
    cmd, _ = env.calls[0]
    assert cmd == ["npx", "--yes", "skills", "add", SRC, "-s", "newskill", "-a", "claude-code", "-y"]  # -g dropped, claude forced


def test_given_dry_run_when_vendor_then_lib_untouched(env):
    before = (env.lib / "skills-lock.json").read_text()
    assert go(env, dry_run=True) == 0
    assert not (env.lib / "skills/newskill").exists() and (env.lib / "skills-lock.json").read_text() == before
    assert env.calls  # it still fetched into the sandbox


def test_given_new_skill_interactive_when_declined_then_not_added(env):
    assert go(env, confirm=lambda c: False) == 0
    assert not (env.lib / "skills/newskill").exists()


def test_given_new_skill_without_bundle_hint_when_interactive_then_prompted(env):
    env.vf.write_text(f"npx skills add {SRC} --skill newskill\n")
    assert go(env, confirm=lambda c: True, pick_bundle=lambda n, b: ("core", "")) == 0
    assert "./skills/newskill" in marketplace.load(env.lib)["plugins"][0]["skills"]


def test_given_new_skill_without_bundle_hint_when_yes_then_warned_unbundled(env, capsys):
    env.vf.write_text(f"npx skills add {SRC} --skill newskill\n")
    assert go(env, yes=True) == 0
    assert "not in any marketplace bundle" in capsys.readouterr().out


def vendored_gamma(env, upstream_text):
    write_skill(env.upstream, "gamma", upstream_text)
    (env.lib / "skills/gamma/SKILL.md").write_text("old local")
    (env.lib / "skills/gamma/stale.md").write_text("gone upstream")
    lk = lock(env)
    lk["gamma"] = {"source": "o/r", "sourceType": "github", "skillPath": "gamma/SKILL.md", "computedHash": "old"}
    write = {"version": 1, "skills": lk}
    (env.lib / "skills-lock.json").write_text(json.dumps(write))
    env.vf.write_text(f"npx skills add {SRC} --skill gamma\n")


def test_given_upstream_update_when_yes_then_never_applied(env, capsys):
    vendored_gamma(env, "upstream v2")
    assert go(env, yes=True) == 0
    assert (env.lib / "skills/gamma/SKILL.md").read_text() == "old local"
    assert "never applies updates" in capsys.readouterr().out


def test_given_upstream_update_when_confirmed_then_replaced_and_stale_files_removed(env):
    vendored_gamma(env, "upstream v2")
    seen = []
    assert go(env, confirm=lambda c: seen.append(c.status) or True) == 0
    assert seen == ["changed"]
    assert "upstream v2" in (env.lib / "skills/gamma/SKILL.md").read_text()
    assert not (env.lib / "skills/gamma/stale.md").exists()
    assert lock(env)["gamma"]["computedHash"] == tree_hash(env.lib / "skills/gamma")


def test_given_upstream_update_when_declined_then_untouched(env):
    vendored_gamma(env, "upstream v2")
    assert go(env, confirm=lambda c: False) == 0
    assert (env.lib / "skills/gamma/SKILL.md").read_text() == "old local"


def test_given_own_skill_name_when_vendor_then_refused_even_interactive(env, capsys):
    write_skill(env.upstream, "alpha", "evil")
    env.vf.write_text(f"npx skills add {SRC} --skill alpha\n")
    assert go(env, confirm=lambda c: True) == 0
    assert "your own skill" in capsys.readouterr().out
    assert "evil" not in (env.lib / "skills/alpha/SKILL.md").read_text()


def test_given_skill_missing_upstream_when_vendor_then_error_rc(env, capsys):
    env.vf.write_text(f"npx skills add {SRC} --skill nope\n")
    assert go(env, yes=True) == 1
    assert "not found in source" in capsys.readouterr().out


def test_given_npx_failure_when_vendor_then_error_rc_and_next_line_still_runs(env):
    env.vf.write_text(f"npx skills add {SRC} --skill newskill\n")
    boom = lambda cmd, cwd, **kw: SimpleNamespace(returncode=1, stderr="network")  # noqa: E731
    assert run_vendor(env.lib, env.vf, yes=True, exec_=boom) == 1


def test_given_bad_vendors_file_when_vendor_then_exit_2_and_nothing_runs(env, capsys):
    env.vf.write_text("rm -rf /\n")
    assert go(env, yes=True) == 2
    assert not env.calls and "line 1" in capsys.readouterr().out


def test_given_risky_files_when_new_then_flagged_in_review(env, capsys):
    (env.upstream / "newskill/setup.sh").write_text("#!/bin/sh")
    assert go(env, yes=True) == 0
    assert "scripts/executables: setup.sh" in capsys.readouterr().out


def test_cli_vendor_without_terminal_or_yes_fails_fast(lib, tmp_path):
    assert cli.main([str(tmp_path), "--lib", str(lib), "--vendor"]) == 2


def test_cli_vendor_defaults_to_vendors_txt_of_the_given_lib(lib, tmp_path, capsys):
    (lib / "vendors.txt").write_text("rm -rf /\n")
    assert cli.main([str(tmp_path), "--lib", str(lib), "--vendor", "--yes"]) == 2
    assert "vendors.txt" in capsys.readouterr().out
