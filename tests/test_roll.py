from datetime import date, datetime

from tally.agents.roll import apply_correction, echo, parse_roll
from tally.models import Child

NOW = datetime(2026, 9, 8, 7, 38)


def child(cid: str, name: str, **kw) -> Child:
    return Child(id=cid, provider_id="rosa", first_name=name, birth_date=date(2022, 1, 1), **kw)


ROSTER = [
    child("maya", "Maya"), child("leo", "Leo"), child("ava", "Ava"), child("mateo", "Mateo"),
    child("nia", "Nia"), child("sam", "Sam"), child("eli", "Eli"),
]


def by_child(events):
    return {e.child_id: e.event for e in events}


def test_the_demo_sentence():
    """The sentence the whole product opens with."""
    events, unknown = parse_roll(
        "Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at 8", ROSTER, NOW)
    assert by_child(events) == {"maya": "arrive", "leo": "arrive", "ava": "absent", "mateo": "expected"}
    assert not unknown


def test_absence_keeps_the_reason():
    events, _ = parse_roll("Ava is sick today", ROSTER, NOW)
    assert events[0].event == "absent" and events[0].note == "sick"


def test_a_later_arrival_records_the_time():
    events, _ = parse_roll("Mateo's coming at 8:15", ROSTER, NOW)
    assert events[0].event == "expected"
    assert events[0].at == datetime(2026, 9, 8, 8, 15)


def test_an_afternoon_arrival_without_a_meridiem_is_the_afternoon():
    """In a child care day, "coming at 3" is never three in the morning."""
    events, _ = parse_roll("Priya is coming at 3", ROSTER + [child("priya", "Priya")], NOW)
    assert events[0].at.hour == 15


def test_departure():
    events, _ = parse_roll("Sam got picked up", ROSTER, NOW)
    assert events[0].event == "depart"


def test_a_name_it_does_not_know_is_reported_not_guessed():
    events, unknown = parse_roll("Maya's here and Tobias is here", ROSTER, NOW)
    assert by_child(events) == {"maya": "arrive"}
    assert unknown == ["Tobias"]


def test_the_last_word_about_a_child_wins():
    events, _ = parse_roll("Leo's here, actually Leo is sick", ROSTER, NOW)
    assert by_child(events) == {"leo": "absent"}


def test_correction_after_the_fact():
    events, _ = parse_roll("Maya's here, Leo's here", ROSTER, NOW)
    fixed = apply_correction("No, Leo's not here yet", events, ROSTER, NOW)
    assert by_child(fixed) == {"maya": "arrive", "leo": "expected"}


def test_a_sentence_that_is_not_a_correction_changes_nothing():
    events, _ = parse_roll("Maya's here", ROSTER, NOW)
    assert apply_correction("Leo is here too", events, ROSTER, NOW) == events


def test_echo_reads_back_what_was_recorded():
    events, _ = parse_roll(
        "Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at 8", ROSTER, NOW)
    line = echo(events, ROSTER)
    assert "Maya, Leo here" in line
    assert "Ava absent sick" in line
    assert "Mateo at 8:00" in line


def test_echo_when_nothing_was_heard():
    assert "did not catch" in echo([], ROSTER)


def test_empty_input():
    events, unknown = parse_roll("", ROSTER, NOW)
    assert events == [] and unknown == []
