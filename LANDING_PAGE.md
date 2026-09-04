# Tally: Landing Page Specification

Follows `../DESIGN_SYSTEM.md`. Final copy. InfoTip text is given inline as `[i: ...]`.

Accent: deep green (`#0F6E56` light, `#4FC79E` dark). Hero imagery: a kitchen table with a child's plate (apple slices, crackers, a cup of milk), photographed from above, warm light. In dark mode, the same table in evening light.

---

## Header

Wordmark "Tally". Menu: Live demo, How it works, For judges, Developers, References. Theme toggle. "Try the live demo" button.

---

## Section 1: Hero

Heading (h1): **She feeds twelve kids and files paperwork for every bite. Tally does the counting.**

Subheading: A hands-free agent for home child care providers. Photograph the plate, say who is here, and every meal, attendance record, ratio check, parent note, and monthly claim is done, correctly, before the food is cold.

Buttons: "Try the live demo", "Watch the 4-minute video".

Looping recording (12 seconds): a phone photographs a snack plate; the screen shows "Crackers, apple. Add milk and this qualifies"; a cup of milk is placed; a second photo; a green badge "Snack logged for six."

Credibility line: "97,000 licensed family child care homes closed in twelve years [i: HHS Office of Child Care. Licensed family child care homes fell 52 percent from 2005 to 2017. Reference 1.] · Paperwork is the number one barrier named by state agencies [i: American Journal of Public Health, 2023. Reference 2.] · Runs on Amazon Bedrock AgentCore [i: AgentCore hosts, secures, and observes the agents.]"

---

## Section 2: The problem

Heading: **The paperwork happens at 9 pm, and that is why it goes wrong.**

Intro: A licensed family child care provider cares for 4 to 12 children in her own home [i: Family child care, or FCC, is licensed or registered care in the provider's residence. It is the most common form of care for infants, rural families, and parents working nonstandard hours.]. To be paid for the meals she serves, she must log every meal for every child by component under the federal food program [i: The Child and Adult Care Food Program, CACFP, reimburses providers for meals that meet USDA meal patterns. A meal is reimbursable only if the required components are documented.]. Since 2024 she must also document actual daily attendance for every subsidized child [i: The 2024 federal child care subsidy rule requires attendance-based billing, replacing enrollment-based billing in many states.]. She does this after the last child goes home.

Three stat cards:

1. **52 percent gone.** Licensed family child care homes fell by half between 2005 and 2017. [i: Reference 1.]
2. **80 percent of states.** Name burdensome paperwork as the top barrier to food program participation. [i: Reference 2.]
3. **Evening work.** Researchers found meal documentation "frequently becomes evening responsibilities" for home providers. [i: Reference 3.]

Story block: Rosa runs a licensed home in Texas with nine children on a normal day and twelve after school. Last month a snack was rejected because the log did not show a second component. It had one. She forgot to write it down at 9:40 pm.

Money line: A lunch is reimbursed at 3.31 dollars per child at Tier I this year. One lunch a day that fails the log for six children is 436.92 dollars gone in a month. [i: 2026-2027 USDA day care home rates: breakfast 1.74, lunch or supper 3.31, snack 0.98 dollars per child. Six children, 22 serving days. Reference 10.]

Timeliness line: On August 19, 2026, the National CACFP Association published a report titled "Stretched Thin: The Administrative Burden of the CACFP in Family Child Care Homes." [i: Reference 4.] We built Tally for the problem that report describes.

---

## Section 3: How it works

Heading: **Her hands are full. So there is nothing to type.**

Four steps:

1. **Say who is here.** "Maya's here, Leo's here, Ava's mom said she's sick." Attendance, subsidy attestation, and ratio check, done. [i: The Roll agent turns speech into attendance events, reconciles them with each subsidized child's authorized schedule, and predicts whether the afternoon arrivals will exceed the state ratio.]
2. **Photograph the plate.** The agent identifies the components and checks the meal pattern for every age group present. [i: The Plate agent uses Amazon Bedrock vision to identify foods and map them to CACFP categories: milk, fruit, vegetable, grain, meat and meat alternate. The Rules agent then applies the USDA meal pattern as versioned data.]
3. **Fix it while it is on the table.** "Add a fruit and lunch qualifies." Not a rejection next month. [i: The Rules agent computes the smallest change that makes the meal reimbursable, using foods the provider already uses.]
4. **Evening: approve, do not type.** Parent notes are drafted from what she said. The claim builds itself. One question, if any. [i: The Provider Gate agent is the only agent allowed to ask her anything, and it is limited to two questions a day outside meal moments. That limit is enforced in code.]

Two smaller cards:

- **When it is unsure, it asks.** "Is that milk or juice?" It never guesses a component into compliance. [i: Each identified item carries a confidence score. Below a threshold, the agent asks a single question instead of logging.]
- **Allergies are checked before anything is logged.** [i: A hook compares every identified component against the allergies of every child present and speaks an alert before the meal is recorded.]

---

## Section 4: See it happen

Heading: **Play the day.**

Embedded demo in Judge mode: "You are Rosa. Press Play the day." The demo advances through the six moments (roll call, breakfast, snack with the question, lunch with the fix, afternoon arrivals, evening digest) with a speed control, and ends on the month view with "Send to sponsor."

Tabs: Provider app, Evening digest, Month review, Trace Viewer. Each with a screenshot in the current theme and an InfoTip.

---

## Section 5: What makes it different

Heading: **Three things no child care app does.**

1. **It works without hands.** Camera and voice. Large buttons for the moments a hand is free. Everything else is spoken. Existing tools are forms; forms get filled at 9 pm.
2. **It checks the rule before the meal ends.** Reimbursability is decided at the table, with the smallest fix spoken aloud, not discovered at claim time when it is unfixable.
3. **It uses the half of food vision that works.** Models are good at naming foods and poor at estimating grams. The food program only needs components. We do not estimate portions, and we say so. [i: Reference 8 evaluates vision-language models on food recognition, about 88 percent, versus nutrient estimation, which remains imprecise.]

Honest comparison block, heading "What about KidKare and the others?":

KidKare is the food program standard, used by tens of thousands of providers, and its claim edit checks are thorough. brightwheel, Playground, and Procare run centers well. All of them are typed. Tally is the first tool designed for a provider who cannot touch a screen, and it exports in a KidKare-compatible format so a sponsor can accept its records today.

---

## Section 6: Built on Strands Agents and AgentCore

Heading: **Seven agents. One question a day.**

Interactive diagram with InfoTips:

- Day Orchestrator [i: A Strands agent that receives each photo or utterance and calls the right specialist agent as a tool. Fast and bounded, because the provider is waiting with a plate in her hand.]
- Plate, Rules, Roll, Provider Gate [i: one sentence each]
- Nightly Graph [i: A Strands Graph that runs Ledger, Parent Notes, Compliance Clock, and the evening digest in a fixed, auditable order.]
- AgentCore Runtime [i: Hosts the day agent and the nightly job with isolation per provider.]
- AgentCore Memory [i: Remembers each child, allergies, subsidy schedules, and the provider's own names for foods, so "the usual crackers" resolves correctly.]
- AgentCore Gateway [i: Serves the food program rules, state licensing tables, records, and parent messaging as tools, so rules can be updated without redeploying agents.]
- AgentCore Identity [i: Separate rights for the provider and for a sponsor with read-only access.]
- AgentCore Code Interpreter [i: Runs the claim math and ratio math as code with logged inputs and outputs.]
- AgentCore Observability [i: Records the vision reading, the verdict, the rule version, and the question decision for every meal.]

---

## Section 7: For judges

Heading: **Everything the rubric asks for, in one place.**

| Criterion | Evidence |
|---|---|
| Technical Implementation | Repo · Live demo · Trace Viewer · Eval results (rules 150 meals, plates 100 trials, voice 100 utterances) · CDK · AgentCore services used |
| Design | Landing page · Provider app in judge mode · Evening digest · Light and dark · Mobile-first · Accessibility report |
| Potential Impact | The problem section · References including the August 2026 sector report · The demo day |
| Creativity and Originality | No-hands design · Fix-at-the-table · The deliberate choice of component identification over portion estimation · Positioning against existing tools |
| Presentation | The video · Transcript · Architecture diagram |

Blog posts on builder.aws.com: three links. License: MIT, visible in About.

---

## Section 8: For developers

Heading: **Send a photo, get a compliant record.**

Quickstart: clone, `make demo`, open localhost. Sandbox key with copy button. Examples: POST a meal photo and receive items and verdict; POST an attendance utterance; GET the month's claim. Link to OpenAPI. Link to `/rules/cacfp` so anyone can inspect the rules data. [i on rules endpoint: The exact meal pattern data the agent uses, with its version. Sponsors can verify it against USDA tables.]

---

## Section 9: Safety and limits

Heading: **What it will never do.**

- It never photographs children. The camera guide frames the plate, and any face is blurred on the device before upload.
- It never submits a claim by itself. The provider reviews the month and presses send.
- It never guesses a missing component into compliance. When unsure, it asks.
- It never estimates portions or calories. It identifies components, which is what the food program requires.
- It never asks more than two questions a day outside meal moments.
- Everything can be exported or deleted in one tap. The data is hers.

---

## Section 10: References

1. HHS Administration for Children and Families, Office of Child Care, "The Decreasing Number of Family Child Care Providers in the United States."
2. "Barriers to Participation in the Child and Adult Care Food Program for Early Childhood Care Providers," American Journal of Public Health, 2023.
3. "The Child and Adult Care Food Program (CACFP): Nutritional Benefits and Barriers Hindering Participation by Home-Based Childcare Providers," PMC, 2023.
4. National CACFP Association, "Stretched Thin: The Administrative Burden of the CACFP in Family Child Care Homes," August 19, 2026.
5. USDA Food and Nutrition Administration, "Report to Congress: Reducing Paperwork in the Child and Adult Care Food Program."
6. USDA Food and Nutrition Administration, "Nutrition Standards for CACFP Meals and Snacks."
7. 2024 CCDF final rule on attendance-based subsidy billing (as summarized in subsidy management guidance).
8. "A comparative study of vision-language models for food ingredient recognition and nutrient estimation," 2026.
9. Texas Health and Human Services, minimum standards for licensed and registered child care homes (ratio and group size tables).
10. USDA Federal Register, Day Care Home Food Service Payment Rates, July 1, 2026 through June 30, 2027; summarized by KidKare and the National CACFP Association.
11. Strands Agents SDK documentation. 12. Amazon Bedrock AgentCore documentation.

---

## Footer

MIT License · GitHub · Contact · Theme toggle · "Built for the AWS Agents for Humans Hackathon, September 2026. Rosa's Family Child Care and all children are fictional; all data is synthetic."
