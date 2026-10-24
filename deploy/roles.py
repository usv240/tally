"""Create the two IAM roles App Runner needs, idempotently.

- An access role, so App Runner may pull the image from ECR.
- An instance role per service, so the running container may call Amazon Bedrock. Scoped to
  InvokeModel on the specific foundation models and inference profiles each app uses, rather than
  a wildcard, because a demo credential that can call anything is a bad example to ship. The
  same role gets the AgentCore Code Interpreter and Memory actions the apps use at run time.
"""

import json
import time
from pathlib import Path

import boto3

iam = boto3.client("iam")
ACCOUNT = boto3.client("sts").get_caller_identity()["Account"]
REGION = "us-east-1"

ACCESS_ROLE = "AppRunnerECRAccessRole"
INSTANCE_ROLE = "AgentsForHumansBedrockRole"

MODELS = [
    "anthropic.claude-sonnet-4-6",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon.nova-2-lite-v1:0",
    "amazon.nova-pro-v1:0",
]


def ensure_role(name: str, principal: str, description: str) -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": principal},
                       "Action": "sts:AssumeRole"}],
    }
    try:
        r = iam.get_role(RoleName=name)
        print(f"  role exists: {name}")
        return r["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        r = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust),
                            Description=description)
        print(f"  created role: {name}")
        return r["Role"]["Arn"]


def put_policy(role: str, name: str, doc: dict) -> None:
    iam.put_role_policy(RoleName=role, PolicyName=name, PolicyDocument=json.dumps(doc))
    print(f"  policy {name} on {role}")


access_arn = ensure_role(ACCESS_ROLE, "build.apprunner.amazonaws.com",
                         "Lets App Runner pull images from ECR")
try:
    iam.attach_role_policy(
        RoleName=ACCESS_ROLE,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess")
    print("  attached ECR access policy")
except Exception as exc:
    print(f"  ECR access policy: {exc}")

instance_arn = ensure_role(INSTANCE_ROLE, "tasks.apprunner.amazonaws.com",
                           "Lets Turnout and Tally call Amazon Bedrock")

resources = []
for m in MODELS:
    resources.append(f"arn:aws:bedrock:{REGION}::foundation-model/{m}")
    resources.append(f"arn:aws:bedrock:*::foundation-model/{m}")
    resources.append(f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/us.{m}")

put_policy(INSTANCE_ROLE, "InvokeBedrockModels", {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "InvokeTheModelsTheseAppsUse",
        "Effect": "Allow",
        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        "Resource": sorted(set(resources)),
    }],
})

# The two AgentCore services the apps use at run time. Code Interpreter runs the risk and claim
# arithmetic; Memory holds each department's response history. Both planes share the
# bedrock-agentcore action prefix in IAM, including ListMemories and GetMemory, which the SDK
# exposes on the separate bedrock-agentcore-control client. The first version of this policy used
# bedrock-agentcore-control as the prefix for those two, which is not an IAM namespace, and every
# Memory write in production quietly fell back to the local store until the trace said why.
put_policy(INSTANCE_ROLE, "UseAgentCore", {
    "Version": "2012-10-17",
    "Statement": [
        {"Sid": "CodeInterpreterSessions", "Effect": "Allow", "Resource": "*",
         "Action": ["bedrock-agentcore:StartCodeInterpreterSession",
                    "bedrock-agentcore:InvokeCodeInterpreter",
                    "bedrock-agentcore:StopCodeInterpreterSession",
                    "bedrock-agentcore:GetCodeInterpreterSession",
                    "bedrock-agentcore:ListCodeInterpreterSessions"]},
        {"Sid": "MemoryReadWrite", "Effect": "Allow", "Resource": "*",
         "Action": ["bedrock-agentcore:CreateEvent", "bedrock-agentcore:ListEvents",
                    "bedrock-agentcore:GetEvent", "bedrock-agentcore:RetrieveMemoryRecords",
                    "bedrock-agentcore:ListMemoryRecords"]},
        {"Sid": "MemoryLookup", "Effect": "Allow", "Resource": "*",
         "Action": ["bedrock-agentcore:ListMemories", "bedrock-agentcore:GetMemory"]},
    ],
})

# The prove_answer tool (October 2026). ApplyGuardrail on the one guardrail that carries the CACFP
# Automated Reasoning policy, read from reasoning/deployed.json so the role and the app agree on
# which one. Nothing here can create, change or delete a policy; that stays with the deploy user.
_deployed = Path(__file__).resolve().parent.parent / "reasoning" / "deployed.json"
if _deployed.exists():
    _d = json.loads(_deployed.read_text())
    guardrail_arn = _d.get("guardrail_arn")
    if guardrail_arn:
        # The guardrail carries a cross-Region profile (us.guardrail.v1:0), which Automated Reasoning
        # checks require, and the call is authorised against the profile as well as the guardrail.
        # The first live deploy had only the guardrail and every proof came back AccessDenied.
        # The profile routes the call to another US Region, where the same guardrail id is
        # authorised under that Region's ARN, so the guardrail is allowed in every Region too.
        resources = [guardrail_arn, guardrail_arn.replace(f":{REGION}:", ":*:"),
                     f"arn:aws:bedrock:{REGION}:{ACCOUNT}:guardrail-profile/us.guardrail.v1:0",
                     f"arn:aws:bedrock:*:{ACCOUNT}:guardrail-profile/us.guardrail.v1:0",
                     "arn:aws:bedrock:*::guardrail-profile/us.guardrail.v1:0"]
        statements = [{"Sid": "ApplyTheProveGuardrail", "Effect": "Allow",
                       "Action": ["bedrock:ApplyGuardrail"], "Resource": resources}]
        if _d.get("policy_arn"):
            # Applying a guardrail that carries an Automated Reasoning policy also invokes that
            # policy, under its own action, on its versioned ARN. The cross-Region permissions page
            # does not mention it; the live service's AccessDenied did.
            statements.append({"Sid": "InvokeTheReasoningPolicy", "Effect": "Allow",
                               "Action": ["bedrock:InvokeAutomatedReasoningPolicy"],
                               "Resource": [_d["policy_arn"], _d["policy_arn"] + ":*"]})
        if _d.get("ledger_bucket"):
            # Write receipts and read them back. No delete and no lock changes: with compliance
            # mode there is nothing to grant, which is the point of the ledger.
            statements.append({"Sid": "FileProofReceipts", "Effect": "Allow",
                               "Action": ["s3:PutObject", "s3:GetObject", "s3:GetObjectRetention"],
                               "Resource": f"arn:aws:s3:::{_d['ledger_bucket']}/proofs/*"})
        put_policy(INSTANCE_ROLE, "ProveAnswers", {"Version": "2012-10-17", "Statement": statements})

print(f"\nACCESS_ROLE_ARN={access_arn}")
print(f"INSTANCE_ROLE_ARN={instance_arn}")
time.sleep(8)  # IAM is eventually consistent; App Runner rejects a role it cannot yet see
print("done")
