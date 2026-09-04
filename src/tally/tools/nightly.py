"""Tools for the evening run: the ledger, the parent notes, the compliance clock, the digest."""

from __future__ import annotations

from datetime import date, timedelta

from strands import tool

from tally import runtime
from tally.agents.gate import digest, new_question
from tally.engine.claim import claim_day, load_rates, lost_value, month_lines, rate_for
from tally.models import Claim, MealType, ParentNote


def rt():
    return runtime.get()


@tool
def close_the_day() -> dict:
    """Work out what today was worth, and what was lost.

    Applies the daily reimbursable maximum per child, so a day with three meals and two snacks is
    claimed as the best allowed combination rather than everything served. Meals that were corrected
    by a later photograph are counted once.
    """
    r = rt()
    on = r.now().date()
    provider = r.store.get_provider()
    superseded = r.store.superseded_ids()
    meals = [m for m in r.store.list_meals(on) if m.id not in superseded]

    served_by_child: dict[str, list[MealType]] = {}
    lost: list[tuple[MealType, int]] = []
    for m in meals:
        ok = bool(m.verdict and m.verdict.reimbursable)
        for cid in m.children_served:
            if ok:
                served_by_child.setdefault(cid, []).append(m.meal_type)
        if not ok and m.children_served:
            lost.append((m.meal_type, len(m.children_served)))

    days = [claim_day(v, provider.tier) for v in served_by_child.values()]
    total = round(sum(d.amount for d in days), 2)
    dropped = sum(len(d.dropped) for d in days)
    lost_amount = lost_value(lost, provider.tier)

    r.emit("day_closed", date=on.isoformat(), children=len(served_by_child), amount=total,
           over_daily_maximum=dropped, not_reimbursable=len(lost), lost_amount=lost_amount)
    return {
        "date": on.isoformat(),
        "children_fed": len(served_by_child),
        "amount": total,
        "dropped_over_daily_maximum": dropped,
        "not_reimbursable_meals": len(lost),
        "lost_amount": lost_amount,
    }


@tool
def build_month_claim(month: str = "") -> dict:
    """Build the month's claim from every reimbursable meal, ready to send to the sponsor.

    Args:
        month: YYYY-MM. Defaults to the current month.
    """
    r = rt()
    now = r.now()
    month = month or now.strftime("%Y-%m")
    provider = r.store.get_provider()
    superseded = r.store.superseded_ids()

    by_day: dict[date, dict[str, list[MealType]]] = {}
    lost: list[tuple[MealType, int]] = []
    for m in r.store.list_meals():
        if m.id in superseded or m.at.strftime("%Y-%m") != month:
            continue
        ok = bool(m.verdict and m.verdict.reimbursable)
        day = by_day.setdefault(m.at.date(), {})
        for cid in m.children_served:
            if ok:
                day.setdefault(cid, []).append(m.meal_type)
        if not ok and m.children_served:
            lost.append((m.meal_type, len(m.children_served)))

    days = [claim_day(v, provider.tier) for per_child in by_day.values() for v in per_child.values()]
    lines, total = month_lines(days, provider.tier)
    claim = Claim(provider_id=provider.id, month=month, lines=lines, total=total,
                  not_reimbursable=len(lost), lost_amount=lost_value(lost, provider.tier))
    r.store.put_claim(claim)
    r.emit("claim_built", month=month, total=total, lines=len(lines),
           not_reimbursable=claim.not_reimbursable, lost_amount=claim.lost_amount)
    return claim.model_dump(mode="json")


@tool
def draft_parent_notes() -> dict:
    """Draft one short note per child from what was actually logged today.

    The note is assembled from the record, not invented: the meals that child was served, any
    substitution, and whether they were present. Each family gets it in their own language.
    """
    r = rt()
    on = r.now().date()
    superseded = r.store.superseded_ids()
    meals = [m for m in r.store.list_meals(on) if m.id not in superseded]
    present = r.store.present_ids(on)

    drafted = []
    for cid in sorted(present):
        child = r.store.get_child(cid)
        eaten = []
        for m in meals:
            if cid not in m.children_served:
                continue
            items = m.substitutions.get(cid) or m.items
            foods = ", ".join(i.name for i in items[:4])
            if foods:
                eaten.append(f"{m.meal_type.value} of {foods}")
        if child.family_language == "es":
            body = (f"{child.first_name} comió: " + "; ".join(eaten) + "."
                    if eaten else f"{child.first_name} tuvo un buen día.")
        else:
            body = (f"{child.first_name} had " + "; ".join(eaten) + "."
                    if eaten else f"{child.first_name} had a good day.")
        note = ParentNote(child_id=cid, on=on, text=body, language=child.family_language)
        r.store.put_note(note)
        drafted.append({"child_id": cid, "name": child.first_name, "text": body,
                        "language": child.family_language})
    r.emit("notes_drafted", count=len(drafted))
    return {"notes": drafted}


@tool
def check_compliance() -> dict:
    """Find compliance items that are due or overdue, such as a fire drill or a training hour."""
    r = rt()
    today = r.now().date()
    due = []
    for item in r.store.list_compliance():
        if item.due < today:
            item.status = "overdue"
        elif item.due <= today + timedelta(days=14):
            item.status = "due"
        else:
            item.status = "ok"
        r.store.put_compliance(item)
        if item.status in ("due", "overdue"):
            due.append({"id": item.id, "label": item.label, "due": item.due.isoformat(),
                        "status": item.status})
    r.emit("compliance_checked", due=len(due))
    return {"due": due}


@tool
def reconcile_subsidy() -> dict:
    """Compare today's attendance with each subsidised child's authorised days.

    Since 2024 a home is paid for subsidised care only on days the child actually attended, so a day
    that does not match the authorisation has to be resolved before the claim goes out. This never
    interrupts her during the day; it becomes one question in the evening.
    """
    r = rt()
    now = r.now()
    on = now.date()
    provider = r.store.get_provider()
    mismatches = []
    for cid in sorted(r.store.present_ids(on)):
        child = r.store.get_child(cid)
        if not child.subsidized:
            continue
        if child.subsidy_days and on.weekday() not in child.subsidy_days:
            days = ", ".join(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d]
                             for d in child.subsidy_days)
            text = (f"{child.first_name} was here today, but the subsidy authorisation says "
                    f"{days}. Was {child.first_name} here?")
            q = new_question(provider.id, text, now, "reconciliation", options=["Yes", "No", "Not sure"])
            r.store.put_question(q)
            mismatches.append({"child_id": cid, "question_id": q.id, "text": text})
    r.emit("subsidy_reconciled", mismatches=len(mismatches))
    return {"mismatches": mismatches}


@tool
def build_digest() -> dict:
    """Assemble the evening digest: notes to approve, the questions worth her time, what waits."""
    r = rt()
    on = r.now().date()
    provider = r.store.get_provider()
    notes = r.store.list_notes(on)
    tonight, later = digest(r.store.list_questions(), provider.question_budget)
    compliance = [c for c in r.store.list_compliance() if c.status in ("due", "overdue")]

    spoken_parts = []
    if notes:
        spoken_parts.append(f"{len(notes)} notes ready")
    if tonight:
        spoken_parts.append(f"{len(tonight)} question" + ("s" if len(tonight) != 1 else ""))
    if compliance:
        spoken_parts.append(compliance[0].label.lower() + " due")
    line = ". ".join(spoken_parts) + "." if spoken_parts else "Nothing needs you tonight."

    r.emit("digest_built", notes=len(notes), questions=len(tonight), deferred=len(later),
           compliance=len(compliance))
    r.say(line, tone="ok")
    return {
        "notes": [{"child_id": n.child_id, "text": n.text, "language": n.language} for n in notes],
        "questions": [{"id": q.id, "text": q.text, "options": q.options, "priority": q.priority}
                      for q in tonight],
        "deferred": [{"id": q.id, "text": q.text} for q in later],
        "compliance": [{"id": c.id, "label": c.label, "status": c.status} for c in compliance],
        "spoken": line,
    }


@tool
def rates_in_force() -> dict:
    """The reimbursement rates the claim is being computed with, and where they came from."""
    rates = load_rates()
    provider = rt().store.get_provider()
    return {
        "version": rates["version"], "source": rates["source"], "tier": provider.tier,
        "per_meal": {m.value: rate_for(m, provider.tier)
                     for m in (MealType.BREAKFAST, MealType.LUNCH, MealType.SUPPER, MealType.SNACK)},
    }
