"""Prove Tally's own rulebook against the regulation.

rules/cacfp_rules.json is what every verdict Tally has ever recorded was decided under, and the
text in web/app.js and web/try.html is what the provider is told to check on a label. Each of those
statements is restated as a claim and put through the same tool the Day agent uses. A rule the
regulation contradicts is a rule Tally has been applying wrongly.

    python -m evals.rulebook_audit                      print the audit
    python -m evals.rulebook_audit --out docs/EVAL.md   write it into the eval page
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

START = "<!-- audit:start -->"
END = "<!-- audit:end -->"
RESULTS = Path("evals/audit_results.json")

QUESTION = "What does the meal pattern say?"
BEFORE_START = "<!-- audit-before:start -->"
BEFORE_END = "<!-- audit-before:end -->"

REF: str | None = None
"""A git ref. When set, the rulebook and the pages are read as they were at that commit, so the
audit that found the stale rule can be rerun after the rule was fixed."""


def _read(path: str) -> str:
    if REF:
        import subprocess

        return subprocess.run(["git", "show", f"{REF}:{path}"], check=True, capture_output=True,
                              text=True, encoding="utf-8").stdout
    return Path(path).read_text(encoding="utf-8")


def statements() -> list[dict]:
    """Every rule-shaped sentence Tally holds, with where it lives."""
    rules = json.loads(_read("rules/cacfp_rules.json"))
    out = []
    for lc in rules.get("label_checks", []):
        out.append({"where": f"rules/cacfp_rules.json label_checks.{lc['id']}", "claim": lc["description"]})
        # A limit stated too loosely is not a contradiction, it is a weaker truth: every yogurt under
        # 12 g is also under 23 g. The error shows when the rule is applied at its own boundary, which
        # is exactly how Tally applies it: a label at the stated limit passes the check.
        m = re.search(r"no more than (\d+) grams of (\w+ )?sugars?", lc["description"])
        if m:
            n, kind = m.group(1), (m.group(2) or "").strip() or "sugar"
            unit = "per dry ounce" if "cereal" in lc["id"] else "per 6 ounces"
            food = "breakfast cereal" if "cereal" in lc["id"] else "yogurt"
            role = "as a grain" if "cereal" in lc["id"] else "as a meat alternate"
            out.append({"where": f"rules/cacfp_rules.json label_checks.{lc['id']} (as applied)",
                        "claim": f"A {food} whose label shows {n} grams of {kind} {unit} passes the label "
                                 f"check and is creditable {role}."})
    for dr in rules.get("daily_rules", []):
        out.append({"where": f"rules/cacfp_rules.json daily_rules.{dr['id']}", "claim": dr["description"]})
    for age, text in rules.get("milk_by_age", {}).items():
        out.append({"where": f"rules/cacfp_rules.json milk_by_age.{age}",
                    "claim": f"For children aged {age}: {text}"})
        # The same boundary test for milk: what the sentence tells a provider she may not serve.
        if "Low fat or fat free" in text and age == "3-5":
            out.append({"where": f"rules/cacfp_rules.json milk_by_age.{age} (as applied)",
                        "claim": "Unflavored whole milk is not creditable as fluid milk for a child aged 3 to 5."})
    meals = rules.get("meals", {})
    for meal, spec in meals.items():
        if "required" in spec:
            comps = ", ".join(c.replace("_", " ") for c in spec["required"])
            out.append({"where": f"rules/cacfp_rules.json meals.{meal}.required",
                        "claim": f"A reimbursable {meal} for a child must contain: {comps}."})
        for sub in spec.get("substitutions", []):
            if sub.get("note"):
                out.append({"where": f"rules/cacfp_rules.json meals.{meal}.substitutions", "claim": sub["note"]})
        if "choose_any" in spec:
            out.append({"where": f"rules/cacfp_rules.json meals.{meal}",
                        "claim": f"A reimbursable {meal} for a child must contain any {spec['choose_any']} "
                                 "of the five components."})
        for fp in spec.get("forbidden_pairs", []):
            if fp.get("note"):
                out.append({"where": f"rules/cacfp_rules.json meals.{meal}.forbidden_pairs", "claim": fp["note"]})
    # The sentences the provider actually reads on the screen.
    for f in ("web/app.js", "web/try.html"):
        text = _read(f)
        for m in re.finditer(r'"((?:Yoghurt|Cereal) must be under [^"]+?)[,.]', text):
            out.append({"where": f, "claim": m.group(1) + "."})
    return out


def run() -> dict:
    from tally import prove

    rows = []
    for s in statements():
        ch = prove.prove(QUESTION, s["claim"])
        rows.append({**s, "verdict": ch.verdict, "rule": ch.rules[0] if ch.rules else ""})
        print(f"  {ch.verdict:<12} {s['where']}\n               {s['claim'][:110]}")
    stale = [r for r in rows if r["verdict"] in ("INVALID", "IMPOSSIBLE")]
    return {"n": len(rows), "stale": len(stale), "proved": sum(1 for r in rows if r["verdict"] == "VALID"),
            "rows": rows}


def render(a: dict) -> str:
    if REF:
        lines = [BEFORE_START, f"## Tally's own rulebook, proved, as it was at `{REF[:7]}`", "",
                 f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by "
                 f"`python -m evals.rulebook_audit --before {REF[:7]}`.", "",
                 "This is the run that found the stale rule. The rulebook and the pages are read from git "
                 "at that commit, so it can be rerun after the fix.", ""]
    else:
        lines = [START, "## Tally's own rulebook, proved", "",
                 f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m evals.rulebook_audit`.", "",]
    lines += [
             "Every rule-shaped sentence in `rules/cacfp_rules.json`, and every label instruction the "
             "provider reads on screen, put through the same proof the Day agent uses.", "",
             f"**{a['stale']} of {a['n']} statements contradicted the regulation. {a['proved']} were proved; "
             f"the rest could not be decided from the sentence alone.**", "",
             "A limit stated too loosely is not a contradiction but a weaker truth, so each numeric limit "
             "is also tested the way Tally applies it: a label at the stated limit passes. Those rows are "
             "marked \"as applied\".", "",
             "| Verdict | Where | The statement | The rule it rests on or breaks |", "|---|---|---|---|"]
    for r in a["rows"]:
        mark = "**INVALID**" if r["verdict"] in ("INVALID", "IMPOSSIBLE") else r["verdict"]
        lines.append(f"| {mark} | `{r['where']}` | {r['claim']} | {r['rule']} |")
    lines += ["", END]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--before", default=None, help="a git ref: audit the rulebook as it was then")
    a = ap.parse_args()
    global REF
    REF = a.before
    result = run()
    out_json = Path("evals/audit_before_results.json") if REF else RESULTS
    out_json.write_text(json.dumps(result, indent=1) + "\n")
    body = render(result)
    print("\n" + body)
    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        start, end = (BEFORE_START, BEFORE_END) if REF else (START, END)
        if start in text:
            text = re.sub(re.escape(start) + ".*?" + re.escape(end), lambda _: body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
