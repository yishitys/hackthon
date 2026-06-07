# Hackathon Slides OCR

Source PDF: C:\Users\10639\OneDrive\Desktop\hackathon slides.pdf

## Slide 1

```markdown
# cognee

## Memory Platform for Agents

![Cube Image](#)  <!-- Placeholder for the image -->

---

**M-Agent Hackathon · June 7, 2026**
```

## Slide 2

```markdown
# The State of Agent Context

Most journeys start with an .md file.  
Easy for a few documents.  
Breaks as you grow / change.

---

## COGNEE ENABLES AGENTS TO
- Unify context across data sources
- Reason over relationships
- Maintain structured, reliable memory
- Learn from outcomes

---

### Diagram

**Axes:**
- Vertical: speed
- Horizontal: accuracy

**Quadrants:**
1. **Fine-Tuning**
2. **One-Shot Reasoning**
3. **Deep Thinking**
4. **COGNEE MEMORY THAT LEARNS**: Works in production, learns and evolves

**Note:** The diagram indicates a progression from low speed and accuracy to high speed and accuracy, with "COGNEE MEMORY THAT LEARNS" positioned prominently in the top right quadrant.
```

## Slide 3

```markdown
# MEMORY ENGINE THAT LEARNS

## From Data Ingestion To Smarter Agents
### With Cognee

---

### Multi-Modal Ingestion
- Connectors
  - Source Tracking
- Input Formats
  - .csv
  - .mp4
  - .txt
  - .pdf

---

### Knowledge Structuring
- Ontology Grounding
- Custom Data Models

---

### Access Control & Isolation
- Tenant Isolation
  - User/Team/Org Scopes
  - Physical Data Isolation

---

### Retrieval
- Semantic Graph Traversal
- Temporal

---

### Memory
- Short-Term
- Long-Term
- Procedural

---

### Feedback
- Implicit
- Explicit
- Outcome Driven

---

## Smarter Agents
```
### Diagram Structure
The diagram visually represents a process flow from "Multi-Modal Ingestion" through to "Smarter Agents," highlighting specific components and their relationships. Each step is outlined with subcategories or inputs that further define the functions within each category.

## Slide 4

```markdown
# MEMORY ENGINE THAT LEARNS
## TRUSTED BY ENGINEERS IN

### Software
- Splunk
- AWS
- Infosys
- Atlassian
- Autodesk
- Botpress
- Studocu
- Kovai.co
- Ribbon
- Reply
- Rentpost

### eCommerce
- Alibaba

### Hardware
- Intel

### Finance
- QRT
- DBS
- Royal Bank of Canada
- ALTUM

### Energy
- Raizen
- Peers

### Academia
- Technische Universität Berlin
- Berkeley
- GESIS Leibniz-Institut für Sozialwissenschaften
- Brown University
- PUC Rio

+80 other companies and thousands of open source developers

### Stats
- ⭐ 17.6k GitHub stars
- ➤ 5M+ SDK runs/month

---

Brain behind your agents · SF · 2026
```

## Slide 5

```markdown
# MEMORY ENGINE THAT LEARNS

## TYPICAL WORKFLOW — MANY REPOSITORIES AND DOCS AROUND THE ORGANIZATION

### Diagram Structure:
- A central hexagon labeled **Engine** surrounded by other hexagons:
  - **Plugins**
  - **Analytics**
  - **Infra**
  - **Legacy project**
  - **Notion/Slack/Jira**
  - **Docker**
  - **Frontend React**
  - **Stripe plugin**

### Agent Sessions:
- **Agent 1**
- **Agent 2**
- **Agent 3**

---

*Brain behind your agents* · *SF* · *2026*
```

## Slide 6

```markdown
# MEMORY ENGINE THAT LEARNS

## HOW A TYPICAL WORKFLOW LOOKS LIKE

### Bash Command
```
echo "== PR #2785 branch on remote (latest 3 commits) ==;" rtk git --no-pager log --online 3 origin/faq/recall-pydantic-source 2>/dev/null; cd /Users/vasilije/Projects/hermes_cognee/cogne-integrations && echo "PR #249 branch on remote (latest 3 commits) ==>"; rtk git --no-pager log --online 3 origin/fix/claude-code-recall-graph-completion-and-audit 2>/dev/null
```

- **Wait**: Waiting...

#### Prompt
```
Do you want to proceed?
1. Yes
2. Yes, and don’t ask again for rtk git *
3. No
```

- **Command**: `esc` to cancel - `Tab` to amend - `ctrl + e` to explain

### Scratch
```
brain behind your agents - SF: 2026
```
- Path: `/Users/vasilije/Projects-hermes-cognee` 
- Command: `tail -n 1 ~/.cogne-plugin/recall-audit.log | grep -r -context | head -250`
```

### Claude Code (node)
```
- Two new test files: test_get_default_tasks_by_indices.py and test_extract_graph_from_data_v2.py

- Local checks passed:
   - uv run ruff check ...
   - uv run ruff fmt --check ...
   - uv run pytest cognee/tests/unit/modules/data/deletion/test_prune_data.py -q
   - uv run pytest cognee/tests/unit/modules/pipelines/run_task_from_queue_test.py cognee/ ...
   - uv run pytest cognee/tests/unit/modules/pipelines/run_tasks_test.py cognee/tests/unit/modules/pipelines/
run_tasks_with_context_test.py -q
```

### Recap
- Goal: Build out cognee O2 contributor and PR-rolling automation. Current state: dev-onboarding PRs and weekly routines are live. Next action: confirm whether to merge open PRs #2772 and #2773 next.

```
cognee[local] dsl:claude_sessions sees=74f2b7ad530a | saving: 1p/4a
new task? /clear to save 672.4k tokens
```
```

### Additional Information
```
- PR #2769 is now at ...
```

## Slide 7

```markdown
# MEMORY ENGINE THAT LEARNS
## SOLUTION — LLM KNOWLEDGE WIKI

**LLM builds and maintains** ***Knowledge Wiki***

### STEP 1
**Ingest**

### STEP 2
**Query + Self Improve**

### STEP 3
**Lint**

---

*Brain behind your agents · SF · 2026*
```

## Slide 8

# MEMORY ENGINE THAT LEARNS
**SOLUTION — LLM KNOWLEDGE WIKI**

| EVENT              | WHEN IT FIRES                                    | TYPICAL USE                                               |
|--------------------|--------------------------------------------------|----------------------------------------------------------|
| SessionStart       | Once when Claude opens a session                 | Ingest -> Bootstrap state, register agents, print a banner|
| UserPromptSubmit    | Every user prompt, before model call             | Ingest -> Inject context (memory, docs, RAG) via `additionalContext` |
| PreToolUse         | Before any tool runs                             | Ingest -> Guard / approve / deny tool calls              |
| PostToolUse        | After a tool returns                             | Self-improve -> Capture, log, redact, audit             |
| Stop               | After the assistant finishes responding          | Self-improve -> Save the final answer, run analytics     |
| PreCompact         | Before context-window compaction                 | Self-improve -> Distill state so post-compact Claude isn't amnesic |
| SessionEnd         | When the session closes                          | Lint -> Flush, persist, summarize                        |

---

## Diagram Description

1. **User Trigger**: "You type a prompt"
   - Down to `[UserPromptSubmit hook]` which calls `cognee.recall(prompt)`
   - Points to `LanceDB ANN search + Kuzu graph traversal`
   
2. **Context Injection**: "Top-k chunks + traces injected into Claude's context"
   - Connects to "Claude answers"

3. **Follow-up Actions**:
   - `[Stop hook]` stores Q+A
   - `[PostToolUse]` stores tool calls
   - `[SessionEnd]` calls `cognee.improve()`, which persists to graph

## Slide 9

```markdown
# MEMORY ENGINE THAT LEARNS
## LET'S CONNECT THE DOTS

### SELF-IMPROVING SKILLS

```
+-----------+  1. run agent  +---------+
|  SKILL.md | --------------> | answer  |
+-----------+                 +---------+
      ^
      |
      |  5. apply
      |
+------+------+
|  proposal   | <----------------- 4. propose
+-------------+                     | feedback |
(if score < thr)                    +---------+
               v
           +-----------+
           |   2. score 0..1  |
           +-----------+

bad run  ->  proposal  ->  apply  ->  smarter next run
```
```

## Slide 10

```markdown
# MEMORY ENGINE THAT LEARNS

## PROBLEM — MEMORY COMPACTION

### LINT ➔ 
**How do you control and version edits?**  
**What about conflicting information?**

---

- Knowledge drifts over time
- What is the best way to distill data
```

## Slide 11

```markdown
# MEMORY ENGINE THAT LEARNS
## CASE STUDY · BAYER

### BAYER · PHARMACEUTICAL R&D

**Agentic research system for hypothesis generation in drug discovery**  
Global life science company Bayer carried out an extensive R&D project together with Cognee, which utilized graph-vector reasoning to generate, rank and explain novel research hypotheses inside Bayer's internal AI Scientist platform.

![Diagram](URL to diagram if available)

*Diagram Description*:  
The diagram visually represents a network with nodes and connections. Central to the diagram is a branded logo for "BAYER." Nodes are colored differently, suggesting various categories or associations, interconnected by lines that indicate relationships among them.
```

## Slide 12

```markdown
# MEMORY ENGINE THAT LEARNS

## PROBLEM — MEMORY COMPACTION

### Resources ➔
Your info is here

**Promo Code:** HACKATHON

![QR Code](URL-to-QR-Code)

---

*Brain behind your agents · NY · 2026*
``` 

(Note: Please replace "URL-to-QR-Code" with the actual URL if needed.)

## Slide 13

```markdown
# MEMORY ENGINE THAT LEARNS

## CONTACT US

---

### Dave Nielsen
- **Email:** dave@cognee.ai
- **Title:** Founding Head of DevRel
- **Organization:** Cognee AI

---

### Yuxin Ren
- **Email:** yr2110@nyu.edu
- **Organization:** NYU

---

*Brain behind your agents  ·  NY  ·  2026*
```
