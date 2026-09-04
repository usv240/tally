"""The CACFP meal pattern check. Deterministic, versioned, and explainable.

No model reasoning happens here. The vision model says what is on the plate; this decides whether
that is a reimbursable meal, and if not, the smallest change that would make it one.

The rules themselves live in rules/cacfp_rules.json so they can be updated without touching code,
and every verdict records the version it was decided under, which is what makes an audit possible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from tally.models import AgeGroup, Component, Item, MealType, Verdict

RULES_DIR = Path(__file__).resolve().parents[3] / "rules"

# Foods a provider is likely to have on hand, by the component they satisfy. Used to suggest a fix
# in terms of real food rather than a category name. The provider's own vocabulary, learned in
# Memory, is layered on top of this at runtime.
COMMON_FOODS = {
    Component.MILK: ["milk"],
    Component.FRUIT: ["apple slices", "banana", "orange slices", "pear"],
    Component.VEGETABLE: ["carrot sticks", "green beans", "peas"],
    Component.GRAIN: ["whole grain crackers", "brown rice", "whole wheat bread"],
    Component.MEAT_ALT: ["cheese", "yogurt", "beans", "chicken"],
}

LABEL_CHECK_FOODS = {
    "cereal": "cereal_sugar",
    "breakfast cereal": "cereal_sugar",
    "yogurt": "yogurt_sugar",
}


@lru_cache(maxsize=4)
def load_rules(path: str | None = None) -> dict:
    p = Path(path) if path else RULES_DIR / "cacfp_rules.json"
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class DayContext:
    """What else happened today, which some rules depend on."""

    juice_already_counted: bool = False
    whole_grain_rich_served: bool = False


def components_present(items: list[Item]) -> set[Component]:
    """Juice is a fruit, but a limited one, so it is tracked as its own component and folded in
    only when the daily juice allowance has not been used."""
    return {i.component for i in items if i.component != Component.NONE}


def _satisfied(present: set[Component], day: DayContext) -> set[Component]:
    out = set(present)
    if Component.JUICE in out:
        out.discard(Component.JUICE)
        if not day.juice_already_counted:
            out.add(Component.FRUIT)
    return out


def _label_checks(items: list[Item]) -> list[str]:
    checks = []
    for item in items:
        low = item.name.lower()
        for food, check in LABEL_CHECK_FOODS.items():
            if food in low and check not in checks:
                checks.append(check)
    return checks


def _fix_phrase(component: Component, pantry: dict[Component, list[str]] | None) -> str:
    options = (pantry or {}).get(component) or COMMON_FOODS.get(component) or []
    if not options:
        return component.value.replace("_", " ")
    return options[0]


def check_meal(
    items: list[Item],
    meal_type: MealType,
    age_groups: set[AgeGroup],
    day: DayContext | None = None,
    pantry: dict[Component, list[str]] | None = None,
    rules: dict | None = None,
) -> Verdict:
    """Decide whether this plate is reimbursable for the children at the table."""
    rules = rules or load_rules()
    day = day or DayContext()
    version = rules["version"]
    present = components_present(items)
    usable = _satisfied(present, day)
    label_checks = _label_checks(items)
    flags: list[str] = []

    if Component.JUICE in present and day.juice_already_counted:
        flags.append("Juice has already counted once today, so it does not count again.")

    child_groups = {g for g in age_groups if g != AgeGroup.INFANT}
    if not child_groups:
        return Verdict(
            reimbursable=False, missing=[], smallest_fix="",
            flags=["Only infants at this meal. Infants follow a separate meal pattern, "
                   "so Tally records the meal and does not judge it."],
            label_checks=label_checks, rule_version=version,
            explanation="Recorded for infants. The infant meal pattern is not modelled.",
        )

    spec = rules["meals"][meal_type.value]

    if meal_type == MealType.SNACK:
        need = spec["choose_any"]
        have = sorted(c.value for c in usable)
        ok = len(usable) >= need
        # Juice and milk cannot be the only two components at a snack.
        if ok and Component.JUICE in present and usable == {Component.FRUIT, Component.MILK} and len(items) <= 2:
            ok = False
            flags.append("Juice and milk cannot be the only two components at snack.")
        missing: list[Component] = []
        fix = ""
        if not ok:
            candidates = [c for c in (Component.MILK, Component.FRUIT, Component.VEGETABLE,
                                      Component.GRAIN, Component.MEAT_ALT) if c not in usable]
            missing = candidates[: max(0, need - len(usable))]
            if missing:
                fix = f"Add {_fix_phrase(missing[0], pantry)} and this snack qualifies."
        explanation = (f"Snack needs {need} different components. "
                       + (f"You have {len(usable)}: {', '.join(have)}." if have else "You have none."))
        return Verdict(reimbursable=ok, missing=missing, smallest_fix=fix, flags=flags,
                       label_checks=label_checks, rule_version=version, explanation=explanation,
                       by_age_group={g.value: ok for g in child_groups})

    required = list(spec["required"])
    missing = []
    for req in required:
        if req == "fruit_or_vegetable":
            if not ({Component.FRUIT, Component.VEGETABLE} & usable):
                missing.append(Component.FRUIT)
            continue
        comp = Component(req)
        if comp in usable:
            continue
        # A second fruit may stand in for the vegetable at lunch and supper.
        if comp == Component.VEGETABLE and meal_type in (MealType.LUNCH, MealType.SUPPER):
            fruit_items = [i for i in items if i.component in (Component.FRUIT, Component.JUICE)]
            if len(fruit_items) >= 2:
                flags.append("A second fruit is standing in for the vegetable.")
                continue
        # A meat or meat alternate may replace the grain at breakfast, up to three times a week.
        if comp == Component.GRAIN and meal_type == MealType.BREAKFAST and Component.MEAT_ALT in usable:
            flags.append("A meat or meat alternate is replacing the grain at breakfast. "
                         "That is allowed up to three times a week.")
            continue
        missing.append(comp)

    ok = not missing
    fix = ""
    if missing:
        first = missing[0]
        food = _fix_phrase(first, pantry)
        word = "a " + first.value.replace("_", " ") if first != Component.MILK else "milk"
        fix = (f"Add {food} and this {meal_type.value} qualifies."
               if len(missing) == 1
               else f"This {meal_type.value} is short {len(missing)} components. Start with {food}.")
        explanation = (f"{meal_type.value.capitalize()} needs "
                       f"{', '.join(r.replace('_', ' ') for r in required)}. "
                       f"Missing {', '.join(m.value.replace('_', ' ') for m in missing)}.")
        _ = word
    else:
        explanation = (f"{meal_type.value.capitalize()} has every required component: "
                       f"{', '.join(sorted(c.value for c in usable))}.")

    return Verdict(reimbursable=ok, missing=missing, smallest_fix=fix, flags=flags,
                   label_checks=label_checks, rule_version=version, explanation=explanation,
                   by_age_group={g.value: ok for g in child_groups})


def allergy_conflicts(items: list[Item], allergies_by_child: dict[str, list[str]]) -> dict[str, list[str]]:
    """Which present children have an allergy matching something on this plate.

    Runs before anything is written. Matching is deliberately generous: a dairy allergy should catch
    milk, cheese and yogurt, because missing one is far worse than asking an unnecessary question.
    """
    families = {
        "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "cottage cheese"],
        "milk": ["milk", "cheese", "yogurt", "butter", "cream"],
        "peanut": ["peanut", "peanut butter"],
        "tree nut": ["almond", "walnut", "cashew", "pecan", "nut"],
        "egg": ["egg", "omelet", "omelette"],
        "wheat": ["bread", "cracker", "pasta", "tortilla", "cereal", "wheat"],
        "gluten": ["bread", "cracker", "pasta", "tortilla", "cereal", "wheat", "barley", "rye"],
        "soy": ["soy", "tofu", "edamame"],
        "fish": ["fish", "salmon", "tuna", "cod"],
        "shellfish": ["shrimp", "crab", "lobster"],
        "sesame": ["sesame", "tahini", "hummus"],
    }
    out: dict[str, list[str]] = {}
    names = [i.name.lower() for i in items]
    for child_id, allergies in allergies_by_child.items():
        hits = []
        for allergy in allergies:
            key = allergy.strip().lower()
            triggers = families.get(key, [key])
            for trigger in triggers:
                for name in names:
                    if trigger in name and name not in hits:
                        hits.append(name)
        if hits:
            out[child_id] = hits
    return out
