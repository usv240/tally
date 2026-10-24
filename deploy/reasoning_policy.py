"""Build the Automated Reasoning policy that `prove_answer` checks against, idempotently.

The rulebook is `reasoning/cacfp_meal_pattern.txt`, a plain-text restatement of 7 CFR 226.20 (see
reasoning/SOURCES.md). Amazon Bedrock turns it into formal logic once, here; at run time the guardrail
proves or contradicts an answer against that logic. Stages, each skipped when already done:

    python -m deploy.reasoning_policy build       create the policy, ingest the document, wait
    python -m deploy.reasoning_policy report      print the quality report and the rules it inferred
    python -m deploy.reasoning_policy version     freeze a policy version
    python -m deploy.reasoning_policy guardrail   create the guardrail that carries that version
    python -m deploy.reasoning_policy probe       prove three known answers against the live guardrail
    python -m deploy.reasoning_policy all         every stage in order

IDs land in reasoning/deployed.json, which api.py and the deploy read. Building takes minutes;
proving takes seconds and costs 0.17 dollars per thousand text units.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from pathlib import Path

import boto3

REGION = "us-east-1"
POLICY_NAME = "tally-cacfp-meal-pattern"
GUARDRAIL_NAME = "tally-prove-answer"
ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "reasoning" / "cacfp_meal_pattern.txt"
DEPLOYED = ROOT / "reasoning" / "deployed.json"
DEFINITION = ROOT / "reasoning" / "policy_definition.json"
QUALITY = ROOT / "reasoning" / "quality_report.json"

DESCRIPTION = (
    "CACFP meal pattern rules for child care, restated from 7 CFR 226.20 (as of 2026-10-22) and USDA "
    "memo CACFP 06-2025. Used by Tally's prove_answer tool to check answers to providers' food-program "
    "questions."
)
DOCUMENT_DESCRIPTION = (
    "A rulebook for the Child and Adult Care Food Program (CACFP) meal pattern for children aged 1 "
    "through 18 and for infants. Each numbered rule is one requirement. Variables should capture: the "
    "meal type (breakfast, lunch, supper, snack); which of the five components a meal contains (fluid "
    "milk, vegetables, fruits, grains, meats/meat alternates); whether a meal is reimbursable; whether a "
    "food is creditable; a child's age in years; milk type and whether it is flavored; yogurt's added "
    "sugars per 6 ounces in grams; a breakfast cereal's added sugars per dry ounce in grams; whether a "
    "figure is added sugars or total sugars; whether juice was already served that day; whether a whole "
    "grain-rich grain was served that day; whether a food was deep-fat fried on site; how many times a "
    "meat alternate replaced grains at breakfast this week; whether the participant is an infant. The "
    "rules about former sugar limits that expired on September 30, 2025 mean that a claim stating the "
    "old limit (23 grams total sugars for yogurt, 6 grams total sugars for cereal) is false today."
)

bedrock = boto3.client("bedrock", region_name=REGION)
runtime = boto3.client("bedrock-runtime", region_name=REGION)


def load() -> dict:
    return json.loads(DEPLOYED.read_text()) if DEPLOYED.exists() else {}


def save(state: dict) -> None:
    DEPLOYED.write_text(json.dumps(state, indent=2) + "\n")


def find_policy() -> str | None:
    token = None
    while True:
        kw = {"nextToken": token} if token else {}
        page = bedrock.list_automated_reasoning_policies(**kw)
        for p in page.get("automatedReasoningPolicySummaries", []):
            if p["name"] == POLICY_NAME and p.get("version", "DRAFT") == "DRAFT":
                return p["policyArn"]
        token = page.get("nextToken")
        if not token:
            return None


def build(state: dict) -> dict:
    arn = state.get("policy_arn") or find_policy()
    if not arn:
        r = bedrock.create_automated_reasoning_policy(
            name=POLICY_NAME, description=DESCRIPTION, clientRequestToken=uuid.uuid4().hex)
        arn = r["policyArn"]
        print(f"  created policy {arn}")
    else:
        print(f"  policy exists {arn}")
    state["policy_arn"] = arn
    save(state)

    wf = state.get("build_workflow_id")
    if wf:
        status = bedrock.get_automated_reasoning_policy_build_workflow(
            policyArn=arn, buildWorkflowId=wf)["status"]
        if status == "COMPLETED" and "--rebuild" not in sys.argv:
            print(f"  build already completed ({wf})")
            return state
        if status in ("FAILED", "CANCELLED") or "--rebuild" in sys.argv:
            wf = None
    if not wf:
        doc = SOURCE.read_bytes()
        r = bedrock.start_automated_reasoning_policy_build_workflow(
            policyArn=arn, buildWorkflowType="INGEST_CONTENT", clientRequestToken=uuid.uuid4().hex,
            sourceContent={"workflowContent": {"documents": [{
                "document": doc, "documentContentType": "txt",
                "documentName": SOURCE.name, "documentDescription": DOCUMENT_DESCRIPTION,
            }]}})
        wf = r["buildWorkflowId"]
        state["build_workflow_id"] = wf
        save(state)
        print(f"  started build {wf} from {SOURCE.name} ({len(doc)} bytes)")

    started = time.time()
    while True:
        status = bedrock.get_automated_reasoning_policy_build_workflow(
            policyArn=arn, buildWorkflowId=wf)["status"]
        print(f"  {int(time.time() - started):4d}s {status}")
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            break
        time.sleep(20)
    if status != "COMPLETED":
        log = bedrock.get_automated_reasoning_policy_build_workflow_result_assets(
            policyArn=arn, buildWorkflowId=wf, assetType="BUILD_LOG")
        print(json.dumps(log.get("buildWorkflowAssets", {}), indent=1, default=str)[:4000])
        sys.exit(f"build {status}")
    return state


def report(state: dict) -> dict:
    arn, wf = state["policy_arn"], state["build_workflow_id"]
    assets = bedrock.get_automated_reasoning_policy_build_workflow_result_assets(
        policyArn=arn, buildWorkflowId=wf, assetType="POLICY_DEFINITION")["buildWorkflowAssets"]
    definition = assets["policyDefinition"]
    DEFINITION.write_text(json.dumps(definition, indent=2, default=str) + "\n")
    quality = bedrock.get_automated_reasoning_policy_build_workflow_result_assets(
        policyArn=arn, buildWorkflowId=wf, assetType="QUALITY_REPORT")["buildWorkflowAssets"]
    QUALITY.write_text(json.dumps(quality, indent=2, default=str) + "\n")
    q = quality.get("qualityReport", {})
    print(f"  types {q.get('typeCount')}  variables {q.get('variableCount')}  rules {q.get('ruleCount')}")
    print(f"  unused variables {len(q.get('unusedVariables', []))}  "
          f"conflicting rule sets {len(q.get('conflictingRules', []))}  "
          f"disjoint rule sets {len(q.get('disjointRuleSets', []))}")
    print("\n  variables:")
    for v in definition.get("variables", []):
        print(f"    {v['name']} : {v['type']}  -- {v['description'][:90]}")
    print("\n  rules:")
    for r in definition.get("rules", []):
        print(f"    {r['id']}  {r.get('alternateExpression') or r['expression']}")
    return state


# Variables the build inferred from the rulebook's "what these rules do not cover" paragraph. They
# turned every off-topic question into SATISFIABLE ("is this question about ratios?") instead of
# NO_TRANSLATIONS, which is the honest answer for a question the rulebook has nothing to say about.
PRUNE_VARIABLES = {"topicCoveredByTheseRules", "questionIsAboutPortionSizeRatioRateOrTiering",
                   "mealTypeIsNotOther",
                   # "Milk must be served as a beverage or on cereal" is about the manner of service,
                   # which no provider question turns on, and the translator read "fat-free milk ...
                   # as long as it is unflavored" as a manner of service, contradicting a correct
                   # answer. The rule is in the regulation; it is not a creditability decision.
                   "milkService"}
PRUNE_TYPES = {"MilkService"}

# The build's wording of a variable decides how the translator fills it. "Replaced the grains this
# week" read as including the breakfast being asked about, so "already three times, is a fourth
# okay" came back as three, within the limit. Counted before this occasion, the rules below hold.
VARIABLE_NOTES = {
    "meatReplacedGrainsAtBreakfastThisWeek":
        "The number of times a meat or meat alternate has already replaced the grains component at "
        "breakfast earlier this week, before the breakfast being asked about. If it has happened "
        "three times already, the next one would be the fourth.",
}


def prune(state: dict) -> dict:
    d = json.loads(DEFINITION.read_text())
    before = (len(d["variables"]), len(d["rules"]))
    d["variables"] = [v for v in d["variables"] if v["name"] not in PRUNE_VARIABLES]
    d["types"] = [t for t in d.get("types", []) if t["name"] not in PRUNE_TYPES]
    d["rules"] = [r for r in d["rules"]
                  if not any(name in r["expression"] for name in PRUNE_VARIABLES)]
    for v in d["variables"]:
        if v["name"] in VARIABLE_NOTES:
            v["description"] = VARIABLE_NOTES[v["name"]]
    DEFINITION.write_text(json.dumps(d, indent=2, default=str) + "\n")
    print(f"  variables {before[0]} -> {len(d['variables'])}, rules {before[1]} -> {len(d['rules'])}")
    return state


# Rules the build left one-directional. The rulebook says yogurt is creditable "only if" its added
# sugars are 12 g or less, which the solver reads as a necessary condition: a 17 g yogurt is
# contradicted, but a 9 g yogurt is merely "satisfiable" because nothing says what makes it
# creditable. These give the other direction, so a correct answer can be proved, not just not
# disproved. Each restates a sentence already in the regulation.
PATCH_RULES = [
    # Deliberately without the "not a frozen or drinkable product" clause: with it, every correct
    # yogurt answer came back SATISFIABLE because nobody had said the cup was not frozen yogurt.
    # Rule R7WGHG9DT3DF still says those products are not creditable, so a frozen yogurt under 12 g
    # is a contradiction (IMPOSSIBLE), which the tool treats as INVALID. A plain cup is proved.
    ("TALLYY9SUFFI", "(=> (<= yogurtAddedSugarsPer6Ounces 12) isYogurtCreditable)",
     "Yogurt with no more than 12 grams of added sugars per 6 ounces is creditable as a meat alternate."),
    ("TALLYG5SUFFI", "(=> (and (<= cerealAddedSugarsPerDryOunce 6) grainMadeWithEnrichedOrWholeGrain) "
                     "isBreakfastCerealCreditable)",
     "A breakfast cereal made with enriched or whole grain meal or flour, with no more than 6 grams of "
     "added sugars per dry ounce, is creditable as a grain."),
    ("TALLYS1SUFFI", "(=> (and (= mealType MealType_SNACK) (>= snackComponentCount 2) "
                     "(not snackOnlyItemsAreMilkAndJuice)) isMealReimbursable)",
     "A snack with two or more of the five components, that is not only milk and juice, is reimbursable."),
    ("TALLYS2INVAL", "(=> (and (= mealType MealType_SNACK) snackOnlyItemsAreMilkAndJuice) (not isMealReimbursable))",
     "A snack whose only two items are fluid milk and juice is not reimbursable."),
    # Rules Y5 and G7 of the rulebook, which the build read as descriptions rather than as rules: the
    # limits are measured in added sugars. Without these, "the limit is 23 grams of total sugars"
    # stated on its own, with no food in hand, could not be contradicted.
    ("TALLYY5MEASU", "(= yogurtSugarLimitMeasure SugarFigureType_ADDED)",
     "The yogurt sugar limit is measured in added sugars, not total sugars; the former total sugars "
     "limit no longer applies."),
    ("TALLYG7MEASU", "(= cerealSugarLimitMeasure SugarFigureType_ADDED)",
     "The breakfast cereal sugar limit is measured in added sugars, not total sugars; the former total "
     "sugars limit no longer applies."),
    # Rules B2 and B3, rebuilt on the count of earlier replacements this week (see VARIABLE_NOTES).
    # The build's versions were consistent with each other and wrong about the fourth time.
    ("V4HO1LHK7WFI", "(=> isMeatReplacingGrainsAtBreakfastAllowed (<= meatReplacedGrainsAtBreakfastThisWeek 2))",
     "A meat or meat alternate may replace the grains at breakfast only if it has done so at most "
     "twice earlier this week, so that this is at most the third time."),
    ("ECNI3CCSZQLS", "(=> (>= meatReplacedGrainsAtBreakfastThisWeek 3) (not isMeatReplacingGrainsAtBreakfastAllowed))",
     "If a meat or meat alternate has already replaced the grains at breakfast three times this week, "
     "it may not do so again this week."),
    ("JIIKTAC3TJ4E", "(=> (and (= mealType MealType_BREAKFAST) (>= meatReplacedGrainsAtBreakfastThisWeek 3)) "
                     "(not isMeatReplacingGrainsAtBreakfastAllowed))",
     "At breakfast, after three replacements earlier in the week, a meat or meat alternate does not "
     "meet the grains requirement."),
    ("TALLYB2SUFFI", "(=> (<= meatReplacedGrainsAtBreakfastThisWeek 2) isMeatReplacingGrainsAtBreakfastAllowed)",
     "A meat or meat alternate may replace the entire grains component at breakfast when it has done "
     "so at most twice earlier this week."),
]


def patch(state: dict) -> dict:
    d = json.loads(DEFINITION.read_text())
    by_id = {r["id"]: r for r in d["rules"]}
    added = changed = 0
    for rid, expr, words in PATCH_RULES:
        if rid in by_id:
            if by_id[rid]["expression"] != expr:
                by_id[rid].update(expression=expr, alternateExpression=words)
                changed += 1
        else:
            d["rules"].append({"id": rid, "expression": expr, "alternateExpression": words})
            added += 1
    DEFINITION.write_text(json.dumps(d, indent=2, default=str) + "\n")
    print(f"  added {added}, changed {changed}, now {len(d['rules'])} rules")
    return state


def version(state: dict) -> dict:
    if state.get("policy_version_arn") and "--reversion" not in sys.argv:
        print(f"  version exists {state['policy_version_arn']}")
        return state
    arn = state["policy_arn"]
    # The build workflow leaves its definition in the result assets; the policy draft does not pick
    # it up on its own. A version frozen before adopting it carries zero rules, and a guardrail with
    # zero rules answers VALID to everything with the claim "true". That was the first probe run.
    built = json.loads(DEFINITION.read_text()) if DEFINITION.exists() else None
    draft = bedrock.export_automated_reasoning_policy_version(policyArn=arn)["policyDefinition"]
    same = built and {r["id"]: r["expression"] for r in draft.get("rules", [])} == \
        {r["id"]: r["expression"] for r in built.get("rules", [])}
    if built and not same:
        bedrock.update_automated_reasoning_policy(
            policyArn=arn, name=POLICY_NAME, description=DESCRIPTION,
            policyDefinition={k: built[k] for k in ("version", "types", "rules", "variables") if k in built})
        print(f"  adopted the built definition: {len(built['rules'])} rules, "
              f"{len(built['variables'])} variables (draft had {len(draft.get('rules', []))})")
    policy = bedrock.get_automated_reasoning_policy(policyArn=arn)
    r = bedrock.create_automated_reasoning_policy_version(
        policyArn=arn, clientRequestToken=uuid.uuid4().hex,
        lastUpdatedDefinitionHash=policy["definitionHash"])
    state["policy_version"] = r["version"]
    state["policy_version_arn"] = f"{arn}:{r['version']}"
    state["definition_hash"] = r["definitionHash"]
    save(state)
    print(f"  created version {state['policy_version_arn']}")
    return state


GUARDRAIL_DESCRIPTION = ("Carries the CACFP meal pattern Automated Reasoning policy for Tally's "
                         "prove_answer tool. Detect only; the agent acts on the findings.")


def guardrail(state: dict) -> dict:
    policy_version_arn = state["policy_version_arn"]
    gid = state.get("guardrail_id")
    if gid:
        bedrock.update_guardrail(
            guardrailIdentifier=gid, name=GUARDRAIL_NAME, description=GUARDRAIL_DESCRIPTION,
            automatedReasoningPolicyConfig={"policies": [policy_version_arn],
                                            "confidenceThreshold": state.get("confidence", 1.0)},
            crossRegionConfig={"guardrailProfileIdentifier": "us.guardrail.v1:0"},
            blockedInputMessaging="Tally could not check that.",
            blockedOutputsMessaging="Tally could not check that.")
        print(f"  updated guardrail {gid}")
    else:
        r = bedrock.create_guardrail(
            name=GUARDRAIL_NAME, description=GUARDRAIL_DESCRIPTION, clientRequestToken=uuid.uuid4().hex,
            automatedReasoningPolicyConfig={"policies": [policy_version_arn],
                                            "confidenceThreshold": state.get("confidence", 1.0)},
            crossRegionConfig={"guardrailProfileIdentifier": "us.guardrail.v1:0"},
            blockedInputMessaging="Tally could not check that.",
            blockedOutputsMessaging="Tally could not check that.")
        gid = r["guardrailId"]
        state["guardrail_id"] = gid
        state["guardrail_arn"] = r["guardrailArn"]
        print(f"  created guardrail {gid}")
    for _ in range(30):
        g = bedrock.get_guardrail(guardrailIdentifier=gid)
        if g["status"] == "READY":
            break
        time.sleep(5)
    v = bedrock.create_guardrail_version(
        guardrailIdentifier=gid, clientRequestToken=uuid.uuid4().hex,
        description=f"policy version {state['policy_version']}")
    state["guardrail_version"] = v["version"]
    save(state)
    print(f"  guardrail version {v['version']}")
    return state


# (question, facts the agent would pass, draft answer, expected verdict). The facts block is how the
# tool sends what she has told it; stating them as plain variable facts is what keeps the two
# translators from reading "snack" as "lunch".
PROBES = [
    ("Can I serve the strawberry yogurt cups as the meat alternate at snack? The label says 17 grams.",
     "The meal is a snack. The children are 3 to 5 years old. "
     "The yogurt has 17 grams of added sugars per 6 ounces.",
     "Yes. Yogurt credits as a meat alternate and 17 grams is under the 23 gram limit.",
     "INVALID"),
    ("Can I serve the yogurt as the meat alternate at snack?",
     "The meal is a snack. The children are 3 to 5 years old. "
     "The yogurt has 9 grams of added sugars per 6 ounces.",
     "Yes. Yogurt is creditable as a meat alternate because 9 grams of added sugars per 6 ounces "
     "is within the 12 gram limit.",
     "VALID"),
    ("Can I serve strawberry yogurt as the meat alternate at snack?",
     "The meal is a snack. The children are 3 to 5 years old.",
     "Yes, the yogurt is creditable as a meat alternate.",
     "SATISFIABLE"),
    ("Is milk and apple juice an okay snack for the 3 to 5 year olds?",
     "The meal is a snack. The children are 3 to 5 years old. "
     "The snack contains fluid milk and fruit juice and nothing else.",
     "Yes, the snack is reimbursable because milk and juice are two components.",
     "INVALID"),
    ("What is the staff to child ratio for infants in Texas?",
     "",
     "One adult for every four infants.",
     "UNVERIFIED"),
    ("Can the 4 year olds have chocolate milk at lunch?",
     "The meal is lunch. The child is 4 years old. The milk is flavored.",
     "Yes, flavored milk is fine at lunch.",
     "IMPOSSIBLE"),  # the situation itself breaks rule D99; the tool reads this as INVALID
    ("Do I need a whole grain today? Breakfast was white toast and lunch is rice.",
     "No whole grain-rich grain has been served today.",
     "Yes. At least one grain serving each day must be whole grain-rich, so today's whole grain-rich "
     "requirement is not met yet.",
     "VALID"),
]

ORDER = ["translationAmbiguous", "tooComplex", "impossible", "invalid", "satisfiable", "valid",
         "noTranslations"]


def probe(state: dict) -> dict:
    for question, facts, answer, expected in PROBES:
        t0 = time.time()
        content = [{"text": {"text": question, "qualifiers": ["query"]}}]
        if facts:
            content.append({"text": {"text": facts, "qualifiers": ["query"]}})
        content.append({"text": {"text": answer, "qualifiers": ["guard_content"]}})
        r = runtime.apply_guardrail(
            guardrailIdentifier=state["guardrail_id"], guardrailVersion=state["guardrail_version"],
            source="OUTPUT", outputScope="FULL", content=content)
        findings = []
        for a in r.get("assessments", []):
            findings += a.get("automatedReasoningPolicy", {}).get("findings", [])
        units = r.get("usage", {}).get("automatedReasoningPolicyUnits")
        # Same reading the tool applies, so the probe grades what the agent will see.
        from tally.prove import interpret

        worst = interpret(r).verdict
        mark = "ok " if worst == expected else "XX "
        print(f"\n{mark}{worst:<22} expected {expected:<16} {time.time() - t0:4.1f}s  units {units}")
        print(f"   Q: {question}\n   A: {answer}")
        for f in findings:
            k = next(iter(f))
            d = f[k]
            tr = d.get("translation", {})
            for p in tr.get("premises", []):
                print(f"     premise  {p.get('naturalLanguage')}")
            for c in tr.get("claims", []):
                print(f"     claim    {c.get('naturalLanguage')}")
            for rule in d.get("contradictingRules", []) + d.get("supportingRules", []):
                print(f"     rule     {rule.get('identifier')}")
            if k == "satisfiable":
                for s in d.get("claimsFalseScenario", {}).get("statements", []):
                    print(f"     false-if {s.get('naturalLanguage')}")
            if k == "translationAmbiguous":
                for s in d.get("differenceScenarios", []):
                    for st in s.get("statements", []):
                        print(f"     differs  {st.get('naturalLanguage')}")
    return state


STAGES = {"build": build, "report": report, "prune": prune, "patch": patch, "version": version,
          "guardrail": guardrail, "probe": probe}


def main() -> int:
    argv = sys.argv[1:]
    state = load()
    # --confidence 0.6: below this the translators' disagreement reads as TRANSLATION_AMBIGUOUS.
    # At 1.0 any disagreement does, and the first live probe returned ambiguous for every answer.
    if "--confidence" in argv:
        i = argv.index("--confidence")
        state["confidence"] = float(argv[i + 1])
        save(state)
        argv = argv[:i] + argv[i + 2:]
    args = [a for a in argv if not a.startswith("--")] or ["all"]
    stages = list(STAGES) if args == ["all"] else args
    for name in stages:
        print(f"\n== {name}")
        state = STAGES[name](state)
    save(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
