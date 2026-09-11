# Tally: Technical Design

Python 3.12, Strands Agents SDK (Python), Amazon Bedrock (multimodal), Amazon Transcribe, Amazon Bedrock AgentCore, AWS CDK. This document is complete enough to build from.

---

## 1. Architecture overview

```
   +-----------------------------------------------------------+
   |  Provider PWA (Next.js, Amplify)                          |
   |  camera capture, push-to-talk, spoken replies, offline    |
   |  queue, evening digest, month review                      |
   +----------------------------+------------------------------+
                                |  HTTPS, Cognito (provider) or API key
   +----------------------------v------------------------------+
   |  API Gateway (REST + WebSocket) + Lambda, usage plans, WAF|
   +------+----------------------+-----------------------------+
          |                      |
   +------v-----------+   +------v----------------------------+
   | Amazon Transcribe|   | AgentCore Runtime: Day Orchestrator|
   | streaming (voice)|   |  Strands Agent, agents as tools:   |
   +------------------+   |  Plate, Rules, Roll, Provider Gate |
                          +---+-------+--------+---------------+
                              |       |        |
              +---------------+       |        +------------------+
              |                       |                           |
   +----------v---------+  +----------v-----------+  +------------v-----------+
   | AgentCore Memory   |  | AgentCore Gateway    |  | AgentCore Code         |
   | per provider:      |  | MCP tools:           |  | Interpreter:           |
   | children, allergies|  |  records (DDB)       |  |  claim_math.py         |
   | subsidy schedules, |  |  cacfp_rules (JSON)  |  |  ratio_math.py         |
   | provider's food    |  |  state_licensing     |  +------------------------+
   | vocabulary         |  |  sponsor_export      |
   +--------------------+  |  sms_email (parents) |  +------------------------+
                           +----------------------+  | AgentCore Identity     |
                                                     |  provider, sponsor     |
   +------------------------------------------------++------------------------+
   | AgentCore Runtime: Nightly Graph (EventBridge 18:30 local)              |
   |  Ledger -> Parent Notes -> Compliance Clock -> Provider Gate (digest)   |
   +-------------------------------------------------------------------------+

   DynamoDB (single table)   S3 (plate photos, exports)   AgentCore Observability -> CloudWatch
```

---

## 2. Strands patterns used, and why each

| Pattern | Where | Why |
|---|---|---|
| Orchestrator `Agent` with agents-as-tools | The live day: the Day Orchestrator receives a photo or an utterance and calls Plate, Rules, Roll, or Provider Gate as tools | During the day, inputs arrive one at a time and each needs a fast, bounded response. Agents-as-tools keeps latency low and the reasoning shallow. |
| `GraphBuilder` graph | Nightly: Ledger to Parent Notes to Compliance Clock to Provider Gate | The evening run is a fixed pipeline whose outputs feed each other. Deterministic order, auditable. |
| Hooks | All agents | `BeforeToolInvocation` blocks any write of a meal marked non-reimbursable as reimbursable; `AfterModelInvocation` logs the rule version used. An allergy hook fires a spoken alert before any meal write. |
| Structured output | Plate, Roll, Rules, Ledger | Pydantic models for components, attendance events, rule verdicts, and claim lines. |
| Conversation manager | Day Orchestrator | Sliding window so a full day of interactions fits; Memory holds the durable facts. |
| Session persistence with AgentCore Memory | Day Orchestrator and Nightly Graph | Child profiles and the provider's own food vocabulary ("the usual crackers" resolves to a whole grain-rich cracker she uses) persist across days. |

This is deliberately a different Strands shape from Turnout (agents-as-tools plus a nightly Graph, versus a conditional Graph plus A2A), so the two submissions demonstrate breadth of the SDK.

---

## 3. The agents

### 3.1 Day Orchestrator

**Not in the shipped build.** The deployed day path calls one tool per event directly from
the API, and `log_plate` runs the Plate agent below. `day_agent` exists in `agents/graph.py`
and nothing calls it. The orchestrator described here is the design, not the running system.

- Input: one event: `{type: photo|utterance|tap, payload, timestamp, provider_id}`.
- Behavior: classifies the event (a photo is a meal unless the provider said otherwise; an utterance is attendance, a meal statement, a correction, a note for a parent, or a question), calls the right tool agent, and returns a short spoken response under 20 words plus a structured record. Never asks more than one question per event.

### 3.2 Plate

- Input: image, meal type (inferred from time of day and confirmed by the provider's schedule in Memory), present children's age groups.
- Model: Bedrock multimodal (Claude Sonnet-class primary, Nova Pro fallback).
- Output: `PlateReading { items: [{name, cacfp_category, confidence, notes}], meal_type_guess, needs_clarification: [{item, question}] }`.
- Rules for the prompt: identify only what is visible; map each item to a CACFP category (milk, fruit, vegetable, grain, meat_alt, none); return confidence; if a beige liquid could be milk or juice, ask; never infer quantities.
- Memory use: the provider's vocabulary map. If she says "the usual crackers," Plate resolves it.
- Eval: five demo plates times 20 trials; a 60-photo held-out set.

### 3.3 Rules

- Input: `PlateReading`, meal type, age groups present, date.
- Logic: deterministic, in code, against a versioned `cacfp_rules.json` derived from the USDA meal pattern tables. Checks the required components for the meal type and age group, the juice limit (once per day, and not for infants), the whole grain-rich requirement (at least one grain per day must be whole grain-rich), breakfast cereal and yogurt sugar limits (flagged as "verify label" since we cannot read grams from a plate), fluid milk type by age, and infant meal patterns separately.
- Output: `Verdict { reimbursable: bool, missing: [category], smallest_fix: string, flags: [string], rule_version }`.
- The smallest fix is computed, not guessed: the single component addition that makes the meal qualify, preferring items in the provider's own vocabulary.
- State licensing: a `state_rules.json` with ratio and group size tables by state and license type (Texas registered and licensed homes for the demo), used by Roll.

### 3.4 Roll

- Input: transcript from Transcribe streaming, current roster, time.
- Output: `AttendanceEvents [{child_id, event: arrive|depart|absent|late, time, note}]`, plus `RatioCheck { now_ok, next_change_time, next_change_ok, explanation }`.
- Handles names phonetically against the roster, handles "Ava's mom said she's sick" as an absence with a reason, handles corrections ("no, Leo's not here yet"), and confirms in one sentence.
- Subsidy reconciliation: compares today's attendance with each subsidized child's authorized schedule and queues a Provider Gate question only if they differ.
- Ratio lookahead: uses the enrolled schedule to predict the after-school arrival and warns in the morning if the afternoon will exceed ratio.

### 3.5 Ledger (nightly)

- Computes the day's meal counts per child per meal type, splits by age group and by subsidy tier, accumulates the month, and computes the claim using `claim_math.py` in Code Interpreter with the current reimbursement rates table (versioned).
- Produces the sponsor export in a KidKare-compatible column layout and a human-readable month view with photos attached.

### 3.6 Parent Notes (nightly)

- For each child present, drafts a note under 60 words from the day's utterances tagged with that child's name (meals, nap if mentioned, activity if mentioned, any incident). Tone: warm, factual. The provider approves the batch with one tap or edits any note by voice.
- Sends by SMS or email through Gateway. Spanish output when the family's language preference is Spanish.

### 3.7 Compliance Clock (nightly)

- Tracks fire drill (monthly), training hours (annual target), license renewal, background check renewals, CPR and first aid expiry, and each child's immunization record due dates.
- Nudges appear in the evening digest with a one-tap "done" that logs the completion with a timestamp.

### 3.8 Provider Gate

- The only agent that can ask the provider anything. Maintains a queue with priority: safety (allergy conflict) immediately; compliance blockers (meal will not qualify) at the moment of the meal; reconciliation questions in the evening digest; everything else in the weekly summary.
- Budget: at most two spoken questions during the day outside of meal moments. Enforced in code.

---

## 4. Deterministic logic

### 4.1 Meal pattern check

Encoded as data, not prose. Excerpt of `cacfp_rules.json` structure:

```
{
  "version": "2026-09",
  "age_groups": ["1-2", "3-5", "6-12", "13-18"],
  "meals": {
    "breakfast": { "required": ["milk", "fruit_or_vegetable", "grain"], "notes": ["meat_alt may replace grain up to 3 times per week"] },
    "lunch":     { "required": ["milk", "fruit", "vegetable", "grain", "meat_alt"] },
    "supper":    { "required": ["milk", "fruit", "vegetable", "grain", "meat_alt"] },
    "snack":     { "required_any_two_of": ["milk", "fruit", "vegetable", "grain", "meat_alt"], "not_both": [["fruit_juice", "milk_as_only_other"]] }
  },
  "daily": { "whole_grain_rich_min": 1, "juice_max_per_day": 1 },
  "infants": { ... separate structure ... }
}
```

Tests: 150 labeled meals across age groups and meal types, including edge cases (juice as the only fruit at snack with milk, cereal flagged for sugar, infant meals).

### 4.2 Ratio lookahead

Input: state rule table, present children with birth dates, enrolled schedule for the rest of the day. Output: whether the current and each upcoming state is within ratio and group size, with the time of the first violation if any. Exact computation, tested on 40 scenarios.

### 4.3 Claim math

Per child per day: count of reimbursable meals by type, capped at the program's daily maximum (two meals and one snack, or one meal and two snacks), multiplied by the tier rate for the provider's tier and the child's eligibility. Month total, with a line-by-line breakdown. Exact match against a hand-computed demo month is a test.

---

## 5. Voice pipeline

- Push-to-talk in the PWA streams audio to Amazon Transcribe streaming through a WebSocket Lambda. Partial results are shown; the final transcript goes to the Day Orchestrator.
- Custom vocabulary includes the roster's first names and the provider's food vocabulary from Memory, which measurably improves name recognition.
- Spoken responses use Amazon Polly (neural voice) so the provider never has to look at the screen. Text is always shown as well.
- Spanish: Transcribe `es-US` and Polly Spanish voice, selected per provider.

---

## 6. AgentCore mapping, with the reason for each

| Service | Use | Why it is the right primitive |
|---|---|---|
| Runtime | Two runtimes: Day Orchestrator (request-driven) and Nightly Graph (scheduled) | Managed hosting with isolation per provider session; the nightly run is a long job |
| Memory | Child profiles, allergies, subsidy schedules, provider vocabulary, family language preferences | Durable facts the agent must recall every day without re-asking |
| Gateway | Records, CACFP rules, state licensing tables, sponsor export, parent messaging as MCP tools | Rules are data behind a tool so they can be versioned and updated without redeploying agents |
| Identity | Provider login; sponsor read-only access; outbound credentials for messaging | Two roles with different rights over the same data |
| Code Interpreter | Claim math, ratio math, month report rendering | Money and safety math must run as code with logged inputs and outputs |
| Observability | Traces for every day event and every nightly run; the judge's Trace Viewer | Shows the vision reading, the rule verdict, and the question decision for any meal |

---

## 7. Data model

DynamoDB single table `Tally`, pk and sk, GSI for date ranges.

| Entity | pk | sk | Key attributes |
|---|---|---|---|
| Provider | `PROV#<id>` | `META` | name, state, license_type, tier, language, sponsor_id, schedule, quiet_hours |
| Child | `PROV#<id>` | `CHILD#<id>` | first_name, birth_date, age_group (derived), enrolled_days, arrival_time, subsidy {authorized_days, hours}, allergies[], family_contact, family_language |
| Attendance | `PROV#<id>` | `ATT#<date>#<child_id>` | events[], present_minutes, subsidy_match |
| Meal | `PROV#<id>` | `MEAL#<date>#<meal_type>#<seq>` | photo_s3, items[], verdict, rule_version, children_served[], fixed_from_seq |
| ClaimMonth | `PROV#<id>` | `CLAIM#<yyyy-mm>` | lines[], total, export_s3, status, submitted_at |
| Note | `PROV#<id>` | `NOTE#<date>#<child_id>` | text, language, approved, sent_at |
| ComplianceItem | `PROV#<id>` | `COMP#<type>` | due_date, last_done, status |
| Question | `PROV#<id>` | `Q#<timestamp>` | text, priority, answered, answer |

S3 `tally-artifacts`: plate photos (face-blurred client-side), exports. Lifecycle 13 months to cover audit windows.

---

## 8. Public API

Base `https://api.tally.example/v1`, `x-api-key` via API Gateway usage plans, sandbox key on the developer page scoped to the demo provider.

| Method | Path | Purpose |
|---|---|---|
| POST | `/providers` | Create provider with state and license type |
| POST | `/providers/{id}/children` | Add or update children |
| POST | `/providers/{id}/meals` | Multipart image plus optional meal type; returns items, verdict, smallest fix |
| POST | `/providers/{id}/attendance` | Audio or text; returns attendance events and ratio check |
| GET | `/providers/{id}/days/{date}` | The day's records with photos and verdicts |
| GET | `/providers/{id}/claims/{yyyy-mm}` | Claim lines, total, export link |
| POST | `/providers/{id}/claims/{yyyy-mm}/submit` | Marks submitted; sends export to sponsor |
| GET | `/providers/{id}/compliance` | Upcoming compliance items |
| GET | `/rules/cacfp?version=` | The rules data, for transparency |
| GET | `/providers/{id}/traces/{traceId}` | Trace summary |

OpenAPI 3.1 at `/openapi.json`. Sandbox rate limit 60 per minute.

---

## 9. Provider PWA

Next.js 15, PWA with service worker, installable on Android and iOS, deployed on Amplify.

Screens:

| Route | Purpose |
|---|---|
| `/` | Landing page |
| `/demo` | Judge mode: loads Rosa's home on the demo day; "Play the day" |
| `/app` | The provider's home screen: a big camera button, a big talk button, today's meals as a strip with green or amber badges, the current ratio as a small indicator |
| `/app/meal/{id}` | Photo, items, verdict, the fix suggestion, "Re-take" |
| `/app/day` | Today's attendance and meals |
| `/app/evening` | The digest: notes to approve, questions to answer, compliance nudges |
| `/app/month` | Month review with photos, claim total, "Send to sponsor" |
| `/sponsor/{provider}` | Read-only sponsor view (Could) |
| `/developers`, `/judges`, `/references` | As in the design system |

Offline: photos and audio are queued in IndexedDB and sent when connectivity returns; the badge shows "queued." Camera framing guide keeps the plate centered; a client-side face detector blurs any face before upload.

---

## 10. Infrastructure and deployment

CDK stacks: `Data`, `Agents` (two runtimes, Memory, Gateway, Identity), `Voice` (Transcribe and Polly permissions, WebSocket), `Api`, `Web`, `Ops` (EventBridge nightly at 18:30 provider-local, health check, budgets). Secrets in Secrets Manager. Health check posts to a status page. Budget alarms at 30 and 45 dollars.

---

## 11. Testing and evaluation

| Layer | Method |
|---|---|
| Rules engine | 150 labeled meals; 100 percent expected |
| Ratio lookahead | 40 scenarios; 100 percent expected |
| Claim math | Demo month hand-computed; exact match |
| Plate | 5 plates times 20 trials; 60-photo held-out set; report per-category precision and recall |
| Roll | 100 utterances with names, absences, corrections, Spanish subset; report accuracy |
| Hooks | Tests proving a non-reimbursable meal cannot be written as reimbursable, and that an allergy conflict blocks the write and emits an alert |
| Provider Gate budget | Tests proving at most two non-meal questions per day |
| Web | Playwright in light and dark, 360 px and 1280 px; axe-core |

Results in `docs/EVAL.md`, linked from the README.

---

## 12. Repository layout

```
tally/
  README.md, LICENSE (MIT)
  docs/ architecture.png, architecture-dark.png, EVAL.md, LATER.md, SAFETY.md, RULES_SOURCES.md
  agents/
    day/ orchestrator.py, plate.py, rules.py, roll.py, provider_gate.py, hooks.py, prompts/, models.py
    nightly/ graph.py, ledger.py, parent_notes.py, compliance_clock.py
    tools/ records.py, cacfp_rules.py, state_rules.py, sponsor_export.py, messaging.py
    code_interpreter/ claim_math.py, ratio_math.py, month_report.py
  rules/ cacfp_rules.json, state_rules.json, rates.json (all versioned)
  infra/  api/  web/
  data/ generate.py, scenarios/demo_day.json, plates/ (the five photos)
  tests/  evals/  .github/workflows/ci.yml
```

---

## 13. Sequence: the demo day, end to end

1. 07:40 Rosa says "Maya's here, Leo's here, Ava's mom said she's sick, Mateo's coming at 8." Roll logs three arrivals, one absence with reason, one expected. Ratio now fine; lookahead warns that at 15:10, when two school-age children arrive, group size will hit the licensed maximum but remain within ratio. Spoken: "Got it. Ava absent, sick. You will be at your maximum of 12 at 3:10."
2. 08:05 Photo: milk, banana, oatmeal. Plate reads three items at high confidence. Rules: breakfast qualifies for all age groups present. Spoken: "Breakfast logged for five. Milk, banana, oatmeal. All qualify."
3. 10:15 Photo: crackers and apple slices, with a beige cup. Plate: crackers (grain, 0.96), apple (fruit, 0.98), cup (uncertain). Provider Gate asks: "Is that milk or juice?" Rosa: "Milk." Rules: snack qualifies with grain and milk. Spoken: "Snack logged. Crackers, apple, milk."
4. 12:10 Photo: chicken, rice, green beans, milk, no fruit. Rules: lunch missing fruit. Spoken: "Lunch needs a fruit to qualify. You have oranges." Rosa adds orange slices, photographs again. Rules: qualifies. The record links the fix to the first photo.
5. 12:12 Allergy hook: Leo's profile lists a peanut allergy; nothing on the plate matches; no alert. (The test suite includes the positive case.)
6. 15:10 Two school-age children arrive; Roll logs them; group size 12, within Texas limits for a licensed home with an assistant present. Spoken confirmation.
7. 18:30 Nightly Graph. Ledger computes the day and month to date. Parent Notes drafts six notes. Compliance Clock notes the September fire drill is not logged. Provider Gate builds the digest: "Six notes ready. One question: Mateo was here Monday but his subsidy says Tuesday through Friday, was he here? Fire drill due this month."
8. 18:35 Rosa approves the notes with one tap, answers the question by voice, taps "drill done." Notes go out.
9. Month end: the claim is computed, matches the hand calculation, exports in the sponsor's format. Rosa taps send at 6:05 pm.
10. The Trace Viewer shows every event with the vision reading, the verdict, the rule version, and the decision whether to ask.
