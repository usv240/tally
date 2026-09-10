# Tally: Demo Data, Judge Walkthrough, and Video Script

Rewritten after the system was built, so every line matches what it actually does. Where the plan
and the running system disagreed, the system won. The most interesting case is in section 2: the
allergy alert in the demo was never scripted. It happened because the photograph really does contain
peanut butter and Leo really is allergic to peanuts.

---

## 1. The demo home

`src/tally/data/generate.py`, committed as `data/demo_day.json`.

**Rosa's Family Child Care**, a licensed child care home in Texas, tier 1, sponsored by Hill Country
Child Nutrition. Fictional, as is every child.

| Child | Age group | Days | Subsidised | Allergy | Notes home |
|---|---|---|---|---|---|
| Maya | 1 to 2 | Mon to Fri | yes | | English |
| Leo | 3 to 5 | Mon to Fri | yes | **peanut** | Spanish |
| Ava | 3 to 5 | Mon to Fri | no | | English |
| Mateo | 3 to 5 | Mon to Fri | yes, Tue to Fri | | Spanish |
| Nia | 1 to 2 | Mon, Wed, Fri | yes | **dairy** | English |
| Sam | 3 to 5 | Mon to Fri | no | | English |
| Eli | infant | Mon to Thu | yes | | English |
| Priya | 6 to 12 | after school | no | | English |
| Jordan | 6 to 12 | after school | yes | | English |

The day is **Tuesday 8 September 2026**. Nia comes Monday, Wednesday and Friday, so she is not in.
Eli is an infant, which is why Tally records his meals and explicitly declines to judge them against
the child meal pattern.

### The photographs

Real photographs under open licences from Wikimedia Commons, fetched by
`python -m tally.data.fetch_plates` and credited in `data/plates/ATTRIBUTION.md`. Testing food
recognition against drawings would prove nothing.

Two images, `oatmeal_with_milk` and `chicken_rice_veg_fixed`, are composites of those photographs
laid side by side by `make_plates.py`, standing in for the second photograph a provider takes after
adding a missing component. There is no openly licensed photograph of exactly that, and the
attribution says so plainly.

---

## 2. What actually happens when you press the steps

A transcript of a real run.

| Step | What the system does |
|---|---|
| **Say who is here** (07:38) | "Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at 8." Two arrivals, one absence with its reason, one expected arrival with a time. Tally answers: "Maya, Leo here. Mateo at 8:00. Ava absent sick." |
| **Mateo arrives** (08:02) | "Mateo's here now, and Sam and Eli are here." Five children present. The ratio look ahead updates. |
| **Breakfast** (08:05) | The porridge photograph. Vision reads oatmeal, peanut butter and raisins. **The allergy check fires before anything is written**: Leo is allergic to peanuts. It also asks whether the pale liquid is milk, because that changes the verdict. Missing milk, so: not reimbursable. |
| **Add the milk** (08:09) | The composite photograph. Vision reads oatmeal, peanut butter, raisins and fluid milk. Breakfast now has milk, a grain and a fruit, so it qualifies. The first record is superseded rather than doubled. |
| **Lunch** (12:10) | Chicken, white rice, peas and carrots. Missing milk and fruit. Tally says out loud: "This lunch is short 2 components. Start with milk." |
| **Add milk and fruit** (12:16) | The composite. Chicken, rice, peas and carrots, milk, orange slice. Every required component. "Lunch logged for 5." |
| **Afternoon snack** (15:20) | Yoghurt. One component, and a snack needs two, so it will not be paid: "Add milk and this snack qualifies." It also raises a label check, because yoghurt has a sugar limit a photograph cannot establish. |
| **Evening digest** (18:30) | The Strands Graph runs. The day is closed and valued, five notes home are drafted in each family's language, compliance is checked, and the digest reports: "5 notes ready. 2 questions." |

### The moment nobody scripted

The plan said the allergy demonstration would be Nia and the yoghurt. Instead the porridge
photograph, chosen for the breakfast step, genuinely contains peanut butter, and Leo genuinely has a
peanut allergy in the roster. The check fired on the real reading of a real photograph.

That is a better demonstration than the scripted one, because it was not arranged. It is the moment
to point at in the video.

### What the month shows

The demo day plus six seeded earlier days give a claim of **161.98 dollars** for the month so far,
with **one meal that will not be paid**, worth **6.86 dollars**. Those numbers come from the
published 2026-2027 rates through the same arithmetic the tests check.

---

## 3. Judge walkthrough, about four minutes

1. Open the live URL, read the hero, press **Open the live demo**.
2. Press the eight steps in order, or press **Play the rest of the day** and watch it run itself.
   Vision calls take a few seconds each. A step that is not next is disabled: playing the evening
   before lunch would ask the agents to close a day that has not happened.
3. **Today**: every meal with its photograph, the components with the confidence behind each one,
   the verdict, the rule version, and any label check.
4. **What Tally said out loud**: the spoken log, colour coded. Red is a safety alert, amber is a
   meal that can still be fixed, blue is a question.
5. **Children**: allergies and subsidy status at a glance.
6. **Evening**: the questions, ranked, each explaining why it was asked now or held.
7. **Month**: the claim, the line breakdown at the published rates, and what the unpaid meal cost.
8. **Agent trace**: every step, including the decision whether to interrupt.
9. **The sponsor's month** (`/sponsor.html`): the same month from the other side of the desk. Every
   meal with the photograph it was judged from and the rulebook version that judged it, which is
   what makes a claim defensible to a state reviewer a year later.
10. **Set up your own home** (`/start.html`): paste any list of children, in any of the shapes
    people actually write one, and see what was understood plus a ratio check, before anything is
    saved. Lines it cannot read are shown, not dropped.

Try it with your own photograph:

```bash
curl -X POST <host>/api/meals -H "x-api-key: tally-sandbox-2026" \
  -F "photo=@your-lunch.jpg" -F "meal_type=lunch"
```

---

## 4. Video script, target 4:10, hard cap 4:30

> **Record from [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md), not from this section.**
>
> This one was written while the system was being built and carries more detail than a judge can
> absorb at speed. The shooting script is shorter, puts the product on screen inside the first
> minute, and says where to point and what to press at each beat. This section stays because it is
> the record of what the system actually does, which is what the shooting script was checked
> against.


| Time | Visual | Voiceover |
|---|---|---|
| 0:00 to 0:12 | A kitchen at 7:38 am. A child's plate. A small hand reaching in. Title: "Rosa's Family Child Care. Tuesday." | "Nine children before eight in the morning. Twelve by three. One adult." |
| 0:12 to 0:42 | The three stat cards, sources visible. | "Home child care is where most infants, most rural families and most parents working nights find care. Half of these homes closed in twelve years. The reason providers give most often is paperwork. Every meal, every child, every component, logged to be paid. And since 2024, every subsidised child's actual attendance, every day. All of it done at nine at night, by hand." |
| 0:42 to 0:58 | A binder. A form on a phone. A clock reading 9:40 pm. | "Last month a snack was rejected because the log showed one component. There were two. She forgot to write the second one down. Three weeks ago the national food program association published a report on exactly this, and called it Stretched Thin." |
| 0:58 to 1:08 | Title: "Tally. She feeds twelve kids and files paperwork for every bite. Tally does the counting." | "Tally is a hands-free agent for the one professional who cannot touch a screen." |
| 1:08 to 1:30 | Live: the roll call step. The sentence appears, then the spoken reply. | "She says who is here, in one sentence. Attendance, the subsidy check, and the ratio for the rest of the day. It hears the absence and the reason, and the child arriving later and when." |
| 1:30 to 2:05 | Live: the breakfast step. Components appear as chips with confidences. Then the red allergy line. | "She photographs the plate. Amazon Bedrock vision names the foods and maps each to a food program component. Then this happens, and it is worth saying that nobody arranged it: the photograph really does contain peanut butter, and Leo really is allergic to peanuts. Every food is checked against every present child's allergies before anything is written at all." |
| 2:05 to 2:25 | Live: the breakfast verdict, then the fixed photograph turning green. | "It also notices the breakfast is missing milk, and says so while the bowl is still on the table. She adds milk, photographs it again, and it qualifies. The first record is replaced, not doubled." |
| 2:25 to 2:50 | Live: lunch, amber. "This lunch is short 2 components. Start with milk." Then the fix, green. | "Lunch: chicken, rice, peas and carrots. Short milk and fruit. The fix is computed, not generated, from food she already has, and it is said out loud at ten past twelve. This is the whole product: the difference between fixing a meal at the table and losing it at claim time, when nothing can be done." |
| 2:50 to 3:10 | Live: the yoghurt snack. Not reimbursable, plus the label check. The confidence chip. | "The afternoon snack is yoghurt alone, and a snack needs two components, so it will not be paid. Tally also flags that yoghurt has a sugar limit a photograph cannot establish. It does not guess at that, and it never estimates a portion, because the food program pays on components and that is the half of food vision that actually works." |
| 3:10 to 3:35 | Live: the evening digest, then the Month tab. | "At half past six a Strands Graph closes the day, drafts a note home for every child in that family's language from what was actually logged, checks the compliance clock, and puts two questions to her. Two, because the budget is enforced in code. And it does not spend one on something she already settled: her answers are held in AgentCore Memory against the child and the weekday, which is what recurs. The month's claim is computed from the published rates, and it shows what the unpaid meal cost." |
| 3:35 to 3:45 | Live: the Agent trace. | "Every step is in the trace. A hundred and twenty three tests, and a vision eval at a hundred percent component recall over thirteen real photographs." |
| 3:45 to 3:58 | Live: `/sponsor.html`. The month's claim, then every meal beside the photograph it was judged from and the rulebook version that decided it. | "This is the same month a sponsor or a state reviewer reads. Every meal, the photograph it was judged from, and the rulebook version that decided it, so a claim can be defended years later." |
| 3:58 to 4:10 | Live: `/start.html`. A pasted list of children read back, birthdays parsed, the state ratio checked. | "And it is not built around one home. Paste any list of children and it checks the ratio before it saves. Tally. So the paperwork is done before the food is cold." |

About 610 words. The clip runs 3:50 against a 4:10 script, so `make_captions.py` scales the
timeline by 0.92. The sponsor and setup beats are new: the recording spends its last fifty
seconds on those two screens and the first draft of this script did not cover them at all.

---

## 5. Recording checklist

- Record from the deployed URL, clean profile, 1920 by 1080.
- Press Reset first. The eight steps in one take, cut later.
- The allergy moment at 1:30 is the shot. Hold on it.
- Captions checked against the audio. Export 4:10 to 4:30, public on YouTube, verified logged out.
