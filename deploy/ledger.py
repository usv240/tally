"""Create the proof ledger bucket, idempotently.

    python -m deploy.ledger            create or confirm the bucket and print its name

Object Lock must be enabled at creation; it cannot be switched on later. Versioning comes with it.
Public access is blocked, encryption is the default SSE-S3. The name is recorded in
reasoning/deployed.json so deploy/apprunner.py can hand it to the service as TALLY_LEDGER_BUCKET,
and deploy/roles.py grants the instance role PutObject and GetObject on it, and nothing else: with
compliance mode even the account's root cannot shorten a retention period, so there is no delete
to grant.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import boto3

REGION = "us-east-1"
ACCOUNT = boto3.client("sts").get_caller_identity()["Account"]
NAME = f"tally-proof-ledger-{ACCOUNT}"
DEPLOYED = Path(__file__).resolve().parent.parent / "reasoning" / "deployed.json"

s3 = boto3.client("s3", region_name=REGION)


def main() -> int:
    try:
        s3.head_bucket(Bucket=NAME)
        print(f"  bucket exists: {NAME}")
    except Exception:
        s3.create_bucket(Bucket=NAME, ObjectLockEnabledForBucket=True)
        print(f"  created bucket: {NAME} (object lock on)")
    s3.put_public_access_block(Bucket=NAME, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    s3.put_object_lock_configuration(Bucket=NAME, ObjectLockConfiguration={
        "ObjectLockEnabled": "Enabled",
        "Rule": {"DefaultRetention": {"Mode": "COMPLIANCE", "Days": 1095}}})
    lock = s3.get_object_lock_configuration(Bucket=NAME)["ObjectLockConfiguration"]
    print(f"  object lock: {lock['ObjectLockEnabled']}, default {lock['Rule']['DefaultRetention']}")
    state = json.loads(DEPLOYED.read_text()) if DEPLOYED.exists() else {}
    state["ledger_bucket"] = NAME
    DEPLOYED.write_text(json.dumps(state, indent=2) + "\n")
    print(f"LEDGER_BUCKET={NAME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
