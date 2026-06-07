# Hackathon Requirements Captures

This file records requirements captured from ad hoc source images and slide photos.

## 2026-06-07 - Available Tools Slide Photo

Source image:
`C:\Users\10639\OneDrive\文档\WeChat Files\wxid_aggva5vn3vkg12\FileStorage\Temp\d2e8ee61b2ab46feee556656b0ba6a8.jpg`

Observed slide title: `Available Tools`

| Tool | Status | Who uses it | Requirement / usage |
| --- | --- | --- | --- |
| Blue `{}` logo tool, name not readable in photo | Mandatory | Builder + Designer | The agent design and final product deployment interface |
| Kaggle | Optional | Builder | Use it and judges verify findings against the hidden answer key; bonus credibility |
| PyMC Labs | Optional - special prize | Builder | Confidence levels on agent outputs, e.g. `"94% probability"` rather than `"yes"` |
| Cognee | Mandatory | Builder | Memory layer between all four agents |
| Green/black logo tool, name not readable in photo | Mandatory | Domain Expert | Web platform research on the product's real-world entities: customers, companies, and market. No code. |
| trypeer | Mandatory | Builder + Designer | 5-minute demo video; required submission |

Derived build requirements:

- The final project should use the mandatory agent design/deployment interface from the first row once the tool name is confirmed.
- The Builder role must implement a shared memory layer between all four agents using Cognee.
- The Domain Expert role must use the mandatory no-code web research platform to research real-world customers, companies, and market entities once the tool name is confirmed.
- The Builder + Designer roles must prepare and submit a 5-minute demo video through trypeer.
- Optional credibility improvement: use Kaggle for judge-verifiable findings against a hidden answer key.
- Optional special-prize improvement: use PyMC Labs to express uncertainty with probabilistic confidence levels instead of binary answers.

## 2026-06-07 - Judging Criteria Slide Photo

Source image:
`C:\Users\10639\OneDrive\文档\WeChat Files\wxid_aggva5vn3vkg12\FileStorage\Temp\3765c1b9c670659b68d5d54e548c814.jpg`

Observed slide topic: `How you're judged`

Scoring structure:

- Five questions.
- 5 points each.
- 25 points maximum.
- 15 points required to qualify.

Judging criteria:

1. Agents that work: they ran on real data.
2. Real collaboration: Agent N+1 used what Agent N found, via Cognee.
3. Matches your brief: judged against your own Step 0.
4. Your end user can use it: a judge operates it cold.
5. Explainable: every decision has a visible reason.

Timeline / submission requirements:

- Judges walk the room from 4-5 PM.
- Submissions close at 5 PM.
- Top 3 demo live.

Derived build requirements:

- The demo must run agents on real input data, not only mocked examples.
- Agent handoff must be visible: later agents should consume earlier agent outputs through Cognee.
- The final product must clearly satisfy the Step 0 brief.
- The user interface or workflow must be usable by a judge without coaching.
- Agent decisions, recommendations, and outputs must expose their reasons or evidence.
- The project must be ready for judge walkthrough before 4 PM and submitted before 5 PM.

## 2026-06-07 - Rules Checklist Screenshot

Source: user-provided screenshot in chat.

Mandatory rules:

| ID | Requirement |
| --- | --- |
| R01 | Minimum 4 agents with real handoffs, not one LLM call in a loop. |
| R02 | Cognee is the memory layer; every agent reads from and writes to it. |
| R03 | Trupeer demo video is a mandatory submission. No video means disqualified. |
| R04 | Geodo research is mandatory, done by the Domain Expert on the web platform only. |
| R05 | Product Brief, Step 0, is required, submitted, and judged against the team's own product. |
| R06 | Data: bring your own data or use the Kaggle benchmark; benchmark use earns bonus verification. |
| R07 | Every agent decision must have a visible reason. "The model said so" fails judging. |
| R08 | Agent 4's summary must be downloadable from the product. |
| R09 | Teams must have 2-6 people, with at least one Builder and one other role. No solo submissions. |
| R10 | Submit on Devpost by 5:00 PM. No extensions. |

Derived build requirements:

- Implement at least four distinct agents with observable handoff artifacts.
- Ensure every agent both reads from and writes to Cognee.
- Make all agent decisions explainable with visible reasons or evidence.
- Keep the Step 0 Product Brief as the primary acceptance target for judging.
- Provide a downloadable Agent 4 summary in the product UI.
- Prepare the mandatory Trupeer demo video and Devpost submission before 5:00 PM.
