"""Model selection. Ids are configuration, never hard-coded in agent code."""

from __future__ import annotations

import os

from strands.models import BedrockModel

REGION = os.environ.get("AWS_REGION", "us-east-1")

# Verified against this account in us-east-1 on 4 September 2026.
VISION_MODEL = os.environ.get("TALLY_VISION_MODEL", "us.anthropic.claude-sonnet-4-6")
REASONING_MODEL = os.environ.get("TALLY_REASONING_MODEL", "us.anthropic.claude-sonnet-4-6")
FAST_MODEL = os.environ.get("TALLY_FAST_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")


def vision_model() -> BedrockModel:
    """Reads a plate. Temperature 0, because the same photograph should give the same record."""
    return BedrockModel(model_id=VISION_MODEL, region_name=REGION, temperature=0, max_tokens=1500)


def reasoning_model() -> BedrockModel:
    return BedrockModel(model_id=REASONING_MODEL, region_name=REGION, temperature=0.2, max_tokens=2000)


def fast_model() -> BedrockModel:
    """Attendance parsing and short confirmations, where latency is what the provider feels."""
    return BedrockModel(model_id=FAST_MODEL, region_name=REGION, temperature=0, max_tokens=800)
