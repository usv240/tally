# Tally: UX Specification

Screen-by-screen and line-by-line. Follows `DESIGN_SYSTEM.md` sections 9 to 16. Spoken lines are final copy and are also shown as text.

---

## 1. Users and contexts

| User | Context | Device | Hands | Design consequence |
|---|---|---|---|---|
| Provider | Kitchen, play room, yard; children present; noise | Phone, often propped on a counter; sometimes a tablet on the wall | Rarely free | Voice and camera first. Two big buttons. Everything else spoken. |
| Assistant | Afternoons | Same device | Sometimes free | Same screens, limited rights (no claim submission). |
| Sponsor reviewer | Office | Desktop | Free | Read-only month view with photos and rule checks. |
| Parent | Evening | Phone | Free | Receives a short note by SMS or email in their language. |
| Judge | Five minutes | Laptop or phone | Free | `/judges` page and Judge mode. |

---

## 2. Home screen (`/app`)

Purpose: the provider's whole day happens here.

Layout, phone:

1. Status line, 20 px: "Today: 3 meals logged, all qualify. 9 here." Amber variant: "Lunch needs a fruit." Red variant: "Nia: dairy allergy, yogurt on plate."
2. Two buttons, each 96 px tall, full width, stacked: "Photograph the plate" and "Say who is here." Both are also triggered by the phone's volume buttons when the app is open, for one-handed use.
3. Ratio dot with text: "9 of 12. At 3:10, 12 of 12." Tap for the rule.
4. Quiet meter: "Asked you 1 question today. Budget 2." InfoTip.
5. Today strip: meals as small cards with a green or amber badge and time.
6. Bottom bar: Today, Evening, Month, More.

Layout, tablet on the wall: same, two columns, buttons on the left, strip on the right.

---

## 3. Capture flow: photograph the plate

1. Camera opens with a plate-shaped framing guide and the line "Frame the plate. Faces are blurred automatically."
2. Shutter is a 72 px button; the volume button also works.
3. Immediately after capture: earcon (two-note), then spoken "Reading the plate" with a text progress line "Usually under 5 seconds."
4. Verdict card appears and is spoken.

### 3.1 Verdict card anatomy

```
Snack, 10:15                                     [green circle] QUALIFIES
Crackers (grain)  Apple (fruit)  Milk (milk)
Logged for 6 children present.                    [Undo 10:00]
[ Right ]  [ Wrong ]  [ Re-take ]
```

Amber:

```
Lunch, 12:10                                  [amber triangle] NEEDS A FRUIT
Chicken (meat)  Rice (grain)  Green beans (vegetable)  Milk (milk)
Add a fruit and lunch qualifies. You have oranges.   [i]
[ Added oranges, re-take ]  [ Log as is (not reimbursable) ]  [ Wrong ]
```

InfoTip on the fix: "Lunch requires milk, a fruit, a vegetable, a grain, and a meat or meat alternate for children 1 to 12. Rule version 2026-09."

Spoken lines:

- Qualifies: "Snack logged for six. Crackers, apple, milk."
- Needs fix: "Lunch needs a fruit to qualify. You have oranges."
- After fix: "Lunch logged for six. Qualifies."

### 3.2 The question pattern

When an item is below the confidence threshold, no verdict is shown yet. Earcon (single low tone), then:

```
Is that milk or juice?
[ Milk ]   [ Juice ]   [ Something else ]
```

Spoken: "Is that milk or juice?" The provider may answer by voice or tap. After the answer the verdict card appears. The trace records "asked because confidence 0.61 on item 3."

### 3.3 The allergy alert

Before any write. Triple earcon, red status line, spoken: "Nia has a dairy allergy. Yogurt is on the plate." Card:

```
[red octagon] ALLERGY: Nia, dairy. Yogurt on the plate.
What is Nia having?
[ Say it ]   [ Nia is not eating this ]   [ Nia is not here ]
```

The meal is logged only after the answer, with Nia's substitute recorded.

---

## 4. Roll call flow: say who is here

1. Press and hold "Say who is here." Waveform shows. Release to send.
2. Earcon, then the echo card and spoken echo.

Echo card:

```
Here: Maya, Leo, Mateo (8:00)
Absent: Ava (sick)
9 of 12 now. 12 of 12 at 3:10, within limits.
[ Right ]  [ Fix ]
```

Spoken: "Maya here, Leo here, Mateo at eight, Ava absent sick. You will be at your maximum of twelve at three ten."

Corrections by voice: "No, Leo's not here yet" updates one line and speaks "Leo not here yet." Corrections by tap: "Fix" opens a list of children with three chips each: Here, Absent, Later.

Subsidy reconciliation is never asked at the door. It waits for the evening digest.

---

## 5. Evening digest (`/app/evening`), 18:30

Purpose: approve, do not type.

Sections in order:

1. Notes to parents: six cards, each under 60 words, in the family's language, with "Send all" at the top and "Edit by voice" on each. Example: "Leo had oatmeal, crackers with apple, chicken and rice with oranges, and yogurt. Napped 1:00 to 2:30. Painted a blue house."
2. Questions, at most two: "Mateo was here Monday but is authorized Tuesday to Friday. Was he here Monday?" Buttons: Yes, No, Not sure. InfoTip explains attendance-based billing.
3. Compliance: "Fire drill due this month." Button: "Done today" logs a timestamp. "Remind me Friday."
4. Summary line: "Today: 4 meals, all qualify. Month so far: 112 meals, 2 not reimbursable."

Spoken on open: "Six notes ready. One question. Fire drill due."

---

## 6. Month review (`/app/month`)

- Calendar grid with a small badge per day: number of meals and a green or amber mark.
- Tap a day to see meals with photos and verdicts.
- Claim panel: total, line breakdown by meal type and tier, "computed as code" InfoTip, export preview in sponsor format.
- "Send to sponsor" opens a confirmation stating the total, that photos are included, and the sponsor's name. Then a 4-second success with Undo.

---

## 7. Sponsor view (`/sponsor/{provider}`), read-only

Desktop-first. The month grid, each meal with photo, components, verdict, rule version, and the question log. Filter by "not reimbursable" and "asked a question." Download the export. No edit rights.

---

## 8. Settings (`/app/more`)

Global controls (G17), each with an InfoTip:

- Nap time (no speech during this window).
- Question budget per day (default 2).
- Language (English, Spanish) for speech and for notes per family.
- Camera framing guide on or off.
- Assistant account.
- Pause Tally (banner everywhere).
- Data: export everything, delete everything.
- Rules version and effective date, with "what changed."

---

## 9. Onboarding (`/start`)

Under three minutes, voice-first, with "Load the sample home" on step one.

1. State and license type: two radio cards lists.
2. Children: press to talk, say "Maya, born March 3, 2025." Card appears; add allergies and subsidized days by chips. Repeat.
3. Sponsor: name and email for exports.
4. Finish: "I will speak after each plate and each roll call. In the evening I will have the notes ready. I will ask you at most two questions a day."

---

## 10. States

- Empty home: "Add your first child by saying their name and birthday." Big talk button.
- Loading after photo: "Reading the plate, usually under 5 seconds."
- Low confidence: the question pattern, never a guess.
- Offline: "Saved. Will check the rules when back online." Badge "queued" on the meal card; the meal is never lost.
- Model unavailable: "Photo saved for review. I will check it as soon as I can." No block.
- Success: green line, earcon, spoken confirmation, Undo for 10 minutes.

---

## 11. Microcopy table

| Situation | Text and spoken line |
|---|---|
| All good | Today: 3 meals logged, all qualify. |
| Needs fix | Lunch needs a fruit to qualify. You have oranges. |
| Uncertain item | Is that milk or juice? |
| Allergy | Nia has a dairy allergy. Yogurt is on the plate. |
| Ratio ahead | You will be at your maximum of twelve at three ten. |
| Notes ready | Six notes ready. One question. |
| Claim sent | Sent to Hill Country Child Nutrition. 412 dollars and 60 cents. Undo |
| Paused | Tally is paused. Nothing will be logged or spoken. Resume |

---

## 12. Accessibility and physical constraints

- Both primary buttons are reachable with a thumb on a 6-inch phone held in one hand, and also mapped to the volume keys.
- Spoken output is never the only channel; text mirrors it. Text is never the only channel for questions; the earcon and speech mirror it.
- 18 px base, 20 px status line, 48 px targets, no sliders or dropdowns.
- The framing guide and face blur run on device so a provider does not have to think about privacy.
- Spanish speech and text are equal citizens, not a translation layer added later.
