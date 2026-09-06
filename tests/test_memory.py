"""What Rosa has already answered, without AWS.

The thing that has to hold is that her two nightly questions are not spent re-asking something she
settled last week, and that a lookup which fails asks her anyway rather than silently dropping a
subsidy day she is owed.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from tally.agentcore import memory
from tally.models import AttendanceEvent


class _FakeMemory:
    """AgentCore Memory's two calls, in memory, keyed the way the service keys them."""

    def __init__(self, broken: bool = False):
        self.broken = broken
        self.events: dict[tuple[str, str], list[dict]] = {}
        self.writes = 0

    def create_event(self, **kw):
        if self.broken:
            raise RuntimeError("AccessDeniedException: not authorised")
        self.writes += 1
        self.events.setdefault((kw["actorId"], kw["sessionId"]), []).append(
            {"payload": kw["payload"]})
        return {}

    def list_events(self, **kw):
        if self.broken:
            raise RuntimeError("AccessDeniedException: not authorised")
        return {"events": self.events.get((kw["actorId"], kw["sessionId"]), [])}


@pytest.fixture
def store(monkeypatch):
    """An AnswerMemory wired to the fake, with the module level caches cleared."""
    fake = _FakeMemory()
    memory._memories.clear()
    memory.written.clear()
    m = memory.AnswerMemory("rosa")
    m.memory_id = "tally_rosa-TEST"
    m._cp, m._dp = object(), fake
    memory._memories["rosa"] = m
    return fake


NOW = datetime(2026, 9, 8, 18, 30)


def test_a_topic_is_the_child_and_the_weekday_not_the_date():
    """Two Tuesdays share a topic. Leo and Mia never do."""
    assert memory.topic_for_subsidy("leo", 1) == memory.topic_for_subsidy("leo", 1)
    assert memory.topic_for_subsidy("leo", 1) != memory.topic_for_subsidy("leo", 2)
    assert memory.topic_for_subsidy("leo", 1) != memory.topic_for_subsidy("mia", 1)


def test_an_answer_comes_back_the_next_week(store):
    topic = memory.topic_for_subsidy("leo", 1)
    memory.record_answer("rosa", topic, "Yes", NOW - timedelta(days=7))
    standing = memory.already_answered("rosa", topic, NOW)
    assert standing is not None
    assert standing["answer"] == "Yes"
    assert standing["days_ago"] == 7
    assert standing["source"] == "agentcore_memory"


def test_a_question_she_has_never_been_asked_is_still_asked(store):
    assert memory.already_answered("rosa", memory.topic_for_subsidy("mia", 3), NOW) is None


def test_an_answer_older_than_the_window_is_asked_again(store):
    """A family's schedule changes. An answer from months ago is not evidence about this week."""
    topic = memory.topic_for_subsidy("leo", 1)
    memory.record_answer("rosa", topic, "Yes",
                         NOW - timedelta(days=memory.ANSWER_STANDS_DAYS + 1))
    assert memory.already_answered("rosa", topic, NOW) is None


def test_the_most_recent_answer_wins(store):
    topic = memory.topic_for_subsidy("leo", 1)
    memory.record_answer("rosa", topic, "Yes", NOW - timedelta(days=21))
    memory.record_answer("rosa", topic, "No", NOW - timedelta(days=3))
    assert memory.already_answered("rosa", topic, NOW)["answer"] == "No"


def test_a_failed_lookup_asks_her_rather_than_staying_quiet(monkeypatch):
    """Failing safe here means asking a question twice, not losing a day she is owed."""
    memory._memories.clear()
    memory.written.clear()
    m = memory.AnswerMemory("rosa")
    m.memory_id = "tally_rosa-TEST"
    m._cp, m._dp = object(), _FakeMemory(broken=True)
    memory._memories["rosa"] = m

    assert memory.already_answered("rosa", memory.topic_for_subsidy("leo", 1), NOW) is None
    assert memory.status("rosa")["last_error"]


def test_a_failed_write_falls_back_and_says_so(monkeypatch):
    memory._memories.clear()
    memory.written.clear()
    m = memory.AnswerMemory("rosa")
    m.memory_id = "tally_rosa-TEST"
    m._cp, m._dp = object(), _FakeMemory(broken=True)
    memory._memories["rosa"] = m

    out = memory.record_answer("rosa", "subsidy-leo-1", "Yes", NOW)
    assert out["stored_in"] == "local_fallback"
    assert "AccessDenied" in out["reason"]
    assert memory.status("rosa")["local"] == 1


def test_turning_agentcore_off_writes_locally_and_never_recalls(store):
    topic = memory.topic_for_subsidy("leo", 1)
    assert memory.record_answer("rosa", topic, "Yes", NOW,
                                use_agentcore=False)["stored_in"] == "local"
    assert store.writes == 0
    assert memory.already_answered("rosa", topic, NOW, use_agentcore=False) is None


def test_status_counts_what_happened_rather_than_asserting_it(store):
    topic = memory.topic_for_subsidy("leo", 1)
    memory.record_answer("rosa", topic, "Yes", NOW - timedelta(days=2))
    memory.already_answered("rosa", topic, NOW)
    s = memory.status("rosa")
    assert s["agentcore"] == 1 and s["recalled"] == 1 and s["local"] == 0
    assert s["memory_id"] == "tally_rosa-TEST"


def test_what_is_written_is_readable_json_carrying_the_topic(store):
    memory.record_answer("rosa", "subsidy-leo-1", "Yes", NOW)
    (payload,) = next(iter(store.events.values()))[0]["payload"]
    blob = json.loads(payload["conversational"]["content"]["text"])
    assert blob["topic"] == "subsidy-leo-1"
    assert blob["answer"] == "Yes"


def _reconcile(monkeypatch, fake):
    """Run one evening's subsidy reconciliation against a real scenario runtime."""
    from tally.service import setup
    from tally.tools import nightly

    rt, _ = setup()
    monkeypatch.setenv("TALLY_USE_AGENTCORE", "1")
    memory._memories.clear()
    m = memory.AnswerMemory(rt.store.get_provider().id)
    m.memory_id = "tally_test-MEM"
    m._cp, m._dp = object(), fake
    memory._memories[rt.store.get_provider().id] = m

    # Mark everyone present, so any subsidised child on an unauthorised day raises a mismatch.
    on = rt.now().date()
    rt.store.add_attendance(on, [AttendanceEvent(child_id=c.id, event="arrive", at=rt.now())
                                 for c in rt.store.list_children()])
    return rt, nightly.reconcile_subsidy.__wrapped__()


def test_the_same_mismatch_is_not_asked_about_two_weeks_running(monkeypatch):
    """The point of the whole module: her two nightly questions go on new things."""
    memory.written.clear()
    fake = _FakeMemory()

    rt, first = _reconcile(monkeypatch, fake)
    asked = first["mismatches"]
    if not asked:
        pytest.skip("this scenario has no subsidy mismatch on the demo day")
    assert not first["already_answered"]

    # She answers each one, which is what the evening digest is for.
    for m in asked:
        q = next(q for q in rt.store.list_questions() if q.id == m["question_id"])
        memory.record_answer(rt.store.get_provider().id, q.topic, "Yes", rt.now())

    _, second = _reconcile(monkeypatch, fake)
    assert not second["mismatches"], "she was asked the same question a second time"
    assert len(second["already_answered"]) == len(asked)
    assert second["already_answered"][0]["answer"] == "Yes"
    assert second["already_answered"][0]["source"] == "agentcore_memory"
