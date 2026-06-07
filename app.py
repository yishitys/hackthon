from __future__ import annotations

import asyncio
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from src.audit_passport.agents import run_audit_pipeline
from src.audit_passport.data_loader import DATA_DIR, list_kaggle_csvs
from src.audit_passport.memory import MemoryRecorder
from src.audit_passport.models import UserFeedbackCard
from src.audit_passport.report import readiness_score
from src.audit_passport.ripple import apply_memory_ripple


st.set_page_config(
    page_title="Audit Passport",
    page_icon="AP",
    layout="wide",
    initial_sidebar_state="expanded",
)


CSS = """
<style>
:root {
  --paper: #f7f2e8;
  --ink: #1c1a17;
  --steel: #5e6974;
  --rule: #c8bca8;
  --red: #a63d32;
  --green: #2f6b4f;
  --blue: #315f86;
  --gold: #9f7835;
}
.stApp {
  background:
    linear-gradient(90deg, rgba(28,26,23,.035) 1px, transparent 1px),
    linear-gradient(rgba(28,26,23,.028) 1px, transparent 1px),
    var(--paper);
  background-size: 24px 24px;
  color: var(--ink);
}
.block-container {
  padding-top: .85rem;
  max-width: 1500px;
}
h1, h2, h3 {
  font-family: Georgia, 'Times New Roman', serif;
  letter-spacing: 0;
}
div[data-testid="stMetric"] {
  background: rgba(255,255,255,.52);
  border: 1px solid var(--rule);
  border-left: 5px solid var(--blue);
  padding: 10px 13px;
  box-shadow: 0 8px 22px rgba(31, 29, 24, .08);
}
.passport-hero {
  border: 1px solid var(--rule);
  border-left: 7px double var(--red);
  background: rgba(255,255,255,.58);
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 16px 38px rgba(28,26,23,.12);
}
.passport-title {
  font-family: Georgia, 'Times New Roman', serif;
  font-size: 34px;
  line-height: 1.02;
  font-weight: 700;
  margin-bottom: 5px;
}
.passport-kicker {
  color: var(--red);
  font-weight: 700;
  text-transform: uppercase;
  font-size: 12px;
  letter-spacing: .08em;
}
.stamp-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin: 8px 0 2px;
}
.stamp {
  border: 2px solid var(--blue);
  color: var(--blue);
  padding: 5px 10px;
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 800;
  transform: rotate(-1.5deg);
  background: rgba(255,255,255,.42);
  white-space: nowrap;
}
.stamp.hot {
  border-color: var(--red);
  color: var(--red);
}
.chip {
  display: inline-block;
  border: 1px solid var(--rule);
  border-radius: 999px;
  padding: 4px 9px;
  font-size: 12px;
  background: rgba(255,255,255,.55);
  margin-right: 6px;
}
.panel {
  border: 1px solid var(--rule);
  background: rgba(255,255,255,.55);
  padding: 12px 14px;
  margin-bottom: 12px;
}
.stage-card {
  min-height: 164px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.stage-card h3 {
  font-size: 20px;
  margin: 8px 0 6px;
}
.stage-card p {
  font-size: 13px;
  line-height: 1.35;
}
.memory-count {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.memory-pill {
  border: 1px solid var(--rule);
  background: rgba(247,242,232,.75);
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 700;
}
.diff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 10px;
}
.diff-box {
  border: 1px solid var(--rule);
  background: rgba(255,255,255,.5);
  padding: 10px;
}
.diff-label {
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 800;
  color: var(--steel);
}
.risk-critical { color: var(--red); font-weight: 800; }
.risk-high { color: #b25d22; font-weight: 800; }
.risk-medium { color: var(--gold); font-weight: 800; }
.risk-low { color: var(--green); font-weight: 800; }
section[data-testid="stSidebar"] button p,
section[data-testid="stSidebar"] button span,
div.stButton > button p,
div.stButton > button span {
  color: inherit !important;
}
div.stButton > button {
  border-radius: 4px;
  border: 1px solid var(--ink);
  background: var(--ink);
  color: #fff;
  font-weight: 700;
  min-height: 42px;
  width: 100%;
}
div.stDownloadButton > button {
  border-radius: 4px;
  border: 1px solid var(--green);
  color: var(--green);
  font-weight: 700;
  min-height: 42px;
  width: 100%;
}
div[data-testid="stDataFrame"] {
  border: 1px solid rgba(200,188,168,.75);
}
@media (max-width: 900px) {
  .passport-title { font-size: 28px; }
  .diff-grid { grid-template-columns: 1fr; }
}
</style>
"""


def run_async(coro):
    return asyncio.run(coro)


def severity_class(severity: str) -> str:
    return {
        "Critical": "risk-critical",
        "High": "risk-high",
        "Medium": "risk-medium",
        "Low": "risk-low",
    }.get(severity, "")


def render_hero() -> None:
    st.markdown(
        """
        <div class="passport-hero">
          <div class="passport-kicker">Forensic Passport System</div>
          <div class="passport-title">Audit Passport</div>
          <div>
            A multi-agent audit desk that turns corrupted manufacturing data into ranked, evidence-backed,
            signable audit passports. Cognee stores semantic memory, not raw CSV rows.
          </div>
          <div class="stamp-row">
            <span class="stamp">Found</span>
            <span class="stamp">Ranked</span>
            <span class="stamp">Planned</span>
            <span class="stamp">Explained</span>
            <span class="stamp hot">Memory Ripple</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> tuple[bool, bool, bool]:
    st.sidebar.title("Audit controls")
    st.sidebar.caption("Track 01 Kaggle files must live under data/kaggle.")
    use_cognee = st.sidebar.checkbox(
        "Use Cognee semantic memory",
        value=False,
        help="Turn this on for the full memory demo. Leave off for the fastest local UI run.",
    )
    csvs = list_kaggle_csvs(DATA_DIR)
    st.sidebar.write(f"Detected CSV files: **{len(csvs)}**")
    for path in csvs[:8]:
        st.sidebar.caption(path.name)
    run_clicked = st.sidebar.button("Run Audit Agents", width="stretch")
    ripple_disabled = "audit_run" not in st.session_state or st.session_state.get("audit_run") is None
    ripple_clicked = st.sidebar.button("New Evidence Found", disabled=ripple_disabled, width="stretch")
    return run_clicked, ripple_clicked if "audit_run" in st.session_state else False, use_cognee


def metric_row(run) -> None:
    findings = run.findings if run else []
    score = run.report.readiness_score if run and run.report else readiness_score(findings)
    critical = sum(1 for item in findings if item.severity == "Critical")
    ready = sum(1 for item in findings if item.suggested_action in {"Safe Auto-Fix", "Suggested Fix"})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Audit readiness", f"{score}/100")
    c2.metric("Critical blockers", critical)
    c3.metric("Findings found", len(findings))
    c4.metric("Passports ready to sign", ready)


def outcome_for_stage(run, agent_number: int):
    if not run:
        return None
    needle = f"Agent {agent_number}"
    names = {
        1: "Data Ingestion",
        2: "Classification",
        3: "Reconciliation",
        4: "Narrative",
        5: "UI Demo",
    }
    for outcome in run.outcomes:
        if names[agent_number] in outcome.agent or needle in outcome.agent:
            return outcome
    return None


def render_agent_map(run) -> None:
    st.subheader("Five-agent handoff map")
    cols = st.columns(5)
    stages = [
        (1, "Find", "Profiles Kaggle data and writes source/schema/finding cards."),
        (2, "Rank", "Recalls findings and writes baseline plus risk ranking."),
        (3, "Act", "Writes reconciliation decisions and Memory Patch."),
        (4, "Explain", "Recalls evidence chain and writes PDF report."),
        (5, "Show", "Displays memory trail and records explicit feedback."),
    ]
    for col, (number, verb, desc) in zip(cols, stages):
        outcome = outcome_for_stage(run, number)
        reads = outcome.memory_reads if outcome else 0
        writes = outcome.memory_writes if outcome else 0
        status = "Ready" if outcome else "Waiting"
        col.markdown(
            f"""
            <div class="panel stage-card">
              <div>
              <span class="chip">Agent {number}</span>
              <span class="chip">{status}</span>
              <h3>{verb}</h3>
              <p>{desc}</p>
              </div>
              <div class="memory-count">
                <span class="memory-pill">Reads {reads}</span>
                <span class="memory-pill">Writes {writes}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def findings_dataframe(run) -> pd.DataFrame:
    rows = []
    for finding in run.findings:
        rows.append(
            {
                "ID": finding.finding_id,
                "Severity": finding.severity,
                "Risk": finding.risk_score,
                "Confidence": finding.confidence,
                "Type": finding.type,
                "Affected": finding.affected_entity,
                "Action": finding.suggested_action,
                "Status": finding.status,
            }
        )
    return pd.DataFrame(rows)


def render_findings(run) -> str | None:
    st.subheader("Passport queue")
    if not run.findings:
        st.info("No findings were generated from the current Kaggle files.")
        return None
    st.dataframe(findings_dataframe(run), hide_index=True, width="stretch")
    selected = st.selectbox(
        "Open an audit passport",
        [finding.finding_id for finding in run.findings],
        format_func=lambda item: f"{item} - {next(f.type for f in run.findings if f.finding_id == item)}",
    )
    return selected


def render_passport_detail(run, finding_id: str) -> None:
    finding = next(item for item in run.findings if item.finding_id == finding_id)
    st.subheader("Passport detail")
    st.markdown(
        f"""
        <div class="panel">
          <span class="chip">{finding.finding_id}</span>
          <span class="{severity_class(finding.severity)}">{finding.severity}</span>
          <h3>{finding.type}</h3>
          <p><strong>Affected entity:</strong> {finding.affected_entity}</p>
          <p><strong>Why it matters:</strong> {finding.why_broken}</p>
          <p><strong>Ranking reason:</strong> {finding.ranking_reason or 'Pending ranking'}</p>
          <p><strong>Recommended action:</strong> {finding.suggested_action}</p>
          <p><strong>Action rationale:</strong> {finding.action_rationale or 'Pending remediation'}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if finding.ripple_note:
        st.success(finding.ripple_note)
    st.markdown("**Evidence pointers**")
    st.dataframe(pd.DataFrame([asdict(ev) for ev in finding.evidence]), hide_index=True, width="stretch")

    with st.expander("Cognee memory trail for this passport", expanded=True):
        related = [
            event
            for event in run.memory_events
            if finding.finding_id in str(event) or event.get("event_type") in {"recall", "remember"}
        ][:20]
        if related:
            st.dataframe(display_safe_frame(related), hide_index=True, width="stretch")
        else:
            st.caption("No memory events recorded yet.")


def render_ripple(run) -> None:
    st.subheader("Memory Ripple")
    if not run.patches:
        st.markdown(
            """
            <div class="panel">
              <strong>No patch applied yet.</strong><br>
              Click <em>New Evidence Found</em> after the first run to show how one agent's memory update changes
              downstream ranking, remediation, and report language.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return
    patch = run.patches[-1]
    before = patch.before
    after = patch.after
    st.markdown(
        f"""
        <div class="panel">
          <span class="chip">{patch.patch_id}</span>
          <h3>{patch.change_type}</h3>
          <p>{patch.change_summary}</p>
          <p><strong>Reason:</strong> {patch.reason}</p>
          <p><strong>Affected findings:</strong> {', '.join(patch.affected_findings)}</p>
          <div class="diff-grid">
            <div class="diff-box">
              <div class="diff-label">Before</div>
              <strong>Risk {before.get('risk_score')}</strong><br>
              {before.get('action')}<br>
              <small>{before.get('interpretation')}</small>
            </div>
            <div class="diff-box">
              <div class="diff-label">After</div>
              <strong>Risk {after.get('risk_score')}</strong><br>
              {after.get('action')}<br>
              <small>{after.get('interpretation')}</small>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_report(run) -> None:
    if not run.report:
        st.info("Run the agents to generate the PDF report.")
        return
    st.markdown(f"**Executive summary:** {run.report.executive_summary}")
    st.markdown(f"**Open risks:** {len(run.report.open_risks)}")
    path = Path(run.report.pdf_path)
    if path.exists():
        st.download_button(
            "Download Audit PDF",
            data=path.read_bytes(),
            file_name=path.name,
            mime="application/pdf",
            width="stretch",
        )
    else:
        st.warning("PDF path was recorded but the file is not present.")


def render_feedback(run, use_cognee: bool) -> None:
    if not run.findings:
        return
    finding_id = st.selectbox("Finding to update", [item.finding_id for item in run.findings], key="feedback_finding")
    decision = st.radio("Feedback", ["Accept recommendation", "Reject recommendation", "Mark as needs review"], horizontal=True)
    note = st.text_input("Correction note")
    if st.button("Record feedback"):
        card = UserFeedbackCard(finding_id=finding_id, feedback=decision, note=note)
        recorder = MemoryRecorder(enabled=use_cognee)
        run_async(recorder.remember_card(card, "user_feedback", "UI Demo & Feedback Agent"))
        run.memory_events.extend(event.__dict__ for event in recorder.events)
        run.cognee_errors.extend(recorder.errors)
        st.session_state.audit_run = run
        st.success("Feedback recorded as semantic memory.")


def display_safe_frame(rows) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for col in frame.columns:
        if frame[col].dtype == "object":
            frame[col] = frame[col].map(lambda value: ", ".join(value) if isinstance(value, list) else str(value))
    return frame


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    render_hero()
    run_clicked, ripple_clicked, use_cognee = render_sidebar()

    if run_clicked:
        if not list_kaggle_csvs(DATA_DIR):
            st.session_state.audit_run = None
            st.error("No Kaggle CSV files found. Place Track 01 files under data/kaggle/ and run again.")
        else:
            with st.spinner("Running five-agent audit pipeline..."):
                st.session_state.audit_run = run_async(run_audit_pipeline(DATA_DIR, use_cognee=use_cognee))

    if ripple_clicked and st.session_state.get("audit_run"):
        with st.spinner("Applying Memory Ripple and regenerating report..."):
            st.session_state.audit_run = run_async(
                apply_memory_ripple(st.session_state.audit_run, use_cognee=use_cognee)
            )

    run = st.session_state.get("audit_run")
    metric_row(run)

    if not list_kaggle_csvs(DATA_DIR):
        st.warning("Kaggle Track 01 data is required. Add CSV files to data/kaggle/. The app will not create synthetic fallback data.")
        return

    render_agent_map(run)

    if run:
        if run.cognee_errors:
            st.warning("Cognee memory is degraded. The local product state still rendered; expand Memory Events for details.")
        left, right = st.columns([1.1, 0.9])
        with left:
            selected = render_findings(run)
            if selected:
                render_passport_detail(run, selected)
        with right:
            tabs = st.tabs(["Ripple", "Report", "Feedback"])
            with tabs[0]:
                render_ripple(run)
            with tabs[1]:
                render_report(run)
            with tabs[2]:
                render_feedback(run, use_cognee)

        with st.expander("Raw memory events and checkpoints"):
            if run.memory_events:
                st.dataframe(display_safe_frame(run.memory_events), hide_index=True, width="stretch")
            else:
                st.caption("No memory events recorded.")
            if run.cognee_errors:
                st.code("\n".join(run.cognee_errors))
    else:
        st.info("Click Run Audit Agents to create source cards, finding cards, rankings, reconciliation decisions, and a PDF report.")


if __name__ == "__main__":
    main()
