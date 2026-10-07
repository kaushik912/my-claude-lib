import pytest

from skills_tui import cli
from skills_tui.kinds import Ctx
from skills_tui.kinds.copy import CopyKind

KINDS = [CopyKind("rules", "rules"), CopyKind("commands", "commands"), CopyKind("agents", "agents")]
ids = [k.name for k in KINDS]


@pytest.fixture(params=KINDS, ids=ids)
def kind(request):
    return request.param


@pytest.fixture
def clib(lib, kind):
    d = lib / kind.dir
    d.mkdir(parents=True)
    (d / "style.md").write_text("# Code Style\n\nuse tabs\n")
    (d / "fm.md").write_text("---\nname: fm\ndescription: >-\n  from\n  frontmatter\n---\nbody\n")
    (d / "bare.md").write_text("no heading here\n")
    return lib


def test_given_lib_when_catalog_then_descriptions_from_frontmatter_or_heading(kind, clib):
    items = {i.name: i for i in kind.catalog(clib)}
    assert set(items) == {"style", "fm", "bare"}
    assert items["style"].description == "Code Style"
    assert items["fm"].description == "from frontmatter"
    assert items["bare"].description == ""
    assert items["style"].key == f"{kind.name}/style"


def test_given_no_dir_when_catalog_then_empty(kind, lib):
    assert kind.catalog(lib) == []


def test_given_add_when_run_then_real_file_copied_not_symlink(kind, clib, tmp_path):
    for a in kind.add(("style",), Ctx(tmp_path, clib)):
        assert a.run() == 0
    dest = tmp_path / kind.dir / "style.md"
    assert dest.is_file() and not dest.is_symlink()
    assert dest.read_text() == "# Code Style\n\nuse tabs\n"
    assert kind.installed(tmp_path) == {"style"}


def test_given_installed_when_remove_then_deleted_and_lib_untouched(kind, clib, tmp_path):
    ctx = Ctx(tmp_path, clib)
    for a in kind.add(("style",), ctx):
        a.run()
    for a in kind.remove(("style",), ctx):
        assert a.run() == 0
    assert kind.installed(tmp_path) == set()
    assert (clib / kind.dir / "style.md").exists()


def test_given_global_when_add_then_error(kind, clib, tmp_path):
    with pytest.raises(ValueError, match="project-only"):
        kind.add(("style",), Ctx(tmp_path, clib, global_=True))


def test_given_cli_pick_when_run_then_copied(kind, clib, tmp_path):
    rc = cli.main([str(tmp_path), "--lib", str(clib), "--no-tui", "--pick", f"{kind.name}/style"])
    assert rc == 0 and (tmp_path / kind.dir / "style.md").is_file()


def test_shipped_registry_has_all_kinds():
    from skills_tui.kinds import KINDS as REG

    assert [k.name for k in REG] == ["skills", "rules", "commands", "agents"]
