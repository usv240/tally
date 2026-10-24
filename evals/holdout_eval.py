"""The held-out run, and whether the agent reaches for the tool when it should and only then.

Two numbers the main eval cannot give honestly. The 30 cases in prove_cases.json were in front of
us while the policy was repaired, so a good score on them is partly a score on the repairs. The ten
in holdout_cases.json were written after the last change to the policy, the tool and the prompt,
run once, and reported as they came out. The git log shows the order.

The second number is about the agent, not the solver: on every rule question it should call
prove_answer, and on a roll call, a thank-you or a question about the weather it should not. A tool
that is never called protects nobody; one called on everything slows the day and spends money.

    python -m evals.holdout_eval --solver          the ten held-out cases, both polarities
    python -m evals.holdout_eval --agent           30 rule questions + 10 other inputs: did it call the tool?
    python -m evals.holdout_eval --solver --agent --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

START = "<!-- holdout:start -->"
END = "<!-- holdout:end -->"
HOLDOUT = Path("evals/cases/holdout_cases.json")
CASES = Path("evals/cases/prove_cases.json")
RESULTS = Path("evals/holdout_results.json")


def run_solver() -> dict:
    from tally import prove

    cases = json.loads(HOLDOUT.read_text(encoding="utf-8"))["cases"]
    rows = []
    for c in cases:
        row = {"id": c["id"], "source": c["source"]}
        for side in ("correct", "wrong"):
            ch = prove.prove(c["question"], c[side], c["facts"])
            row[side] = ch.verdict
            print(f"  {c['id']:<30} {side:<8} {ch.verdict}")
        rows.append(row)
    return {
        "n": len(rows),
        "caught": sum(1 for r in rows if r["wrong"] in ("INVALID", "IMPOSSIBLE")),
        "wrong_proved": sum(1 for r in rows if r["wrong"] == "VALID"),
        "blocked": sum(1 for r in rows if r["correct"] == "INVALID"),
        "proved": sum(1 for r in rows if r["correct"] == "VALID"),
        "rows": rows,
    }


def run_agent() -> dict:
    from tally import runtime
    from tally.agents.graph import ask, reset_conversations
    from tally.service import setup

    rule_qs = [(c["id"], c["question"]) for c in json.loads(CASES.read_text(encoding="utf-8"))["cases"]]
    others = [(c["id"], c["text"]) for c in json.loads(HOLDOUT.read_text(encoding="utf-8"))["not_rule_questions"]]
    rows = []
    for kind, items in (("rule", rule_qs), ("other", others)):
        for cid, text in items:
            rt, _ = setup()
            runtime.configure(rt)
            reset_conversations()
            out = ask(text, with_prove=True)
            called = len(out["proof_ids"])
            rows.append({"id": cid, "kind": kind, "called": called, "answer": out["answer"][:160]})
            print(f"  {kind:<6} {cid:<30} prove_answer x{called}  {out['answer'][:70]}")
    rule_rows = [r for r in rows if r["kind"] == "rule"]
    other_rows = [r for r in rows if r["kind"] == "other"]
    return {
        "rule_n": len(rule_rows), "rule_called": sum(1 for r in rule_rows if r["called"]),
        "other_n": len(other_rows), "other_called": sum(1 for r in other_rows if r["called"]),
        "rows": rows,
    }


def render(solver: dict | None, agent: dict | None) -> str:
    lines = [START, "## Held out, and whether the agent reaches for the tool", "",
             f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m evals.holdout_eval`.", ""]
    if solver:
        s = solver
        lines += [
            "The 30 cases above were in front of us while the policy was repaired. These ten were written "
            "after the last change to the policy, the tool and the prompt, run once, and are reported as "
            "they came out; nothing was adjusted afterwards. The git history shows the order.", "",
            f"**Held out, 10 questions: {s['caught']} of {s['n']} wrong answers contradicted, "
            f"{s['blocked']} of {s['n']} correct answers wrongly blocked, {s['wrong_proved']} wrong answers "
            f"proved, {s['proved']} correct answers proved outright.**", "",
            "| Case | Source | USDA's answer | The wrong answer |", "|---|---|---|---|"]
        for r in s["rows"]:
            lines.append(f"| {r['id']} | {r['source']} | {r['correct']} | {r['wrong']} |")
        lines.append("")
    if agent:
        a = agent
        lines += [
            "Whether the Day agent calls the tool is a separate question from whether the tool is right. "
            "Every rule question should reach it; a roll call, a thank-you or a question about the weather "
            "should not.", "",
            f"**The agent called prove_answer on {a['rule_called']} of {a['rule_n']} rule questions and on "
            f"{a['other_called']} of {a['other_n']} inputs that were not rule questions.**", "",
            "| Input | Kind | prove_answer calls | What it said |", "|---|---|---|---|"]
        for r in a["rows"]:
            if r["kind"] == "other" or r["called"] == 0:
                lines.append(f"| {r['id']} | {r['kind']} | {r['called']} | {r['answer'][:90]} |")
        lines.append("")
        lines.append("Rule questions that did reach the tool are not listed; the ones that did not, and every "
                     "non-rule input, are.")
    lines += ["", "Rerun with `python -m evals.holdout_eval --solver --agent --out docs/EVAL.md`.", END]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", action="store_true")
    ap.add_argument("--agent", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    prev = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    solver = run_solver() if a.solver else prev.get("solver")
    agent = run_agent() if a.agent else prev.get("agent")
    RESULTS.write_text(json.dumps({"solver": solver, "agent": agent}, indent=1) + "\n")
    body = render(solver, agent)
    print("\n" + body)
    if a.out:
        p = Path(a.out)
        text = p.read_text(encoding="utf-8")
        if START in text:
            text = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: body, text, flags=re.S)
        else:
            text = text.rstrip() + "\n\n" + body + "\n"
        p.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
