"""The refusal eval is the headline number on docs/EVAL.md, so it runs in CI like anything else.

A published number nobody reruns is an assertion. This makes it a measurement: if a refusal stops
working, or if Tally starts refusing a meal it should credit, the build fails rather than the page
quietly becoming untrue.
"""

from __future__ import annotations

import pathlib
import re

from evals import refusal_eval


def _run() -> refusal_eval.Result:
    r = refusal_eval.Result()
    for check in (refusal_eval.check_confidence_gate, refusal_eval.check_meal_pattern,
                  refusal_eval.check_allergies, refusal_eval.check_state_ratio,
                  refusal_eval.check_onboarding):
        check(r)
    return r


def test_every_adversarial_case_is_refused():
    failed = [c.name for c in _run().adversarial if not c.passed]
    assert not failed, f"these were not refused: {failed}"


def test_no_meal_she_actually_served_is_refused():
    """The control. A false refusal is the provider losing money for food she did serve."""
    failed = [c.name for c in _run().legitimate if not c.passed]
    assert not failed, f"these were wrongly refused: {failed}"


def test_the_published_number_matches_what_the_eval_measures():
    r = _run()
    page = pathlib.Path("docs/EVAL.md").read_text(encoding="utf-8")
    claim = f"{len(r.adversarial)} of {len(r.adversarial)} adversarial cases refused"
    assert claim in page, f"EVAL.md does not say {claim!r}. Rerun the eval with --out docs/EVAL.md"
    assert re.search(rf"{len(r.legitimate)} legitimate cases", page)


def test_both_sides_are_actually_populated():
    r = _run()
    assert len(r.adversarial) >= 10
    assert len(r.legitimate) >= 5


def test_the_baseline_comparison_is_reproducible_and_honest():
    """The named baseline is a headline claim, so it runs here too.

    Two properties matter. The number has to be stable, because a figure that moves between runs is
    not evidence. And whole services must stay separated from single foods, because counting a
    banana beside a lunch tray as the same kind of case is exactly how this number gets inflated.
    """
    from evals import baseline_eval

    a, b = baseline_eval.run(), baseline_eval.run()
    assert len(a["short"]) == len(b["short"]), "the baseline number moved between two runs"
    assert a["lost_per_service"] == b["lost_per_service"]

    assert a["services"] and a["singles"], "the two kinds must both be populated"
    assert not ({r["photo"] for r in a["services"]} & {r["photo"] for r in a["singles"]})

    # A plate carrying every required component has to pass, or the comparison is measuring a bug.
    tray = next(r for r in a["rows"] if r["photo"] == "lunch_tray")
    assert tray["qualifies"], "a full lunch tray must be reimbursable"


def test_the_published_baseline_matches_what_the_eval_measures():
    import pathlib

    from evals import baseline_eval

    s = baseline_eval.run()
    page = pathlib.Path("docs/EVAL.md").read_text(encoding="utf-8")
    assert f"{len(s['svc_short'])} of the {len(s['services'])} photographs" in page
    assert f"{s['lost_per_service']:.2f} dollars" in page
