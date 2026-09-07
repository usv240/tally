"""House style on text a model wrote.

check_copy.py holds the repository to no emoji and no em dashes, and never saw the text that
actually reaches Rosa. Two questions on the deployed service came back with em dashes in them, which
made the rule true of the repository and false of the product.
"""

from __future__ import annotations

from datetime import datetime

from tally.agents.gate import new_question
from tally.house import plain, plain_all

EM = chr(0x2014)
EN = chr(0x2013)
ELLIPSIS = chr(0x2026)
CURLY = chr(0x2019)
NBSP = chr(0x00A0)


def test_the_question_that_actually_shipped_is_fixed():
    """Verbatim from the deployed service on 6 September 2026."""
    live = f"The pale liquid pooled in the oatmeal bowl {EM} is it fluid milk, water, or broth?"
    out = plain(live)
    assert EM not in out
    assert out == "The pale liquid pooled in the oatmeal bowl, is it fluid milk, water, or broth?"


def test_an_em_dash_becomes_a_comma_and_an_en_dash_a_hyphen():
    assert plain(f"lunch {EM} short two components") == "lunch, short two components"
    assert plain(f"ages 3{EN}5") == "ages 3-5"


def test_emoji_go_and_the_sentence_still_reads():
    assert plain("Nice work \U0001F389 the meal qualifies") == "Nice work the meal qualifies"
    assert plain(chr(0x2705) + " logged") == "logged"   # written so check_copy passes
    assert plain(chr(0x2B50) + " starred") == "starred"


def test_smart_quotes_ellipses_and_odd_spaces_are_normalised():
    assert plain(f"that{CURLY}s hers") == "that's hers"
    assert plain(f"wait{ELLIPSIS}") == "wait..."
    assert plain(f"one{NBSP}two") == "one two"


def test_ordinary_text_is_left_exactly_alone():
    for s in ["Lunch is short 2 components. Start with milk.",
              "Leo has a peanut allergy.",
              "$436.92 a month",
              "café au lait, 20°C"]:
        assert plain(s) == s


def test_it_is_idempotent_and_safe_on_nothing():
    once = plain(f"a {EM} b \U0001F600")
    assert plain(once) == once
    assert plain("") == ""


def test_plain_all_drops_what_was_only_punctuation():
    assert plain_all([f"ok {EM} fine", "\U0001F600", "", "  "]) == ["ok, fine"]


def test_every_question_is_cleaned_on_the_way_in():
    """The choke point that matters: whoever writes a question, this is what is stored."""
    q = new_question("rosa", f"Is the pale liquid milk {EM} or water?", datetime(2026, 9, 8),
                     "meal", options=[f"Milk {EM} whole", "Water \U0001F4A7"])
    assert EM not in q.text
    assert q.text == "Is the pale liquid milk, or water?"
    assert q.options == ["Milk, whole", "Water"]


def test_everything_spoken_to_her_is_cleaned():
    from tally.service import setup

    rt, _ = setup()
    rt.say(f"Lunch is short two components {EM} start with milk.")
    assert EM not in rt.spoken[-1]["text"]
    assert rt.spoken[-1]["text"].endswith("short two components, start with milk.")
