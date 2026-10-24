"""The obvious alternative to a proof: two agents argue, a third decides.

Ask any engineer how to make an agent's rule answers safer and this is the first design on the
whiteboard. A Yes agent argues the draft is right, a No agent argues it is wrong, two rounds, and a
Judge writes the answer. It costs three model calls and feels rigorous. The research says it does not
reliably beat a single agent (Smit et al., ICML 2024; arXiv 2502.08788), and this file exists so
that claim is measured on our questions rather than cited.

Same model as the Day agent, same preamble, no tools. Nothing here can see the regulation.
"""

from __future__ import annotations

from strands import Agent

from tally.agents.graph import NL2, preamble
from tally.agents.models import reasoning_model

YES = """You argue that the draft answer to the provider's question is correct under the CACFP meal
pattern rules. Be concrete: cite the limit or the rule as you understand it. Three sentences at most."""

NO = """You argue that the draft answer to the provider's question is wrong or incomplete under the
CACFP meal pattern rules. Be concrete: cite the limit or the rule as you understand it. Three
sentences at most."""

JUDGE = """You have read a provider's question, a draft answer, and two rounds of argument for and
against it. Write the final answer to the provider: one plain decision with the numbers in it, under
40 words. Decide; do not hedge or ask her anything."""


def debate(question: str, draft: str, facts: str = "", rounds: int = 2) -> dict:
    yes = Agent(name="Yes", model=reasoning_model(), system_prompt=preamble() + NL2 + YES, callback_handler=None)
    no = Agent(name="No", model=reasoning_model(), system_prompt=preamble() + NL2 + NO, callback_handler=None)
    judge = Agent(name="Judge", model=reasoning_model(), system_prompt=preamble() + NL2 + JUDGE, callback_handler=None)

    context = f"Provider's question: {question}\nWhat she said: {facts or 'nothing more'}\nDraft answer: {draft}"
    transcript = [context]
    last_no = ""
    for i in range(rounds):
        so_far = context + "\n\n" + "\n".join(transcript[1:])
        rebuttal = f"\n\nThe No side said: {last_no}" if last_no else ""
        y = str(yes(so_far + rebuttal)).strip()
        transcript.append(f"Yes (round {i + 1}): {y}")
        last_no = str(no(context + "\n\n" + "\n".join(transcript[1:]))).strip()
        transcript.append(f"No (round {i + 1}): {last_no}")
    final = str(judge("\n\n".join(transcript))).strip()
    return {"answer": final, "transcript": transcript[1:]}
