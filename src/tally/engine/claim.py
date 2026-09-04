"""Claim arithmetic and the daily reimbursable maximum. Money, so it runs as code and is tested.

A home may claim at most two meals and one snack, or one meal and two snacks, per child per day.
When a provider serves more than that, the program pays for the best combination, so that is what
Tally claims.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tally.models import ClaimLine, MealType

RULES_DIR = Path(__file__).resolve().parents[3] / "rules"

MEALS = (MealType.BREAKFAST, MealType.LUNCH, MealType.SUPPER)


@lru_cache(maxsize=4)
def load_rates(path: str | None = None) -> dict:
    p = Path(path) if path else RULES_DIR / "rates.json"
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class DayClaim:
    """What one child's day is worth, after the daily maximum is applied."""

    claimed: list[MealType]
    dropped: list[MealType]
    amount: float


def rate_for(meal_type: MealType, tier: str, rates: dict | None = None) -> float:
    rates = rates or load_rates()
    return float(rates["day_care_home"][tier][meal_type.value])


def claim_day(served: list[MealType], tier: str, rates: dict | None = None) -> DayClaim:
    """Pick the most valuable allowed combination from what was actually served and reimbursable."""
    rates = rates or load_rates()
    counts = Counter(served)
    meals = sorted([m for m in served if m in MEALS], key=lambda m: -rate_for(m, tier, rates))
    snacks = [m for m in served if m == MealType.SNACK]

    best: DayClaim | None = None
    for n_meals, n_snacks in ((2, 1), (1, 2)):
        take = meals[:n_meals] + snacks[:n_snacks]
        amount = round(sum(rate_for(m, tier, rates) for m in take), 2)
        if best is None or amount > best.amount:
            kept = Counter(take)
            dropped = list((counts - kept).elements())
            best = DayClaim(claimed=take, dropped=dropped, amount=amount)
    return best or DayClaim([], [], 0.0)


def month_lines(claims: list[DayClaim], tier: str, rates: dict | None = None) -> tuple[list[ClaimLine], float]:
    rates = rates or load_rates()
    counter: Counter[MealType] = Counter()
    for c in claims:
        counter.update(c.claimed)
    lines = []
    for meal_type in (MealType.BREAKFAST, MealType.LUNCH, MealType.SUPPER, MealType.SNACK):
        n = counter.get(meal_type, 0)
        if not n:
            continue
        rate = rate_for(meal_type, tier, rates)
        lines.append(ClaimLine(meal_type=meal_type, count=n, rate=rate, amount=round(n * rate, 2)))
    return lines, round(sum(x.amount for x in lines), 2)


def lost_value(missed: list[tuple[MealType, int]], tier: str, rates: dict | None = None) -> float:
    """What non-reimbursable meals would have paid. The number that closes homes."""
    rates = rates or load_rates()
    return round(sum(rate_for(m, tier, rates) * n for m, n in missed), 2)
