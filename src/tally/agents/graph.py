"""The agents, and the two shapes they run in.

During the day the work is request driven: a photograph or a sentence arrives and the provider is
standing there waiting, so the Day Orchestrator calls one specialist as a tool and answers in a few
seconds. Shallow on purpose.

In the evening the work is a fixed pipeline whose steps feed each other, so it is a Strands Graph:
Ledger, then Parent Notes, then Compliance, then the Digest. Deterministic order, and the trace
shows each step.

This is deliberately a different Strands shape from Turnout, which uses a conditional Graph and the
Agent-to-Agent protocol, so the two submissions show two different ways to build with the SDK.
"""

from __future__ import annotations

from strands import Agent
from strands.multiagent import GraphBuilder

from tally import runtime
from tally.agents.models import fast_model, reasoning_model
from tally.tools.day import (
    answer_open_question,
    log_plate,
    record_substitution,
    take_roll,
    today_so_far,
)
from tally.tools.nightly import (
    build_digest,
    build_month_claim,
    check_compliance,
    close_the_day,
    draft_parent_notes,
    rates_in_force,
    reconcile_subsidy,
)

NL2 = chr(10) * 2


def preamble() -> str:
    r = runtime.get()
    p = r.store.get_provider()
    children = r.store.list_children()
    now = r.now()
    roster = ", ".join(f"{c.first_name} ({c.age_group(now.date()).value}"
                       + (f", allergic to {', '.join(c.allergies)}" if c.allergies else "") + ")"
                       for c in children)
    return (
        f"You work for {p.name}, a {p.license_type} child care home in {p.state}. "
        f"It is {now:%A %d %B %Y, %H:%M}.\n"
        f"Children on the roster: {roster}.\n\n"
        "How to behave:\n"
        "- She has a child on each hip. Answer in one short sentence, under 20 words.\n"
        "- Never ask more than one question at a time.\n"
        "- Never invent a food, a child, or a number. Use the tools.\n"
        "- Never say a meal is reimbursable unless the rules tool said so.\n"
        "- Speak plainly, the way a colleague would. No exclamation marks."
    )


DAY = """You are Tally during the child care day.

One thing arrives at a time: a photograph of a plate, or a sentence about who is here, or an answer
to a question you asked. Call the one tool that handles it and report what happened in one sentence.

Use log_plate for a photograph. Use take_roll for a sentence about children arriving, leaving or
being absent. Use record_substitution when she says what a particular child had instead. Use
answer_open_question when she is answering something you asked.

Never decide reimbursability yourself. The tool does that, against versioned rules."""

LEDGER = """You close out the day's meals.

Call close_the_day, then report in one sentence: how many children were fed, what the day is worth,
and whether anything was not reimbursable. If anything was lost, say what it would have paid, because
that is the number that decides whether this home stays open."""

NOTES = """You draft the notes that go home to parents.

Call draft_parent_notes. The notes are assembled from what was actually logged, so do not add
anything that is not in the record: no invented activities, no invented moods. Report how many notes
are ready and in which languages."""

COMPLIANCE = """You watch the deadlines that are not about food.

Call check_compliance and reconcile_subsidy. Report what is due and what needs her answer, in one
sentence each. A subsidy mismatch is a question for the evening, never an interruption during the
day."""

DIGEST = """You assemble the evening digest, and you are the only agent allowed to ask her anything.

Call build_digest. Report exactly what is waiting: notes to approve, questions to answer, compliance
items. If nothing needs her, say so in one sentence and stop. Never pad."""


def day_agent() -> Agent:
    """Request driven, shallow, fast. The provider is waiting with a plate in her hand."""
    return Agent(name="Tally", description="Handles one photograph or sentence at a time.",
                 model=reasoning_model(), system_prompt=preamble() + NL2 + DAY,
                 tools=[log_plate, take_roll, record_substitution, answer_open_question, today_so_far],
                 callback_handler=None)


def ledger_agent() -> Agent:
    return Agent(name="Ledger", description="Closes the day and builds the claim.",
                 model=fast_model(), system_prompt=preamble() + NL2 + LEDGER,
                 tools=[close_the_day, build_month_claim, rates_in_force], callback_handler=None)


def notes_agent() -> Agent:
    return Agent(name="ParentNotes", description="Drafts the notes that go home.",
                 model=fast_model(), system_prompt=preamble() + NL2 + NOTES,
                 tools=[draft_parent_notes], callback_handler=None)


def compliance_agent() -> Agent:
    return Agent(name="ComplianceClock", description="Watches drills, training and subsidy days.",
                 model=fast_model(), system_prompt=preamble() + NL2 + COMPLIANCE,
                 tools=[check_compliance, reconcile_subsidy], callback_handler=None)


def gate_agent() -> Agent:
    return Agent(name="ProviderGate", description="Assembles the evening digest.",
                 model=reasoning_model(), system_prompt=preamble() + NL2 + DIGEST,
                 tools=[build_digest], callback_handler=None)


def build_nightly_graph():
    """Ledger, then Notes, then Compliance, then the Digest. A fixed, auditable order."""
    b = GraphBuilder()
    b.add_node(ledger_agent(), "ledger")
    b.add_node(notes_agent(), "notes")
    b.add_node(compliance_agent(), "compliance")
    b.add_node(gate_agent(), "digest")
    b.add_edge("ledger", "notes")
    b.add_edge("notes", "compliance")
    b.add_edge("compliance", "digest")
    b.set_entry_point("ledger")
    b.set_max_node_executions(6)
    b.set_execution_timeout(300)
    return b.build()


def run_evening() -> dict:
    """The 18:30 run. Everything that can wait until the children have gone home happens here."""
    r = runtime.get()
    r.emit("evening_start")
    graph = build_nightly_graph()
    result = graph("Close out today and tell her what needs her.")
    summary = {"status": str(result.status),
               "order": [n.node_id for n in result.execution_order],
               "outputs": {}}
    for node_id, node_result in result.results.items():
        try:
            summary["outputs"][node_id] = str(node_result.result)[:600]
        except Exception:
            summary["outputs"][node_id] = "?"
    r.emit("evening_end", **summary)
    return summary
