"""The Plate agent: a photograph of a plate becomes a list of CACFP components.

Two deliberate limits, both of which are the point rather than a shortcut.

First, it names foods and maps them to components. It does not estimate portions, weights or
calories. Recent evaluations of vision language models put food recognition around 88 percent while
portion and nutrient estimation remains imprecise, and the food program reimburses on components,
not grams. So Tally uses the half of the problem these models are good at, and says so.

Second, when it is not sure enough about an item, it asks one question rather than logging a guess.
Guessing a component into compliance would create a false claim, which is worse for the provider
than being asked whether the cup is milk or juice.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from strands import Agent

from tally.house import plain_all
from tally.models import Component, Item, MealType, PlateReading

ASK_BELOW = 0.75
"""Confidence below which the agent asks instead of logging. Chosen so a clearly identified food
goes straight through and an ambiguous one, such as a pale liquid in an opaque cup, is questioned."""

SYSTEM = """You identify food in a photograph for a child care food program record.

Return every distinct food you can see, and map each to exactly one CACFP component:

- milk: fluid milk of any kind
- fruit: whole or cut fruit, including canned or frozen fruit
- juice: 100 percent fruit or vegetable juice, which is a fruit but limited, so tag it as juice
- vegetable: any vegetable
- grain: bread, crackers, rice, pasta, tortilla, oatmeal, cereal
- meat_alt: meat, poultry, fish, eggs, beans, cheese, yogurt, nut butters, tofu
- none: anything that counts toward no component, such as water, condiments or a garnish

Rules you must follow:

1. Report only what is visible. Never infer a food because it usually accompanies another.
2. Never estimate portion size, weight, volume or calories. You are not asked for them.
3. Give each item a confidence between 0 and 1 for how certain you are of the identification.
4. If a food could plausibly be more than one thing in a way that changes its component, give it a
   low confidence and add a short question with the two most likely options. A pale liquid that
   could be milk or juice is the common case, and the two components are treated differently.
5. Use the plainest name a provider would use: "apple slices", not "sliced Malus domestica".
6. If the photograph shows no food at all, return no items.

Also guess the meal type from what is on the plate, if it is obvious."""


def _image_block(path: str | Path) -> dict:
    p = Path(path)
    data = p.read_bytes()
    mime, _ = mimetypes.guess_type(p.name)
    fmt = {"image/jpeg": "jpeg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}.get(
        mime or "", "jpeg")
    return {"image": {"format": fmt, "source": {"bytes": data}}}


def read_plate(image_path: str | Path, agent: Agent | None = None,
               vocabulary: dict[str, str] | None = None) -> PlateReading:
    """Identify the components on a plate.

    Args:
        image_path: the photograph.
        agent: an override, used by tests.
        vocabulary: the provider's own names for foods, learned over time, so that "the usual
            crackers" resolves to the whole grain-rich cracker she actually buys.
    """
    from tally.agents.models import vision_model

    prompt = SYSTEM
    if vocabulary:
        known = "; ".join(f"{k} is {v}" for k, v in sorted(vocabulary.items())[:20])
        prompt += f"\n\nFoods this provider serves regularly, for naming: {known}"

    agent = agent or Agent(name="Plate", model=vision_model(), system_prompt=prompt,
                           callback_handler=None)
    reading = agent(
        [_image_block(image_path), {"text": "Identify every food on this plate."}],
        structured_output_model=PlateReading,
    ).structured_output
    return apply_confidence_gate(reading)


def apply_confidence_gate(reading: PlateReading) -> PlateReading:
    """Move low confidence items out of the record and into a question.

    An item the model is unsure about is not logged at all. That is the difference between a record
    that survives an audit and one that does not.
    """
    kept: list[Item] = []
    questions = plain_all(list(reading.questions))
    for item in reading.items:
        if item.component == Component.NONE:
            continue
        if item.confidence < ASK_BELOW:
            question = item.note or f"Is the {item.name} milk or juice?"
            if question not in questions:
                questions.append(question)
            continue
        kept.append(item)
    return PlateReading(items=kept, meal_type_guess=reading.meal_type_guess, questions=questions)


def meal_type_for_time(hour: int) -> MealType:
    """A sensible default when the model cannot tell from the plate alone."""
    if hour < 10:
        return MealType.BREAKFAST
    if hour < 11:
        return MealType.SNACK
    if hour < 14:
        return MealType.LUNCH
    if hour < 16:
        return MealType.SNACK
    return MealType.SUPPER
