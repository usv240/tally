from datetime import date

import pytest

from tally.onboarding import (
    age_group_for,
    clean_name,
    find_allergies,
    find_days,
    parse_birth_date,
    parse_children,
    ratio_preview,
)

TODAY = date(2026, 9, 8)

ENROLMENT = """
Maya, born 3 March 2025, subsidised Mon-Fri
Leo, 1 June 2022, peanut allergy, Mon to Fri, subsidised
Ava, 09/01/2022, Mon Tue Wed Thu Fri
Nia, 2024-11-05, Mon Wed Fri, dairy allergy, voucher
Eli, born 2 Feb 2026, Mon-Thu, subsidised
"""


def test_the_shapes_people_actually_write_a_birthday_in():
    for text in ["born 3 March 2025", "March 3, 2025", "3rd Mar 2025", "2025-03-03", "3/3/2025",
                 "03/03/25"]:
        assert parse_birth_date(text, TODAY) == date(2025, 3, 3), text


def test_a_line_with_no_date_is_not_a_child():
    assert parse_birth_date("Maya, subsidised, peanut allergy", TODAY) is None


def test_an_impossible_date_is_refused_rather_than_guessed():
    assert parse_birth_date("30 February 2025", TODAY) is None
    assert parse_birth_date("2025-13-40", TODAY) is None


def test_a_whole_enrolment_paste():
    r = parse_children(ENROLMENT, TODAY)
    assert [c.first_name for c in r.children] == ["Maya", "Leo", "Ava", "Nia", "Eli"]
    assert not r.unreadable


def test_allergies_are_read_and_nothing_is_invented():
    r = parse_children(ENROLMENT, TODAY)
    by_name = {c.first_name: c.allergies for c in r.children}
    assert by_name["Leo"] == ["peanut"]
    assert by_name["Nia"] == ["dairy"]
    assert by_name["Maya"] == []


def test_an_allergy_word_without_the_word_allergy_is_not_assumed():
    """"Maya loves milk" is not an allergy, and treating it as one would be its own kind of wrong."""
    assert find_allergies("Maya loves milk and eggs") == []
    assert find_allergies("Maya is allergic to milk") == ["milk"]


def test_days_from_a_range_and_from_a_list():
    assert find_days("Mon-Fri") == [0, 1, 2, 3, 4]
    assert find_days("Mon Wed Fri") == [0, 2, 4]
    assert find_days("Tue to Fri") == [1, 2, 3, 4]
    assert find_days("no days here") == []


def test_subsidy_is_recognised_in_the_words_providers_use():
    r = parse_children(ENROLMENT, TODAY)
    by_name = {c.first_name: c for c in r.children}
    assert by_name["Maya"].subsidized and by_name["Maya"].subsidy_days == [0, 1, 2, 3, 4]
    assert by_name["Nia"].subsidized and by_name["Nia"].subsidy_days == [0, 2, 4]
    assert not by_name["Ava"].subsidized


def test_the_name_survives_and_the_rest_does_not():
    assert clean_name("Leo, 1 June 2022, peanut allergy, Mon to Fri, subsidised", "") == "Leo"


def test_an_infant_is_flagged_because_the_rules_are_different():
    r = parse_children("Eli, born 2 Feb 2026", TODAY)
    assert r.children[0].age_group == "infant"
    assert any("infant pattern" in w for w in r.warnings)


def test_a_birthday_in_the_future_is_refused_and_explained():
    r = parse_children("Zoe, born 3 March 2027", TODAY)
    assert not r.children
    assert any("future" in w for w in r.warnings)


def test_a_repeated_child_is_kept_once_and_reported():
    r = parse_children("Maya, 3 March 2025\nMaya, 3 March 2025", TODAY)
    assert len(r.children) == 1
    assert any("more than once" in w for w in r.warnings)


def test_a_line_it_cannot_read_is_reported_not_dropped():
    """A child missing from the roster is a child whose allergy is never checked."""
    r = parse_children("Maya, 3 March 2025\nsomething about the fire drill", TODAY)
    assert len(r.children) == 1
    assert r.unreadable == ["something about the fire drill"]


@pytest.mark.parametrize("birth,expected", [
    (date(2026, 3, 1), "infant"), (date(2024, 3, 1), "1-2"), (date(2021, 3, 1), "3-5"),
    (date(2017, 3, 1), "6-12"),
])
def test_age_groups(birth, expected):
    assert age_group_for(birth, TODAY) == expected


def test_the_ratio_preview_says_yes_when_the_group_fits():
    r = parse_children(ENROLMENT, TODAY)
    p = ratio_preview(r.children, "TX", "licensed")
    assert p["ok"] and p["enrolled"] == 5 and p["limit"] == 12


def test_the_ratio_preview_refuses_a_state_it_has_no_table_for():
    r = parse_children(ENROLMENT, TODAY)
    p = ratio_preview(r.children, "ZZ", "licensed")
    assert not p["ok"] and "rather than guessing" in p["error"]


NAMES = ["Ana", "Ben", "Cara", "Dev", "Eve", "Finn", "Gia", "Hugo", "Iris", "Jack",
         "Kira", "Liam", "Mira", "Noah", "Opal"]


def test_the_ratio_preview_catches_too_many_children_before_anything_is_saved():
    """She finds out at setup, not when an inspector counts heads."""
    text = "\n".join(f"{n}, 1 June 2022" for n in NAMES)
    r = parse_children(text, TODAY)
    assert len(r.children) == 15
    p = ratio_preview(r.children, "TX", "licensed")
    assert not p["ok"]
    assert any("over the limit of 12" in x for x in p["problems"])


def test_the_ratio_preview_catches_too_many_under_twos():
    text = "\n".join(f"{n}, 1 June 2025" for n in NAMES[:6])
    r = parse_children(text, TODAY)
    assert len(r.children) == 6
    p = ratio_preview(r.children, "TX", "licensed")
    assert not p["ok"]
    assert any("under two" in x for x in p["problems"])


def test_blank_input_produces_nothing_and_complains_about_nothing():
    r = parse_children("\n\n   \n", TODAY)
    assert not r.children and not r.unreadable and not r.warnings
