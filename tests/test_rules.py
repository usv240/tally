from datetime import date

import pytest

from tally.engine.rules import DayContext, allergy_conflicts, check_meal, load_rules
from tally.models import AgeGroup, Component, Item, MealType, age_group_for

TODDLER = {AgeGroup.A1_2}
PRESCHOOL = {AgeGroup.A3_5}
MIXED = {AgeGroup.A1_2, AgeGroup.A3_5}


def item(name: str, component: Component, confidence: float = 0.95) -> Item:
    return Item(name=name, component=component, confidence=confidence)


MILK = item("milk", Component.MILK)
BANANA = item("banana", Component.FRUIT)
OATMEAL = item("oatmeal", Component.GRAIN)
CRACKERS = item("whole grain crackers", Component.GRAIN)
APPLE = item("apple slices", Component.FRUIT)
CHICKEN = item("chicken", Component.MEAT_ALT)
RICE = item("brown rice", Component.GRAIN)
BEANS = item("green beans", Component.VEGETABLE)
ORANGE = item("orange slices", Component.FRUIT)
JUICE = item("apple juice", Component.JUICE)
YOGURT = item("yogurt", Component.MEAT_ALT)
PEAR = item("pear", Component.FRUIT)


def test_rules_file_loads_and_is_versioned():
    r = load_rules()
    assert r["version"]
    assert set(r["meals"]) == {"breakfast", "lunch", "supper", "snack"}


# Breakfast -------------------------------------------------------------------

def test_breakfast_qualifies():
    v = check_meal([MILK, BANANA, OATMEAL], MealType.BREAKFAST, MIXED)
    assert v.reimbursable
    assert v.missing == []
    assert v.rule_version


def test_breakfast_missing_milk_names_the_fix():
    v = check_meal([BANANA, OATMEAL], MealType.BREAKFAST, MIXED)
    assert not v.reimbursable
    assert v.missing == [Component.MILK]
    assert "milk" in v.smallest_fix.lower()


def test_breakfast_accepts_meat_alternate_instead_of_grain():
    v = check_meal([MILK, BANANA, YOGURT], MealType.BREAKFAST, PRESCHOOL)
    assert v.reimbursable
    assert any("meat or meat alternate is replacing the grain" in f for f in v.flags)


def test_breakfast_vegetable_satisfies_the_fruit_or_vegetable_slot():
    v = check_meal([MILK, OATMEAL, BEANS], MealType.BREAKFAST, PRESCHOOL)
    assert v.reimbursable


# Lunch -----------------------------------------------------------------------

def test_lunch_qualifies():
    v = check_meal([MILK, CHICKEN, RICE, BEANS, ORANGE], MealType.LUNCH, MIXED)
    assert v.reimbursable


def test_lunch_missing_fruit_is_the_demo_case():
    """The moment the whole product exists for: caught at the table, not at claim time."""
    v = check_meal([MILK, CHICKEN, RICE, BEANS], MealType.LUNCH, MIXED)
    assert not v.reimbursable
    assert v.missing == [Component.FRUIT]
    assert "qualifies" in v.smallest_fix
    assert any(word in v.smallest_fix.lower() for word in ("apple", "banana", "orange", "pear"))


def test_lunch_accepts_a_second_fruit_instead_of_a_vegetable():
    v = check_meal([MILK, CHICKEN, RICE, ORANGE, PEAR], MealType.LUNCH, MIXED)
    assert v.reimbursable
    assert any("second fruit" in f for f in v.flags)


def test_one_fruit_does_not_stand_in_for_the_vegetable():
    v = check_meal([MILK, CHICKEN, RICE, ORANGE], MealType.LUNCH, MIXED)
    assert not v.reimbursable
    assert Component.VEGETABLE in v.missing


def test_lunch_short_two_components_says_so():
    v = check_meal([MILK, RICE], MealType.LUNCH, MIXED)
    assert not v.reimbursable
    assert len(v.missing) == 3
    assert "short 3 components" in v.smallest_fix


# Snack -----------------------------------------------------------------------

def test_snack_needs_two_components():
    assert check_meal([CRACKERS, APPLE], MealType.SNACK, PRESCHOOL).reimbursable
    v = check_meal([CRACKERS], MealType.SNACK, PRESCHOOL)
    assert not v.reimbursable
    assert "qualifies" in v.smallest_fix


def test_snack_of_juice_and_milk_alone_does_not_qualify():
    v = check_meal([JUICE, MILK], MealType.SNACK, PRESCHOOL)
    assert not v.reimbursable
    assert any("Juice and milk cannot be the only two" in f for f in v.flags)


def test_juice_counts_once_a_day():
    fresh = check_meal([JUICE, CRACKERS], MealType.SNACK, PRESCHOOL, DayContext(juice_already_counted=False))
    assert fresh.reimbursable
    again = check_meal([JUICE, CRACKERS], MealType.SNACK, PRESCHOOL, DayContext(juice_already_counted=True))
    assert not again.reimbursable
    assert any("already counted" in f for f in again.flags)


# Label checks and infants -----------------------------------------------------

def test_yogurt_raises_a_label_check_but_does_not_block():
    v = check_meal([YOGURT, PEAR], MealType.SNACK, PRESCHOOL)
    assert v.reimbursable
    assert "yogurt_sugar" in v.label_checks


def test_infant_only_meal_is_recorded_not_judged():
    v = check_meal([MILK, BANANA], MealType.LUNCH, {AgeGroup.INFANT})
    assert not v.reimbursable
    assert "separate meal pattern" in " ".join(v.flags)


def test_pantry_suggestion_prefers_the_providers_own_food():
    v = check_meal([MILK, CHICKEN, RICE, BEANS], MealType.LUNCH, MIXED,
                   pantry={Component.FRUIT: ["the pears from Tuesday"]})
    assert "the pears from Tuesday" in v.smallest_fix


# Age groups ------------------------------------------------------------------

@pytest.mark.parametrize("birth,expected", [
    (date(2026, 3, 1), AgeGroup.INFANT),
    (date(2024, 3, 1), AgeGroup.A1_2),
    (date(2021, 3, 1), AgeGroup.A3_5),
    (date(2017, 3, 1), AgeGroup.A6_12),
    (date(2010, 3, 1), AgeGroup.A13_18),
])
def test_age_groups(birth, expected):
    assert age_group_for(birth, date(2026, 9, 9)) == expected


def test_age_group_on_the_birthday_boundary():
    assert age_group_for(date(2025, 9, 10), date(2026, 9, 9)) == AgeGroup.INFANT
    assert age_group_for(date(2025, 9, 9), date(2026, 9, 9)) == AgeGroup.A1_2


# Allergies -------------------------------------------------------------------

def test_dairy_allergy_catches_yogurt_not_only_milk():
    hits = allergy_conflicts([YOGURT, PEAR], {"nia": ["dairy"]})
    assert hits == {"nia": ["yogurt"]}


def test_peanut_allergy_is_quiet_when_nothing_matches():
    assert allergy_conflicts([MILK, CHICKEN, RICE], {"leo": ["peanut"]}) == {}


def test_allergy_check_covers_every_present_child():
    hits = allergy_conflicts([MILK, CRACKERS], {"nia": ["dairy"], "sam": ["wheat"], "ava": []})
    assert set(hits) == {"nia", "sam"}


# Bring your own photograph -----------------------------------------------------

def test_no_children_signed_in_is_not_the_same_as_only_infants():
    """A standalone API call has nobody signed in. Answering "only infants" would be wrong, and
    answering "not reimbursable" with nothing missing and no fix is three claims that cannot all
    be true at once."""
    v = check_meal([MILK, BANANA, OATMEAL], MealType.BREAKFAST, set())
    assert not v.reimbursable
    assert v.missing == [] and v.smallest_fix == ""
    assert "nobody to judge this meal for" in " ".join(v.flags)
    assert "infant" not in " ".join(v.flags).lower()


def test_an_explicit_age_group_gives_a_real_verdict_with_nobody_present():
    v = check_meal([MILK, BANANA, OATMEAL], MealType.BREAKFAST, {AgeGroup.A3_5})
    assert v.reimbursable
