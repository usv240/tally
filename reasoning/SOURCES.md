# Where the rulebook comes from

`cacfp_meal_pattern.txt` is the source document for the Automated Reasoning policy that
`prove_answer` checks against. Every rule in it restates a sentence of the regulation or of a
USDA policy memorandum. Nothing in it is Tally's own interpretation.

| Rules | Source | Text |
|---|---|---|
| B1–B3, L1–L3, S1–S5 | 7 CFR 226.20(c)(1)–(3) and table footnotes | https://www.ecfr.gov/current/title-7/section-226.20 (as of 2026-10-22) |
| M1–M7 | 7 CFR 226.20(a)(1)(i)–(iv), (c) footnotes 3–6 | same |
| M8 | 7 CFR 226.20(g)(3) | same |
| V1–V3, F1–F2, J1–J2 | 7 CFR 226.20(a)(2)–(3), (c) footnotes 7–8 | same |
| G1–G7 | 7 CFR 226.20(a)(4)(i)–(iii), (c) footnotes 8–9 | same |
| P1–P3 | 7 CFR 226.20(a)(5)(i)–(ii), (iv)–(vi) | same |
| Y1–Y7 | 7 CFR 226.20(a)(5)(iii)(A)–(C) | same |
| Y8 | CACFP 06-2025, "Meats and Meat Alternates", p. 13; infant Q&A 10 and 12 | https://www.fns.usda.gov/cacfp/feeding-infants-and-meal-pattern-requirements-cacfp-questions-and-answers |
| D1–D2 | 7 CFR 226.20(d) | eCFR |
| D3 | 7 CFR 226.20(p) | eCFR |
| D4 | 7 CFR 226.20(n)(3) | eCFR |
| D5 | 7 CFR 226.20(g)(1)(i) | eCFR |
| D6 | 7 CFR 226.20(g)(2)(iii) | eCFR |
| I1–I3, I5–I6, I9–I11 | 7 CFR 226.20(b)(1)–(5) and table footnotes 2, 4, 6, 8 | eCFR |
| I4 | CACFP 06-2025, infant Q&A 16 | USDA memo |
| I7 | CACFP 06-2025, infant Q&A 14 | USDA memo |
| I8 | CACFP 06-2025, "Meats and Meat Alternates", p. 13 | USDA memo |

The sugar limits changed on October 1, 2025 (89 FR 31962, final rule of April 25, 2024). The
regulation text still carries both the old and the new clause. The rulebook states the clause in
force today and says explicitly that the old one expired, so that an answer quoting the old limit
is contradicted rather than merely unproven.

The eCFR XML was fetched from `https://www.ecfr.gov/api/versioner/v1/full/2026-10-22/title-7.xml?part=226&section=226.20`.
The memo PDF was fetched from the North Carolina DHHS mirror of CACFP 06-2025 (the USDA host blocks automated downloads).
