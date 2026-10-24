"""Deploy prove_answer as a Lambda Function URL, idempotently.

    python -m deploy.prove_lambda         build the bundle, sam deploy, probe the URL, record it

The bundle is only what the proof needs: tally/prove.py, the exported policy definition so rule ids
become sentences, and the handler. boto3 comes with the runtime. SAM runs through uvx so nothing
is installed into the project.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAMBDA = ROOT / "lambda"
BUILD = LAMBDA / "build"
DEPLOYED = ROOT / "reasoning" / "deployed.json"
STACK = "tally-prove-answer"
REGION = "us-east-1"


def bundle() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "tally").mkdir(parents=True)
    (BUILD / "tally" / "__init__.py").write_text("")
    shutil.copy(ROOT / "src" / "tally" / "prove.py", BUILD / "tally" / "prove.py")
    shutil.copy(LAMBDA / "handler.py", BUILD / "handler.py")
    # prove.py looks for the definition two levels up from itself: build/reasoning/.
    (BUILD / "reasoning").mkdir()
    shutil.copy(ROOT / "reasoning" / "policy_definition.json", BUILD / "reasoning" / "policy_definition.json")
    print(f"  bundled {sum(1 for _ in BUILD.rglob('*') if _.is_file())} files")


def deploy(state: dict) -> str:
    cmd = ["uvx", "--from", "aws-sam-cli", "sam", "deploy",
           "--template-file", str(LAMBDA / "template.yaml"), "--stack-name", STACK, "--region", REGION,
           "--resolve-s3", "--capabilities", "CAPABILITY_IAM", "--no-confirm-changeset",
           "--no-fail-on-empty-changeset",
           "--parameter-overrides",
           f"GuardrailId={state['guardrail_id']}", f"GuardrailVersion={state['guardrail_version']}",
           f"PolicyArn={state['policy_arn']}"]
    subprocess.run(cmd, check=True, cwd=LAMBDA)
    out = subprocess.run(["aws", "cloudformation", "describe-stacks", "--stack-name", STACK, "--region", REGION,
                          "--query", "Stacks[0].Outputs[?OutputKey=='ProveUrl'].OutputValue", "--output", "text"],
                         check=True, capture_output=True, text=True).stdout.strip()
    return out


def probe(url: str) -> None:
    body = json.dumps({"question": "Can I serve this yogurt as the meat alternate at snack?",
                       "facts": "The meal is a snack. The yogurt has 17 grams of added sugars per 6 ounces.",
                       "answer": "Yes, 17 grams is under the 23 gram limit."}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read())
    print(f"  probe: {d['verdict']} in {d['latency_ms']} ms; rule: {(d['rules'] or [''])[0][:80]}")


def main() -> int:
    state = json.loads(DEPLOYED.read_text())
    print("== bundle")
    bundle()
    print("== deploy")
    url = deploy(state)
    print(f"  url: {url}")
    state["prove_lambda_url"] = url
    DEPLOYED.write_text(json.dumps(state, indent=2) + "\n")
    print("== probe")
    probe(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
