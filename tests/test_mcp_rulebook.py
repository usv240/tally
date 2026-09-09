"""The rulebook over MCP, exercised by a client that holds no Tally code.

Every call here crosses a real process boundary: the server is spawned as a subprocess and answers
over stdio, exactly as a sponsoring organisation's own agent would reach it. Nothing is stubbed,
and no model is called, so this is deterministic and free and belongs in CI.

What it is actually protecting: the rules are versioned data behind a protocol so somebody who does
not trust Tally can reach their own verdict. If the server stops answering, or answers without a
rule version, or starts guessing at a state it does not hold a table for, that argument is gone.
"""

from __future__ import annotations

import json

import pytest

from tally.mcp.sponsor import rulebook


@pytest.fixture(scope="module")
def client():
    with rulebook() as c:
        yield c


def call(client, name: str, **args) -> dict:
    r = client.call_tool_sync(tool_use_id=f"t-{name}", name=name, arguments=args)
    assert r["status"] == "success", f"{name} failed: {r}"
    return json.loads("".join(c.get("text", "") for c in r["content"]))


def test_the_five_tools_are_discoverable(client):
    names = {t.tool_name for t in client.list_tools_sync()}
    assert names == {"rule_version", "meal_pattern", "check_components",
                     "payment_rate", "state_ratio"}


def test_every_answer_carries_a_rule_version(client):
    """A verdict without a version cannot be re-decided later under the rules in force."""
    assert call(client, "rule_version")["meal_pattern_version"]
    assert call(client, "meal_pattern", meal_type="lunch")["rule_version"]
    assert call(client, "check_components", components=["milk"],
                meal_type="snack")["rule_version"]


def test_an_incomplete_lunch_is_refused_and_the_fix_is_named(client):
    v = call(client, "check_components", components=["milk", "grain"],
             meal_type="lunch", age_group="3-5")
    assert v["reimbursable"] is False
    assert set(v["missing"]) >= {"fruit", "vegetable", "meat_alt"}


def test_a_complete_lunch_is_reimbursable(client):
    v = call(client, "check_components",
             components=["milk", "grain", "fruit", "vegetable", "meat_alt"],
             meal_type="lunch", age_group="3-5")
    assert v["reimbursable"] is True
    assert v["missing"] == []


def test_the_verdict_matches_tally_own_engine_exactly(client):
    """A reviewer who disagrees with the provider's software over the same facts is the failure
    this whole design exists to prevent, so the two paths are compared directly."""
    from tally.engine.rules import check_meal
    from tally.models import AgeGroup, Component, Item, MealType

    combos = [
        (["milk", "grain"], MealType.LUNCH),
        (["milk", "grain", "fruit", "vegetable", "meat_alt"], MealType.LUNCH),
        (["milk", "fruit"], MealType.SNACK),
        (["milk", "grain", "fruit"], MealType.BREAKFAST),
        (["grain"], MealType.BREAKFAST),
    ]
    for comps, meal in combos:
        over_mcp = call(client, "check_components",
                        components=comps, meal_type=meal.value, age_group="3-5")
        items = [Item(name=c, component=Component(c), confidence=1.0) for c in comps]
        direct = check_meal(items, meal, {AgeGroup.A3_5})
        assert over_mcp["reimbursable"] == direct.reimbursable, comps
        assert set(over_mcp["missing"]) == {m.value for m in direct.missing}, comps


def test_a_state_with_no_table_is_refused_rather_than_guessed(client):
    """A wrong ratio limit tells a provider she has room for a child when she may not."""
    v = call(client, "state_ratio", state="NY", license_type="licensed")
    assert "error" in v
    assert "limits" not in v

    held = call(client, "state_ratio", state="TX", license_type="registered")
    assert held["limits"]["max_group_size"] == 6


def test_infants_are_recorded_and_not_judged(client):
    v = call(client, "meal_pattern", meal_type="lunch", age_group="infant")
    assert v["judged"] is False
    assert "spec" not in v


def test_an_unknown_meal_type_names_what_is_known(client):
    v = call(client, "meal_pattern", meal_type="brunch")
    assert "error" in v
    assert "lunch" in v["known"]


def test_the_rate_is_the_published_one(client):
    from tally.engine.claim import load_rates, rate_for
    from tally.models import MealType

    v = call(client, "payment_rate", meal_type="lunch", tier="tier_1")
    assert v["amount"] == rate_for(MealType.LUNCH, "tier_1", load_rates())


def test_nothing_here_can_write(client):
    """Read only by construction. The worst an untrusted caller can do is read public tables."""
    names = {t.tool_name for t in client.list_tools_sync()}
    for verb in ("log", "record", "submit", "claim", "delete", "set", "update", "create"):
        assert not any(n.startswith(verb) for n in names), verb
