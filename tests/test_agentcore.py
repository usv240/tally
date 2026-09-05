"""AgentCore Code Interpreter session handling, without AWS.

The claim arithmetic runs in a sandbox session that the service ends after its timeout. What has to
hold is that an ended session is replaced rather than reused, because reusing it made every later
claim fall back to local, silently, about fifteen minutes after each deploy.
"""

import pytest

from tally.agentcore import code

PAYLOAD = {"days": [["breakfast", "lunch"]], "missed": [],
           "tier_rates": {"breakfast": 1.74, "lunch": 3.31, "supper": 3.31, "snack": 0.98}}


class _FakeInterpreter:
    def __init__(self):
        self.started = 0
        self.dead: set[str] = set()
        self.stopped: list[str] = []

    def start_code_interpreter_session(self, **kw):
        self.started += 1
        return {"sessionId": f"session-{self.started}"}

    def stop_code_interpreter_session(self, **kw):
        self.stopped.append(kw["sessionId"])
        return {}

    def kill(self, session_id):
        self.dead.add(session_id)

    def invoke_code_interpreter(self, **kw):
        if kw["sessionId"] in self.dead:
            raise RuntimeError("ValidationException: session is not active")
        if kw["name"] == "writeFiles":
            return {"stream": [{"result": {"content": [{"type": "text", "text": "ok"}]}}]}
        src = kw["arguments"]["code"]
        text = "kernel loaded 12" if "kernel loaded" in src else (
            f"{src}\n{code.MARKER}" + '{"lines": [], "total": 5.05, "lost_amount": 0.0}\n')
        return {"stream": [{"result": {"content": [{"type": "text", "text": text}]}}]}


def _session_with(fake):
    s = code.ClaimKernelSession(region="us-east-1")
    s._client = fake
    return s


def test_a_terminated_session_is_replaced_rather_than_reused():
    fake = _FakeInterpreter()
    s = _session_with(fake)
    first = s.compute(PAYLOAD)
    assert first["ran_in"] == "agentcore_code_interpreter" and first["session_id"] == "session-1"
    fake.kill("session-1")
    second = s.compute(PAYLOAD)
    assert second["session_id"] == "session-2"
    assert fake.started == 2


def test_a_session_near_its_deadline_is_renewed_before_it_fails():
    fake = _FakeInterpreter()
    s = _session_with(fake)
    s.compute(PAYLOAD)
    s._started_at -= code.SESSION_SECONDS
    assert s.compute(PAYLOAD)["session_id"] == "session-2"
    assert "session-1" in fake.stopped


def test_two_failures_in_a_row_give_up_honestly():
    fake = _FakeInterpreter()
    s = _session_with(fake)
    s.compute(PAYLOAD)
    for sid in ("session-1", "session-2", "session-3"):
        fake.kill(sid)
    with pytest.raises(code.CodeInterpreterUnavailable) as err:
        s.compute(PAYLOAD)
    assert "not active" in str(err.value)


def test_the_fallback_carries_its_reason_to_the_caller():
    """The month view says "computed locally, because AgentCore did not answer". It should also be
    able to say why, so a fallback is a fact on the screen rather than a quiet substitution."""
    saved = code._session
    fake = _FakeInterpreter()
    s = _session_with(fake)
    s.compute(PAYLOAD)
    for sid in ("session-1", "session-2", "session-3"):
        fake.kill(sid)
    code._session = s
    try:
        out = code.compute(PAYLOAD, use_agentcore=True)
    finally:
        code._session = saved
    assert out["ran_in"] == "local_fallback"
    assert "not active" in out["fallback_reason"]
    assert out["total"] == pytest.approx(5.05)
