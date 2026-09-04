"""The money and the meal pattern, as plain Python over plain types.

Dependency free on purpose: standard library only, no pydantic, no project imports. That is what
lets the identical source run in two places. Locally it is imported. On AWS the source of this file
is uploaded into an Amazon Bedrock AgentCore Code Interpreter session and the same functions are
called there, so "the claim arithmetic runs as code in Code Interpreter" is a statement about this
exact file rather than a second implementation that might drift.

Nothing here knows what a child is. It knows components, combinations and money.
"""

from __future__ import annotations

MEALS = ("breakfast", "lunch", "supper")
SNACK = "snack"

DAILY_COMBINATIONS = ((2, 1), (1, 2))
"""A home may claim at most two meals and one snack, or one meal and two snacks, per child per day."""


def claim_day(served: list, tier_rates: dict) -> dict:
    """The most valuable allowed combination of what was actually served and reimbursable.

    served: meal type strings, repeats allowed.
    tier_rates: {"breakfast": 1.74, "lunch": 3.31, "supper": 3.31, "snack": 0.98}
    """
    meals = sorted([m for m in served if m in MEALS], key=lambda m: -float(tier_rates[m]))
    snacks = [m for m in served if m == SNACK]

    best = None
    for n_meals, n_snacks in DAILY_COMBINATIONS:
        take = meals[:n_meals] + snacks[:n_snacks]
        amount = round(sum(float(tier_rates[m]) for m in take), 2)
        if best is None or amount > best["amount"]:
            remaining = list(served)
            for m in take:
                remaining.remove(m)
            best = {"claimed": take, "dropped": remaining, "amount": amount}
    return best or {"claimed": [], "dropped": [], "amount": 0.0}


def month_total(day_claims: list, tier_rates: dict) -> dict:
    """Roll a month of day claims into lines and a total."""
    counts: dict = {}
    for c in day_claims:
        for m in c["claimed"]:
            counts[m] = counts.get(m, 0) + 1
    lines = []
    for meal_type in ("breakfast", "lunch", "supper", "snack"):
        n = counts.get(meal_type, 0)
        if not n:
            continue
        rate = float(tier_rates[meal_type])
        lines.append({"meal_type": meal_type, "count": n, "rate": rate,
                      "amount": round(n * rate, 2)})
    return {"lines": lines, "total": round(sum(x["amount"] for x in lines), 2)}


def lost_value(missed: list, tier_rates: dict) -> float:
    """What the meals that did not qualify would have paid.

    missed: [[meal_type, count], ...]. This is the number that decides whether a home stays open.
    """
    return round(sum(float(tier_rates[m]) * int(n) for m, n in missed), 2)


def compute(payload: dict) -> dict:
    """The whole month from one JSON-shaped input, so the remote call is a single round trip.

    payload: {
      "days": [["breakfast","lunch","snack"], ...],   one entry per child per day
      "missed": [["lunch", 12], ...],
      "tier_rates": {"breakfast": 1.74, ...}
    }
    """
    rates = payload["tier_rates"]
    day_claims = [claim_day(list(d), rates) for d in payload.get("days", [])]
    month = month_total(day_claims, rates)
    month["lost_amount"] = lost_value(payload.get("missed", []), rates)
    month["dropped_over_daily_maximum"] = sum(len(c["dropped"]) for c in day_claims)
    month["days_counted"] = len(day_claims)
    return month
