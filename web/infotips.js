/* Every InfoTip in one file, so the copy can be reviewed as copy.
   Rule: at most three short sentences. What it is, why it exists, where to read more. */

window.INFOTIPS = {
  where_it_runs: "Both projects run on AWS App Runner and call Amazon Bedrock directly. The Strands agents, the Graph, the hooks and the Agent-to-Agent protocol are all live. The AgentCore services are the deployment this is designed for, each for a stated reason, and are not wired in yet.",
  /* Domain terms ------------------------------------------------------- */
  fcc: "Family child care: licensed or registered care for a small group of children in the provider's own home. It is the most common form of care for infants, rural families, and parents working nights and early mornings.",
  cacfp: "The Child and Adult Care Food Program. It reimburses providers for meals that meet USDA meal patterns. A meal is paid only if the required components were served and documented.",
  component: "CACFP counts food by component, not by weight: milk, fruit, vegetable, grain, and meat or meat alternate. Which components were on the plate is what decides whether a meal is paid.",
  meal_pattern: "The set of components each meal must have for each age group. Breakfast needs milk, a grain, and a fruit or vegetable. Lunch needs all five. A snack needs any two.",
  reimbursable: "The meal has every component the pattern requires, so the food program will pay for it. Tally decides this with versioned rules in code, never with model reasoning.",
  smallest_fix: "The single change that would make this meal qualify, chosen from foods the provider already serves. Said out loud while the food is still on the table, because that is the only moment it is useful.",
  ratio: "The number of children one provider may care for, set by the state and by the type of licence. Exceeding it is a licensing violation, so Tally looks ahead to the afternoon arrivals and says so in the morning.",
  subsidy_authorization: "The days a subsidised child is approved to attend. Since a 2024 federal rule, a home is paid for subsidised care only on days the child actually attended, so attendance that does not match has to be resolved before the claim goes out.",
  tier: "Day care homes are paid at one of two rates. Tier 1 homes, in lower income areas or run by lower income providers, are paid substantially more per meal than tier 2.",
  daily_maximum: "A home may claim at most two meals and one snack, or one meal and two snacks, per child per day. When more is served, Tally claims the most valuable allowed combination.",
  label_check: "Some rules turn on a number printed on the packet, such as sugar per ounce in cereal or yoghurt. A photograph cannot establish that, so Tally raises it for the provider to check rather than deciding it.",

  /* Metrics and behaviour ----------------------------------------------- */
  confidence: "How sure the vision model is that it identified this food correctly. Below 0.75 the item is left out of the record and a question is asked instead, because guessing a component into compliance would create a false claim.",
  question_budget: "A hard limit on how many questions Tally may put to the provider in a day, outside safety and meal moments. Recovering focus after an interruption takes about 23 minutes (Gloria Mark, UC Irvine), and she is interrupted by children all day already.",
  allergy_check: "Before any meal is written, every food on the plate is checked against the allergies of every child present. Matching is deliberately generous, so a dairy allergy catches milk, cheese and yoghurt.",
  superseded: "When a provider adds a missing component and photographs the plate again, the second record replaces the first. The meal is counted once, and both photographs stay as evidence.",
  lost_amount: "What the meals that did not qualify would have paid. At the 2026-2027 tier 1 rates, one lunch a day that fails the log, for six children, is 436.92 dollars in a month.",
  rule_version: "The version of the meal pattern data this verdict was decided under. Recording it is what makes an audit reproducible a year later, when the rules have changed.",

  /* Agents and platform -------------------------------------------------- */
  agent_plate: "Reads the photograph and maps each food to a CACFP component. It never estimates portions, weights or calories, because a photograph cannot establish them and the food program does not ask for them.",
  agent_rules: "Applies the meal pattern as versioned data, decides whether the meal is reimbursable, and computes the smallest change that would fix it. Deterministic, so the same plate always gets the same answer.",
  agent_roll: "Turns a spoken sentence into attendance. It understands absences with a reason, later arrivals with a time, and corrections that start with no, and it reports any name it did not recognise rather than guessing.",
  agent_gate: "The only agent allowed to ask the provider anything. Safety and meal questions go through immediately; everything else waits for the evening and spends the daily budget.",
  agent_ledger: "Closes the day, applies the daily maximum per child, and builds the month's claim from the rates in force.",
  agent_notes: "Drafts one short note per child from what was actually logged, in each family's language. It adds nothing that is not in the record.",
  nightly_graph: "A Strands Graph that runs Ledger, then Parent Notes, then Compliance, then the Digest, in that fixed order. The evening work is a pipeline whose steps feed each other, so a Graph is the right shape for it.",
  day_orchestrator: "During the day the provider is standing there with a plate in her hand, so the work is request driven and shallow: one specialist agent is called as a tool and answers in a few seconds.",
  bedrock_vision: "Amazon Bedrock runs the vision model that reads the plate, at temperature zero so the same photograph gives the same record.",
  agentcore_runtime: "Hosts the day agent and the nightly job, isolated per provider, with sessions that outlive a single request.",
  agentcore_memory: "Remembers each child, their allergies and subsidy days, and the provider's own words for foods, so that the usual crackers resolves to the product she actually buys.",
  agentcore_gateway: "Serves the meal pattern rules, the payment rates and the state ratio tables as tools, so the rules can be updated without redeploying an agent.",
  agentcore_code: "Runs the claim arithmetic and the ratio maths as real Python with the inputs and outputs recorded. This is why a number on this screen can be shown rather than asserted.",
  agentcore_observability: "Records every step: the vision reading, the rule verdict, the rule version, and the decision whether to ask. It is what the trace shows.",

  /* Product -------------------------------------------------------------- */
  judge_mode: "The demo runs with no login and no account. Press the steps in order to play one Tuesday. Everything is the real system: real photographs, a real vision model, real rules.",
  sandbox_key: "A public key that identifies your integration and applies a rate limit. In a real deployment each sponsor has their own.",
  synthetic: "Rosa's Family Child Care and every child are fictional. The photographs are real, openly licensed pictures of real food, credited in the repository.",
  real_photos: "These are real photographs under open licences from Wikimedia Commons, not drawings and not generated images. Testing food recognition against drawings would prove nothing."
};
