from skills_tui.plan import make_plan

CAT = {"a", "b", "c"}


def test_given_selection_when_plan_then_add_and_remove():
    p = make_plan({"a", "b"}, {"b", "c"}, CAT)
    assert p.to_add == ("a",)
    assert p.to_remove == ("c",)


def test_given_foreign_installed_skill_when_plan_then_untouched():
    assert not make_plan({"a"}, {"a", "third-party"}, CAT)


def test_given_same_state_when_plan_then_empty():
    assert not make_plan({"a"}, {"a"}, CAT)
