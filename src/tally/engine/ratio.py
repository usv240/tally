"""State ratio and group size, with a look ahead to the rest of the day.

A provider finds out she is over her limit when the school age children walk in at ten past three.
The point of computing this in the morning is that she can do something about it.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time
from functools import lru_cache
from pathlib import Path

from tally.models import AgeGroup, Child, RatioCheck

RULES_DIR = Path(__file__).resolve().parents[3] / "rules"


@lru_cache(maxsize=4)
def load_state_rules(path: str | None = None) -> dict:
    p = Path(path) if path else RULES_DIR / "state_rules.json"
    return json.loads(p.read_text(encoding="utf-8"))


def limits_for(state: str, license_type: str, rules: dict | None = None) -> dict:
    rules = rules or load_state_rules()
    try:
        return rules["states"][state]["license_types"][license_type]
    except KeyError as exc:
        raise KeyError(
            f"No ratio table for {state} {license_type}. Add it to rules/state_rules.json rather "
            f"than guessing: an incorrect limit is worse than no answer."
        ) from exc


def _parse(hhmm: str, on: date) -> datetime:
    h, m = hhmm.split(":")
    return datetime.combine(on, time(int(h), int(m)))


def check_ratio(
    present_ids: set[str],
    children: list[Child],
    provider_state: str,
    license_type: str,
    now: datetime,
    absent_ids: set[str] | None = None,
    rules: dict | None = None,
) -> RatioCheck:
    """Current count against the limit, plus the next arrival that changes the answer.

    A child enrolled today who is neither signed in nor marked absent, and whose usual arrival has
    already passed, is unaccounted for. Those children count toward the limit, because assuming they
    are not coming is the unsafe direction: it tells a provider she has room when she may not. They
    are also named, so she can resolve it in one word.
    """
    limits = limits_for(provider_state, license_type, rules)
    limit = int(limits.get("max_with_school_age") or limits["max_group_size"])
    absent_ids = absent_ids or set()
    today = now.date()
    weekday = now.weekday()

    count = len([c for c in children if c.id in present_ids])

    upcoming: list[tuple[datetime, Child]] = []
    unaccounted: list[str] = []
    for c in children:
        if c.id in present_ids or c.id in absent_ids or weekday not in c.enrolled_days:
            continue
        arrival = _parse(c.usual_arrival, today)
        if arrival > now:
            upcoming.append((arrival, c))
        else:
            unaccounted.append(c.id)
    upcoming.sort(key=lambda pair: pair[0])

    effective = count + len(unaccounted)
    ok = effective <= limit

    next_at = next_count = next_ok = None
    if upcoming:
        # Everyone arriving at the same time arrives together, so step by arrival time.
        first_time = upcoming[0][0]
        arriving = [c for t, c in upcoming if t == first_time]
        next_at = first_time
        next_count = effective + len(arriving)
        next_ok = next_count <= limit

    parts = [f"{count} of {limit} now"]
    if unaccounted:
        parts.append(f"{len(unaccounted)} not signed in yet")
    if next_at is not None:
        when = f"{next_at.hour % 12 or 12}:{next_at.minute:02d}{'am' if next_at.hour < 12 else 'pm'}"
        parts.append(f"{next_count} of {limit} at {when}")
        if not next_ok:
            parts.append("over the limit")
    return RatioCheck(now_count=count, now_ok=ok, limit=limit, next_change_at=next_at,
                      next_change_count=next_count, next_change_ok=next_ok,
                      unaccounted=unaccounted, explanation=", ".join(parts))


def under_two_count(present_ids: set[str], children: list[Child], on: date) -> int:
    return sum(1 for c in children
               if c.id in present_ids and c.age_group(on) in (AgeGroup.INFANT, AgeGroup.A1_2))
