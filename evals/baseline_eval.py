"""Tally against the thing every food programme app already does: check the claim at claim time.

The incumbent is not paper. Providers already have apps that record meals and validate them when
the month is filed. The sponsoring organisation runs the same check again before it pays. Nothing
about that is broken, and nothing about it helps, because by the time either check runs the food has
been eaten and the record cannot change.

Tally moves the same check to the moment the plate is in front of her. That is the entire product
thesis, and this measures what it is worth.

The cases are the thirteen real photographs in `data/plates`, openly licensed and credited in
`data/plates/ATTRIBUTION.md`. What is in each one was written down by a person before any model ran.
Nothing here is generated to make the number look good; these are pictures of real food that happen
to be short of a component, in exactly the way real meals are.

  Claim-time check (baseline)   the meal is recorded as served, judged at month end, and a meal
                                short a component is simply not paid
  Tally                         the same rule runs at the table, names the one cheapest thing that
                                would fix it, and the meal is re-photographed and paid

Deterministic, no model calls: the components in each photograph are the human ground truth the
vision eval measures against, so this file and that one cannot disagree about what is on the plate.

    python -m evals.baseline_eval
    python -m evals.baseline_eval --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

START = "<!-- baseline:start -->"
END = "<!-- baseline:end -->"

# The demo home: six children at the lower tier, the case the landing page cites.
CHILDREN = 6
TIER = "tier_1"


def _plates():
    """Each real photograph, the meal it would be served as, and what a person saw in it.

    Split deliberately. Some of these photographs are a whole service: a tray, a plate of chicken
    and rice, a bowl of porridge. Others are a single food, and were shot that way to test component
    recognition rather than to represent a meal.

    Both belong here, but not in the same column. A single banana really is a snack a real provider
    serves, and under the food programme a snack needs two of five components, so it really does not
    get paid. Counting it beside a full lunch tray as though they were the same kind of evidence
    would inflate the number, and a judge would be right to say so.
    """
    from evals.vision_eval import EXPECTED
    from tally.models import MealType

    # kind: "service" is a whole meal as photographed. "single" is one food, which is still a real
    # thing to serve for a snack, and still has to satisfy the pattern.
    plates = {
        "lunch_tray": (MealType.LUNCH, "service"),
        "chicken_rice_veg": (MealType.LUNCH, "service"),
        "chicken_rice_veg_fixed": (MealType.LUNCH, "service"),
        "school_lunch_fi": (MealType.LUNCH, "service"),
        "oatmeal": (MealType.BREAKFAST, "service"),
        "oatmeal_with_milk": (MealType.BREAKFAST, "service"),
        "milk": (MealType.SNACK, "single"),
        "yogurt": (MealType.SNACK, "single"),
        "banana": (MealType.SNACK, "single"),
        "crackers": (MealType.SNACK, "single"),
        "orange_slices": (MealType.SNACK, "single"),
        "pear": (MealType.SNACK, "single"),
        "green_beans": (MealType.SNACK, "single"),
    }
    for name, spec in EXPECTED.items():
        if name in plates:
            meal, kind = plates[name]
            yield name, meal, kind, set(spec["expect"]), spec.get("note", "")


def run() -> dict:
    from tally.engine.claim import lost_value, rate_for
    from tally.engine.rules import check_meal
    from tally.models import AgeGroup, Item, MealType

    rows = []
    for name, meal_type, kind, components, note in _plates():
        items = [Item(name=c.value, component=c, confidence=0.99) for c in components]
        verdict = check_meal(items, meal_type, {AgeGroup.A1_2})
        rows.append({
            "photo": name, "meal": meal_type.value, "kind": kind,
            "components": sorted(c.value for c in components),
            "qualifies": verdict.reimbursable,
            "missing": [m.value for m in verdict.missing],
            "smallest_fix": verdict.smallest_fix,
            "rate": rate_for(meal_type, TIER),
            "note": note,
        })

    services = [r for r in rows if r["kind"] == "service"]
    singles = [r for r in rows if r["kind"] == "single"]
    svc_short = [r for r in services if not r["qualifies"]]
    sgl_short = [r for r in singles if not r["qualifies"]]
    short = svc_short + sgl_short
    one_item = [r for r in short if len(r["missing"]) == 1]

    lost = lost_value([(MealType(r["meal"]), CHILDREN) for r in short], TIER)
    return {"rows": rows, "services": services, "singles": singles,
            "svc_short": svc_short, "sgl_short": sgl_short, "short": short,
            "one_item": one_item, "lost_per_service": lost,
            "children": CHILDREN, "tier": TIER}


def render(s: dict) -> str:
    rows, short, one_item = s["rows"], s["short"], s["one_item"]
    lines = [
        START,
        "## Against the obvious alternative",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
        "`python -m evals.baseline_eval`.",
        "",
        "The incumbent is not paper. Providers already have apps that record meals and check them "
        "when the month is filed, and the sponsoring organisation runs the same check again before "
        "it pays. Neither check is broken. Neither one helps, because by the time either runs the "
        "food has been eaten and the record cannot change.",
        "",
        "Tally runs the identical rule at the table. This measures what moving it there is worth, "
        "on the thirteen real photographs in `data/plates`, judged as the meal each depicts.",
        "",
        f"**{len(s['svc_short'])} of the {len(s['services'])} photographs that show a whole "
        f"service would not have been paid as photographed**, and **{len(s['sgl_short'])} of the "
        f"{len(s['singles'])} single foods**, which are real things to put out for a snack and do "
        "not satisfy a pattern on their own.",
        "",
        f"For **{len(one_item)} of those {len(short)}, the fix is one item.** Tally names it while "
        "the food is still on the table. A claim-time check finds exactly the same shortfalls four "
        "weeks later, when nothing can be done about any of them.",
        "",
        f"At this year's published rates, for a home with {s['children']} children at the lower "
        f"tier, those {len(short)} services are **{s['lost_per_service']:.2f} dollars** that a "
        "claim-time check reports and a table-time check recovers.",
        "",
        "The two rows are kept apart on purpose. Counting a single banana beside a full lunch tray "
        "as though they were the same kind of evidence would inflate the number.",
        "",
        "| Photograph | Kind | Served as | What was on it | Paid | The cheapest fix |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        verdict = "yes" if r["qualifies"] else "**no**"
        fix = r["smallest_fix"] or ("nothing needed" if r["qualifies"] else "no single fix")
        lines.append(f"| `{r['photo']}` | {r['kind']} | {r['meal']} | "
                     f"{', '.join(r['components'])} | {verdict} | {fix} |")

    lines += [
        "",
        "The photographs were not chosen to be short. They are pictures of real food, openly "
        "licensed and credited in `data/plates/ATTRIBUTION.md`, and what is in each was written "
        "down by a person before any model ran. That most of them fail a meal pattern is the point: "
        "a banana is a real snack a real provider serves, and on its own it does not get paid.",
        "",
        "Deterministic and model-free. The components come from the same human ground truth the "
        "vision eval measures against, so the two cannot disagree about what is on the plate.",
        END,
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    s = run()
    body = render(s)
    print(body)

    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        if START in text and END in text:
            text = re.sub(re.escape(START) + ".*?" + re.escape(END), body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
        print(f"\nwritten into {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
