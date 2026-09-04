"""Tools for the live day: photograph a plate, take the roll, answer a question.

These are the functions the Day Orchestrator calls. Each returns a typed result and records what
happened, so the trace shows the vision reading, the rule verdict and the decision whether to ask.
"""

from __future__ import annotations

import uuid
from datetime import date

from strands import tool

from tally import runtime
from tally.agents.gate import may_ask_now, new_question
from tally.agents.plate import meal_type_for_time, read_plate
from tally.agents.roll import apply_correction, echo, parse_roll
from tally.engine.ratio import check_ratio
from tally.engine.rules import DayContext, allergy_conflicts, check_meal
from tally.models import AgeGroup, Component, Item, Meal, MealType


def rt():
    return runtime.get()


def _day_context(on: date) -> DayContext:
    r = rt()
    superseded = r.store.superseded_ids()
    meals = [m for m in r.store.list_meals(on) if m.id not in superseded]
    juice = any(i.component == Component.JUICE for m in meals for i in m.items)
    whole_grain = any("whole grain" in i.name.lower() or "whole wheat" in i.name.lower()
                      for m in meals for i in m.items)
    return DayContext(juice_already_counted=juice, whole_grain_rich_served=whole_grain)


def _age_groups_present(on: date) -> set:
    r = rt()
    present = r.store.present_ids(on)
    return {r.store.get_child(cid).age_group(on) for cid in present}


@tool
def log_plate(image_path: str, meal_type: str = "", replaces: str = "",
              age_groups: str = "") -> dict:
    """Read a photograph of a plate and decide whether it is a reimbursable meal.

    Identifies the foods, maps them to CACFP components, checks the meal pattern for every age group
    at the table, checks allergies for every child present, and returns the smallest change that
    would make the meal qualify if it does not.

    Args:
        image_path: path to the photograph.
        meal_type: breakfast, lunch, supper or snack. Inferred from the time of day if omitted.
        replaces: the id of an earlier meal this photograph corrects, after a component was added.
        age_groups: comma separated age groups such as "1-2,3-5", for judging a photograph when
            nobody is signed in. Defaults to whoever is actually present.
    """
    r = rt()
    now = r.now()
    on = now.date()
    provider = r.store.get_provider()

    reading = read_plate(image_path, vocabulary=r.store.vocabulary)
    r.emit("plate_read", image=image_path,
           items=[{"name": i.name, "component": i.component.value, "confidence": i.confidence}
                  for i in reading.items],
           questions=reading.questions)

    mt = MealType(meal_type) if meal_type else (reading.meal_type_guess or meal_type_for_time(now.hour))
    present = sorted(r.store.present_ids(on))
    if age_groups.strip():
        groups = {AgeGroup(g.strip()) for g in age_groups.split(",") if g.strip()}
    else:
        groups = _age_groups_present(on)

    # Safety runs before anything is written.
    allergies = {cid: r.store.get_child(cid).allergies for cid in present}
    conflicts = allergy_conflicts(reading.items, allergies)
    for cid, foods in conflicts.items():
        child = r.store.get_child(cid)
        text = (f"{child.first_name} has a {', '.join(child.allergies)} allergy. "
                f"{foods[0].capitalize()} is on the plate. What is {child.first_name} having?")
        q = new_question(provider.id, text, now, "safety",
                         options=["Say it", f"{child.first_name} is not eating this",
                                  f"{child.first_name} is not here"])
        r.store.put_question(q)
        r.emit("allergy_alert", child=cid, foods=foods, question_id=q.id)
        r.say(text, tone="alert")

    verdict = check_meal(reading.items, mt, groups, _day_context(on), pantry=None)
    meal = Meal(id=f"meal-{uuid.uuid4().hex[:8]}", provider_id=provider.id, at=now, meal_type=mt,
                photo_key=image_path, items=reading.items, verdict=verdict,
                children_served=present, replaces=replaces or None)
    r.store.put_meal(meal)
    r.emit("meal_logged", meal_id=meal.id, meal_type=mt.value, reimbursable=verdict.reimbursable,
           rule_version=verdict.rule_version, replaces=meal.replaces,
           children=len(present), missing=[m.value for m in verdict.missing])

    # One question at the table, only when the answer changes what she can do about it.
    if reading.questions:
        allowed, why = may_ask_now("meal", r.store.questions_asked_today(on), provider.question_budget)
        q = new_question(provider.id, reading.questions[0], now, "meal")
        r.store.put_question(q)
        r.emit("question", priority="meal", asked_now=allowed, why=why, text=q.text)
        if allowed:
            r.say(reading.questions[0], tone="ask")
    elif verdict.reimbursable:
        names = ", ".join(i.name for i in reading.items[:4])
        r.say(f"{mt.value.capitalize()} logged for {len(present)}. {names}.", tone="ok")
    else:
        r.say(verdict.smallest_fix or verdict.explanation, tone="fix")

    return {
        "meal_id": meal.id,
        "meal_type": mt.value,
        "items": [{"name": i.name, "component": i.component.value, "confidence": i.confidence}
                  for i in reading.items],
        "reimbursable": verdict.reimbursable,
        "missing": [m.value for m in verdict.missing],
        "smallest_fix": verdict.smallest_fix,
        "explanation": verdict.explanation,
        "flags": verdict.flags,
        "label_checks": verdict.label_checks,
        "rule_version": verdict.rule_version,
        "questions": reading.questions,
        "allergy_conflicts": conflicts,
        "children_served": present,
    }


@tool
def take_roll(spoken_text: str) -> dict:
    """Record who is here from a spoken roll call, and check the ratio for the rest of the day.

    Understands names, absences with a reason, later arrivals with a time, and corrections that
    start with "no". Reports any name it did not recognise rather than guessing.

    Args:
        spoken_text: what the provider said.
    """
    r = rt()
    now = r.now()
    on = now.date()
    provider = r.store.get_provider()
    children = r.store.list_children()

    existing = r.store.list_attendance(on)
    events, unknown = parse_roll(spoken_text, children, now)
    if existing and not events:
        events = apply_correction(spoken_text, existing, children, now)
    elif existing:
        merged = apply_correction(spoken_text, existing, children, now)
        if merged is not existing:
            events = merged
    r.store.add_attendance(on, events)

    ratio = check_ratio(r.store.present_ids(on), children, provider.state, provider.license_type,
                        now, absent_ids=r.store.absent_ids(on))
    line = echo(events, children)
    if ratio.next_change_at and not ratio.next_change_ok:
        line += f" You would be over your limit of {ratio.limit} at " \
                f"{ratio.next_change_at.hour % 12 or 12}:{ratio.next_change_at.minute:02d}."
    elif ratio.next_change_at:
        line += f" You will be at {ratio.next_change_count} of {ratio.limit} at " \
                f"{ratio.next_change_at.hour % 12 or 12}:{ratio.next_change_at.minute:02d}."
    if unknown:
        line += f" I did not recognise {', '.join(unknown)}."

    r.emit("roll_taken", events=[{"child": e.child_id, "event": e.event} for e in events],
           unknown=unknown, ratio=ratio.explanation)
    r.say(line, tone="ok")
    return {
        "events": [{"child_id": e.child_id, "event": e.event, "at": e.at.isoformat(), "note": e.note}
                   for e in events],
        "unrecognised": unknown,
        "ratio": ratio.model_dump(mode="json"),
        "spoken": line,
    }


@tool
def record_substitution(meal_id: str, child_id: str, food: str, component: str) -> dict:
    """Record that one child had something different, usually because of an allergy.

    Args:
        meal_id: the meal.
        child_id: the child.
        food: what that child actually had, in the provider's words.
        component: the CACFP component it satisfies.
    """
    r = rt()
    meal = r.store.get_meal(meal_id)
    item = Item(name=food, component=Component(component), confidence=1.0, note="provider stated")
    meal.substitutions[child_id] = [item]
    r.store.put_meal(meal)
    r.emit("substitution", meal_id=meal_id, child=child_id, food=food, component=component)
    child = r.store.get_child(child_id)
    r.say(f"Logged. {child.first_name} had {food}.", tone="ok")
    return {"meal_id": meal_id, "child_id": child_id, "food": food, "component": component}


@tool
def answer_open_question(question_id: str, answer: str) -> dict:
    """Record the provider's answer to a question Tally asked.

    Args:
        question_id: the question.
        answer: what she said.
    """
    r = rt()
    q = r.store.answer_question(question_id, answer)
    r.emit("question_answered", question_id=question_id, answer=answer, priority=q.priority)
    return {"question_id": question_id, "answer": answer, "priority": q.priority}


@tool
def today_so_far() -> dict:
    """A summary of today: who is here, what has been logged, and what still needs her."""
    r = rt()
    on = r.now().date()
    superseded = r.store.superseded_ids()
    meals = [m for m in r.store.list_meals(on) if m.id not in superseded]
    return {
        "present": sorted(r.store.present_ids(on)),
        "absent": sorted(r.store.absent_ids(on)),
        "meals": [{"id": m.id, "type": m.meal_type.value,
                   "reimbursable": bool(m.verdict and m.verdict.reimbursable)} for m in meals],
        "open_questions": [{"id": q.id, "text": q.text, "priority": q.priority}
                           for q in r.store.list_questions()],
    }
