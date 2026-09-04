"""Provider Gate: the only thing allowed to ask her a question.

Her hands are full and her attention is the scarce resource. Interrupting a person costs about 23
minutes of recovered focus (Gloria Mark, UC Irvine), and a provider is interrupted by children all
day already. So questions are ranked and rationed, and the budget is enforced here in code rather
than left to a prompt.

Four priorities:

- safety: an allergy on the plate. Immediate, never counted against the budget, never deferred.
- meal: this plate will not qualify. Asked at the table, because that is the only moment the answer
  is useful, and not counted against the budget for the same reason.
- reconciliation: attendance that does not match a subsidy authorisation. Waits for the evening.
- compliance: a fire drill, a training hour. Waits for the evening, and can wait a day.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from tally.models import Question

PRIORITY_ORDER = {"safety": 0, "meal": 1, "reconciliation": 2, "compliance": 3}
BUDGETED = ("reconciliation", "compliance")


def new_question(provider_id: str, text: str, at: datetime, priority: str,
                 options: list[str] | None = None) -> Question:
    return Question(id=f"q-{uuid.uuid4().hex[:8]}", provider_id=provider_id, at=at, text=text,
                    options=options or [], priority=priority)


def may_ask_now(priority: str, asked_today: int, budget: int) -> tuple[bool, str]:
    """Whether this question may interrupt her right now, and why.

    Safety and meal questions always may: one is a child's health and the other is only useful while
    the food is still on the table. Everything else waits for the evening digest and spends budget.
    """
    if priority == "safety":
        return True, "a child at this table has an allergy to something on the plate"
    if priority == "meal":
        return True, "the answer is only useful while the food is still on the table"
    if asked_today >= budget:
        return False, f"already asked {asked_today} of {budget} questions today, so this waits"
    return False, "this can wait for the evening, so it is not worth interrupting her now"


def rank(questions: list[Question]) -> list[Question]:
    return sorted(questions, key=lambda q: (PRIORITY_ORDER.get(q.priority, 9), q.at))


def digest(questions: list[Question], budget: int) -> tuple[list[Question], list[Question]]:
    """The evening digest: the questions worth her time tonight, and the ones that wait."""
    ordered = rank([q for q in questions if not q.answered])
    return ordered[:budget], ordered[budget:]
