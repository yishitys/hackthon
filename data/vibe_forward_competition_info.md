# vibeFORWARD M-AGENTS Competition Info

Captured: 2026-06-07

Primary source: https://vibe-forward.vercel.app/

Related dataset noted earlier:
https://www.kaggle.com/datasets/quantologist/track01-vibeforward-m-agents

## Event Snapshot

- Event: M-AGENTS / vibeFORWARD
- Date: June 7, 2026
- Location: Fordham Lincoln Center, NYC
- Context: NYC Tech Week / a16z
- Format: 1-day hackathon build sprint
- Team size: 4-6 people
- Registered: 400+
- Tracks: 2
- Cash prizes: $2,000 total

Core challenge:

> You're given a real business crisis. Build a multi-agent system that addresses it, then ideate and design your own product that puts the solution in the hands of someone who needs it.

The crisis is the prompt. The product is chosen by the team.

## Tracks

### Track 01 - Data Rescue

Problem:

> A manufacturer's data is corrupted four days before a regulatory audit - duplicates, unit conflicts, numbers that contradict each other.

Build any product that helps an organization find, fix, and explain broken data.

End user archetype:

- Compliance officer who has never opened a database.

Dataset:

- https://www.kaggle.com/datasets/quantologist/track01-vibeforward-m-agents

### Track 02 - Fraud Watch

Problem:

> A fraud ring stayed under every alert threshold - small transactions, circular flows, coordinated accounts.

Build any product that helps a fraud team see what rules miss.

End user archetype:

- Analyst with three minutes per case.

Dataset:

- https://www.kaggle.com/datasets/quantologist/track02-vibeforward-m-agents

Dataset note:

- Kaggle datasets are optional.
- Using the benchmark gives bonus credibility because judges verify findings against a hidden answer key.
- Teams may also bring their own data.

## Required Team Roles

Every team needs at least one Builder and at least one other role.

- Builder: makes the agents run, wires Cognee, connects agent outputs to the product interface.
- Designer: owns the Product Brief and everything the user sees. Step 0 and Step 5 are theirs.
- Domain Expert: validates outputs, writes the Agent 4 narrative, and runs Geodo research on real-world entities.
- Presenter: owns the demo script, Trupeer recording, and finalist stage presentation.

Important implication:

- Non-technical roles are judged as core contributors, not support.
- A team with one Builder and three strong non-technical teammates can win.

## Five-Step Pipeline

### Step 00 - Define

Write the Product Brief first.

One page before any code:

- Who is it for?
- What does it do in one sentence?
- What does success look like?
- What will the team not build?

### Step 01 - Find It

Agent 1 reads the dataset and finds what is wrong:

- Duplicates
- Anomalies
- Suspicious patterns
- Broken or contradictory records

### Step 02 - Rank It

Agent 2 prioritizes findings:

- Worst first
- Reasons for every ranking decision

### Step 03 - Act On It

Agent 3 fixes, flags, or escalates findings.

Every action must have a logged reason. "The model said so" fails judging.

### Step 04 - Explain It

Agent 4 writes a human-readable summary.

Requirements:

- Human can read and sign it.
- Summary is downloadable from the product.
- Domain Expert owns this step.

### Step 05 - Show It

Build the product from the Product Brief.

Demo it as the end user, not as an engineer explaining code.

Memory requirement:

- Memory connects everything.
- Each agent recalls previous agents' work through Cognee.

## Tool Stack

### LingCode.dev

- Status: recommended IDE
- Use: design and customize agents.
- Includes Claude Code, Codex, and Gemini CLI.
- URL: https://lingcode.dev

### Cognee

- Status: mandatory
- Use: memory layer between all four agents.
- Trial: 14-day Cloud trial.
- Prize credits: top prize $200/month credits; 2nd and 3rd $35/month credits.
- URL: https://www.cognee.ai
- Discord: https://discord.gg/5SHNNhe7t

### Trupeer

- Status: mandatory
- Use: required 5-minute demo video.
- Trial: 14-day trial for all participants.
- URL: https://app.trupeer.ai/auth

### Geodo

- Status: mandatory
- Use: Domain Expert researches product's real-world entities, including customers, companies, and market.
- Platform: web platform, no code.
- Included: 100 credits + 5-day Pro access.
- URL: https://geodo.ai
- Access form: https://docs.google.com/forms/d/e/1FAIpQLSeadm1fz7ev7S_z4WxvpWGueeUrW_GN6EiYGB3QzXAZ23br-Q/viewform

### Kaggle

- Status: data source, optional
- Use: both track datasets.
- Benefit: benchmark earns bonus credibility through hidden answer key verification.
- Track 01: https://www.kaggle.com/datasets/quantologist/track01-vibeforward-m-agents
- Track 02: https://www.kaggle.com/datasets/quantologist/track02-vibeforward-m-agents

### PyMC Open-Source Stack

- Status: optional, special prize relevant
- PyMC: probabilistic reasoning and Bayesian modeling.
- PyMC GitHub: https://github.com/pymc-devs
- PyMC-Marketing: media mix modeling and budget optimization.
- PyMC-Marketing GitHub: https://github.com/pymc-labs/pymc-marketing
- Decision Hub: discover validated agent skills before writing the brief.
- Decision Hub URL: https://hub.decision.ai
- Daimon: data-scientist agent in the PyMC Labs Discord.
- PyMC Labs Discord: https://discord.com/invite/tUSMHWJEyR
- Decision Lab: harness for agentic data science.
- Decision Lab GitHub: https://github.com/pymc-labs/decision-lab

## Registration And Submission Links

- RSVP on Partiful: https://partiful.com/e/ONYSrk9bi7nfpjTjY48B
- Register on Devpost: https://vibeforward-m2-agents.devpost.com/
- Team verification form: https://forms.gle/HGoa9fKruQEHazLAA
- Day-of issue form: https://forms.gle/82kdnM75eubDA42M8

Submission deadline:

- Devpost submission closes at 5:00 PM.
- No extensions.

Required Devpost submission items:

- Product Brief PDF
- GitHub repo link
- Trupeer video URL
- Track selection
- Written product description

Partial submissions are not accepted.

## Schedule

- 9:30 AM: Doors open, breakfast, networking
- 10:05 AM: Lightning Talk - Christian Luhmann, COO, PyMC Labs (virtual)
- 10:17 AM: Lightning Talk - Dave Nielsen, Head of DevRel, Cognee
- 10:29 AM: Lightning Talk - Atin Woodard, Founder, Stage 11 Agentics
- 10:45 AM: Team formation, role cards, challenge reveal
- 11:00 AM: Build sprint begins - Step 0 Product Brief first
- 1:00 PM: Lunch
- 4:00 PM: Science fair - judges walk the room
- 5:00 PM: Submissions close on Devpost - no extensions
- 5:00-5:20 PM: Judges deliberate, three finalists selected
- 5:20 PM: Finalists announced
- 5:25-6:00 PM: Finalist demos and special prize demos
- 6:00 PM: Awards, job opportunities, close

## Rules

- R01: Minimum 4 agents with real handoffs; not one LLM call in a loop.
- R02: Cognee is the memory layer; every agent reads from and writes to it.
- R03: Trupeer demo video is mandatory. No video means disqualification.
- R04: Geodo research is mandatory, done by the Domain Expert, using the web platform only.
- R05: Product Brief / Step 0 is required, submitted, and judged against the team's own product.
- R06: Data may be brought by the team or taken from the Kaggle benchmark. Benchmark usage earns bonus verification.
- R07: Every agent decision must have a visible reason. "The model said so" fails judging.
- R08: Agent 4's summary must be downloadable from the product.
- R09: Teams must have 4-6 members, at least one Builder and one other role. No solo submissions.
- R10: Submit on Devpost by 5:00 PM. No extensions.

## Judging

Total score: 25 points.

Criteria:

- Agents that work: ran on real data; outputs are not hardcoded. 5 points.
- Real collaboration: Agent N+1 demonstrably used what Agent N found, via Cognee. 5 points.
- Matches the brief: judged against the team's own Step 0 success condition. 5 points.
- End user can use it: a judge operates the product cold during the science fair. 5 points.
- Explainable: every decision has a visible reason a human can follow. 5 points.

Finalist qualification:

- Minimum 15 points to qualify for finalist consideration.
- In-person judges walk the science fair from 4-5 PM.
- Virtual judges review Devpost from 5 PM.
- Top three teams demo live.

## Prizes

Cash and tool prizes:

- 1st Place: $1,500 cash
- 2nd Place: $200 cash
- 3rd Place: $100 cash
- Best Use of Trupeer: $200 cash
- Geodo Top Team: 3 Pro accounts, about $3,000 value
- Cognee: $200/month cloud credits for 1st; $35/month credits for 2nd and 3rd
- PyMC Special Prize: course seat, about $2,000 value

Everyone gets:

- 14-day Trupeer trial
- 14-day Cognee Cloud trial
- 100 Geodo credits + 5-day Pro access

Other:

- Job opportunities announced in the room, including SWE and GTM roles from sponsor companies.

## How-To Resources

- Recording your demo with Trupeer: https://www.youtube.com/watch?v=_F4eiBKsiyk
- Building agents in LingCode.dev: https://www.youtube.com/watch?v=XG5NTG6oN9Q&t=3s

## FAQ Notes

Non-technical participants:

- Yes, they can compete.
- Designer, Domain Expert, and Presenter are core roles.
- Steps 0, 4, 5 and all Geodo research belong to non-technical teammates.

Kaggle dataset:

- Not required.
- Optional benchmark.
- Bonus credibility if used because judges compare findings to hidden answer key.

API keys:

- Participants need their own key for OpenAI, Anthropic, or Groq.
- Groq has a free tier with no card required.
- API keys are not provided at the event.

Finalists:

- Picked from science-fair scores plus Devpost review.
- Science fair: 4-5 PM.
- Devpost review: from 5 PM.
- Top three teams demo live at 5:25 PM.
- Minimum score: 15 of 25 points.

## Practical Build Checklist For Track 01

- Write a one-page Product Brief before implementation.
- Make the product explicitly serve a non-technical compliance officer.
- Run on real Track 01 data or another real dataset.
- Implement four distinct agents:
  - Agent 1: find broken data.
  - Agent 2: rank issues by audit/compliance risk.
  - Agent 3: fix, flag, or escalate with logged reasons.
  - Agent 4: generate downloadable human-readable audit summary.
- Store every agent output and handoff in Cognee.
- Surface explanations and evidence in the product UI.
- Include a downloadable Agent 4 summary.
- Prepare a judge-cold workflow: the judge should understand and operate it without engineering explanation.
- Record a 5-minute Trupeer demo.
- Complete Geodo research and weave it into the product narrative.
- Submit Product Brief PDF, GitHub repo, Trupeer URL, track selection, and product description on Devpost before 5:00 PM.
