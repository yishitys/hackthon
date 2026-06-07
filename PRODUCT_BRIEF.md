# Product Brief — Audit Passport

**Track:** 01 · Data Rescue · M-AGENTS / vibeFORWARD (2026-06-07)
**Team roles:** Builder · Designer · Domain Expert · Presenter
**One-line position:** A Data Rescue Copilot that turns corrupted manufacturing records into traceable, fixable, and explainable audit findings — built on a five-agent pipeline that remembers every step through Cognee.

---

## 1. Who is it for?

A **manufacturing compliance officer four days before a regulatory audit** who has never opened a database.

She cannot write SQL, does not understand table joins, and has no time to hand-check thousands of rows across production, shipment, and customer-master files. She needs to know, in plain language: *what is most dangerous, why it is dangerous, what to fix first, and how to explain it to the auditor.*

Secondary readers: the **external audit reviewer** who signs off on her workpapers, and **leadership** who wants a single readiness number before the audit.

## 2. What does it do — in one sentence?

Audit Passport ingests real manufacturing data, runs five collaborating agents that find broken records, rank them by audit risk, decide how to fix them, and write a downloadable auditor-ready report — with every decision backed by a visible row-level reason and a probabilistic confidence.

## 3. What does success look like?

Concrete, judge-checkable success criteria (these are the bar we are judged against):

1. **Agents that work on real data.** The pipeline runs on the Kaggle Track 01 dataset (`data/kaggle/`) — production, shipment, and customer-master CSVs — with no hardcoded findings. Deterministic detectors surface candidates; agents reason over them.
2. **Real collaboration through Cognee.** Each of the five agents reads prior agents' cards from Cognee and writes its own back. Agent 2 ranks only the findings Agent 1 recalled; Agent 3 acts only on Agent 2's ranked findings; Agent 4 narrates only from recalled memory. The shared session id makes the handoff inspectable.
3. **Matches this brief.** A judge can run the demo cold from the dashboard and reach a downloadable report without coaching — exactly the flow described here.
4. **The end user can use it.** First screen is an Audit Risk dashboard (readiness score, urgent issues, fixable-now count), not a landing page or a JSON dump. No SQL, no database concepts exposed.
5. **Everything is explainable.** Every finding carries `source_file → row → field → observed vs. conflicting value`, a `why_broken` reason, a `ranking_reason`, an `action_rationale`, and a PyMC-derived `audit_blocker_probability` with a credible interval. "The model said so" appears nowhere.
6. **The Memory Ripple moment lands.** Clicking **Add new evidence** writes a `MemoryPatch` to Cognee; the affected finding, its risk score, the recommended action, and the PDF all update from shared memory — proving the system *remembers* rather than re-runs.

We qualify at 15/25; we are designing to score on all five judging questions.

## 4. What the team will NOT build

To stay shippable in a one-day sprint and true to the user, we explicitly will **not** build:

- A data-cleaning script or an engineer's SQL dashboard.
- A static report generator or a single LLM prompt in a loop.
- A raw error-row table or a chat-only interface with no dashboard and no downloadable summary.
- Blind auto-correction of audit data. Fixes are tiered — Safe Auto-Fix, Suggested Fix, Manual Review Required, Escalate — and risky reconciliations stay with a human.
- Synthetic fallback data. If the Kaggle CSVs are absent the app says so rather than inventing rows.
- A full Memory-Governance/LINT engine. The LINT concept ships as an explanation layer and memory-status field, not a complete subsystem.

---

## 5. How it maps to the build (proof, not promises)

### Five agents, real handoffs (R01) — `src/audit_passport/agents.py`

| Step | Agent | Reads from Cognee | Writes to Cognee | Visible reason it emits |
| --- | --- | --- | --- | --- |
| Find It | **1 · Data Ingestion & Detective** | sources, schema, memory patches | sources, schema, detection candidates, findings | `why_broken` + row-level evidence per finding |
| Rank It | **2 · Classification & Risk Prioritizer** | findings, sources, schema | baseline, ranked findings | `ranking_reason` + severity + confidence |
| Act On It | **3 · Reconciliation & Remediation** | ranked findings, baseline | reconciliation decisions, updated findings | `action_rationale` + chosen action tier |
| Explain It | **4 · Narrative & Audit Report** | findings, decisions, baseline, Geodo research, patches | insights, report (PDF) | evidence-linked claims + executive summary |
| Show It | **5 · UI Demo & Feedback** | all agent outcomes, insights, feedback | feedback digest | memory-timeline health + next action |

### Detected problem types (≥3 required) — Agent 1 detectors
Duplicate records · Unit conflicts (kg/lb, mm/cm) · Contradictory numbers · Impossible dates (ship before produce) · Impossible values · Orphaned references (customer not in master) · Missing evidence. **Seven classes, exceeding the three-class minimum.**

### Mandatory tool stack
- **Cognee (R02):** memory layer for all five agents; one shared session + per-agent sessions; cards persisted as graph-backed memory (`src/audit_passport/memory.py`).
- **Geodo (R04):** Domain Expert's real-world market/firm/customer research, collected on geodo.ai (not code-substituted), woven into Agent 4's narrative (`src/audit_passport/geodo.py`).
- **Kaggle (R06, bonus):** Track 01 benchmark dataset for judge-verifiable findings.
- **PyMC (optional prize):** probabilistic audit-blocker risk with credible intervals instead of yes/no (`src/audit_passport/probabilistic.py`).
- **Trupeer (R03):** 5-minute demo video, submitted to Devpost.

### Downloadable Agent-4 summary (R08)
The **Download brief** button serves Agent 4's generated PDF (`src/audit_passport/report.py`) from the live `/api/run` endpoint.

### Explainability (R07)
Every finding, ranking, action, and report claim exposes its evidence and reason in the Evidence View — enforced by the `FindingCard` schema (`src/audit_passport/models.py`).

---

## 6. User flow (what a judge does, cold)

1. Open `http://127.0.0.1:5173` → **Audit Passport Command Center** dashboard.
2. Click **Start demo** → live five-agent pipeline runs on the Kaggle data via `/api/run`.
3. Read the headline: **Ready Chance** (probabilistic readiness score), urgent issues, fixable-now count, new facts.
4. Open the top finding → see source file, row, conflicting values, why it matters, recommended action tier, and confidence.
5. Click **Add new evidence** → watch the Memory Ripple update the finding, score, action, and report from Cognee.
6. Click **Download brief** → export Agent 4's auditor-ready PDF.

---

*Step 0 deliverable for Devpost. Submit alongside the GitHub repo link, Trupeer video URL, Track 01 selection, and written product description before 5:00 PM.*
