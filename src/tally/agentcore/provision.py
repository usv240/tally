"""Create the AgentCore memory ahead of time.

Provisioning takes minutes. That is fine once and unacceptable while Rosa is standing at a table
with twelve children and a phone in her hand, so it happens here rather than on the first request.
At request time `tally.agentcore.memory` only looks the memory up, and falls back to the local store
with the reason on the screen if it is not there.

    python -m tally.agentcore.provision
    python -m tally.agentcore.provision --list

The provider ids come from the scenario rather than a constant here, so a second home added to the
demo data gets a memory without anyone remembering to edit this file.
"""

from __future__ import annotations

import argparse
import time

import boto3

from tally.agentcore.memory import AnswerMemory


def provider_ids(scenario: str | None = None) -> list[str]:
    from tally.service import SCENARIO, load_scenario

    store, _ = load_scenario(scenario or SCENARIO)
    return [store.get_provider().id]


def provision(region: str = "us-east-1", wait: int = 600, scenario: str | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    for pid in provider_ids(scenario):
        m = AnswerMemory(pid, region)
        started = time.time()
        try:
            mid = m.ensure(wait_seconds=wait, create=True)
            out[pid] = mid
            print(f"  {pid:12s} {mid}  ({time.time() - started:.0f}s)")
        except Exception as exc:
            print(f"  {pid:12s} FAILED {type(exc).__name__}: {str(exc)[:120]}")
    return out


def show(region: str = "us-east-1") -> None:
    cp = boto3.client("bedrock-agentcore-control", region_name=region)
    found = False
    for m in cp.list_memories(maxResults=100).get("memories", []):
        if m.get("id", "").startswith("tally_"):
            print(f"  {m['id']:44s} {m.get('status')}")
            found = True
    if not found:
        print("  none yet. Run python -m tally.agentcore.provision")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="us-east-1")
    ap.add_argument("--scenario", default=None)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        show(a.region)
        return
    print("Provisioning the AgentCore memory. This takes a few minutes.")
    provision(a.region, scenario=a.scenario)


if __name__ == "__main__":
    main()
