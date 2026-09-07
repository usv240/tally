"""Runtime context. Tools reach the store, the clock and the event stream through this."""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from tally.store import Clock, MemoryStore

Listener = Callable[[str, dict], None]

@dataclass
class Runtime:
    store: MemoryStore
    clock: Clock
    listeners: list[Listener] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    spoken: list[dict] = field(default_factory=list)
    """Everything Tally said out loud, in order. The provider hears these; the screen mirrors them."""

    def emit(self, kind: str, **payload: Any) -> None:
        evt = {"kind": kind, "at": self.clock.now().isoformat(), **payload}
        self.trace.append(evt)
        for fn in list(self.listeners):
            # A listener is the web app or the trace viewer. Neither is allowed to break an agent
            # mid decision, so a listener that raises is dropped rather than propagated.
            with contextlib.suppress(Exception):
                fn(kind, evt)

    def say(self, text: str, tone: str = "info") -> None:
        """Speak to the provider. Always mirrored as text, because a noisy room swallows audio.

        Most of what is said here was written by a model a moment ago, so it goes through the house
        style on the way out. See tally.house.
        """
        from tally.house import plain

        entry = {"at": self.clock.now().isoformat(), "text": plain(text), "tone": tone}
        self.spoken.append(entry)
        self.emit("spoken", **entry)

    def now(self) -> datetime:
        return self.clock.now()

ctx: Runtime | None = None

def configure(rt: Runtime) -> Runtime:
    global ctx
    ctx = rt
    return rt

def get() -> Runtime:
    if ctx is None:
        raise RuntimeError("tally.runtime.configure() has not been called")
    return ctx
