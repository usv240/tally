# Every Strands surface, and what Tally does with it

The judging criterion is "how thoroughly and skillfully does the project use Strands Agents". That
invites a certain kind of dishonesty, where you reach for every module in the SDK so the list looks
long. This is the list, including the parts deliberately left alone and why, because a feature used
without a reason is worse evidence of understanding than a feature rejected with one.

Strands Agents SDK 1.18.0. Every row was checked against the installed package, not the docs.

| Surface | Used | Where, or why not |
|---|---|---|
| `strands.Agent` | yes | Plate, Roll and Gate agents |
| `strands.tool` | yes | Every tool in `tools/`, typed and docstring-described |
| `strands.models.BedrockModel` | yes | Sonnet 4.6 for vision and reasoning, Haiku 4.5 for parsing |
| `strands.multiagent.GraphBuilder` | yes | `agents/graph.py`, conditional edges on the confidence gate |
| `strands.tools.mcp.MCPClient` | yes | `mcp/sponsor.py`, a reviewer's agent holding no Tally code |
| `strands.telemetry` | yes | `observability.py`, OTLP spans for AgentCore Observability |
| `strands.hooks` | no | See below |
| `strands.session` | no | See below |
| `strands.interrupt` | no | See below |
| `strands.experimental` | no | Explicitly unstable. Not in something a provider's income depends on |

## MCP, and why the rulebook is a server

Tally tells a provider her lunch is reimbursable. She is not the one who has to be convinced.

The sponsoring organisation signs the claim and carries the liability if a state reviewer disagrees,
and increasingly what reviews a claim on their side is an agent rather than a person with a browser.
So the same USDA meal pattern rules Tally judges with are published over the Model Context Protocol
by `mcp/server.py`, and `mcp/sponsor.py` is a Strands agent that consumes them.

That reviewer agent holds no Tally code at all. Its entire toolset is discovered at runtime over
stdio, so it knows what a lunch requires only because it asked, and every answer it gets carries the
rule version it came from. Point it at a different rulebook server and it reviews against those
rules instead, having changed nothing.

The server is read only by construction. Nothing it exposes can log a meal, change a rule or touch
a claim, and `tests/test_mcp_rulebook.py` asserts that no tool name begins with a writing verb. The
worst an untrusted caller can do is learn what the published federal tables say, which is public.

One test in that file matters more than the others. `test_the_verdict_matches_tally_own_engine_exactly`
runs five component combinations through the MCP boundary and through `engine/rules.py` directly,
and asserts the verdicts are identical. A reviewer who disagrees with the provider's software over
the same facts is the failure this whole design exists to prevent.

```
python -m tally.mcp.sponsor --check
```

Calls every tool over the real protocol, spawning the server as a subprocess. No model, so it costs
nothing and runs in CI.

## Telemetry, and the claim it had to back

`runtime.py` emits an event for every step an agent takes, and the web app renders those into a
readable story. That is the right thing for a provider looking back at a day. It is also our own
format, read by our own viewer, and it stops at the edge of this process.

Strands instruments itself with OpenTelemetry, so every agent invocation, model call and tool call
becomes a span with timings and token counts, including the path taken through the graph. AgentCore
Observability and CloudWatch both ingest OTLP directly.

It is off unless an endpoint is configured, and that is a decision rather than an oversight. The
submitted demo runs with no collector reachable. If tracing were on by default, every start would
spend its timeout failing to reach one. `/api/health` reports which state it is in, so the status
page cannot claim tracing that is not running.

```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318   send spans to a collector
TALLY_TRACE_CONSOLE=1                               print spans, no collector needed
```

## The three that were rejected, and the reason for each

**`strands.hooks`.** Turnout uses these to enforce contact policy in code rather than in the prompt,
which is the right use of them. Tally's equivalent guarantees are not tool-call-shaped. The
confidence gate is a graph edge, and the allergy check runs on every meal whether or not an agent
asked for it. Putting either behind a hook would move a guarantee from a place where it always runs
to a place where it runs when a model calls a tool.

**`strands.session`.** Session managers persist conversation state so an agent can resume a thread
after a restart. Tally has no threads. A photograph is one shot, and onboarding is rule-based
parsing with no model in it at all. What Tally does need to remember across days is a specific
thing, not a transcript: which question it already asked a parent, so it does not ask twice. That is
in AgentCore Memory keyed on the topic, with a 45 day answer-stands window. `S3SessionManager` would
be storage nobody reads.

**`strands.interrupt`.** This is the one that looks like it should fit, since the hackathon theme is
an agent that surfaces only when there is a real decision, and Turnout's chief interrupt budget is
exactly that. It does not fit, and the reason is worth stating.

`Interrupt` pauses an in-process agent run and resumes it with a response. Both of these projects
escalate to a human over a channel measured in hours: a text message to a chief who is asleep, or a
question that waits until a parent is at pickup. Holding an agent run open across that would be
strictly worse than what is built, which records the question, ends the run and applies the answer
whenever it arrives. The escalation being asynchronous is the design, not a limitation of it.

Using `Interrupt` here would have added an SDK import and removed a property the product depends on.
