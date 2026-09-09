"""The other side of the rulebook: a reviewer's agent that checks a claim without trusting Tally.

`tally.mcp.server` publishes the meal pattern rules over the Model Context Protocol. This is the
consumer, and it exists to make a specific point rather than to be a feature.

Tally tells a provider her lunch is reimbursable. She is not the one who has to be convinced. The
sponsoring organisation signs the claim and carries the liability if a state reviewer disagrees, so
the question that matters is whether somebody who does not trust Tally reaches the same verdict.

Here that somebody is a Strands agent holding no Tally code. Its entire toolset is discovered at
runtime from the MCP server, so it knows what a lunch requires only because it asked, and it can
name the rule version behind every answer. Point it at a different rulebook server and it reviews
against those rules instead, having changed nothing.

That is the whole argument for putting the rules behind a protocol rather than inside the product.

    python -m tally.mcp.sponsor --check          call the tools directly, no model, no cost
    python -m tally.mcp.sponsor "lunch was milk and bread for a four year old"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from mcp import StdioServerParameters, stdio_client
from strands import Agent
from strands.tools.mcp import MCPClient

from tally.house import plain

REVIEWER = """You review child care food program claims for a sponsoring organisation.

You do not have the meal pattern rules. You have tools that answer questions about them, published
by the provider's software over an open protocol. Use them. Never answer a rule question from your
own memory of the USDA tables, because the tables change and the version in force on the day the
meal was served is what governs the claim.

For any claim put to you:
1. Call rule_version first and state the version you are reviewing under.
2. Call check_components with what was actually served.
3. If it is not reimbursable, say what is missing and what the smallest fix would have been.
4. If it is reimbursable, call payment_rate and say what it pays.

If a tool returns an error or declines to answer, say so plainly and stop. An unanswered question
is a claim for a human to review, not one for you to guess at. Never state a ratio limit or a
payment rate that a tool did not give you.

Be brief. A reviewer reads hundreds of these.

Write plain text. No emoji and no dashes other than the hyphen. A claim summary gets
pasted into systems that mangle both."""


def rulebook() -> MCPClient:
    """Connect to the rulebook server, spawned as a subprocess over stdio.

    Deliberately the same entry point anybody else would use. Nothing here reaches into Tally.
    """
    root = Path(__file__).resolve().parents[2]
    # Merged into the inherited environment rather than replacing it. Passing a bare dict to
    # StdioServerParameters hands the child that dict as its whole environment, which drops PATH,
    # HOME and the rest. It survives on Windows because the interpreter path is absolute, and it is
    # not something to rely on. PYTHONPATH is only needed when the package is not installed.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")
    return MCPClient(lambda: stdio_client(StdioServerParameters(
        command=sys.executable,
        args=["-m", "tally.mcp.server"],
        env=env,
    )))


def check() -> int:
    """Call every tool over the real protocol and print what came back.

    No model, so this costs nothing and runs in CI. It answers the only question that matters
    about the server: does a client that holds no Tally code get usable answers out of it.
    """
    with rulebook() as client:
        tools = client.list_tools_sync()
        print(f"discovered {len(tools)} tools over MCP:")
        for t in tools:
            print(f"  {t.tool_name}")
        print()

        calls = [
            ("rule_version", {}),
            ("meal_pattern", {"meal_type": "lunch", "age_group": "3-5"}),
            ("check_components", {"components": ["milk", "grain"],
                                  "meal_type": "lunch", "age_group": "3-5"}),
            ("check_components", {"components": ["milk", "grain", "fruit", "vegetable", "meat_alt"],
                                  "meal_type": "lunch", "age_group": "3-5"}),
            ("payment_rate", {"meal_type": "lunch", "tier": "tier_1"}),
            ("state_ratio", {"state": "TX", "license_type": "registered"}),
            ("state_ratio", {"state": "NY", "license_type": "licensed"}),
            ("meal_pattern", {"meal_type": "lunch", "age_group": "infant"}),
        ]
        for name, args in calls:
            r = client.call_tool_sync(tool_use_id=f"check-{name}", name=name, arguments=args)
            text = "".join(c.get("text", "") for c in r.get("content", []))
            print(f"--- {name}({json.dumps(args)}) -> {r.get('status')}")
            print(f"    {text[:400]}")
        print()
        print("Every answer above came back over stdio from a separate process. The reviewer holds "
              "no Tally code.")
    return 0


def review(claim: str) -> int:
    from tally.agents.models import reasoning_model

    with rulebook() as client:
        # callback_handler=None turns off Strands' own token-by-token printing. Two reasons,
        # both found by running this: it prints before anything can be filtered, so the
        # house rule could never apply to it, and on a Windows cp1252 console a single
        # emoji from the model raises UnicodeEncodeError and takes the whole review down.
        agent = Agent(model=reasoning_model(), tools=client.list_tools_sync(),
                      system_prompt=REVIEWER, callback_handler=None)
        # The model is told to write plain text and the model is not what enforces it. This
        # is the same house rule every other surface in the project passes through, and a
        # live run of this agent is what showed it was missing here: it answered with a
        # cross mark emoji and an em dash, which then crashed a Windows console outright.
        print(plain(str(agent(claim))))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("claim", nargs="?", help="the claim to review")
    ap.add_argument("--check", action="store_true",
                    help="call the tools directly with no model and print the answers")
    a = ap.parse_args()

    if a.check or not a.claim:
        return check()
    return review(a.claim)


if __name__ == "__main__":
    sys.exit(main())
