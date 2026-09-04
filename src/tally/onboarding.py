"""Getting a home set up, from whatever the provider already has.

A provider does not have her children in a database. She has an enrolment form, a note on the
fridge, or a spreadsheet the sponsor sent her. So the first screen takes a paste of any of those and
works out names, birthdays, subsidy days and allergies, then shows her what it understood before
saving anything.

Parsing is rules rather than a model, so it is instant, testable and identical every time. Anything
it cannot read is reported rather than dropped, because a child missing from the roster is a child
whose allergy is never checked.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

DAY_WORDS = {"mon": 0, "monday": 0, "tue": 1, "tues": 1, "tuesday": 1, "wed": 2, "weds": 2,
             "wednesday": 2, "thu": 3, "thur": 3, "thurs": 3, "thursday": 3, "fri": 4, "friday": 4}

ALLERGY_WORDS = ["peanut", "tree nut", "nut", "dairy", "milk", "egg", "wheat", "gluten", "soy",
                 "fish", "shellfish", "sesame", "strawberry", "kiwi"]

SUBSIDY_WORDS = ("subsid", "voucher", "assisted", "ccdf", "state pay", "state-pay")

# Words that look like a name but are not one.
NOT_NAMES = {"born", "dob", "birthday", "allergy", "allergic", "allergies", "to", "and", "the",
             "subsidised", "subsidized", "subsidy", "voucher", "none", "no", "child", "children",
             "name", "days", "attends", "full", "time", "part"}


class ParsedChild(BaseModel):
    first_name: str
    birth_date: date
    age_group: str
    enrolled_days: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    subsidized: bool = False
    subsidy_days: list[int] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    source_line: str = ""


class ParsedRoster(BaseModel):
    children: list[ParsedChild] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list)
    """Lines with words on them but no usable birthday. Reported, never silently dropped."""
    warnings: list[str] = Field(default_factory=list)


def parse_birth_date(text: str, today: date | None = None) -> date | None:
    """Read a birthday in the shapes people actually write them."""
    today = today or date.today()
    low = text.lower()

    # 3 March 2025, March 3 2025, 3rd Mar 2025
    m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]{3,9})\.?\s+(\d{4})\b", low)
    if m and m.group(2)[:3] in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(2)[:3]], int(m.group(1)))
        except ValueError:
            return None
    m = re.search(r"\b([a-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", low)
    if m and m.group(1)[:3] in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(1)[:3]], int(m.group(2)))
        except ValueError:
            return None
    # 2025-03-03
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", low)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    # 3/3/2025 and 03/03/25, read as month/day/year, which is what a US enrolment form uses.
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", low)
    if m:
        month, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        try:
            return date(year, month, day)
        except ValueError:
            return None
    return None


def find_allergies(text: str) -> list[str]:
    low = text.lower()
    if not any(w in low for w in ("allerg", "intoleran")):
        return []
    found: list[str] = []
    for word in ALLERGY_WORDS:
        if word in low and not any(word in f for f in found):
            found.append(word)
    return found


def find_days(text: str) -> list[int]:
    """Days from a phrase like "Mon Wed Fri" or "Tue-Fri". Empty means the caller should default."""
    low = text.lower()
    m = re.search(r"\b(mon|tue|tues|wed|weds|thu|thur|thurs|fri)[a-z]*\s*(?:-|to|through)\s*"
                  r"(mon|tue|tues|wed|weds|thu|thur|thurs|fri)[a-z]*\b", low)
    if m:
        a, b = DAY_WORDS[m.group(1)], DAY_WORDS[m.group(2)]
        if a <= b:
            return list(range(a, b + 1))
    days = []
    for token in re.findall(r"\b(mon|tues|tue|weds|wed|thurs|thur|thu|fri)[a-z]*\b", low):
        d = DAY_WORDS.get(token)
        if d is not None and d not in days:
            days.append(d)
    return sorted(days)


def clean_name(text: str, birth_text: str) -> str:
    """Whatever is left once the date, the days, the allergies and the keywords are taken out."""
    s = text
    for pattern in (r"\b\d{1,2}(?:st|nd|rd|th)?\s+[a-z]{3,9}\.?\s+\d{4}\b",
                    r"\b[a-z]{3,9}\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
                    r"\b\d{4}-\d{1,2}-\d{1,2}\b", r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"):
        s = re.sub(pattern, " ", s, flags=re.I)
    s = re.sub(r"\b(mon|tues?|weds?|thur?s?|fri)[a-z]*\b", " ", s, flags=re.I)
    for word in ALLERGY_WORDS + list(SUBSIDY_WORDS) + ["allergy", "allergic", "allergies",
                                                       "intolerance", "born", "dob", "birthday"]:
        s = re.sub(rf"\b{re.escape(word)}\w*\b", " ", s, flags=re.I)
    s = re.sub(r"[^A-Za-z'\-. ]+", " ", s)
    tokens = [t for t in s.split() if t.lower().strip(".'-") not in NOT_NAMES and len(t) > 1]
    _ = birth_text
    return " ".join(t.capitalize() if t.islower() or t.isupper() else t for t in tokens[:2]).strip()


def age_group_for(birth: date, on: date) -> str:
    years = on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))
    if years < 1:
        return "infant"
    if years <= 2:
        return "1-2"
    if years <= 5:
        return "3-5"
    if years <= 12:
        return "6-12"
    return "13-18"


def parse_children(text: str, today: date | None = None) -> ParsedRoster:
    """Read a pasted list of children, in whatever shape the provider already keeps it."""
    today = today or date.today()
    out = ParsedRoster()
    seen: set[str] = set()

    for raw in text.splitlines():
        line = raw.strip().strip("|,;")
        if not line or len(line) < 3:
            continue
        birth = parse_birth_date(line, today)
        if birth is None:
            if re.search(r"[A-Za-z]{3,}", line):
                out.unreadable.append(line)
            continue
        if birth > today:
            out.unreadable.append(line)
            out.warnings.append(f"A birthday in the future was ignored: {line.strip()}")
            continue
        name = clean_name(line, str(birth))
        if not name:
            out.unreadable.append(line)
            continue
        key = name.lower()
        if key in seen:
            out.warnings.append(f"{name} appears more than once, so only the first was kept.")
            continue
        seen.add(key)

        days = find_days(line) or [0, 1, 2, 3, 4]
        subsidised = any(w in line.lower() for w in SUBSIDY_WORDS)
        group = age_group_for(birth, today)
        child = ParsedChild(first_name=name, birth_date=birth, age_group=group,
                            enrolled_days=days, subsidized=subsidised,
                            subsidy_days=days if subsidised else [],
                            allergies=find_allergies(line), source_line=line)
        out.children.append(child)
        if group == "infant":
            out.warnings.append(
                f"{name} is under one, so their meals follow the infant pattern. Tally records "
                f"those and does not judge them against the child meal pattern.")
    return out


def ratio_preview(children: list[ParsedChild], state: str, license_type: str) -> dict:
    """What the state limits mean for this particular group, before anything is saved."""
    from tally.engine.ratio import limits_for

    try:
        limits = limits_for(state, license_type)
    except KeyError as exc:
        return {"ok": False, "error": str(exc)}
    limit = int(limits.get("max_with_school_age") or limits["max_group_size"])
    under_two = sum(1 for c in children if c.age_group in ("infant", "1-2"))
    max_under_two = limits.get("max_under_two")
    problems = []
    if len(children) > limit:
        problems.append(f"{len(children)} children is over the limit of {limit} for a "
                        f"{limits['label'].lower()}.")
    if max_under_two and under_two > int(max_under_two):
        problems.append(f"{under_two} children under two is over the limit of {max_under_two}.")
    return {"ok": not problems, "limit": limit, "enrolled": len(children),
            "under_two": under_two, "label": limits["label"], "problems": problems}
