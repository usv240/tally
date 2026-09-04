from datetime import date, datetime

import pytest

from tally.engine.ratio import check_ratio, limits_for, under_two_count
from tally.models import Child

TODAY = date(2026, 9, 8)  # a Tuesday. Nia comes Monday, Wednesday and Friday, so not today.
MORNING = datetime(2026, 9, 8, 8, 0)


def child(cid: str, birth: date, arrival: str = "07:30", days=(0, 1, 2, 3, 4)) -> Child:
    return Child(id=cid, provider_id="rosa", first_name=cid.title(), birth_date=birth,
                 enrolled_days=list(days), usual_arrival=arrival)


ROSTER = [
    child("maya", date(2025, 3, 3)),
    child("leo", date(2022, 6, 1)),
    child("ava", date(2022, 1, 9), "07:45"),
    child("mateo", date(2022, 4, 2), "08:00"),
    child("nia", date(2024, 11, 5), days=(0, 2, 4)),
    child("sam", date(2021, 8, 8)),
    child("eli", date(2026, 2, 2), days=(0, 1, 2, 3)),
    child("priya", date(2018, 5, 5), "15:10"),
    child("jordan", date(2017, 9, 9), "15:10"),
]

ALL_IDS = {c.id for c in ROSTER}


def absent_except(*present: str) -> set[str]:
    """Everyone not named is explicitly marked absent, so only the named children count."""
    return ALL_IDS - set(present)


def test_texas_licensed_limits_load():
    assert limits_for("TX", "licensed")["max_group_size"] == 12


def test_unknown_state_refuses_rather_than_guessing():
    with pytest.raises(KeyError) as e:
        limits_for("ZZ", "licensed")
    assert "rather than guessing" in str(e.value)


def test_morning_count_is_within_the_limit():
    present = {"maya", "leo", "ava", "sam", "eli"}
    r = check_ratio(present, ROSTER, "TX", "licensed", MORNING,
                    absent_ids=absent_except(*present, "priya", "jordan"))
    assert r.now_count == 5 and r.now_ok
    assert r.limit == 12


def test_it_warns_in_the_morning_about_the_after_school_arrival():
    """The whole point: she hears about ten past three at eight in the morning."""
    present = {"maya", "leo", "ava", "sam", "eli", "mateo"}
    r = check_ratio(present, ROSTER, "TX", "licensed", MORNING,
                    absent_ids=absent_except(*present, "priya", "jordan"))
    assert r.next_change_at == datetime(2026, 9, 8, 15, 10)
    assert r.next_change_count == 8  # both school age children arrive together
    assert r.next_change_ok
    assert "3:10pm" in r.explanation


def test_it_says_over_the_limit_when_the_afternoon_would_break_the_rule():
    extra = [child(f"x{i}", date(2021, 1, 1), "15:10") for i in range(5)]
    roster = ROSTER + extra
    present = {"maya", "leo", "ava", "sam", "eli", "mateo"}
    absent = ({c.id for c in roster} - present - {"priya", "jordan"} - {c.id for c in extra})
    r = check_ratio(present, roster, "TX", "licensed", MORNING, absent_ids=absent)
    assert r.next_change_count == 13
    assert r.next_change_ok is False
    assert "over the limit" in r.explanation


def test_children_not_enrolled_today_are_neither_present_nor_expected():
    """Nia comes Monday, Wednesday and Friday. On a Tuesday she does not appear at all."""
    r = check_ratio({"maya"}, ROSTER, "TX", "licensed", MORNING)
    assert "nia" not in r.unaccounted


def test_a_child_whose_arrival_has_passed_is_named_not_ignored():
    """Ava usually arrives at 07:45. At 08:00 she is neither signed in nor marked absent, so she
    counts toward the limit and is named, rather than being quietly assumed away."""
    r = check_ratio({"maya"}, ROSTER, "TX", "licensed", MORNING)
    assert "ava" in r.unaccounted and "mateo" in r.unaccounted
    assert "not signed in yet" in r.explanation


def test_marking_children_absent_clears_them():
    r = check_ratio({"maya"}, ROSTER, "TX", "licensed", MORNING,
                    absent_ids=absent_except("maya", "priya", "jordan"))
    assert r.unaccounted == []
    assert "not signed in" not in r.explanation


def test_unaccounted_children_can_push_the_count_over_the_limit():
    """Sixteen enrolled, one signed in, nobody marked absent. She is not under the limit, she just
    does not know yet, and saying she has room would be the dangerous answer."""
    roster = ROSTER + [child(f"y{i}", date(2021, 1, 1), "07:00") for i in range(7)]
    r = check_ratio({"maya"}, roster, "TX", "licensed", MORNING)
    assert r.now_ok is False
    assert len(r.unaccounted) == 12


def test_no_upcoming_arrivals_late_in_the_day():
    evening = datetime(2026, 9, 8, 17, 30)
    r = check_ratio({"maya", "leo"}, ROSTER, "TX", "licensed", evening,
                    absent_ids=absent_except("maya", "leo"))
    assert r.next_change_at is None
    assert r.explanation == "2 of 12 now"


def test_under_two_count_includes_infants():
    assert under_two_count({"maya", "eli", "sam"}, ROSTER, TODAY) == 2
