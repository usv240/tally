"""Measure what Tally refuses to do, and prove it does not refuse the wrong things.

Tally decides whether meals get paid for. A wrong yes creates a false claim against a federal food
programme, and a wrong no costs a provider money she is owed. Both directions are failures, so both
directions are measured here.

Two sides, because one alone proves nothing:

  Adversarial   things it must refuse to credit or decline to judge. A food the model was unsure
                about, an infant meal it does not model, a state whose ratio table it does not
                have, a snack one component short. Refusing all of these is easy: a system that
                refuses everything scores 100 percent.

  Legitimate    things it must credit. A complete lunch, a qualifying snack, a state it does know,
                a food it read confidently. This is the control. A false refusal here is the
                provider losing a meal she actually served, which is exactly the failure the
                product exists to prevent.

Deterministic and model-free, so it runs in CI in under a second and the number cannot drift with a
model version. The vision measurement that does call a model lives in evals/vision_eval.py.

    python -m evals.refusal_eval                       print the result
    python -m evals.refusal_eval --out docs/EVAL.md    write it into the eval page
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

START = "<!-- refusal:start -->"
END = "<!-- refusal:end -->"


@dataclass
class Case:
    area: str
    name: str
    kind: str  # "adversarial" or "legitimate"
    expect: str
    passed: bool = False
    got: str = ""


@dataclass
class Result:
    cases: list[Case] = field(default_factory=list)

    def add(self, c: Case) -> Case:
        self.cases.append(c)
        return c

    @property
    def adversarial(self) -> list[Case]:
        return [c for c in self.cases if c.kind == "adversarial"]

    @property
    def legitimate(self) -> list[Case]:
        return [c for c in self.cases if c.kind == "legitimate"]


def _item(name: str, component, confidence: float = 0.95):
    from tally.models import Item

    return Item(name=name, component=component, confidence=confidence)


# --------------------------------------------------------------------------------------------
# The confidence gate. An item the model is unsure about is not logged at all.
# --------------------------------------------------------------------------------------------
def check_confidence_gate(r: Result) -> None:
    from tally.agents.plate import ASK_BELOW, apply_confidence_gate
    from tally.models import Component, MealType, PlateReading

    unsure = _item("pale liquid", Component.MILK, confidence=ASK_BELOW - 0.2)
    unsure.note = "Is the pale liquid milk or the water the oatmeal was cooked in?"
    reading = PlateReading(items=[_item("oatmeal", Component.GRAIN, 0.98), unsure],
                           meal_type_guess=MealType.BREAKFAST, questions=[])
    gated = apply_confidence_gate(reading)

    kept = {i.name for i in gated.items}
    c = r.add(Case("Confidence gate", f"a food read at {ASK_BELOW - 0.2:.2f} confidence",
                   "adversarial", "left out of the record and asked about instead"))
    c.passed = "pale liquid" not in kept and any("pale liquid" in q for q in gated.questions)
    c.got = ("not logged, asked instead" if c.passed
             else f"logged anyway: {sorted(kept)}")

    c = r.add(Case("Confidence gate", f"a food read at 0.98, above the {ASK_BELOW} threshold",
                   "legitimate", "kept in the record"))
    c.passed = "oatmeal" in kept
    c.got = "logged" if c.passed else "wrongly dropped"

    # Nothing is ever estimated. The reading model has no portion field at all, which is a refusal
    # expressed in the type rather than in a branch.
    fields = set(PlateReading.model_fields) | set(type(unsure).model_fields)
    c = r.add(Case("Confidence gate", "asking it for a portion size, weight or calorie count",
                   "adversarial", "impossible: no such field exists"))
    banned = {"portion", "grams", "weight", "calories", "ounces", "serving_size"}
    c.passed = not (fields & banned)
    c.got = "no portion field on the model" if c.passed else f"found {fields & banned}"


# --------------------------------------------------------------------------------------------
# The meal pattern. A wrong yes is a false claim; a wrong no costs her money.
# --------------------------------------------------------------------------------------------
def check_meal_pattern(r: Result) -> None:
    from tally.engine.rules import DayContext, check_meal
    from tally.models import AgeGroup, Component, MealType

    toddler = {AgeGroup.A1_2}

    short = check_meal([_item("yogurt", Component.MEAT_ALT)], MealType.SNACK, toddler)
    c = r.add(Case("Meal pattern", "a snack with one component when two are required",
                   "adversarial", "not reimbursable"))
    c.passed = not short.reimbursable
    c.got = f"not reimbursable, {short.smallest_fix or short.explanation}"[:110]

    lunch_short = check_meal([_item("chicken", Component.MEAT_ALT),
                              _item("rice", Component.GRAIN),
                              _item("peas", Component.VEGETABLE)], MealType.LUNCH, toddler)
    c = r.add(Case("Meal pattern", "a lunch missing milk and fruit", "adversarial",
                   "not reimbursable, and says the smallest fix"))
    c.passed = not lunch_short.reimbursable and bool(lunch_short.smallest_fix)
    c.got = f"not reimbursable: {lunch_short.smallest_fix}"[:110]

    infant_only = check_meal([_item("oatmeal", Component.GRAIN)], MealType.BREAKFAST,
                             {AgeGroup.INFANT})
    c = r.add(Case("Meal pattern", "a meal where only infants are at the table", "adversarial",
                   "recorded, and explicitly not judged"))
    c.passed = not infant_only.reimbursable and any("infant" in f.lower() for f in infant_only.flags)
    c.got = infant_only.flags[0][:110] if infant_only.flags else "no flag raised"

    nobody = check_meal([_item("oatmeal", Component.GRAIN)], MealType.BREAKFAST, set())
    c = r.add(Case("Meal pattern", "a meal with nobody signed in", "adversarial",
                   "no verdict reached, rather than a false negative"))
    c.passed = not nobody.reimbursable and any("nobody" in f.lower() or "no children" in f.lower()
                                               for f in nobody.flags)
    c.got = nobody.flags[0][:110] if nobody.flags else "no flag raised"

    twice = check_meal([_item("juice", Component.JUICE), _item("crackers", Component.GRAIN)],
                       MealType.SNACK, toddler, day=DayContext(juice_already_counted=True))
    c = r.add(Case("Meal pattern", "juice counted a second time in one day", "adversarial",
                   "does not count twice"))
    c.passed = any("juice" in f.lower() for f in twice.flags)
    c.got = next((f for f in twice.flags if "juice" in f.lower()), "not flagged")[:110]

    labelled = check_meal([_item("yogurt", Component.MEAT_ALT), _item("banana", Component.FRUIT)],
                          MealType.SNACK, toddler)
    c = r.add(Case("Meal pattern", "yoghurt, which has a sugar limit a photograph cannot establish",
                   "adversarial", "flags the label check rather than deciding it"))
    c.passed = "yogurt_sugar" in labelled.label_checks
    c.got = ("raised yogurt_sugar: under 23g per 6oz, which a photograph cannot show"
             if c.passed else "no label check raised")

    # The controls. These must be paid.
    good_snack = check_meal([_item("yogurt", Component.MEAT_ALT), _item("banana", Component.FRUIT)],
                            MealType.SNACK, toddler)
    c = r.add(Case("Meal pattern", "a snack with two components", "legitimate", "reimbursable"))
    c.passed = good_snack.reimbursable
    c.got = "reimbursable" if c.passed else f"wrongly refused: {good_snack.explanation}"[:110]

    full_lunch = check_meal([_item("chicken", Component.MEAT_ALT), _item("rice", Component.GRAIN),
                             _item("peas", Component.VEGETABLE), _item("milk", Component.MILK),
                             _item("pear", Component.FRUIT)], MealType.LUNCH, toddler)
    c = r.add(Case("Meal pattern", "a lunch with every required component", "legitimate",
                   "reimbursable"))
    c.passed = full_lunch.reimbursable
    c.got = "reimbursable" if c.passed else f"wrongly refused: {full_lunch.explanation}"[:110]


# --------------------------------------------------------------------------------------------
# Allergies. This runs before anything is written, because the order is the safety property.
# --------------------------------------------------------------------------------------------
def check_allergies(r: Result) -> None:
    from tally.engine.rules import allergy_conflicts
    from tally.models import Component

    plate = [_item("peanut butter", Component.MEAT_ALT), _item("oatmeal", Component.GRAIN)]

    hit = allergy_conflicts(plate, {"leo": ["peanut"]})
    c = r.add(Case("Allergies", "peanut butter on the plate with a peanut-allergic child present",
                   "adversarial", "conflict raised before anything is written"))
    c.passed = "leo" in hit
    c.got = f"leo: {hit.get('leo')}" if c.passed else "not caught"

    # Generous matching: a dairy allergy has to catch yogurt, not just the word milk.
    dairy = allergy_conflicts([_item("yogurt", Component.MEAT_ALT)], {"mia": ["dairy"]})
    c = r.add(Case("Allergies", "yoghurt on the plate with a dairy-allergic child present",
                   "adversarial", "caught, because dairy has to reach yoghurt"))
    c.passed = "mia" in dairy
    c.got = f"mia: {dairy.get('mia')}" if c.passed else "missed: dairy did not reach yoghurt"

    clear = allergy_conflicts(plate, {"sam": ["shellfish"]})
    c = r.add(Case("Allergies", "the same plate with a shellfish-allergic child present",
                   "legitimate", "no conflict, the meal proceeds"))
    c.passed = not clear
    c.got = "no conflict" if c.passed else f"false alarm: {clear}"


# --------------------------------------------------------------------------------------------
# State ratio limits. A wrong limit is worse than no answer.
# --------------------------------------------------------------------------------------------
def check_state_ratio(r: Result) -> None:
    from tally.engine.ratio import limits_for

    try:
        limits_for("ZZ", "licensed")
        raised, why = False, "returned a limit for a state it has no table for"
    except KeyError as e:
        raised, why = True, str(e)[:110]
    c = r.add(Case("State ratio", "a state with no ratio table on file", "adversarial",
                   "raises, rather than guessing a limit"))
    c.passed, c.got = raised, why

    try:
        known = limits_for("TX", "licensed")
        c = r.add(Case("State ratio", "Texas, which is on file", "legitimate", "returns the limit"))
        c.passed, c.got = bool(known), f"limit {known.get('max_group_size')}"
    except Exception as e:
        c = r.add(Case("State ratio", "Texas, which is on file", "legitimate", "returns the limit"))
        c.passed, c.got = False, f"wrongly raised: {e}"[:110]


# --------------------------------------------------------------------------------------------
# Onboarding. A child missing from the roster is a child whose allergy is never checked.
# --------------------------------------------------------------------------------------------
def check_onboarding(r: Result) -> None:
    from fastapi.testclient import TestClient

    from tally.api import app

    client = TestClient(app)

    def parse(text: str, state: str = "TX") -> dict:
        resp = client.post("/api/children/parse",
                           json={"text": text, "state": state, "license_type": "licensed"})
        return resp.json() if resp.status_code == 200 else {"_status": resp.status_code}

    d = parse("Maya, born 3 March 2025\nthis line is not a child at all\nLeo, 1 June 2022")
    unreadable = d.get("unreadable") or []
    c = r.add(Case("Onboarding", "a pasted line that is not a child", "adversarial",
                   "reported, not silently dropped"))
    c.passed = len(unreadable) >= 1
    c.got = f"{len(unreadable)} line reported back" if c.passed else "dropped silently"

    d2 = parse("Ana, born 4 April 2024, peanut allergy")
    kids = d2.get("children") or []
    allergies = kids[0].get("allergies", []) if kids else []
    c = r.add(Case("Onboarding", "the word allergy present, so an allergy is recorded",
                   "legitimate", "recorded"))
    c.passed = bool(allergies)
    c.got = f"recorded {allergies}" if c.passed else "missed the allergy"

    d3 = parse("Ben, born 4 April 2024, loves peanut butter sandwiches")
    kids3 = d3.get("children") or []
    allergies3 = kids3[0].get("allergies", []) if kids3 else []
    c = r.add(Case("Onboarding", "peanut mentioned without the word allergy", "adversarial",
                   "not recorded as an allergy"))
    c.passed = not allergies3
    c.got = "not treated as an allergy" if c.passed else f"invented an allergy: {allergies3}"


# --------------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------------
def render(r: Result) -> str:
    adv, leg = r.adversarial, r.legitimate
    adv_ok = sum(1 for c in adv if c.passed)
    false_refusals = len(leg) - sum(1 for c in leg if c.passed)

    lines = [
        START,
        "## What it refuses to do",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
        "`python -m evals.refusal_eval`.",
        "",
        "Tally decides whether meals get paid for. A wrong yes is a false claim against a federal "
        "food programme. A wrong no is a provider losing money she is owed for food she actually "
        "served. Both are failures, so both directions are measured.",
        "",
        f"**{adv_ok} of {len(adv)} adversarial cases refused. "
        f"{false_refusals} false refusals across {len(leg)} legitimate cases.**",
        "",
        "The second number is the one that matters. Refusing everything scores 100 percent on the "
        "first, and would make the product worthless: the whole point is getting her paid for the "
        "meals she did serve.",
        "",
        "### Refused, correctly",
        "",
        "| Area | What was attempted | What happened |",
        "|---|---|---|",
    ]
    for c in adv:
        mark = "" if c.passed else " **NOT REFUSED**"
        lines.append(f"| {c.area} | {c.name} | {c.got}{mark} |")

    lines += ["", "### Credited, correctly", "",
              "| Area | What was attempted | What happened |", "|---|---|---|"]
    for c in leg:
        mark = "" if c.passed else " **WRONGLY REFUSED**"
        lines.append(f"| {c.area} | {c.name} | {c.got}{mark} |")

    lines += [
        "",
        "Rerun with `python -m evals.refusal_eval`. It calls no model, so it is deterministic and "
        "runs in CI on every push.",
        END,
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    r = Result()
    for check in (check_confidence_gate, check_meal_pattern, check_allergies,
                  check_state_ratio, check_onboarding):
        check(r)

    body = render(r)
    print(body)

    Path("evals/refusal_results.json").write_text(json.dumps(
        {"generated": datetime.now(UTC).isoformat(),
         "cases": [c.__dict__ for c in r.cases]}, indent=2), encoding="utf-8")

    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        if START in text and END in text:
            text = re.sub(re.escape(START) + ".*?" + re.escape(END), body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
        print(f"\nwritten into {a.out}")

    return 1 if any(not c.passed for c in r.cases) else 0


if __name__ == "__main__":
    raise SystemExit(main())
