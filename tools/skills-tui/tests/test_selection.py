from skills_tui import tui
from skills_tui.kinds import Item
from skills_tui.selection import kind_counts, merge, order

CAT = [
    Item("skills", "b", "", "vendored"),
    Item("skills", "a", "", "mine"),
    Item("skills", "z", "", "mine"),
    Item("rules", "r1", "", "mine"),
]


def test_given_installed_when_order_then_installed_first_then_mine_then_name():
    names = [i.name for i in order(CAT[:3], {"skills/z"})]
    assert names == ["z", "a", "b"]


def test_given_selection_when_counts_then_per_kind_ticked_over_total():
    assert kind_counts(CAT, {"skills/a", "rules/r1"}) == {"skills": (1, 3), "rules": (1, 1)}


def test_given_picked_when_merge_then_only_that_kind_replaced():
    kind_keys = {"skills/a", "skills/b", "skills/z"}
    out = merge({"skills/a", "rules/r1"}, kind_keys, {"skills/b"})
    assert out == {"skills/b", "rules/r1"}


def _script(monkeypatch, menu_answers, screen_answers):
    menus, screens = iter(menu_answers), iter(screen_answers)
    monkeypatch.setattr(tui, "_menu", lambda counts, default: next(menus))
    monkeypatch.setattr(tui, "_kind_screen", lambda kind, items, installed, selected: next(screens))


def test_given_drill_down_when_apply_then_returns_accumulated_selection(monkeypatch):
    _script(monkeypatch, ["skills", "rules", tui.APPLY], [{"skills/a"}, {"rules/r1"}])
    assert tui.pick_items(CAT, installed=set(), preticked=set()) == {"skills/a", "rules/r1"}


def test_given_installed_when_unticked_then_removed_from_selection(monkeypatch):
    _script(monkeypatch, ["skills", tui.APPLY], [set()])
    assert tui.pick_items(CAT, installed={"skills/a"}, preticked=set()) == set()


def test_given_screen_cancelled_when_back_then_selection_unchanged(monkeypatch):
    _script(monkeypatch, ["skills", tui.APPLY], [None])
    assert tui.pick_items(CAT, installed={"skills/a"}, preticked={"rules/r1"}) == {"skills/a", "rules/r1"}


def test_given_cancel_when_menu_then_none(monkeypatch):
    _script(monkeypatch, [tui.CANCEL], [])
    assert tui.pick_items(CAT, set(), set()) is None


def test_given_ctrl_c_in_menu_when_pick_then_none(monkeypatch):
    _script(monkeypatch, [None], [])
    assert tui.pick_items(CAT, set(), set()) is None
