"""The rulebook as an MCP server, so somebody else's agent can check a claim without trusting mine.

Tally already publishes its rules at `/api/rules`, which is JSON for a person to read. That is the
right thing and it is not enough. The organisation that actually questions a claim is the sponsoring
agency, and increasingly what reviews a claim on their side is an agent, not a person with a browser.

So the same rulebook is served over the Model Context Protocol. A sponsor's agent, or a state
reviewer's, can ask what a lunch requires for a three year old under version 2026-09, get a
structured answer, and reach its own verdict. It never has to take Tally's word for anything, which
is the whole reason the rules were versioned data rather than Python in the first place.

This is deliberately read only. Nothing here can log a meal, change a rule or touch a claim. The
worst an untrusted caller can do is learn what the published USDA tables say, which is public.

    python -m tally.mcp.server              stdio, for an agent to spawn
    python -m tally.mcp.server --http 8081  streamable http, for a remote one
"""

from __future__ import annotations

import argparse
import json
import sys

from mcp.server.fastmcp import FastMCP

from tally.engine.claim import load_rates, rate_for
from tally.engine.ratio import limits_for
from tally.engine.rules import check_meal, load_rules
from tally.models import AgeGroup, Component, Item, MealType

mcp = FastMCP("tally-rulebook")


@mcp.tool()
def rule_version() -> dict:
    """The version of the meal pattern rulebook these answers come from, and where it came from.

    Every verdict Tally records carries this version, so a claim can be re-decided years later
    under the rules that were in force when the meal was served.
    """
    r = load_rules()
    rates = load_rates()
    return {
        "meal_pattern_version": r["version"],
        "effective": r.get("effective"),
        "source": r.get("source"),
        "rates_version": rates.get("version"),
        "rates_effective_from": rates.get("effective_from"),
        "rates_effective_to": rates.get("effective_to"),
        "rates_source": rates.get("source"),
    }


@mcp.tool()
def meal_pattern(meal_type: str, age_group: str = "3-5") -> dict:
    """What a meal must contain to be reimbursable, for one meal type and one age group.

    Args:
        meal_type: breakfast, lunch, supper or snack.
        age_group: infant, 1-2, 3-5, 6-12 or 13-18. Defaults to 3-5.
    """
    r = load_rules()
    try:
        spec = r["meals"][MealType(meal_type).value]
    except (ValueError, KeyError):
        return {"error": f"unknown meal type {meal_type!r}",
                "known": sorted(r["meals"]), "rule_version": r["version"]}
    try:
        AgeGroup(age_group)
    except ValueError:
        return {"error": f"unknown age group {age_group!r}",
                "known": [a.value for a in AgeGroup], "rule_version": r["version"]}

    if age_group == AgeGroup.INFANT.value:
        return {"meal_type": meal_type, "age_group": age_group, "judged": False,
                "reason": "Infants follow a separate pattern by age in months. Tally records "
                          "infant meals and declines to judge them rather than applying the "
                          "wrong rule.",
                "rule_version": r["version"]}

    return {"meal_type": meal_type, "age_group": age_group, "judged": True,
            "spec": spec, "rule_version": r["version"]}


@mcp.tool()
def check_components(components: list[str], meal_type: str, age_group: str = "3-5") -> dict:
    """Decide whether a set of components satisfies the pattern, and say what is missing.

    The same function Tally uses on its own verdicts, so a sponsor checking a claim gets the
    identical answer rather than a reimplementation that can drift.

    Args:
        components: milk, fruit, vegetable, grain, meat_alt or juice.
        meal_type: breakfast, lunch, supper or snack.
        age_group: infant, 1-2, 3-5, 6-12 or 13-18. Defaults to 3-5.
    """
    try:
        comps = [Component(c) for c in components]
        meal = MealType(meal_type)
        group = AgeGroup(age_group)
    except ValueError as e:
        return {"error": str(e),
                "known_components": [c.value for c in Component],
                "known_meals": [m.value for m in MealType],
                "known_age_groups": [a.value for a in AgeGroup]}

    items = [Item(name=c.value, component=c, confidence=1.0) for c in comps]
    v = check_meal(items, meal, {group})
    return {"reimbursable": v.reimbursable,
            "missing": [m.value for m in v.missing],
            "smallest_fix": v.smallest_fix,
            "flags": v.flags,
            "label_checks": v.label_checks,
            "explanation": v.explanation,
            "rule_version": v.rule_version}


@mcp.tool()
def payment_rate(meal_type: str, tier: str = "tier_1") -> dict:
    """What one reimbursable meal pays, at the published rates.

    Args:
        meal_type: breakfast, lunch, supper or snack.
        tier: tier_1 or tier_2.
    """
    rates = load_rates()
    try:
        amount = rate_for(MealType(meal_type), tier, rates)
    except (ValueError, KeyError):
        return {"error": f"unknown meal type or tier: {meal_type!r}, {tier!r}",
                "known_meals": [m.value for m in MealType],
                "known_tiers": sorted(rates["day_care_home"])}
    return {"meal_type": meal_type, "tier": tier, "amount": amount,
            "currency": rates.get("currency", "USD"),
            "rates_version": rates.get("version"),
            "daily_maximum": load_rules().get("daily_reimbursable_maximum")}


@mcp.tool()
def state_ratio(state: str, license_type: str = "licensed") -> dict:
    """The staffing ratio limits for one state, or an honest refusal if that table is not held.

    An unknown state raises rather than guessing, because a wrong ratio limit tells a provider she
    has room for a child when she may not.

    Args:
        state: two letter state code.
        license_type: licensed or registered.
    """
    try:
        limits = limits_for(state.upper(), license_type)
    except KeyError as e:
        return {"error": str(e).strip("'"), "state": state.upper(),
                "known": "Only the states with a table in rules/state_rules.json are answered. "
                         "Adding one is a data change, not a code change."}
    return {"state": state.upper(), "license_type": license_type, "limits": limits}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--http", type=int, default=None,
                    help="serve streamable http on this port instead of stdio")
    ap.add_argument("--list", action="store_true", help="print the tools and exit")
    a = ap.parse_args()

    if a.list:
        import asyncio

        tools = asyncio.run(mcp.list_tools())
        print(json.dumps([{"name": t.name, "description": (t.description or "").split("\n")[0]}
                          for t in tools], indent=2))
        return 0

    if a.http:
        mcp.settings.port = a.http
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
