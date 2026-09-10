# Tally: the shooting script

This is the one to record from. `DEMO_AND_VIDEO.md` section 4 is the longer reference version,
written while the system was being built; it carries more detail than a judge can absorb at speed.

**Target 3:40. Hard cap 5:00 by the rules.** About 500 words at a comfortable 140 a minute, which
leaves room to breathe. Reading faster to fit more in is the most common way a good demo goes wrong.

## Why it is shaped this way

Rules.md, line 549: **judges are not required to test the project and may judge on the video alone.**
So this is not a Presentation exhibit. It is the only evidence for all five criteria, and every beat
below is doing one of those jobs.

Rules.md also asks the pitch to cover three things by name: **the problem, who it is for, and why it
matters.** Those are the first 36 seconds, said plainly, before any feature appears.

Three changes from the earlier draft, all because a judge is watching a lot of these:

- **The product is on screen at 50 seconds, not 1:08.** The old open spent 30 seconds on statistics
  before anything ran.
- **The allergy catch is the moment this project wins on.** It now has the room it deserves, and the
  line that makes it land, which is that nobody arranged it, is said out loud.
- **One number carries the close.** A month of meals is worth 101 dollars and 76 cents at the table
  that is lost at claim time. That is the whole argument in one figure a provider would feel.

---

## The script

Press **Reset** before recording. Light theme. 1920 by 1080, clean browser profile.

| Time | Point at | Click next | Say |
|---|---|---|---|
| 0:00 | A kitchen at 7:38 am. A child's plate. A small hand reaching in. No UI yet. | Hold on the plate. | **Nine children before eight in the morning. Twelve by three in the afternoon. One adult, and she has no free hands.** |
| 0:12 | The landing page, the three stat cards. Let the sources be readable. | Scroll slowly across them. | **Rosa runs a child care home. Most infants, most rural families, and most parents working night shifts are looked after in homes like hers. Half of those homes closed in twelve years, and the reason providers give most often is the paperwork.** |
| 0:30 | Hold on the third card. | Then the hero line. | **Every meal, every child, every component, written down in order to be paid for. Usually at nine at night, from memory. Last month a snack was rejected because the log said one component. There were two. She forgot to write the second one down.** |
| 0:48 | The hero: "She feeds twelve kids and files paperwork for every bite." | Click through to the demo. | **Tally is a hands-free agent for the one professional who cannot touch a screen.** |
| 0:56 | The **Today** tab. Press **Say who is here**. | Let the sentence and the reply land, then press **Mateo arrives**. The narration below already covers him, so do not stop for a separate line. | **She says who is here, in one sentence, out loud. That is attendance, the subsidy check, and the staffing ratio for the rest of the day. It hears the child who is off sick and the one arriving at noon.** |
| 1:14 | Press **Breakfast**. The components appearing as chips. | Let the chips finish. **Do not talk over the next moment.** | **She photographs the plate. Amazon Bedrock vision names the foods and maps each one to a food program component.** |
| 1:26 | The red allergy line. **This is the shot. Hold it for a full two seconds before speaking.** | Stay on it. | **Then this happens, and it is worth saying that nobody arranged it. The photograph really does contain peanut butter, and Leo really is allergic to peanuts. Every food is checked against every present child's allergies before a single thing is written down.** |
| 1:48 | The breakfast verdict: missing milk. | Press **Add the milk**. Let it turn green. | **It also notices the breakfast is short of milk, and says so while the bowl is still on the table. She adds milk, takes one more photograph, and it qualifies. The first record is replaced, not doubled.** |
| 2:06 | Press **Lunch**, then **Add milk and fruit**. | Point at the smallest fix, not the prose. | **That is the whole product. The difference between fixing a meal at the table, and losing it at claim time when nothing can be done about it. And the fix is computed, not written by a model, so it only ever names food she actually has.** |
| 2:26 | Press **Afternoon snack**. The yoghurt, not reimbursable. Point at the label check. | Point at the confidence chip. | **The afternoon snack is yoghurt on its own, so it will not be paid. Tally also flags that yoghurt has a sugar limit a photograph cannot establish, and refuses to guess it. It never estimates a portion either, because the program pays on components, and that is the half of food vision that actually works.** |
| 2:48 | Press **Evening digest**. Then the **Evening** tab. | Point at the two questions. | **At half past six a Strands Graph closes the day. It drafts a note home for each child in that family's language, checks the compliance clock, and puts exactly two questions to her, because that budget is enforced in code. It will not spend one on something she already settled, because those answers are held in AgentCore Memory.** |
| 3:10 | Navigate to **/sponsor.html**. | Point at one meal, its photograph, and the rule version. | **This is what her sponsor sees. Every meal, the photograph it was judged from, and the version of the rulebook that decided it, so a claim can still be defended years later. That same rulebook is published over MCP, so the sponsor's own agent can check a claim without having to trust ours.** |
| 3:30 | The **Month** tab. Hold on the money. | End. | **One month. A hundred and one dollars of meals caught at the table instead of lost at the claim. Tally. So the paperwork is done before the food is cold.** |

---

## What each beat is scoring

Say this to yourself while editing. If a beat is not doing one of these, cut it.

| Beat | Criterion it is for |
|---|---|
| 0:00 to 0:48 | Potential Impact. The problem, who it is for, why it matters, in that order |
| 1:26 the allergy | Creativity and Originality, and Impact. This is the beat nobody forgets |
| 2:06 the smallest fix | Technical Implementation. Computed rather than generated, and it says why |
| 2:26 the refusal | Creativity. An agent defined by what it declines to do |
| 2:48 two questions | Technical Implementation. A budget kept in code, plus Memory doing real work |
| 3:10 sponsor page | Design. A complete product, including the organisation that pays the claim |

## Recording checklist

- Reset first, then play the eight steps in one take and cut later.
- **The allergy line at 1:26 is the shot.** Two full seconds of silence on it before you speak.
  It is the only moment in either video that a judge will still remember an hour later.
- Do not read faster to fit more in. Cut a sentence instead. The two candidates are the label check
  at 2:26 and the note home at 2:48.
- Export between 3:30 and 4:00. Upload to YouTube as **public**, then verify playback logged out.
- Captions: `video/tally.srt` is timed to the earlier script. Re-run `make_captions.py` after the
  final cut rather than trusting the old timings.
