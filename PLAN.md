# Tally: Product Plan

## 1. The problem, precisely

### 1.1 Who is affected

Licensed and regulated family child care (FCC) providers: one adult, sometimes with an assistant, caring for 4 to 12 children in a private home. They are small-business owners, the group the Professional Agents track names explicitly. They serve infants through school-age children, often across a mix of subsidized and private-pay families, and they typically earn near minimum wage after expenses.

The people inside the problem:

- The provider. Cares for children from 6:30 am to 6 pm, then does paperwork. Every meal, every child, every component, every day. Every subsidized child's actual attendance. Fire drills, training hours, license renewal, background checks, incident reports, daily notes to every parent.
- The children. When the provider drops out of the food program because the paperwork is not worth it, they eat worse.
- The sponsor. A nonprofit organization that administers the food program for many home providers, audits their claims, and cannot afford to visit often.
- The parent. Night-shift nurse, warehouse worker, farm worker. Needs a provider who is still in business next month.

### 1.2 The evidence

| Fact | Source |
|---|---|
| The number of licensed family child care homes fell 52 percent between 2005 and 2017; more than 97,000 homes closed. Licensed FCC providers receiving subsidies declined 51 percent. | HHS Administration for Children and Families, Office of Child Care, "The Decreasing Number of Family Child Care Providers in the United States." https://acf.gov/occ/news/decreasing-number-family-child-care-providers-united-states |
| Almost 80 percent of state agencies name burdensome paperwork as the most frequent barrier to CACFP participation. Providers report penalties for paperwork mistakes and reimbursement that does not match the time required. | American Journal of Public Health, "Barriers to Participation in the Child and Adult Care Food Program for Early Childhood Care Providers," 2023. https://ajph.aphapublications.org/doi/10.2105/AJPH.2023.307473 |
| For home-based providers on CACFP, meal documentation and compliance "frequently become evening responsibilities," and menu planning takes weekends. | "The Child and Adult Care Food Program (CACFP): Nutritional Benefits and Barriers Hindering Participation by Home-Based Childcare Providers," PMC, 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10733890/ |
| The National CACFP Association published "Stretched Thin: The Administrative Burden of the CACFP in Family Child Care Homes" on August 19, 2026. | National CACFP Association. https://www.cacfp.org/2026/08/19/stretched-thin-the-administrative-burden-of-the-cacfp-in-family-child-care-homes/ |
| USDA's own Report to Congress on reducing CACFP paperwork documents the burden and the case for simplification. | USDA Food and Nutrition Administration, "Report to Congress: Reducing Paperwork in the Child and Adult Care Food Program." https://www.fna.usda.gov/research/cacfp/reducing-paperwork |
| In 2024, HHS closed a longstanding loophole and now requires providers to document actual attendance to be reimbursed for each day of subsidized care claimed. | CCDF 2024 final rule, as summarized in child care subsidy management guidance. https://childcarecomp.com/articles/business-and-finance/childcare-subsidy-management-software-comparison |
| CACFP meal patterns define reimbursable meals by component (milk, fruits, vegetables, grains, meat and meat alternates) by age group and meal type, with rules on juice limits, whole grain-rich requirements, and sugar limits. | USDA FNA, "Nutrition Standards for CACFP Meals and Snacks." https://www.fna.usda.gov/cacfp/nutrition-standards |
| Multimodal models identify foods in photos with roughly 88 percent recognition accuracy in recent evaluations; portion and macronutrient estimation remain imprecise. | "A comparative study of vision-language models for food ingredient recognition and nutrient estimation," 2026. https://www.sciencedirect.com/science/article/pii/S266592712600105X |
| 2026-2027 day care home reimbursement, Tier I: breakfast 1.74 dollars, lunch or supper 3.31 dollars, snack 0.98 dollars per child per meal. One lunch a day logged without a required component, for six children, over 22 serving days, is 436.92 dollars of lost reimbursement in a month. One snack a day is 129.36 dollars. | USDA Federal Register, Day Care Home Food Service Payment Rates, July 1, 2026 through June 30, 2027, as published by KidKare. https://www.kidkare.com/20262027-cacfp-reimbursement-rates/ and https://www.fna.usda.gov/cacfp/reimbursement-rates |

### 1.3 The mechanism we target

Providers lose money and drop out of programs not because they feed children badly but because documentation happens after the fact, by hand, on a screen, at night. Errors are discovered at claim time, when they are unfixable, and are penalized. The provider's hands are occupied all day, so any tool that needs typing is a tool used at 9 pm.

Tally moves documentation to the moment of the meal, takes it by camera and voice, checks rules before the meal is over, and lets the provider fix a missing component while the food is still on the table.

---

## 2. The product

### 2.1 One sentence

Tally is a hands-free agent that turns a photo of the plate and a spoken roll call into complete, compliant, claim-ready records, and interrupts the provider only for the one question only she can answer.

### 2.2 What the provider experiences

- Morning: she says "Maya's here, Leo's here, Ava's mom said she's sick." Attendance and subsidy attestation are done. If ratios will be exceeded when the after-school children arrive, she hears about it now.
- Breakfast: she photographs the plate. "Breakfast logged for six: milk, banana, oatmeal. All qualify."
- Snack: she photographs the plate. "Crackers and apple. Add milk or a second fruit or vegetable and this snack qualifies. Otherwise it will not be reimbursed." She adds milk. Photographs again. Done.
- Evening: each parent receives a note assembled from what she said during the day. She never typed it.
- Month end: the claim is ready in the sponsor's format. One tap to send. Zero evening paperwork.

### 2.3 What the sponsor experiences

- Claims arrive with photos attached to every meal and a rules-check record. Audit time drops. Errors are caught before submission, not after.

### 2.4 What is deliberately not there

- No forms to fill during the day. No typing. No menu that needs planning in advance. The agent builds the menu record from what was actually served.

---

## 3. Scope

### 3.1 In scope for the submission

| Feature | Description | Priority |
|---|---|---|
| Plate | Photo to components with per-component confidence; asks one clarifying question when unsure | Must |
| Rules | CACFP meal pattern check by meal type and age group; smallest fix suggestion; juice, whole grain-rich, sugar, and infant rules; state licensing ratios | Must |
| Roll | Voice attendance; handles absences, late arrivals, early pickups; subsidy schedule reconciliation; ratio check with lookahead | Must |
| Ledger | Daily meal counts by child and age group; monthly claim computation by tier; sponsor-format export (CSV matching KidKare import columns for interoperability) | Must |
| Parent Notes | Per-child daily note from the day's voice log; provider approves with one tap or edits by voice | Must |
| Compliance Clock | Fire drill log, training hours, license renewal, background check dates, immunization record reminders; deadline nudges | Must |
| Provider Gate | Exactly one question at a time; an evening digest of what was logged and what needs her | Must |
| Provider app (PWA) | Camera, mic, large buttons, one-handed; installable; works offline for capture and syncs later | Must |
| Landing page, docs, judge mode | Per `LANDING_PAGE.md` | Must |
| Public API with keys | Sponsors and software vendors can send photos and audio and receive structured records | Should |
| Multilingual voice | Spanish voice roll call and Spanish parent notes | Should |
| Sponsor view | Read-only view of a provider's month with photos and rule checks; completes the product story for a judge | Should |

### 3.2 Explicitly out of scope

- Billing parents or processing payments.
- Curriculum, learning assessments, or developmental screening.
- Portion size or calorie estimation. CACFP reimbursement is component-based; we deliberately do not estimate grams.
- Replacing the sponsor's claim system. We export into it.

---

## 4. Positioning against existing tools

| Tool | What it does | What it does not do | Our one-sentence answer |
|---|---|---|---|
| KidKare by Minute Menu | The CACFP incumbent: menus, meal counts, attendance, 250-plus claim edit checks, used by 85,000 sites and providers | Every meal is typed into a form; errors are found by edit checks at claim time | "KidKare is a form on a phone. Tally is the first tool that does not need her hands, and it fixes the meal while it is still on the table." |
| brightwheel, Playground, Procare, Lillio | Center-oriented management: attendance, billing, CACFP menus, ratio tracking | Designed for centers with a front desk; typing-based; CACFP is a module | "Those assume someone at a desk. Tally assumes a toddler on each hip." |
| Paper and a binder | What many home providers actually use | Everything | "This is the binder, filled in by a photo and a sentence." |

We export in KidKare-compatible format so a sponsor already using it can accept our records. That is a feature, not a concession.

---

## 5. Why it wins each criterion

| Criterion | How Tally reaches the ceiling |
|---|---|
| Technical Implementation | Strands agents-as-tools under an orchestrator for the live day, plus a nightly Strands Graph for the ledger, notes, and compliance run. Bedrock multimodal vision. Transcribe streaming for voice. AgentCore Runtime, Memory (child profiles, provider's own food vocabulary), Gateway (rules, licensing tables, sponsor export), Identity, Code Interpreter (claim math, ratio math), Observability. Live URL. CDK. Tests on the five demo plates and a 100-utterance voice eval. |
| Design | A product built around a physical constraint (no hands) and proven in the demo. Large targets, voice-first, camera-first, offline capture, evening digest. Light and dark. Mobile-first, desktop for the sponsor view. InfoTips everywhere. |
| Potential Impact | Eight cited sources including a federal report to Congress and a sector report published two weeks before the deadline. A demo that shows a snack becoming reimbursable and a month becoming a claim. |
| Creativity and Originality | Photo-to-federal-compliance, checked before the meal ends. A professional agent designed for someone who cannot use a screen. Choosing the component-identification half of food vision, where models are strong, and refusing the gram-estimation half, where they are weak, and saying so. |
| Presentation | A 4:10 video that opens on a kitchen at 7:40 am, follows one day, and ends with the monthly claim sending at 6:05 pm instead of 9:30 pm. |

---

## 6. Success criteria for the build

| Metric | Target |
|---|---|
| Component identification on the five demo plates, 20 trials each | 100 percent on unambiguous items; the ambiguous cup triggers a question every time |
| Component identification on a 60-photo held-out set of common child care foods | at least 90 percent |
| Rules engine on 150 labeled meals across age groups and meal types | 100 percent (deterministic) |
| Voice roll call parsing on 100 utterances including absences and corrections | at least 96 percent |
| Ratio lookahead correctness on 40 scenarios | 100 percent |
| Monthly claim equals hand-computed claim on the demo month | exact |
| Provider interrupts per day in the demo | at most 2 |
| Time from photo to spoken confirmation | under 6 seconds |
| Landing page Lighthouse | Performance 95, Accessibility 100 |

---

## 7. Safety, ethics, and trust

- Photos are of food, not faces. The app guides framing to the plate. Any detected face is blurred client-side before upload.
- Children's data is minimal: first name, birth date (for age group), enrolled days, subsidy schedule, allergies. No photos of children are stored.
- The agent never submits a claim on its own. The provider reviews the month and presses send.
- Rules are versioned. Each logged meal records the rule version used, so audits are reproducible.
- When the vision model is unsure, it asks. It never guesses a component into compliance.
- Allergy conflicts (a logged component matching a present child's allergy) trigger an immediate spoken alert. This is a safety feature, not a compliance feature, and it is explained as such.
- Data belongs to the provider. Export everything, delete everything, in one tap.

---

## 8. Naming and language

- Product name: Tally.
- Agent names use the words of a child care day: Plate, Rules, Roll, Ledger, Parent Notes, Compliance Clock, Provider Gate.
- Demo provider: Rosa's Family Child Care, a licensed home in Texas. Fictional. Texas is chosen because its ratio and group size rules for registered and licensed homes are public and specific.
- We never say "AI nutritionist." We say "meal logging."
