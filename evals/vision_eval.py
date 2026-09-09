"""Measure what the Plate agent actually gets right, on the real photographs in data/plates.

This is an eval, not a unit test: it calls a model, so it costs money and takes about a minute. Run
it deliberately and commit the result to docs/EVAL.md, so a claim about accuracy is a measurement
rather than an assertion.

Run: python -m evals.vision_eval --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from tally.agents.plate import read_plate
from tally.models import Component

PLATES = Path("data/plates")

# What a person sees in each photograph, written down before running the model.
# "expect" must all be found. "allow" may appear without counting as a mistake, because these
# photographs are of real food and often contain more than the one thing they were chosen for.
EXPECTED: dict[str, dict] = {
    "lunch_tray": {
        "expect": {Component.MILK, Component.GRAIN, Component.MEAT_ALT, Component.VEGETABLE, Component.FRUIT},
        "allow": set(),
        "note": "USDA MyPlate school lunch tray. Every component is present.",
    },
    "chicken_rice_veg": {
        "expect": {Component.MEAT_ALT, Component.GRAIN, Component.VEGETABLE},
        "allow": set(),
        "note": "Grilled chicken with rice and vegetables. No milk and no fruit.",
    },
    "school_lunch_fi": {
        "expect": {Component.VEGETABLE, Component.GRAIN},
        "allow": {Component.MEAT_ALT},
        "note": "Finnish school lunch: soup and crispbread. The soup may read as containing meat.",
    },
    "milk": {"expect": {Component.MILK}, "allow": set(), "note": "A glass of milk."},
    "yogurt": {"expect": {Component.MEAT_ALT}, "allow": {Component.FRUIT},
               "note": "Yoghurt in a bowl. Yoghurt is a meat alternate under CACFP."},
    "banana": {"expect": {Component.FRUIT}, "allow": set(), "note": "A banana."},
    "oatmeal": {"expect": {Component.GRAIN}, "allow": {Component.FRUIT, Component.MEAT_ALT},
                "note": "Porridge with toppings, so raisins and nut butter may also be seen."},
    "crackers": {"expect": {Component.GRAIN}, "allow": set(), "note": "A wholewheat cracker."},
    "orange_slices": {"expect": {Component.FRUIT}, "allow": set(), "note": "A blood orange slice."},
    "pear": {"expect": {Component.FRUIT}, "allow": set(), "note": "Pears."},
    "green_beans": {"expect": {Component.VEGETABLE}, "allow": set(),
                    "note": "Green beans with onions, both vegetables."},
    "oatmeal_with_milk": {"expect": {Component.GRAIN, Component.MILK},
                          "allow": {Component.FRUIT, Component.MEAT_ALT},
                          "note": "Composite: the breakfast after the milk was added."},
    "chicken_rice_veg_fixed": {
        "expect": {Component.MEAT_ALT, Component.GRAIN, Component.VEGETABLE, Component.MILK, Component.FRUIT},
        "allow": set(),
        "note": "Composite: the lunch after milk and fruit were added.",
    },
}


def run(trials: int = 1) -> dict:
    rows = []
    for stem, spec in EXPECTED.items():
        path = PLATES / f"{stem}.jpg"
        if not path.exists():
            continue
        found_counts: dict[str, int] = {}
        missed_total = spurious_total = asked = 0
        errors = 0
        for _ in range(trials):
            try:
                reading = read_plate(path)
            except Exception as exc:  # a model error is a result, not a crash
                errors += 1
                print(f"  {stem}: ERROR {type(exc).__name__}")
                continue
            got = {i.component for i in reading.items}
            for c in got:
                found_counts[c.value] = found_counts.get(c.value, 0) + 1
            missed_total += len(spec["expect"] - got)
            spurious_total += len(got - spec["expect"] - spec["allow"])
            asked += 1 if reading.questions else 0
        ok_trials = trials - errors
        expected_total = len(spec["expect"]) * max(1, ok_trials)
        recall = (expected_total - missed_total) / expected_total if expected_total else 0.0
        rows.append({
            "photo": stem, "note": spec["note"],
            "expected": sorted(c.value for c in spec["expect"]),
            "recall": round(recall, 3),
            "spurious": spurious_total,
            "asked_a_question": asked,
            "errors": errors,
            "trials": trials,
        })
        print(f"  {stem:24s} recall {recall:5.1%}  spurious {spurious_total}  asked {asked}/{trials}")

    total_recall = sum(r["recall"] for r in rows) / len(rows) if rows else 0.0
    return {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "trials_per_photo": trials,
        "photos": len(rows),
        "mean_component_recall": round(total_recall, 3),
        "total_spurious": sum(r["spurious"] for r in rows),
        "rows": rows,
    }


def to_markdown(result: dict) -> str:
    lines = [
        "# Evaluation results",
        "",
        f"Generated {result['generated']} by `python -m evals.vision_eval`.",
        "",
        "## Plate reading",
        "",
        "Each photograph in `data/plates` is a real photograph under an open licence, credited in",
        "`data/plates/ATTRIBUTION.md`. What a person sees in each was written down before the model",
        "ran. Recall is the share of those components the agent found. Spurious counts components it",
        "reported that a person would not credit, not counting the extras noted per photograph.",
        "",
        f"**Mean component recall: {result['mean_component_recall']:.1%} across {result['photos']} "
        f"photographs, {result['trials_per_photo']} trial(s) each. "
        f"Spurious components: {result['total_spurious']}.**",
        "",
        "| Photograph | Expected components | Recall | Spurious | Asked a question | What it is |",
        "|---|---|---|---|---|---|",
    ]
    for r in result["rows"]:
        lines.append(
            f"| `{r['photo']}` | {', '.join(r['expected'])} | {r['recall']:.0%} | {r['spurious']} | "
            f"{r['asked_a_question']}/{r['trials']} | {r['note']} |"
        )
    lines += [
        "",
        "Asking a question is not a failure. Below a confidence threshold the agent leaves the item",
        "out of the record and asks the provider instead, because guessing a component into",
        "compliance would create a false claim.",
        "",
        "## Deterministic logic",
        "",
        "The meal pattern, ratio and claim maths are exact and covered by unit tests rather than an",
        "eval. Run `pytest -q`.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=1)
    ap.add_argument("--out", default="docs/EVAL.md")
    args = ap.parse_args()

    started = time.time()
    print(f"Reading {len(EXPECTED)} photographs, {args.trials} trial(s) each")
    result = run(args.trials)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(to_markdown(result), encoding="utf-8")
    Path("evals/last_run.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"\nmean recall {result['mean_component_recall']:.1%}, "
          f"{result['total_spurious']} spurious, {time.time() - started:.0f}s")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
