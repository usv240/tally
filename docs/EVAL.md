# Evaluation results

Generated 2026-09-04 14:32 UTC by `python -m evals.vision_eval`.

## Plate reading

Each photograph in `data/plates` is a real photograph under an open licence, credited in
`data/plates/ATTRIBUTION.md`. What a person sees in each was written down before the model
ran. Recall is the share of those components the agent found. Spurious counts components it
reported that a person would not credit, not counting the extras noted per photograph.

**Mean component recall: 100.0% across 13 photographs, 2 trial(s) each. Spurious components: 0.**

| Photograph | Expected components | Recall | Spurious | Asked a question | What it is |
|---|---|---|---|---|---|
| `lunch_tray` | fruit, grain, meat_alt, milk, vegetable | 100% | 0 | 2/2 | USDA MyPlate school lunch tray. Every component is present. |
| `chicken_rice_veg` | grain, meat_alt, vegetable | 100% | 0 | 0/2 | Grilled chicken with rice and vegetables. No milk and no fruit. |
| `school_lunch_fi` | grain, vegetable | 100% | 0 | 2/2 | Finnish school lunch: soup and crispbread. The soup may read as containing meat. |
| `milk` | milk | 100% | 0 | 2/2 | A glass of milk. |
| `yogurt` | meat_alt | 100% | 0 | 2/2 | Yoghurt in a bowl. Yoghurt is a meat alternate under CACFP. |
| `banana` | fruit | 100% | 0 | 0/2 | A banana. |
| `oatmeal` | grain | 100% | 0 | 2/2 | Porridge with toppings, so raisins and nut butter may also be seen. |
| `crackers` | grain | 100% | 0 | 0/2 | A wholewheat cracker. |
| `orange_slices` | fruit | 100% | 0 | 0/2 | A blood orange slice. |
| `pear` | fruit | 100% | 0 | 0/2 | Pears. |
| `green_beans` | vegetable | 100% | 0 | 2/2 | Green beans with onions, both vegetables. |
| `oatmeal_with_milk` | grain, milk | 100% | 0 | 2/2 | Composite: the breakfast after the milk was added. |
| `chicken_rice_veg_fixed` | fruit, grain, meat_alt, milk, vegetable | 100% | 0 | 0/2 | Composite: the lunch after milk and fruit were added. |

Asking a question is not a failure. Below a confidence threshold the agent leaves the item
out of the record and asks the provider instead, because guessing a component into
compliance would create a false claim.

## Deterministic logic

The meal pattern, ratio and claim maths are exact and covered by unit tests rather than an
eval. Run `pytest -q`.
