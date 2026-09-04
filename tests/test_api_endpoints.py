"""The two endpoints a person other than the provider depends on.

`/api/children/parse` is the first screen a provider ever sees, and it must never quietly lose a
child. `/api/sponsor/month` is what a sponsoring organisation and, years later, a state reviewer
read, so every meal it reports has to carry the photograph and the rule version it was judged under.
"""

from fastapi.testclient import TestClient

from tally.api import app

client = TestClient(app)

PASTE = """
Maya, born 3 March 2025, subsidised Mon-Fri
Leo, 1 June 2022, peanut allergy, Mon to Fri, subsidised
a note about the fire drill, which is not a child
"""


def parse(text: str, **kw) -> dict:
    body = {"text": text, "state": kw.get("state", "TX"),
            "license_type": kw.get("license_type", "licensed")}
    r = client.post("/api/children/parse", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_a_pasted_list_comes_back_as_children_with_their_allergies():
    d = parse(PASTE)
    names = [c["first_name"] for c in d["children"]]
    assert names == ["Maya", "Leo"]
    assert d["children"][1]["allergies"] == ["peanut"]


def test_a_line_it_cannot_read_is_reported_rather_than_dropped():
    """A child missing from the roster is a child whose allergy is never checked."""
    d = parse(PASTE)
    assert d["unreadable"] == ["a note about the fire drill, which is not a child"]


def test_the_ratio_is_checked_before_anything_is_saved():
    d = parse(PASTE)
    assert d["ratio"]["ok"] is True
    assert d["ratio"]["enrolled"] == 2 and d["ratio"]["limit"] == 12


def test_a_group_over_the_state_limit_is_refused_at_setup_not_at_inspection():
    text = "\n".join(f"{n}, 1 June 2022" for n in
                     ["Ana", "Ben", "Cara", "Dev", "Eve", "Finn", "Gia", "Hugo", "Iris", "Jack",
                      "Kira", "Liam", "Mira"])
    d = parse(text)
    assert len(d["children"]) == 13
    assert d["ratio"]["ok"] is False
    assert any("over the limit" in p for p in d["ratio"]["problems"])


def test_a_state_with_no_ratio_table_is_refused_rather_than_guessed():
    d = parse(PASTE, state="ZZ")
    assert d["ratio"]["ok"] is False
    assert "rather than guessing" in d["ratio"]["error"]


def test_an_empty_paste_produces_nothing_and_complains_about_nothing():
    d = parse("   \n\n  ")
    assert d["children"] == [] and d["unreadable"] == [] and d["warnings"] == []


def sponsor() -> dict:
    r = client.get("/api/sponsor/month")
    assert r.status_code == 200, r.text
    return r.json()


def test_the_sponsor_month_names_the_home_and_who_it_claims_through():
    d = sponsor()
    p = d["provider"]
    assert p["name"] and p["state"] == "TX" and p["sponsor"]
    assert d["month"].count("-") == 1


def test_every_meal_carries_the_rule_version_it_was_judged_under():
    """Without this a verdict cannot be re-run against the rulebook that produced it."""
    d = sponsor()
    meals = [m for day in d["days"] for m in day["meals"]]
    assert meals
    assert all(m["rule_version"] for m in meals)
    assert d["rule_versions"] == sorted({m["rule_version"] for m in meals})


def test_the_totals_agree_with_the_meals_listed():
    d = sponsor()
    meals = [m for day in d["days"] for m in day["meals"]]
    assert d["totals"]["meals"] == len(meals)
    assert d["totals"]["reimbursable"] == sum(1 for m in meals if m["reimbursable"])
    assert d["totals"]["photographed"] == sum(1 for m in meals if m["photo"])


def test_a_meal_replaced_by_a_later_photograph_is_not_listed_twice():
    d = sponsor()
    meals = [m for day in d["days"] for m in day["meals"]]
    replaced = {m["replaces"] for m in meals if m.get("replaces")}
    assert not (replaced & {m["id"] for m in meals})


def test_the_claim_says_where_its_arithmetic_ran():
    d = sponsor()
    assert d["claim"]["computed_in"] in ("local", "local_fallback", "agentcore_code_interpreter")
