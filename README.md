# Tally

Track: Professional Agents. Target: Golden Agent, and a credible Grand Prize alternate.

Tally is a hands-free agent for home-based child care providers. It logs meals from a photo, takes attendance by voice, checks every federal and state rule in real time, and files the monthly claim, so the provider gets paid in full without an evening of paperwork.

She feeds twelve kids and files paperwork for every bite. Tally does the counting.

## Documents in this folder

| File | What it covers |
|---|---|
| `PLAN.md` | Problem, audience, evidence, scope, feature list, success criteria, positioning against existing tools |
| `TECHNICAL_DESIGN.md` | Architecture, every agent, Strands patterns used, AgentCore mapping, rules engine, data model, API, security, testing, deployment |
| `LANDING_PAGE.md` | Section-by-section landing page specification with final copy, InfoTip text, and references |
| `DEMO_AND_VIDEO.md` | Synthetic provider and children, the five demo plates, the judge walkthrough, the timed video script |

Shared standards live one level up in `../STRATEGY.md` and `../DESIGN_SYSTEM.md`.

## One-paragraph summary

Licensed family child care homes, where one provider cares for 4 to 12 children in her own house, are the backbone of care for working-class and rural families. More than half of them closed between 2005 and 2017, and providers who serve subsidized children fell by 51 percent. The reason providers name most often is paperwork: every meal for every child must be logged by component to be reimbursed under the federal Child and Adult Care Food Program; since 2024, actual daily attendance must be documented for every subsidized child; and ratios, drills, training hours, and licensing renewals all carry deadlines. The provider has a toddler on each hip and no hands for a screen. Tally is built for that: she photographs the plate and the agent identifies the components, checks the meal pattern, tells her right then if a component is missing so the meal still qualifies, and logs it for every child present. She says who is here and attendance is recorded, ratios are checked, and subsidy schedules are reconciled. Parent notes write themselves from what she said during the day. At month end the claim is ready. The agent interrupts her only for the one question only she can answer. Built with Strands Agents and deployed on Amazon Bedrock AgentCore.
