"""Generate the demo home: Rosa, nine children, and the day the demo plays.

Deterministic. Run: python -m tally.data.generate

The day is Tuesday 8 September 2026. Nia comes Monday, Wednesday and Friday, so she is not in today,
and Mateo is authorised Tuesday to Friday, which is what makes the Monday reconciliation question
worth asking. Rosa's home is fictional and so is every child.
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tally.models import Child, ComplianceItem, Provider

DEMO_DAY = datetime(2026, 9, 8, 7, 38)  # a Tuesday
MON, TUE, WED, THU, FRI = 0, 1, 2, 3, 4

PROVIDER = Provider(
    id="rosa", name="Rosa's Family Child Care", state="TX", license_type="licensed",
    tier="tier_1", language="en", sponsor_name="Hill Country Child Nutrition",
    sponsor_email="claims@example.invalid", assistant_from="14:30", question_budget=2,
)

CHILDREN = [
    Child(id="maya", provider_id="rosa", first_name="Maya", birth_date=date(2025, 3, 3),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="07:30",
          subsidized=True, subsidy_days=[MON, TUE, WED, THU, FRI], family_language="en"),
    Child(id="leo", provider_id="rosa", first_name="Leo", birth_date=date(2022, 6, 1),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="07:30",
          subsidized=True, subsidy_days=[MON, TUE, WED, THU, FRI],
          allergies=["peanut"], family_language="es"),
    Child(id="ava", provider_id="rosa", first_name="Ava", birth_date=date(2022, 1, 9),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="07:45", family_language="en"),
    Child(id="mateo", provider_id="rosa", first_name="Mateo", birth_date=date(2022, 4, 2),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="08:00",
          subsidized=True, subsidy_days=[TUE, WED, THU, FRI], family_language="es"),
    Child(id="nia", provider_id="rosa", first_name="Nia", birth_date=date(2024, 11, 5),
          enrolled_days=[MON, WED, FRI], usual_arrival="07:30",
          subsidized=True, subsidy_days=[MON, WED, FRI],
          allergies=["dairy"], family_language="en"),
    Child(id="sam", provider_id="rosa", first_name="Sam", birth_date=date(2021, 8, 8),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="07:30", family_language="en"),
    Child(id="eli", provider_id="rosa", first_name="Eli", birth_date=date(2026, 2, 2),
          enrolled_days=[MON, TUE, WED, THU], usual_arrival="07:30",
          subsidized=True, subsidy_days=[MON, TUE, WED, THU], family_language="en"),
    Child(id="priya", provider_id="rosa", first_name="Priya", birth_date=date(2018, 5, 5),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="15:10", family_language="en"),
    Child(id="jordan", provider_id="rosa", first_name="Jordan", birth_date=date(2017, 9, 9),
          enrolled_days=[MON, TUE, WED, THU, FRI], usual_arrival="15:10",
          subsidized=True, subsidy_days=[MON, TUE, WED, THU, FRI], family_language="en"),
]

COMPLIANCE = [
    ComplianceItem(id="drill-sep", provider_id="rosa", kind="fire_drill",
                   label="Monthly fire drill", due=date(2026, 9, 30),
                   last_done=date(2026, 8, 12)),
    ComplianceItem(id="cpr", provider_id="rosa", kind="certification",
                   label="CPR and first aid renewal", due=date(2026, 11, 14)),
    ComplianceItem(id="training", provider_id="rosa", kind="training",
                   label="Annual training hours, 6 of 24 done", due=date(2026, 12, 31)),
]

# The day, as steps. Each one is a real call into the agent, with a real photograph where there is
# one. The scenario says what should happen; the system decides what does.
DAY_STEPS = [
    {"id": "roll", "at": "2026-09-08T07:38", "title": "Say who is here",
     "kind": "roll",
     "text": "Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at 8",
     "detail": "Attendance, the subsidy check and the ratio look ahead, from one sentence."},
    {"id": "arrivals", "at": "2026-09-08T08:02", "title": "Mateo arrives",
     "kind": "roll",
     "text": "Mateo's here now, and Sam and Eli are here",
     "detail": "Later arrivals, said the same way. The ratio look ahead updates."},
    {"id": "breakfast", "at": "2026-09-08T08:05", "title": "Breakfast",
     "kind": "plate", "photo": "data/plates/oatmeal.jpg", "meal_type": "breakfast",
     "detail": "A bowl of porridge. Watch what the rules say is missing."},
    {"id": "breakfast_fixed", "at": "2026-09-08T08:09", "title": "Add the milk",
     "kind": "plate", "photo": "data/plates/oatmeal_with_milk.jpg", "meal_type": "breakfast",
     "replaces": "breakfast",
     "detail": "She adds milk and photographs it again. The first record is superseded, not doubled."},
    {"id": "lunch", "at": "2026-09-08T12:10", "title": "Lunch",
     "kind": "plate", "photo": "data/plates/chicken_rice_veg.jpg", "meal_type": "lunch",
     "detail": "Chicken, rice and vegetables. Two components short."},
    {"id": "lunch_fixed", "at": "2026-09-08T12:16", "title": "Add milk and fruit",
     "kind": "plate", "photo": "data/plates/chicken_rice_veg_fixed.jpg", "meal_type": "lunch",
     "replaces": "lunch",
     "detail": "Fixed at the table, at ten past twelve, not discovered at claim time."},
    {"id": "afternoon", "at": "2026-09-08T15:20", "title": "Afternoon snack",
     "kind": "plate", "photo": "data/plates/yogurt.jpg", "meal_type": "snack",
     "detail": "Yoghurt. Nia has a dairy allergy, and the check runs before anything is written."},
    {"id": "evening", "at": "2026-09-08T18:30", "title": "Evening digest",
     "kind": "evening",
     "detail": "The nightly Graph: the day's value, the notes home, the compliance clock, one question."},
]


def build() -> dict:
    return {
        "clock_start": DEMO_DAY.isoformat(),
        "provider": PROVIDER.model_dump(mode="json"),
        "children": [c.model_dump(mode="json") for c in CHILDREN],
        "compliance": [c.model_dump(mode="json") for c in COMPLIANCE],
        "steps": DAY_STEPS,
        "vocabulary": {"the usual crackers": "whole grain Ritz crackers"},
        "prior_days": 6,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/demo_day.json")
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    blob = build()
    out.write_text(json.dumps(blob, indent=1), encoding="utf-8")
    print(f"wrote {out}: {len(blob['children'])} children, {len(blob['steps'])} steps")


if __name__ == "__main__":
    main()
