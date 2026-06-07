# Hackathon Cognee Memory Layer

This folder is a minimal Cognee setup for a multi-agent system memory layer.

## Setup

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -e .
Copy-Item .env.example .env
```

Then edit `.env` and set:

```text
LLM_API_KEY="your_openai_api_key"
```

Cognee's default local stack uses SQLite, LanceDB, and Kuzu, so you do not need to run Postgres, Qdrant, or Neo4j for the demo.

## Commands

Check local configuration:

```powershell
cognee-memory check
```

Run a tiny write/read smoke test:

```powershell
cognee-memory smoke
```

Ingest the current hackathon slides:

```powershell
cognee-memory ocr-slides
cognee-memory ingest-slides
```

Ask questions against the slides memory:

```powershell
cognee-memory query "What should our multi-agent system use as memory?"
```

Run the Audit Passport web MVP:

```powershell
uv pip install -e .
python -m src.audit_passport.web_server
```

Then open `http://127.0.0.1:5173`. The `Start demo` button calls the live
`/api/run` endpoint, which runs the GPT + Cognee five-agent pipeline and then
refreshes the web data. If you only use `python -m http.server`, the page can
show saved JSON but cannot run agents from the button.

To pre-generate static JSON without serving the live API:

```powershell
python -m src.audit_passport.export_web_data --use-cognee
```

The older Streamlit prototype remains in `app.py`, but the primary product
front end is now the standalone web app under `web/`.

Place the Kaggle Track 01 CSV files in:

```text
data/kaggle/
```

The app intentionally does not create synthetic fallback data. It keeps raw CSV
rows outside Cognee and writes only semantic memory cards, evidence pointers,
agent outcomes, Memory Patches, and report cards to Cognee.

## Audit Passport MVP

The web product implements a five-agent demo flow:

- Agent 1 profiles Kaggle data and writes source/schema/finding cards.
- Agent 2 recalls Agent 1 output and writes classification/ranking memory.
- Agent 3 recalls rankings, writes remediation decisions, and can create a
  `MemoryPatch` through the `New Evidence Found` button.
- Agent 4 recalls the full evidence chain and generates a downloadable PDF.
- Agent 5 exposes the memory timeline and records explicit user feedback.

`Memory Ripple` is the main demo moment: a new evidence patch from Agent 3 is
written to Cognee, then the affected finding, risk score, action, and PDF report
are updated from the shared semantic memory.

## Agent Integration Sketch

Use `src/cognee_memory.py` as the first memory adapter. Agents can call:

- `remember_path(path, dataset)` to persist project docs, transcripts, or outputs.
- `recall(query, dataset)` to retrieve graph-backed context.

The provided slides PDF is image-based, so run `ocr-slides` first. It writes
`data/hackathon_slides_ocr.md`, which `ingest-slides` will prefer over the PDF
when present.

For a hackathon demo, keep one dataset per knowledge domain, for example:

- `hackathon_slides`
- `agent_outputs`
- `user_preferences`
