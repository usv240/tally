"""The prove eval's published numbers are measurements, so this pins them to what was measured.

The solver half calls AWS and takes minutes, so it is not rerun here. What is checked: the cases are
real and cite a source, the results file exists and agrees with EVAL.md, and the two numbers that
decide whether the tool is safe hold: no correct USDA answer was wrongly blocked, and no off-topic
answer was wrongly proved.
"""

from __future__ import annotations

import json
import pathlib
import re

CASES = json.loads(pathlib.Path("evals/cases/prove_cases.json").read_text(encoding="utf-8"))


def test_every_case_cites_usda_and_carries_both_polarities():
    assert len(CASES["cases"]) >= 25
    for c in CASES["cases"]:
        assert re.search(r"226\.20|CACFP 06-2025", c["source"]), c["id"]
        assert c["correct"] != c["wrong"] and c["question"].strip()
    assert len(CASES["off_topic"]) >= 4


def test_the_published_numbers_match_the_results_file():
    results = json.loads(pathlib.Path("evals/prove_results.json").read_text(encoding="utf-8"))
    s = results["solver"]
    page = pathlib.Path("docs/EVAL.md").read_text(encoding="utf-8")
    claim = (f"{s['caught']} of {s['n']} wrong answers contradicted, {s['blocked']} of {s['n']} correct "
             f"answers wrongly blocked, {s['off_topic_proved']} of {s['off_topic_n']} off-topic answers wrongly proved")
    assert claim in page, f"EVAL.md does not say {claim!r}. Rerun python -m evals.prove_eval --solver --out docs/EVAL.md"
    assert s["n"] == len(CASES["cases"])


def test_the_negative_controls_hold():
    """A correct USDA answer blocked is the provider losing a meal she served. Zero, or the tool is unsafe."""
    s = json.loads(pathlib.Path("evals/prove_results.json").read_text(encoding="utf-8"))["solver"]
    assert s["blocked"] == 0, [r["id"] for r in s["rows"] if r["correct"]["verdict"] in ("INVALID", "IMPOSSIBLE")]
    assert s["off_topic_proved"] == 0
    assert s["caught"] >= 0.8 * s["n"], "the tool stopped catching wrong answers"


def test_the_audit_found_the_stale_yogurt_rule():
    a = json.loads(pathlib.Path("evals/audit_results.json").read_text(encoding="utf-8"))
    page = pathlib.Path("docs/EVAL.md").read_text(encoding="utf-8")
    assert f"{a['stale']} of {a['n']} statements contradicted the regulation" in page
