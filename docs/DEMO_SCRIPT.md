# Tally: demo video script

**Runs 4:15.** 511 spoken words at a comfortable 135 a minute, plus the 28 seconds of pauses the beats below ask for. The rules cap the video at five minutes.

Record from the deployed URL, clean browser profile, 1920 by 1080, light theme. **Press Reset before every take.**

Each beat gives three things: what to point at, what to do next, and the line to say. **Read only the quoted line out loud.** Everything else is a direction to you.

The timecodes are computed from the words plus those pauses, not estimated, so a beat that asks for six seconds of silence has six seconds in the clock. If a take runs long, cut a sentence rather than reading faster. The recording notes say which one to drop first.

---

## 0:00  The cold open

**Point at:** A kitchen at 7:38 am. A child's plate. A small hand reaching in. No interface yet.

**Then:** Hold on the plate. Do not show the product yet.

**Say:**

> Nine children before eight in the morning. Twelve by three in the afternoon. One adult, and she has no free hands.

## 0:11  The problem

**Point at:** The landing page. Let one stat card be readable, not all three.

**Then:** Scroll slowly. Do not stop on each card.

**Say:**

> Rosa runs a child care home. Most infants, and most parents working night shifts, are cared for in homes like hers, and half of those homes closed in twelve years. The reason providers give most often is the paperwork. Every meal, every child, every component, written down in order to be paid for, at nine at night, from memory.

## 0:38  What Tally is

**Point at:** The hero line.

**Then:** Click through to the demo. Press Reset if you have not already.

**Say:**

> Tally does the counting, hands free, for the one professional who cannot touch a screen.

## 0:47  Who is here

**Point at:** The Today tab. Press Say who is here.

**Then:** Let the sentence and the reply land, then press Mateo arrives. The line here already covers him, so do not stop for a separate one.

**Say:**

> She says who is here, in one sentence, out loud. That is attendance, the subsidy check, and the staffing ratio for the rest of the day. It hears the child who is off sick, and the one arriving at noon.

## 1:08  The plate

**Point at:** Press Breakfast. The components appearing as chips.

**Then:** Let the chips finish. Do not talk over what comes next.

**Say:**

> She photographs the plate. Amazon Bedrock vision names the foods and maps each one to a food program component.

## 1:19  The allergy

**Point at:** The red allergy line.

**Then:** This is the shot. Hold two full seconds of silence before you speak, and stay on it.

**Say:**

> Then this happens, and it is worth saying that nobody arranged it. The photograph really does contain peanut butter, and Leo really is allergic to peanuts. Every food is checked against every present child's allergies before a single thing is written down.

## 1:40  The missing milk

**Point at:** The breakfast verdict, missing milk.

**Then:** Press Add the milk. Let it turn green.

**Say:**

> It also notices the breakfast is short of milk, and says so while the bowl is still on the table. She adds milk, takes one more photograph, and it qualifies.

## 1:55  Why it matters

**Point at:** Press Lunch, then Add milk and fruit.

**Then:** Point at the smallest fix, not the prose.

**Say:**

> Last month a snack of Rosa's was rejected because the log said one component. There were two. She forgot to write the second one down, and by the time anyone noticed, the money was gone. That is the whole product. Fixing a meal at the table, instead of losing it at claim time when nothing can be done.

## 2:23  What it will not do

**Point at:** Press Afternoon snack. The yoghurt, not reimbursable. Point at the label check.

**Then:** Point at the confidence chip.

**Say:**

> The afternoon snack is yoghurt on its own, so it will not be paid. Tally also flags that yoghurt has a sugar limit a photograph cannot establish, and refuses to guess it. It never estimates a portion either, because the program pays on components, and that is the half of food vision that actually works.

## 2:49  The evening

**Point at:** Press Evening digest. Then the Evening tab.

**Then:** Point at the two questions.

**Say:**

> At half past six the day closes itself. A note home for each child in that family's language, the compliance clock checked, and exactly two questions put to her, because that budget is enforced in code. It will not spend one on something she already settled.

## 3:12  The sponsor

**Point at:** Navigate to /sponsor.html.

**Then:** Point at one meal, its photograph, and the rule version beside it.

**Say:**

> This is what her sponsor sees. Every meal, the photograph it was judged from, and the version of the rulebook that decided it, so a claim can still be defended years later.

## 3:30  Try it yourself

**Point at:** Navigate to /try.html, Try it with your own lunch. Then /start.html for a moment.

**Then:** Upload any food photograph and let a real verdict come back. Do not narrate the form. (4 seconds before you speak.)

**Say:**

> And none of this is a canned demo. Photograph your own lunch and it will judge that one, paste your own list of children to set up a home, or call the same API with the public sandbox key on the landing page.

## 3:51  What changed

**Point at:** The Month tab. Hold on the money.

**Then:** Hold here.

**Say:**

> Rosa did not spend her evening reconstructing the day. Tally logged every meal as it happened, caught the ones that would not have been paid, and asked her twice. One month, a hundred and one dollars she would have lost.

## 4:10  Close

**Point at:** Hold on the month.

**Then:** End the recording.

**Say:**

> Tally. So the paperwork is done before the food is cold.

---

## Recording notes

- Play the eight steps in one take and cut later.
- **The allergy is the shot.** Two full seconds of silence before you speak. It is the only moment a judge will still remember an hour later.
- If a take runs long, cut the label check in What it will not do, then the note home in The evening.
- Every button, tab and screen named above was checked against the live deployment.

## Before you upload

- Export near 4:15. Anything under four minutes is comfortable.
- Upload to YouTube as **public**, then open it in a logged-out window and confirm it plays.
- Captions in `video/` are timed to an earlier, longer script. Regenerate them from the final cut.
- The recorded visual tracks are from 5 September, before the interface fixes. Record fresh rather than narrating over them, or the video will not match the site a judge opens.

## Why each beat is here

Rules.md scores five equally weighted criteria, and says judges may judge on the video alone. So this is not a Presentation exhibit: it may be the only evidence a judge ever sees, for all five. If a beat is not doing one of these jobs, cut it.

| Beat | What it is carrying |
|---|---|
| 0:11 The problem | Potential Impact. The problem, who it is for, and what it costs her |
| 1:19 The allergy | Creativity and Impact. The beat nobody forgets |
| 1:55 Why it matters | Potential Impact. A real thing that happened, where it explains the feature |
| 2:23 What it will not do | Creativity. An agent defined by what it declines to do |
| 2:49 The evening | The hackathon's own theme. The smallest possible interruption |
| 3:12 The sponsor | Design. A complete product, including the organisation that pays the claim |
| 3:30 Try it yourself | Technical Implementation. Proof it is live, and an invitation to test it |
| 3:51 What changed | Presentation. The change stated once, plainly, before the tagline |
