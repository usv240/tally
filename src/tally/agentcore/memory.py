"""What Rosa has already told us, in Amazon Bedrock AgentCore Memory.

Tally rations itself to two questions a night, enforced in code, because a provider's attention is
the scarce resource this product exists to protect. That budget only means something if the two
questions are new ones.

The subsidy reconciliation question is the case that breaks without memory. It fires whenever a
subsidised child is present on a day their authorisation does not cover, and the mismatch is almost
never a one-off: a family whose Tuesday is not on the paperwork has an unlisted Tuesday every week.
So Rosa answers "yes, Leo was here" on Tuesday, and the same question arrives the next Tuesday, and
the one after, each time spending one of the two things she was going to be asked that night.

So an answer is remembered against its topic, not its question id: the child and the weekday, which
is the thing that actually recurs. Ask again inside the window and the digest says it already knows,
and when it last heard it, rather than silently dropping the question.

One memory per provider, so one home's answers are not reachable from another's. Falls back to the
local store when AgentCore is unavailable and always reports which one answered, the same contract
as `tally.agentcore.code`.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta

RETENTION_DAYS = 90
ACTOR_PREFIX = "provider"

# How long an answer about a recurring topic stands before it is worth asking again. A family's
# schedule does change, and an answer from three months ago is not evidence about this week.
ANSWER_STANDS_DAYS = 45


class MemoryUnavailable(RuntimeError):
    pass


def topic_for_subsidy(child_id: str, weekday: int) -> str:
    """The thing that recurs: this child, this day of the week.

    Not the question id, which is new every time, and not the date, which never repeats.
    """
    return f"subsidy-{child_id}-{weekday}"


class AnswerMemory:
    """One AgentCore memory per provider, holding answered questions as events."""

    def __init__(self, provider_id: str, region: str = "us-east-1") -> None:
        self.provider_id = provider_id
        self.region = region
        self.memory_id: str | None = None
        self._cp = None
        self._dp = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    def _clients(self):
        if self._cp is None:
            import boto3

            self._cp = boto3.client("bedrock-agentcore-control", region_name=self.region)
            self._dp = boto3.client("bedrock-agentcore", region_name=self.region)
        return self._cp, self._dp

    def ensure(self, wait_seconds: int = 20, create: bool = False) -> str:
        """Find this provider's memory. Creating one takes minutes, so that is a deploy step.

        `python -m tally.agentcore.provision` creates it ahead of time. At request time this only
        looks it up, because Rosa is standing at a table with a phone in her hand.
        """
        if self.memory_id:
            return self.memory_id
        with self._lock:
            if self.memory_id:
                return self.memory_id
            cp, _ = self._clients()
            name = f"tally_{self.provider_id}"
            try:
                for m in cp.list_memories(maxResults=100).get("memories", []):
                    if m.get("id", "").startswith(name):
                        self.memory_id = m["id"]
                        if m.get("status") == "ACTIVE":
                            return self.memory_id
                        break
                if not self.memory_id:
                    if not create:
                        raise MemoryUnavailable(
                            f"no memory for {self.provider_id} yet. Run "
                            f"python -m tally.agentcore.provision to create it.")
                    r = cp.create_memory(
                        name=name,
                        description=f"Answered questions for {self.provider_id}, so the nightly "
                                    f"budget is not spent asking the same thing twice.",
                        eventExpiryDuration=RETENTION_DAYS,
                    )
                    self.memory_id = r["memory"]["id"]

                deadline = time.time() + wait_seconds
                while time.time() < deadline:
                    status = cp.get_memory(memoryId=self.memory_id)["memory"]["status"]
                    if status == "ACTIVE":
                        return self.memory_id
                    if status in ("FAILED", "DELETING"):
                        raise MemoryUnavailable(f"memory is {status}")
                    time.sleep(3)
                raise MemoryUnavailable("memory did not become active in time")
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"[:400]
                raise MemoryUnavailable(self.last_error) from exc

    def record(self, topic: str, answer: str, at: datetime | None = None) -> dict:
        """Remember one answer against the topic it settles."""
        _, dp = self._clients()
        self.ensure()
        when = at or datetime.now()
        dp.create_event(
            memoryId=self.memory_id,
            actorId=f"{ACTOR_PREFIX}-{self.provider_id}",
            sessionId=topic,
            eventTimestamp=when,
            payload=[{"conversational": {
                "role": "USER",
                "content": {"text": json.dumps({"topic": topic, "answer": answer,
                                                "at": when.isoformat()})},
            }}],
        )
        return {"stored_in": "agentcore_memory", "memory_id": self.memory_id}

    def latest(self, topic: str) -> tuple[str, datetime] | None:
        """The most recent answer on a topic, or None if she has never been asked."""
        _, dp = self._clients()
        self.ensure()
        r = dp.list_events(memoryId=self.memory_id, actorId=f"{ACTOR_PREFIX}-{self.provider_id}",
                           sessionId=topic, maxResults=20)
        best: tuple[str, datetime] | None = None
        for ev in r.get("events", []):
            for item in ev.get("payload", []):
                text = item.get("conversational", {}).get("content", {}).get("text", "")
                try:
                    blob = json.loads(text)
                except ValueError:
                    continue
                try:
                    when = datetime.fromisoformat(blob["at"])
                except (KeyError, ValueError):
                    continue
                if best is None or when > best[1]:
                    best = (str(blob.get("answer", "")), when)
        return best


_memories: dict[str, AnswerMemory] = {}


def for_provider(provider_id: str, region: str = "us-east-1") -> AnswerMemory:
    if provider_id not in _memories:
        _memories[provider_id] = AnswerMemory(provider_id, region)
    return _memories[provider_id]


# What this process actually wrote and read, per provider, so a page can report it rather than
# assert it. The same reason turnout counts its writes: a claim about where data went is only worth
# making if the number is on the screen.
written: dict[str, dict] = {}


def _stat(provider_id: str) -> dict:
    return written.setdefault(provider_id, {"agentcore": 0, "local": 0, "recalled": 0,
                                            "memory_id": None, "last_error": None})


def record_answer(provider_id: str, topic: str, answer: str, at: datetime | None = None,
                  use_agentcore: bool = True) -> dict:
    """Remember an answer, or say why it went to the local store instead."""
    stat = _stat(provider_id)
    if not use_agentcore:
        stat["local"] += 1
        return {"stored_in": "local"}
    try:
        out = for_provider(provider_id).record(topic, answer, at)
        stat["agentcore"] += 1
        stat["memory_id"] = out.get("memory_id")
        stat["last_error"] = None
        return out
    except Exception as exc:
        stat["local"] += 1
        stat["last_error"] = f"{type(exc).__name__}: {exc}"[:400]
        return {"stored_in": "local_fallback", "reason": stat["last_error"]}


def already_answered(provider_id: str, topic: str, now: datetime,
                     use_agentcore: bool = True) -> dict | None:
    """Her standing answer on a topic, if it is recent enough to still mean something.

    Returns None when she has never been asked, when the answer has aged out, or when AgentCore is
    unavailable. Never asking is the safe failure here: a repeated question wastes her evening, but a
    question suppressed because a lookup failed loses a subsidy day she is owed.
    """
    if not use_agentcore:
        return None
    stat = _stat(provider_id)
    try:
        found = for_provider(provider_id).latest(topic)
    except Exception as exc:
        stat["last_error"] = f"{type(exc).__name__}: {exc}"[:400]
        return None
    if not found:
        return None
    answer, when = found
    age = now - when
    if age > timedelta(days=ANSWER_STANDS_DAYS):
        return None
    stat["recalled"] += 1
    return {"answer": answer, "at": when.isoformat(), "days_ago": max(age.days, 0),
            "topic": topic, "source": "agentcore_memory"}


def status(provider_id: str) -> dict:
    """Where this provider's answers went, counted rather than claimed."""
    return dict(written.get(provider_id) or {"agentcore": 0, "local": 0, "recalled": 0,
                                             "memory_id": None, "last_error": None})
