"""A new kind plugs in without touching core: fake `widgets` kind driven through cli.main."""
from skills_tui import cli
from types import SimpleNamespace

from skills_tui.kinds import Action, Ctx, Item


class FakeKind:
    name = "widgets"

    def __init__(self):
        self.log = []

    def catalog(self, lib):
        return [Item("widgets", "style", "code style", "mine"), Item("widgets", "alpha", "clashes with skill", "mine")]

    def installed(self, project):
        return set()

    def add(self, names, ctx):
        return [Action(f"copy {names}", lambda: self.log.append(("add", names)) or 0)]

    def remove(self, names, ctx):
        return [Action(f"rm {names}", lambda: self.log.append(("rm", names)) or 0)]


def test_given_extra_kind_when_profile_mixes_kinds_then_each_kind_acts(lib, tmp_path, monkeypatch):
    fake = FakeKind()
    monkeypatch.setattr(cli, "KINDS", [*cli.KINDS, fake])
    (lib / "p.json").write_text('{"mix": {"skills": ["beta"], "widgets": ["style"]}}')
    calls = []
    fake_exec = lambda cmd, cwd: calls.append(cmd) or SimpleNamespace(returncode=0)  # noqa: E731
    monkeypatch.setattr(cli, "Ctx", lambda *a, **kw: Ctx(*a, **kw, exec_=fake_exec))

    rc = cli.main([str(tmp_path), "--lib", str(lib), "--profiles-file", str(lib / "p.json"), "--profile", "mix", "--no-tui"])

    assert rc == 0
    assert fake.log == [("add", ("style",))]
    assert len(calls) == 1 and calls[0][3:5] == ["add", str(lib)] and "beta" in calls[0]


def test_given_clashing_bare_name_when_pick_then_ambiguous_but_qualified_works(lib, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "KINDS", [*cli.KINDS, FakeKind()])
    base = [str(tmp_path), "--lib", str(lib), "--no-tui", "--dry-run", "--pick"]
    assert cli.main([*base, "alpha"]) == 2
    assert cli.main([*base, "widgets/alpha"]) == 0
