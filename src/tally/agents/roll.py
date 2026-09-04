"""Roll: who is here, said out loud.

"Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at eight."

Most of that is handled by a rule parser, because a provider holding a toddler should not wait on a
model round trip to be told her roll call was heard. The model is asked only when the rules cannot
read the sentence, which keeps the common case fast and the unusual case handled.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time

from pydantic import BaseModel, Field

from tally.models import AttendanceEvent, Child

ABSENT_WORDS = ("not coming", "is out", "sick", "absent", "away", "staying home", "won't be",
                "wont be", "not in", "no show", "not here today")
LATER_WORDS = ("coming at", "arriving at", "will be here at", "on the way", "later", "running late",
               "comes at")
NEGATIONS = ("no,", "no ", "actually", "scratch that", "correction", "i meant")


class ParsedRoll(BaseModel):
    """What the model returns when the rule parser could not read a sentence."""

    events: list[dict] = Field(default_factory=list)
    """Each: {child_name, event: arrive|absent|expected|depart, time (HH:MM or empty), note}"""
    unrecognised_names: list[str] = Field(default_factory=list)


def _time_in(text: str, on: date, default: datetime) -> datetime:
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\b", text)
    if not m:
        return default
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    mer = (m.group(3) or "").replace(".", "").lower()
    if mer == "pm" and hour < 12:
        hour += 12
    elif mer == "am" and hour == 12:
        hour = 0
    elif not mer and hour <= 6:
        hour += 12  # "coming at 3" in a child care day means the afternoon
    if not (0 <= hour <= 23):
        return default
    return datetime.combine(on, time(hour, minute))


def parse_roll(text: str, children: list[Child], now: datetime) -> tuple[list[AttendanceEvent], list[str]]:
    """Read a spoken roll call. Returns the events and any names it did not recognise."""
    on = now.date()
    events: list[AttendanceEvent] = []
    unknown: list[str] = []
    seen: set[str] = set()

    # Split into clauses so each child is judged on the words around their own name.
    clauses = re.split(r",|\band\b|\.|;", text)
    for clause in clauses:
        low = clause.lower().strip()
        if not low:
            continue
        matched: Child | None = None
        for c in children:
            if re.search(rf"\b{re.escape(c.first_name.lower())}\b", low):
                matched = c
                break
        if matched is None:
            for token in re.findall(r"\b[A-Z][a-z]{2,}\b", clause):
                if token.lower() not in ("mom", "dad", "mum", "the", "she", "her", "his"):
                    unknown.append(token)
            continue
        if matched.id in seen:
            # A later clause about the same child corrects the earlier one.
            events = [e for e in events if e.child_id != matched.id]
        seen.add(matched.id)

        if any(w in low for w in ABSENT_WORDS):
            reason = "sick" if "sick" in low else ""
            events.append(AttendanceEvent(child_id=matched.id, event="absent", at=now, note=reason))
        elif any(w in low for w in LATER_WORDS):
            when = _time_in(low, on, now)
            events.append(AttendanceEvent(child_id=matched.id, event="expected", at=when,
                                          note=clause.strip()))
        elif "left" in low or "picked up" in low or "went home" in low:
            events.append(AttendanceEvent(child_id=matched.id, event="depart", at=now,
                                          note=clause.strip()))
        else:
            events.append(AttendanceEvent(child_id=matched.id, event="arrive", at=now))
    return events, unknown


def apply_correction(text: str, existing: list[AttendanceEvent], children: list[Child],
                     now: datetime) -> list[AttendanceEvent]:
    """Handle "no, Leo's not here yet" without restarting the roll call."""
    low = text.lower().strip()
    if not any(low.startswith(n) or f" {n}" in low for n in NEGATIONS):
        return existing
    new_events, _ = parse_roll(text, children, now)
    if not new_events:
        return existing
    changed = {e.child_id for e in new_events}
    kept = [e for e in existing if e.child_id not in changed]
    # "not here" in a correction means the opposite of arriving.
    fixed = []
    for e in new_events:
        if e.event == "arrive" and ("not here" in low or "isn't here" in low or "not in" in low):
            fixed.append(AttendanceEvent(child_id=e.child_id, event="expected", at=now,
                                         note="corrected: not here yet"))
        else:
            fixed.append(e)
    return kept + fixed


def echo(events: list[AttendanceEvent], children: list[Child]) -> str:
    """One sentence back, naming what was recorded. Confirmation, not a question."""
    by_id = {c.id: c for c in children}
    here = [by_id[e.child_id].first_name for e in events if e.event == "arrive"]
    absent = [(by_id[e.child_id].first_name, e.note) for e in events if e.event == "absent"]
    later = [(by_id[e.child_id].first_name, e.at) for e in events if e.event == "expected"]
    gone = [by_id[e.child_id].first_name for e in events if e.event == "depart"]

    parts = []
    if here:
        parts.append(", ".join(here) + " here")
    for name, at in later:
        parts.append(f"{name} at {at.hour % 12 or 12}:{at.minute:02d}")
    for name, reason in absent:
        parts.append(f"{name} absent{' ' + reason if reason else ''}")
    if gone:
        parts.append(", ".join(gone) + " gone home")
    return ". ".join(parts) + "." if parts else "I did not catch any names."
