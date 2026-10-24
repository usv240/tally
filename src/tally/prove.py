"""Prove an answer against the regulation, with Amazon Bedrock Automated Reasoning checks.

The rulebook (reasoning/cacfp_meal_pattern.txt) was compiled into formal logic once, by
deploy/reasoning_policy.py. This module asks the guardrail that carries it whether a draft answer
follows from the rules. The reply is a proof, not an opinion: VALID comes with the rules that prove
it, INVALID with the rules it breaks, and the two undecided verdicts with the fact that would decide
it. The model is never asked to grade itself.

Nothing here touches the store or the trace; prove() is a pure call so the tool and the API can
share it and the tests can run it against a fake client.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEPLOYED = ROOT / "reasoning" / "deployed.json"
DEFINITION = ROOT / "reasoning" / "policy_definition.json"

# Worst first. One check can return several findings; the verdict is the worst of them, which is
# the order the Bedrock documentation gives.
SEVERITY = ["translationAmbiguous", "tooComplex", "impossible", "invalid", "satisfiable", "valid",
            "noTranslations"]
VERDICT_OF = {
    "valid": "VALID",
    "invalid": "INVALID",
    "satisfiable": "SATISFIABLE",
    "translationAmbiguous": "AMBIGUOUS",
    "impossible": "IMPOSSIBLE",
    "tooComplex": "UNVERIFIED",
    "noTranslations": "UNVERIFIED",
}


def enabled() -> bool:
    """TALLY_PROVE=off runs Tally exactly as it was before the tool existed. That is the Before."""
    return os.environ.get("TALLY_PROVE", "on").lower() not in ("0", "off", "false", "no")


def config() -> dict:
    """Guardrail id and version: from the environment in production, from deployed.json locally."""
    gid = os.environ.get("TALLY_GUARDRAIL_ID")
    ver = os.environ.get("TALLY_GUARDRAIL_VERSION")
    if gid and ver:
        return {"guardrail_id": gid, "guardrail_version": ver}
    if DEPLOYED.exists():
        d = json.loads(DEPLOYED.read_text())
        if d.get("guardrail_id") and d.get("guardrail_version"):
            return {"guardrail_id": d["guardrail_id"], "guardrail_version": str(d["guardrail_version"])}
    return {}


_RULES: dict[str, str] | None = None


def rule_text(identifier: str, definition: dict | None = None) -> str:
    """The rulebook's words for a rule id, so a receipt quotes a sentence, not a hash.

    The finding carries only the id. The natural-language form lives in the exported policy
    definition, which the build step saves next to the rulebook.
    """
    global _RULES
    if definition is not None:
        table = {r["id"]: r.get("alternateExpression") or r["expression"] for r in definition.get("rules", [])}
    else:
        if _RULES is None:
            _RULES = {}
            if DEFINITION.exists():
                d = json.loads(DEFINITION.read_text())
                _RULES = {r["id"]: r.get("alternateExpression") or r["expression"]
                          for r in d.get("rules", [])}
        table = _RULES
    return table.get(identifier, identifier)


@dataclass
class Checked:
    """What the solver said about one answer. The tool turns this into a stored Proof."""

    verdict: str
    rules: list[str] = field(default_factory=list)
    premises: list[str] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    untranslated: list[str] = field(default_factory=list)
    missing_facts: list[str] = field(default_factory=list)
    policy_version: str = ""
    guardrail_version: str = ""
    latency_ms: int = 0
    text_units: int = 0
    raw_kinds: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.verdict == "VALID":
            return "Proved. " + (f"Rule: {self.rules[0]}" if self.rules else "")
        if self.verdict == "INVALID":
            return "Contradicts the rules. " + (f"Rule: {self.rules[0]}" if self.rules else "")
        if self.verdict in ("SATISFIABLE", "AMBIGUOUS"):
            return "Cannot be decided yet. It turns on: " + ("; ".join(self.missing_facts) or "a missing fact")
        if self.verdict == "IMPOSSIBLE":
            return "The facts given contradict each other."
        if self.verdict == "SKIPPED":
            return "Not checked."
        return "Outside the rulebook, so it cannot be proved or disproved."


def _nl(items: list[dict]) -> list[str]:
    return [x.get("naturalLanguage") or x.get("logic") or "" for x in items if x]


def interpret(response: dict, definition: dict | None = None) -> Checked:
    """Turn an ApplyGuardrail response into one verdict. Pure, so it is tested without AWS."""
    findings: list[dict] = []
    for a in response.get("assessments", []):
        findings += a.get("automatedReasoningPolicy", {}).get("findings", [])
    units = int((response.get("usage") or {}).get("automatedReasoningPolicyUnits") or 0)
    if not findings or units == 0:
        # The checks did not run. Saying "verified" here would be the one unforgivable bug.
        return Checked(verdict="SKIPPED", text_units=units)

    kinds = [next(iter(f)) for f in findings]
    worst_kind = min(kinds, key=SEVERITY.index)
    out = Checked(verdict=VERDICT_OF[worst_kind], text_units=units, raw_kinds=kinds)

    for f in findings:
        kind = next(iter(f))
        d = f[kind] or {}
        tr = d.get("translation") or {}
        out.premises += _nl(tr.get("premises", []))
        out.claims += _nl(tr.get("claims", []))
        out.untranslated += [u.get("text", "") for u in tr.get("untranslatedPremises", []) + tr.get("untranslatedClaims", [])]
        for rule in d.get("contradictingRules", []) + d.get("supportingRules", []):
            out.rules.append(rule_text(rule.get("identifier", ""), definition))
            if rule.get("policyVersionArn"):
                out.policy_version = rule["policyVersionArn"]
        if kind == "satisfiable":
            out.missing_facts += _nl((d.get("claimsFalseScenario") or {}).get("statements", []))
        if kind == "translationAmbiguous":
            for sc in d.get("differenceScenarios", []):
                out.missing_facts += _nl(sc.get("statements", []))
            for opt in d.get("options", []):
                for t in opt.get("translations", []):
                    out.claims += _nl(t.get("claims", []))
    # Keep order, drop repeats. A rule that proves two claims is one rule.
    for name in ("rules", "premises", "claims", "untranslated", "missing_facts"):
        seen: list[str] = []
        for x in getattr(out, name):
            if x and x not in seen:
                seen.append(x)
        setattr(out, name, seen)
    # A VALID whose only claim is the literal "true" proved nothing: the logic could not read the
    # answer, so it checked a tautology. That is how an off-topic answer about staff ratios came
    # back "proved" in the first live probe. It is UNVERIFIED, and the untranslated text says why.
    if out.verdict == "VALID" and not [c for c in out.claims if c.strip().lower() != "true"]:
        out.verdict = "UNVERIFIED"
        out.rules = []
    return out


def prove(question: str, answer: str, facts: str = "", client=None, cfg: dict | None = None) -> Checked:
    """Ask the guardrail whether `answer` follows from the rules, given `question` and `facts`.

    The question and the facts enter as user-side context (premises); the answer is the claim. The
    answer alone is never sent without the question, because "yes" proves nothing on its own.
    """
    cfg = config() if cfg is None else cfg
    if not cfg:
        return Checked(verdict="SKIPPED")
    if client is None:
        import boto3

        client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    content = [{"text": {"text": question, "qualifiers": ["query"]}}]
    if facts.strip():
        content.append({"text": {"text": facts, "qualifiers": ["query"]}})
    content.append({"text": {"text": answer, "qualifiers": ["guard_content"]}})
    t0 = time.time()
    response = client.apply_guardrail(
        guardrailIdentifier=cfg["guardrail_id"], guardrailVersion=str(cfg["guardrail_version"]),
        source="OUTPUT", outputScope="FULL", content=content)
    checked = interpret(response)
    checked.latency_ms = int((time.time() - t0) * 1000)
    checked.guardrail_version = str(cfg["guardrail_version"])
    return checked
