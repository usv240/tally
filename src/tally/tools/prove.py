"""The one tool added for the Give your Agent a Tool challenge: prove_answer.

Before this, when a provider asked Tally what the rules say, the model answered from memory, and
memory is where last year's rule lives. Now the draft answer goes to Amazon Bedrock Automated
Reasoning checks, which hold the regulation as formal logic, and comes back proved, contradicted,
or undecided with the fact that would decide it. Every check is kept as a Proof the sponsor can read.

Wiring: the Day agent drafts, calls this, and acts on the verdict; see agents/graph.py DAY. The loop
is the agent's, in the open. This tool only caps it.
"""

from __future__ import annotations

import uuid

from strands import tool

from tally import prove, runtime
from tally.models import Proof

MAX_ATTEMPTS = 3
"""Three proofs per question. After that the honest answer is "I could not verify this"."""


def rt():
    return runtime.get()


def _record(question: str, answer: str, facts: str, checked: prove.Checked, attempt: int,
            meal_id: str | None) -> Proof:
    r = rt()
    p = Proof(
        id=f"proof-{uuid.uuid4().hex[:8]}", provider_id=r.store.get_provider().id, at=r.now(),
        question=question, answer=answer, facts=facts, verdict=checked.verdict,  # type: ignore[arg-type]
        rules=checked.rules, premises=checked.premises, claims=checked.claims,
        untranslated=checked.untranslated, missing_facts=checked.missing_facts,
        policy_version=checked.policy_version, guardrail_version=checked.guardrail_version,
        latency_ms=checked.latency_ms, text_units=checked.text_units, attempt=attempt, meal_id=meal_id,
    )
    r.store.put_proof(p)
    return p


def _next_step(p: Proof) -> str:
    """What the agent should do now, in words it can follow. The verdict decides, not the model."""
    if p.verdict == "VALID":
        return "Proved. Say the answer. Mention the rule in a few words if it helps her."
    if p.verdict in ("INVALID", "IMPOSSIBLE"):
        # IMPOSSIBLE arrives when the situation she described already breaks a rule (flavored milk
        # for a 4 year old): the premises cannot all hold under the rulebook. For her that is the
        # same news as INVALID, with the same rule to quote.
        rule = p.rules[0] if p.rules else "the rule quoted"
        if p.attempt >= MAX_ATTEMPTS:
            return (f"Contradicts the rules and no attempts are left. Tell her you could not verify "
                    f"this and quote the rule: {rule}")
        return (f"Contradicts the rules. Rewrite the answer so it agrees with this rule, then call "
                f"prove_answer again with the rewritten answer: {rule}")
    if p.verdict in ("SATISFIABLE", "AMBIGUOUS"):
        fact = p.missing_facts[0] if p.missing_facts else "the missing fact"
        if p.attempt >= MAX_ATTEMPTS:
            return "Still undecided and no attempts are left. Tell her what it depends on."
        return (f"Cannot be decided yet. Ask her one short question that settles this: {fact}. "
                f"Then call prove_answer again with her answer in `facts`.")
    if p.verdict == "SKIPPED":
        return "Proving is switched off. Answer as you would have, and say it is unchecked."
    return ("Outside the rulebook, so it cannot be proved. Say plainly that this is not in the meal "
            "pattern rules, and answer only if you are sure, labelled as unverified.")


@tool
def prove_answer(question: str, answer: str, facts: str = "", meal_id: str = "") -> dict:
    """Check a draft answer about the food program against the regulation, mathematically.

    Call this before telling her what the rules say about a meal, a food, milk, juice, sugar limits,
    whole grains, snacks, or infants. It does not guess: the answer is proved or contradicted against
    7 CFR 226.20, or it comes back with the one fact that would decide it.

    Args:
        question: her question, word for word.
        answer: your draft answer, as a plain statement with the numbers in it.
        facts: anything she has told you that bears on it, such as "the label says 9 g added sugars"
            or "the children are 3 to 5". Add to this when she answers your question.
        meal_id: the meal this is about, if there is one, so the receipt attaches to the record.

    Returns the verdict, the rules it rests on, and what to do next.
    """
    r = rt()
    previous = r.store.proofs_for_question(question)
    attempt = len(previous) + 1
    if attempt > MAX_ATTEMPTS:
        r.emit("proof_limit", question=question, attempts=len(previous))
        return {"verdict": "UNVERIFIED", "attempt": attempt,
                "next_step": "No attempts left for this question. Tell her you could not verify it."}

    r.emit("answer_drafted", question=question, answer=answer, facts=facts, attempt=attempt)
    if not prove.enabled():
        checked = prove.Checked(verdict="SKIPPED")
    else:
        try:
            checked = prove.prove(question, answer, facts)
        except Exception as exc:  # the service having a bad minute must not take the agent down
            r.emit("proof_error", question=question, error=str(exc)[:200])
            checked = prove.Checked(verdict="SKIPPED")
    p = _record(question, answer, facts, checked, attempt, meal_id or None)
    r.emit("answer_proved", proof_id=p.id, verdict=p.verdict, attempt=attempt, rules=p.rules[:2],
           missing_facts=p.missing_facts[:2], latency_ms=p.latency_ms, text_units=p.text_units)
    return {
        "proof_id": p.id,
        "verdict": p.verdict,
        "attempt": attempt,
        "attempts_left": MAX_ATTEMPTS - attempt,
        "rules": p.rules,
        "premises": p.premises,
        "claims": p.claims,
        "missing_facts": p.missing_facts,
        "untranslated": p.untranslated,
        "latency_ms": p.latency_ms,
        "next_step": _next_step(p),
    }
