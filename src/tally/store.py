"""Everything Tally remembers, behind one interface.

MemoryStore is used by the local demo and the tests. A DynamoDB implementation would satisfy the
same method names; the single table design is described in TECHNICAL_DESIGN.md.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel

from tally.models import (
    AttendanceEvent,
    Child,
    Claim,
    ComplianceItem,
    Meal,
    ParentNote,
    Provider,
    Question,
)


def _dump(obj: BaseModel) -> dict:
    return json.loads(obj.model_dump_json())


class MemoryStore:
    def __init__(self) -> None:
        self.provider: Provider | None = None
        self.children: dict[str, Child] = {}
        self.meals: dict[str, Meal] = {}
        self.attendance: dict[date, list[AttendanceEvent]] = defaultdict(list)
        self.questions: dict[str, Question] = {}
        self.notes: dict[tuple[str, date], ParentNote] = {}
        self.compliance: dict[str, ComplianceItem] = {}
        self.claims: dict[str, Claim] = {}
        self.vocabulary: dict[str, str] = {}
        """The provider's own names for foods, learned over time: "the usual crackers" -> a product."""

    # Provider and children ----------------------------------------------------
    def put_provider(self, p: Provider) -> None:
        self.provider = p

    def get_provider(self) -> Provider:
        if self.provider is None:
            raise RuntimeError("no provider configured")
        return self.provider

    def put_child(self, c: Child) -> None:
        self.children[c.id] = c

    def get_child(self, child_id: str) -> Child:
        return self.children[child_id]

    def list_children(self) -> list[Child]:
        return list(self.children.values())

    def find_child(self, name: str) -> Child | None:
        low = name.strip().lower()
        for c in self.children.values():
            if c.first_name.lower() == low or c.id == low:
                return c
        return None

    # Attendance --------------------------------------------------------------
    def add_attendance(self, on: date, events: list[AttendanceEvent]) -> None:
        for e in events:
            same = [x for x in self.attendance[on] if x.child_id == e.child_id]
            for x in same:
                self.attendance[on].remove(x)
            self.attendance[on].append(e)

    def list_attendance(self, on: date) -> list[AttendanceEvent]:
        return list(self.attendance.get(on, []))

    def present_ids(self, on: date) -> set[str]:
        return {e.child_id for e in self.attendance.get(on, []) if e.event == "arrive"}

    def absent_ids(self, on: date) -> set[str]:
        return {e.child_id for e in self.attendance.get(on, []) if e.event == "absent"}

    def expected_ids(self, on: date) -> set[str]:
        return {e.child_id for e in self.attendance.get(on, []) if e.event == "expected"}

    # Meals -------------------------------------------------------------------
    def put_meal(self, m: Meal) -> None:
        self.meals[m.id] = m

    def get_meal(self, meal_id: str) -> Meal:
        return self.meals[meal_id]

    def list_meals(self, on: date | None = None) -> list[Meal]:
        out = list(self.meals.values())
        if on is not None:
            out = [m for m in out if m.at.date() == on]
        return sorted(out, key=lambda m: m.at)

    def superseded_ids(self) -> set[str]:
        """Meals that were corrected by a later photograph, so they must not be counted twice."""
        return {m.replaces for m in self.meals.values() if m.replaces}

    # Questions ---------------------------------------------------------------
    def put_question(self, q: Question) -> Question:
        """Raise a question, unless the same one is already open.

        Photographing a plate again re-runs the allergy check, and a second identical alert would
        teach a provider to ignore alerts. The existing open question is returned instead.
        """
        for existing in self.questions.values():
            if (not existing.answered and existing.text == q.text
                    and existing.at.date() == q.at.date()):
                return existing
        self.questions[q.id] = q
        return q

    def list_questions(self, unanswered_only: bool = True) -> list[Question]:
        out = list(self.questions.values())
        if unanswered_only:
            out = [q for q in out if not q.answered]
        return sorted(out, key=lambda q: q.at)

    def answer_question(self, question_id: str, answer: str) -> Question:
        q = self.questions[question_id]
        q.answered, q.answer = True, answer
        return q

    def questions_asked_today(self, on: date) -> int:
        """Only counts the ones that spend the budget. Meal and safety questions do not."""
        return sum(1 for q in self.questions.values()
                   if q.at.date() == on and q.priority in ("reconciliation", "compliance"))

    # Notes, compliance, claims ------------------------------------------------
    def put_note(self, n: ParentNote) -> None:
        self.notes[(n.child_id, n.on)] = n

    def list_notes(self, on: date) -> list[ParentNote]:
        return [n for (cid, d), n in self.notes.items() if d == on]

    def put_compliance(self, c: ComplianceItem) -> None:
        self.compliance[c.id] = c

    def list_compliance(self) -> list[ComplianceItem]:
        return sorted(self.compliance.values(), key=lambda c: c.due)

    def put_claim(self, c: Claim) -> None:
        self.claims[c.month] = c

    def get_claim(self, month: str) -> Claim | None:
        return self.claims.get(month)

    # Vocabulary ---------------------------------------------------------------
    def learn_food(self, phrase: str, product: str) -> None:
        self.vocabulary[phrase.strip().lower()] = product

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "provider": _dump(self.provider) if self.provider else None,
            "children": [_dump(c) for c in self.children.values()],
            "meals": [_dump(m) for m in self.meals.values()],
            "attendance": {str(d): [_dump(e) for e in evs] for d, evs in self.attendance.items()},
            "questions": [_dump(q) for q in self.questions.values()],
            "compliance": [_dump(c) for c in self.compliance.values()],
            "vocabulary": self.vocabulary,
        }, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: str) -> "MemoryStore":
        blob = json.loads(Path(path).read_text(encoding="utf-8"))
        s = cls()
        if blob.get("provider"):
            s.put_provider(Provider.model_validate(blob["provider"]))
        for c in blob.get("children", []):
            s.put_child(Child.model_validate(c))
        for m in blob.get("meals", []):
            s.put_meal(Meal.model_validate(m))
        for d, evs in blob.get("attendance", {}).items():
            s.add_attendance(date.fromisoformat(d), [AttendanceEvent.model_validate(e) for e in evs])
        for q in blob.get("questions", []):
            s.put_question(Question.model_validate(q))
        for c in blob.get("compliance", []):
            s.put_compliance(ComplianceItem.model_validate(c))
        s.vocabulary = dict(blob.get("vocabulary", {}))
        return s


class Clock:
    """A clock that can be simulated, so the demo plays the same day every time."""

    def __init__(self, start: datetime | None = None) -> None:
        self.simulated = start is not None
        self._now = start or datetime.now()

    def now(self) -> datetime:
        return self._now if self.simulated else datetime.now()

    def set(self, when: datetime) -> None:
        self.simulated = True
        self._now = when
