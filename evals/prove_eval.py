"""Measure prove_answer on questions USDA answered, not on questions we wrote the answers to.

The cases in evals/cases/prove_cases.json each carry a provider's question, the answer USDA gives
(from 7 CFR 226.20 or memo CACFP 06-2025, cited per case), and a wrong answer of the opposite
polarity. Four off-topic questions the regulation does not decide are the second control.

Two measurements:

  --solver   The tool alone. Every USDA answer is proved; every wrong answer is proved. The numbers
             are: wrong answers caught (INVALID), correct answers wrongly blocked (the false
             refusal rate, the one that matters), and off-topic answers that came back "proved".
             Deterministic enough to pin: the solver is the same every run, the translation is
             not quite, so the test pins a floor rather than an exact figure.

  --agents   The agent, three ways, on every question: Tally without the tool (September's build),
             a two-agent debate with a judge (evals/debate_baseline.py), and Tally with the tool.
             Each final answer is then proved against the regulation with the case's facts. A wrong
             answer served is a final answer the solver contradicts. An agent that asks a question
             instead of answering is counted as "asked", which is the designed behaviour of the
             tool path and a miss for the other two.

    python -m evals.prove_eval --solver                      the tool alone, ~5 minutes
    python -m evals.prove_eval --agents                      the three agents, ~25 minutes
    python -m evals.prove_eval --solver --agents --out docs/EVAL.md
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

START = "<!-- prove:start -->"
END = "<!-- prove:end -->"
CASES = Path("evals/cases/prove_cases.json")
RESULTS = Path("evals/prove_results.json")


def load_cases() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------------------------
# The tool alone
# --------------------------------------------------------------------------------------------
def run_solver(cases: dict) -> dict:
    from tally import prove

    rows = []
    for c in cases["cases"]:
        row = {"id": c["id"], "topic": c["topic"], "source": c["source"]}
        for side in ("correct", "wrong"):
            t0 = time.time()
            ch = prove.prove(c["question"], c[side], c["facts"])
            row[side] = {"verdict": ch.verdict, "rules": ch.rules[:1], "missing": ch.missing_facts[:2],
                         "latency_ms": int((time.time() - t0) * 1000)}
            print(f"  {c['id']:<32} {side:<8} {ch.verdict:<12} {row[side]['latency_ms']:>6} ms")
        rows.append(row)
    off = []
    for c in cases["off_topic"]:
        ch = prove.prove(c["question"], c["answer"])
        off.append({"id": c["id"], "verdict": ch.verdict})
        print(f"  {c['id']:<32} off-topic {ch.verdict}")

    n = len(rows)
    caught = sum(1 for r in rows if r["wrong"]["verdict"] in ("INVALID", "IMPOSSIBLE"))
    wrong_served = sum(1 for r in rows if r["wrong"]["verdict"] == "VALID")
    blocked = sum(1 for r in rows if r["correct"]["verdict"] in ("INVALID", "IMPOSSIBLE"))
    proved = sum(1 for r in rows if r["correct"]["verdict"] == "VALID")
    undecided = sum(1 for r in rows if r["correct"]["verdict"] in ("SATISFIABLE", "AMBIGUOUS"))
    off_proved = sum(1 for o in off if o["verdict"] == "VALID")
    lat = sorted(r[s]["latency_ms"] for r in rows for s in ("correct", "wrong"))
    return {
        "n": n, "caught": caught, "wrong_served": wrong_served, "blocked": blocked, "proved": proved,
        "undecided": undecided, "off_topic_n": len(off), "off_topic_proved": off_proved,
        "latency_median_ms": lat[len(lat) // 2], "latency_p90_ms": lat[int(len(lat) * 0.9)],
        "rows": rows, "off_topic": off,
    }


# --------------------------------------------------------------------------------------------
# The three agents
# --------------------------------------------------------------------------------------------
def _is_question(text: str) -> bool:
    t = text.strip()
    starts = ("is the", "is it", "does the", "do you", "what", "which", "can you tell")
    return t.endswith("?") or t.lower().startswith(starts)


def run_agents(cases: dict, conditions: tuple[str, ...] = ("no_tool", "debate", "tool")) -> dict:
    from evals.debate_baseline import debate
    from tally import prove, runtime
    from tally.agents.graph import ask, reset_conversations
    from tally.service import setup

    rows = []
    for c in cases["cases"]:
        row = {"id": c["id"]}
        for cond in conditions:
            rt, _ = setup()
            runtime.configure(rt)
            reset_conversations()
            t0 = time.time()
            if cond == "no_tool":
                answer = ask(c["question"], with_prove=False)["answer"]
                checks = 0
            elif cond == "tool":
                out = ask(c["question"], with_prove=True)
                answer, checks = out["answer"], len(out["proof_ids"])
            else:
                # The debate starts from the same draft a tool-less agent would make.
                draft = ask(c["question"], with_prove=False)["answer"]
                answer = debate(c["question"], draft, c["facts"])["answer"]
                checks = 0
            secs = time.time() - t0
            # Judge the final answer the same way for all three: prove it against the regulation
            # with the case's facts. The judge never sees which condition produced it.
            asked = _is_question(answer)
            verdict = "ASKED" if asked else prove.prove(c["question"], answer, c["facts"]).verdict
            row[cond] = {"answer": answer, "verdict": verdict, "checks": checks, "seconds": round(secs, 1)}
            print(f"  {c['id']:<32} {cond:<8} {verdict:<12} {secs:5.1f}s  {answer[:70]}")
        rows.append(row)

    summary = {}
    for cond in conditions:
        vs = [r[cond]["verdict"] for r in rows]
        summary[cond] = {
            "wrong_served": sum(1 for v in vs if v in ("INVALID", "IMPOSSIBLE")),
            "proved": sum(1 for v in vs if v == "VALID"),
            "asked": sum(1 for v in vs if v == "ASKED"),
            "undecided": sum(1 for v in vs if v in ("SATISFIABLE", "AMBIGUOUS", "UNVERIFIED")),
            "median_seconds": sorted(r[cond]["seconds"] for r in rows)[len(rows) // 2],
        }
    return {"n": len(rows), "summary": summary, "rows": rows}


# --------------------------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------------------------
def render(solver: dict | None, agents: dict | None) -> str:
    lines = [START, "## Proved against the regulation", "",
             f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m evals.prove_eval`.", "",
             "The questions are a provider's; the answers are USDA's, from 7 CFR 226.20 and memo "
             "CACFP 06-2025, cited per case in `evals/cases/prove_cases.json`. We wrote none of the "
             "answers. The judge for every number below is the same: Amazon Bedrock Automated Reasoning "
             "checks against the regulation held as formal logic.", ""]
    if solver:
        s = solver
        lines += [
            f"**The tool alone, on {s['n']} questions: {s['caught']} of {s['n']} wrong answers "
            f"contradicted, {s['blocked']} of {s['n']} correct answers wrongly blocked, "
            f"{s['off_topic_proved']} of {s['off_topic_n']} off-topic answers wrongly proved.**", "",
            f"Of the {s['n']} correct answers, {s['proved']} were proved outright and "
            f"{s['undecided']} came back undecided, which is the tool asking for a fact rather than "
            f"refusing. {s['wrong_served']} wrong answers were proved. Median check "
            f"{s['latency_median_ms'] / 1000:.1f} s, 90th percentile {s['latency_p90_ms'] / 1000:.1f} s.", "",
            "| Case | Source | USDA's answer | The wrong answer |", "|---|---|---|---|"]
        for r in s["rows"]:
            lines.append(f"| {r['id']} | {r['source']} | {r['correct']['verdict']} | {r['wrong']['verdict']} |")
        lines += ["", "| Off-topic question | Verdict |", "|---|---|"]
        for o in s["off_topic"]:
            lines.append(f"| {o['id']} | {o['verdict']} |")
        lines.append("")
    if agents:
        a = agents
        lines += ["### The same agent three ways", "",
                  "Every final answer was proved against the regulation with the case's facts. "
                  "\"Wrong served\" is a final answer the rules contradict. \"Asked\" is an agent that "
                  "put a question to the provider instead of answering.", "",
                  "| Condition | Wrong answers served | Proved correct | Asked a question | Undecided | Median time |",
                  "|---|---|---|---|---|---|"]
        names = {"no_tool": "Tally, September build (no tool)", "debate": "Two agents debate, a judge decides",
                 "tool": "Tally with prove_answer"}
        for cond, v in a["summary"].items():
            lines.append(f"| {names.get(cond, cond)} | {v['wrong_served']} of {a['n']} | {v['proved']} | "
                         f"{v['asked']} | {v['undecided']} | {v['median_seconds']:.0f} s |")
        lines.append("")
    lines += ["Rerun with `python -m evals.prove_eval --solver --agents --out docs/EVAL.md`. Both halves "
              "call AWS; the solver half costs about a dollar, the agents half about three.", END]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--solver", action="store_true")
    ap.add_argument("--agents", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cases = load_cases()
    prev = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    solver = run_solver(cases) if a.solver else prev.get("solver")
    agents = run_agents(cases) if a.agents else prev.get("agents")
    RESULTS.write_text(json.dumps({"solver": solver, "agents": agents}, indent=1) + "\n")
    body = render(solver, agents)
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
