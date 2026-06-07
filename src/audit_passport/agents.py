from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import pandas as pd

from .data_loader import LoadedTable, evidence_for_rows, load_kaggle_tables, value_preview
from .memory import MemoryRecorder
from .models import (
    AgentOutcomeCard,
    AuditRun,
    ClassificationBaselineCard,
    Evidence,
    FindingCard,
    PROJECT_ID,
    ReconciliationDecisionCard,
    build_sessions,
    new_run_id,
)
from .probabilistic import attach_probabilistic_risk
from .report import generate_pdf


AGENT_1 = "Data Ingestion & Detective Agent"
AGENT_2 = "Classification & Risk Prioritizer Agent"
AGENT_3 = "Reconciliation & Remediation Agent"
AGENT_4 = "Narrative & Audit Report Agent"
AGENT_5 = "UI Demo & Feedback Agent"


def severity_from_score(score: int) -> str:
    if score >= 85:
        return "Critical"
    if score >= 70:
        return "High"
    if score >= 40:
        return "Medium"
    return "Low"


def entity_label(table: LoadedTable, row_index: int | None = None) -> str:
    schema = table.schema_card
    if row_index is not None:
        for col in schema.entity_columns:
            if col in table.dataframe.columns:
                value = table.dataframe.iloc[row_index][col]
                if pd.notna(value):
                    return f"{col}: {value_preview(value, 40)}"
    if schema.entity_columns:
        return f"{table.source_card.source_id} / {schema.entity_columns[0]}"
    return table.source_card.source_id


def make_finding(
    index: int,
    finding_type: str,
    affected_entity: str,
    why: str,
    evidence: list[Evidence],
    risk_score: int,
) -> FindingCard:
    return FindingCard(
        finding_id=f"F-{index:03d}",
        type=finding_type,
        severity=severity_from_score(risk_score),
        risk_score=risk_score,
        confidence=0.76,
        affected_entity=affected_entity,
        audit_risk="Could weaken regulatory audit readiness if left unresolved.",
        why_broken=why,
        suggested_action="Pending triage",
        status="Open",
        evidence=evidence,
        created_by_agent=AGENT_1,
        last_updated_by_agent=AGENT_1,
    )


def detect_duplicate_rows(table: LoadedTable, next_index: int) -> list[FindingCard]:
    duplicate_mask = table.dataframe.duplicated(keep=False)
    key_cols = [
        col
        for col in ["plant_id", "part_number", "customer_id", "production_date", "quantity", "weight_kg"]
        if col in table.dataframe.columns
    ]
    if not duplicate_mask.any() and len(key_cols) >= 4:
        duplicate_mask = table.dataframe.duplicated(key_cols, keep=False)
    if not duplicate_mask.any():
        return []
    rows = list(table.dataframe.index[duplicate_mask])[:4]
    evidence = evidence_for_rows(
        table,
        rows,
        str(table.dataframe.columns[0]),
        "Rows repeat the same record signature and may double-count a batch or inspection.",
        "duplicate row signature",
    )
    return [
        make_finding(
            next_index,
            "Duplicate records",
            table.source_card.source_id,
            "The same source table contains repeated business records. A duplicate can make an audit sample appear larger or cleaner than it is.",
            evidence,
            68,
        )
    ]


def detect_unit_conflicts(table: LoadedTable, next_index: int) -> list[FindingCard]:
    findings: list[FindingCard] = []
    df = table.dataframe
    if {"quantity", "unit"}.issubset(set(df.columns)):
        suspicious_units = {"mm", "cm", "meter", "m", "kg", "lb"}
        units = {str(value).lower() for value in df["unit"].dropna().unique()}
        if units & suspicious_units:
            rows = list(df.index[df["unit"].astype(str).str.lower().isin(suspicious_units)])[:4]
            evidence = evidence_for_rows(
                table,
                rows,
                "unit",
                "Quantity is paired with a physical measurement unit, so count versus measurement semantics need reconciliation.",
                ", ".join(sorted(units & suspicious_units)),
            )
            findings.append(
                make_finding(
                    next_index,
                    "Unit conflict",
                    table.source_card.source_id,
                    "Quantity values are labeled with a dimensional unit. A compliance user must confirm whether quantity means count, length, or another measurement before using it in audit calculations.",
                    evidence,
                    82,
                )
            )
            return findings
    if not table.schema_card.unit_columns or not table.schema_card.entity_columns:
        return findings
    entity_col = table.schema_card.entity_columns[0]
    for unit_col in table.schema_card.unit_columns:
        if entity_col not in df.columns or unit_col not in df.columns:
            continue
        grouped = df[[entity_col, unit_col]].dropna().groupby(entity_col)[unit_col].nunique()
        conflicts = grouped[grouped > 1]
        if conflicts.empty:
            continue
        entity_value = conflicts.index[0]
        rows = list(df.index[df[entity_col] == entity_value])[:4]
        units = sorted(str(x) for x in df.loc[rows, unit_col].dropna().unique())
        evidence = evidence_for_rows(
            table,
            rows,
            unit_col,
            "The same entity appears with multiple unit labels.",
            ", ".join(units),
        )
        findings.append(
            make_finding(
                next_index + len(findings),
                "Unit conflict",
                f"{entity_col}: {value_preview(entity_value, 40)}",
                "The same auditable entity has measurements expressed with incompatible units, so raw numeric comparison can create false contradictions.",
                evidence,
                82,
            )
        )
        break
    return findings


def detect_impossible_dates(table: LoadedTable, next_index: int) -> list[FindingCard]:
    df = table.dataframe.copy()
    if not {"production_date", "ship_date"}.issubset(set(df.columns)):
        return []
    production = pd.to_datetime(df["production_date"], errors="coerce")
    shipped = pd.to_datetime(df["ship_date"], errors="coerce")
    mask = shipped < production
    if not mask.any():
        return []
    rows = list(df.index[mask])[:4]
    evidence = []
    for row in rows:
        evidence.append(
            Evidence(
                source_file=table.path.name,
                row_number=str(row + 2),
                field_name="ship_date",
                observed_value=value_preview(df.iloc[row]["ship_date"]),
                expected_or_conflicting_value=f"after production_date {value_preview(df.iloc[row]['production_date'])}",
                explanation="Shipping date appears before production date.",
            )
        )
    return [
        make_finding(
            next_index,
            "Impossible dates",
            entity_label(table, rows[0]),
            "A shipment is recorded before the item was produced, which breaks audit chronology and evidence sign-off.",
            evidence,
            91,
        )
    ]


def detect_impossible_values(table: LoadedTable, next_index: int) -> list[FindingCard]:
    df = table.dataframe
    if "quantity" not in df.columns:
        return []
    mask = pd.to_numeric(df["quantity"], errors="coerce") <= 0
    if not mask.any():
        return []
    rows = list(df.index[mask])[:4]
    evidence = evidence_for_rows(
        table,
        rows,
        "quantity",
        "Quantity should be positive for manufactured inventory records.",
        "positive quantity",
    )
    return [
        make_finding(
            next_index,
            "Impossible values",
            entity_label(table, rows[0]),
            "A manufacturing record has a non-positive quantity, which cannot be accepted without correction or explicit voiding evidence.",
            evidence,
            86,
        )
    ]


def detect_orphaned_references(table: LoadedTable, next_index: int, lookup_tables: list[LoadedTable]) -> list[FindingCard]:
    df = table.dataframe
    if "customer_id" not in df.columns:
        return []
    customer_table = next(
        (
            lookup
            for lookup in lookup_tables
            if lookup.path.name != table.path.name and "customer_id" in lookup.dataframe.columns
        ),
        None,
    )
    if customer_table is None:
        return []
    valid_customers = set(customer_table.dataframe["customer_id"].dropna().astype(str))
    mask = ~df["customer_id"].dropna().astype(str).isin(valid_customers)
    if not mask.any():
        return []
    rows = list(df.index[mask])[:4]
    evidence = evidence_for_rows(
        table,
        rows,
        "customer_id",
        "Customer reference does not appear in the companion customer master file.",
        "customer_id present in track01_customers.csv",
    )
    return [
        make_finding(
            next_index,
            "Orphaned reference",
            entity_label(table, rows[0]),
            "A production record points to a customer that is missing from the customer master, leaving the audit evidence chain incomplete.",
            evidence,
            79,
        )
    ]


def detect_contradictory_numbers(table: LoadedTable, next_index: int) -> list[FindingCard]:
    findings: list[FindingCard] = []
    df = table.dataframe
    if not table.schema_card.entity_columns or not table.schema_card.numeric_columns:
        return findings
    entity_col = table.schema_card.entity_columns[0]
    for numeric_col in table.schema_card.numeric_columns[:6]:
        grouped = df[[entity_col, numeric_col]].dropna().groupby(entity_col)[numeric_col]
        spread = grouped.agg(["min", "max", "count"])
        spread = spread[(spread["count"] > 1) & (spread["max"] != spread["min"])]
        if spread.empty:
            continue
        spread["relative_gap"] = (spread["max"] - spread["min"]).abs() / spread["max"].replace(0, math.nan)
        spread = spread.sort_values("relative_gap", ascending=False)
        entity_value = spread.index[0]
        rows = list(df.index[df[entity_col] == entity_value])[:4]
        values = sorted(str(value_preview(x, 32)) for x in df.loc[rows, numeric_col].dropna().unique())
        evidence = evidence_for_rows(
            table,
            rows,
            numeric_col,
            "The same entity has different numeric values across records.",
            ", ".join(values),
        )
        findings.append(
            make_finding(
                next_index + len(findings),
                "Contradictory numbers",
                f"{entity_col}: {value_preview(entity_value, 40)}",
                "The same auditable entity carries conflicting numeric values, which can undermine inspection, shipment, or regulatory calculations.",
                evidence,
                88,
            )
        )
        break
    return findings


def detect_missing_evidence(table: LoadedTable, next_index: int) -> list[FindingCard]:
    missing_rates = table.source_card.quality_summary.get("missing_rate", {})
    if not missing_rates:
        return []
    field_name = next(iter(missing_rates.keys()))
    rows = list(table.dataframe.index[table.dataframe[field_name].isna()])[:4]
    if not rows:
        return []
    evidence = evidence_for_rows(
        table,
        rows,
        field_name,
        "A field needed for audit traceability is missing in these source rows.",
        "non-empty audit evidence field",
    )
    return [
        make_finding(
            next_index,
            "Missing evidence",
            table.source_card.source_id,
            "A source field has missing values, leaving part of the audit evidence chain incomplete.",
            evidence,
            74,
        )
    ]


async def run_data_detective(memory: MemoryRecorder, data_dir: Path) -> tuple[list[LoadedTable], list[FindingCard], list[AgentOutcomeCard]]:
    agent = AGENT_1
    await memory.recall(
        "Find prior data source, schema, and active memory patches before ingesting Kaggle audit data.",
        ["sources", "schema", "memory_patches"],
        agent,
    )
    tables = load_kaggle_tables(data_dir)
    findings: list[FindingCard] = []
    for table in tables:
        await memory.remember_card(table.source_card, "sources", agent)
        await memory.remember_card(table.schema_card, "schema", agent)
        findings.extend(detect_orphaned_references(table, len(findings) + 1, tables))
        detectors = (
            detect_impossible_dates,
            detect_impossible_values,
            detect_unit_conflicts,
            detect_contradictory_numbers,
            detect_duplicate_rows,
            detect_missing_evidence,
        )
        for detector in detectors:
            findings.extend(detector(table, len(findings) + 1))
    for finding in findings:
        await memory.remember_card(finding, "findings", agent)
    outcome = AgentOutcomeCard(
        agent=agent,
        task="Profile Kaggle manufacturing data and create evidence-backed finding cards without storing full raw rows in Cognee.",
        read_datasets=["sources", "schema", "memory_patches"],
        wrote_datasets=["sources", "schema", "findings", "agent_outcomes"],
        outcome=f"Loaded {len(tables)} source files and produced {len(findings)} finding cards.",
        reason="Cognee stores semantic cards and evidence pointers; raw CSV remains in data/kaggle.",
        evidence_refs=[finding.finding_id for finding in findings[:5]],
        memory_reads=1,
        memory_writes=2 + len(findings),
    )
    await memory.remember_card(outcome, "agent_outcomes", agent)
    return tables, findings, [outcome]


async def run_risk_prioritizer(
    memory: MemoryRecorder,
    findings: list[FindingCard],
) -> tuple[list[FindingCard], list[ClassificationBaselineCard], list[AgentOutcomeCard]]:
    agent = AGENT_2
    await memory.recall(
        "Rank audit findings using source cards, schema cards, finding cards, and active memory patches.",
        ["sources", "schema", "findings", "baselines", "memory_patches"],
        agent,
    )
    baseline = ClassificationBaselineCard(
        baseline_id="BL-001",
        critical_fields=["batch", "supplier", "inspection", "shipment", "potency", "weight", "quantity", "status"],
        audit_sensitive_issue_types=["Contradictory numbers", "Unit conflict", "Missing evidence", "Duplicate records"],
        severity_rules={
            "Critical": "Score 85-100: direct contradiction in auditable measurement or unresolved regulatory evidence.",
            "High": "Score 70-84: likely audit blocker but can be explained or contained.",
            "Medium": "Score 40-69: needs review, lower direct audit impact.",
            "Low": "Score 0-39: cosmetic or localized issue.",
        },
        unit_rules={"mg_to_g": "Normalize milligrams and grams before treating values as contradictions."},
        confidence=0.82,
    )
    await memory.remember_card(baseline, "baselines", agent)
    ranked: list[FindingCard] = []
    for finding in findings:
        score = finding.risk_score
        reason_parts = []
        if finding.type in {"Contradictory numbers", "Unit conflict"}:
            score += 6
            reason_parts.append("The issue touches auditable measurements.")
        if len(finding.evidence) >= 2:
            score += 4
            reason_parts.append("Multiple evidence pointers support the finding.")
        if finding.type == "Duplicate records":
            score -= 8
            reason_parts.append("Duplicate records are usually easier to quarantine than numeric contradictions.")
        score = max(0, min(100, score))
        ranked_finding = replace(
                finding,
                risk_score=score,
                severity=severity_from_score(score),
                confidence=min(0.96, round(finding.confidence + 0.08, 2)),
                ranking_reason=" ".join(reason_parts)
                or "Ranked using audit impact, evidence strength, and remediation difficulty.",
                last_updated_by_agent=agent,
            )
        ranked.append(attach_probabilistic_risk(ranked_finding))
    ranked.sort(key=lambda item: item.risk_score, reverse=True)
    for finding in ranked:
        await memory.remember_card(finding, "findings", agent)
    outcome = AgentOutcomeCard(
        agent=agent,
        task="Create audit classification baseline and rank findings by regulatory risk.",
        read_datasets=["sources", "schema", "findings", "baselines", "memory_patches"],
        wrote_datasets=["baselines", "findings", "agent_outcomes"],
        outcome=f"Ranked {len(ranked)} findings. Top risk: {ranked[0].finding_id if ranked else 'none'}.",
        reason="Agent 2 recalled Agent 1 finding cards and applied severity rules instead of rescanning raw CSV.",
        evidence_refs=[finding.finding_id for finding in ranked[:5]],
        memory_reads=1,
        memory_writes=1 + len(ranked),
    )
    await memory.remember_card(outcome, "agent_outcomes", agent)
    return ranked, [baseline], [outcome]


async def run_remediation_planner(
    memory: MemoryRecorder,
    findings: list[FindingCard],
) -> tuple[list[FindingCard], list[ReconciliationDecisionCard], list[AgentOutcomeCard]]:
    agent = AGENT_3
    await memory.recall(
        "Plan remediation from ranked findings, classification baselines, prior reconciliation decisions, and patches.",
        ["findings", "baselines", "reconciliation", "memory_patches"],
        agent,
    )
    planned: list[FindingCard] = []
    decisions: list[ReconciliationDecisionCard] = []
    for finding in findings:
        if finding.type == "Duplicate records":
            action = "Safe Auto-Fix"
            rationale = "Duplicate rows can be quarantined or de-duplicated with a reversible audit log."
        elif finding.type == "Unit conflict":
            action = "Manual Review Required"
            rationale = "Unit conflicts need source metadata before numeric values are normalized."
        elif finding.risk_score >= 85:
            action = "Escalate"
            rationale = "The finding affects high-risk audit evidence and needs supervisor review before sign-off."
        else:
            action = "Suggested Fix"
            rationale = "Evidence is strong enough for a recommended correction, but a human should confirm it."
        updated = replace(
            finding,
            suggested_action=action,
            action_rationale=rationale,
            last_updated_by_agent=agent,
        )
        planned.append(updated)
        evidence_refs = [f"{item.source_file}:{item.row_number}" for item in finding.evidence]
        decisions.append(
            ReconciliationDecisionCard(
                decision_id=f"RD-{finding.finding_id[2:]}",
                finding_id=finding.finding_id,
                conflict=finding.why_broken,
                chosen_resolution=action,
                evidence_refs=evidence_refs,
                affected_agents=[AGENT_2, AGENT_4],
                rationale=rationale,
            )
        )
    for decision in decisions:
        await memory.remember_card(decision, "reconciliation", agent)
    for finding in planned:
        await memory.remember_card(finding, "findings", agent)
    outcome = AgentOutcomeCard(
        agent=agent,
        task="Choose fix, flag, manual review, or escalation for ranked findings.",
        read_datasets=["findings", "baselines", "reconciliation", "memory_patches"],
        wrote_datasets=["reconciliation", "findings", "agent_outcomes"],
        outcome=f"Created {len(decisions)} remediation decisions.",
        reason="Agent 3 recalled ranked findings and classification baselines, then wrote action rationales and reconciliation cards.",
        evidence_refs=[decision.decision_id for decision in decisions[:5]],
        memory_reads=1,
        memory_writes=len(decisions) + len(planned),
    )
    await memory.remember_card(outcome, "agent_outcomes", agent)
    return planned, decisions, [outcome]


async def run_audit_narrator(
    memory: MemoryRecorder,
    findings: list[FindingCard],
    patches: list,
) -> tuple[list, object, list[AgentOutcomeCard]]:
    agent = AGENT_4
    await memory.recall(
        "Generate a compliance officer readable audit summary from source, findings, baselines, decisions, patches, and outcomes.",
        ["sources", "schema", "findings", "baselines", "reconciliation", "memory_patches", "agent_outcomes"],
        agent,
    )
    from .models import InsightCard

    top = findings[:3]
    insights = [
        InsightCard(
            insight_id=f"IN-{idx:03d}",
            claim=(
                f"{finding.finding_id} is a {finding.severity.lower()} audit risk because "
                f"{finding.why_broken}"
            ),
            evidence_refs=[f"{ev.source_file}:{ev.row_number}" for ev in finding.evidence],
            confidence=finding.confidence,
            caveats=[
                "Finding uses evidence pointers, not full raw rows in Cognee.",
                "Manual confirmation is required before production data is changed.",
            ],
            status="candidate",
        )
        for idx, finding in enumerate(top, start=1)
    ]
    for insight in insights:
        await memory.remember_card(insight, "insights", agent)
    report = generate_pdf(findings, patches)
    await memory.remember_card(report, "reports", agent)
    outcome = AgentOutcomeCard(
        agent=agent,
        task="Generate evidence-backed executive summary and downloadable PDF from accepted memory cards.",
        read_datasets=["sources", "schema", "findings", "baselines", "reconciliation", "memory_patches", "agent_outcomes"],
        wrote_datasets=["insights", "reports", "agent_outcomes"],
        outcome=f"Generated report {report.report_id} with readiness score {report.readiness_score}.",
        reason="Agent 4 recalled prior agent handoffs and generated a signable narrative instead of reprocessing raw CSV.",
        evidence_refs=[finding.finding_id for finding in top],
        memory_reads=1,
        memory_writes=len(insights) + 1,
    )
    await memory.remember_card(outcome, "agent_outcomes", agent)
    return insights, report, [outcome]


async def run_ui_feedback_agent(memory: MemoryRecorder, run: AuditRun, feedback: str = "") -> list[AgentOutcomeCard]:
    agent = AGENT_5
    await memory.recall(
        "Render memory timeline, agent outcomes, memory patches, insights, and user feedback for the demo UI.",
        ["agent_outcomes", "memory_patches", "insights", "user_feedback"],
        agent,
    )
    outcome = AgentOutcomeCard(
        agent=agent,
        task="Expose the handoff timeline and collect compliance officer feedback without writing ordinary UI clicks to memory.",
        read_datasets=["agent_outcomes", "memory_patches", "insights", "user_feedback"],
        wrote_datasets=["agent_outcomes"] + (["user_feedback"] if feedback else []),
        outcome="Memory timeline and evidence drill-down are available in the Streamlit interface.",
        reason="The UI agent makes Cognee handoff inspectable and only promotes explicit user feedback.",
        evidence_refs=[event.get("dataset", "") for event in run.memory_events[:5]],
        memory_reads=1,
        memory_writes=1,
    )
    await memory.remember_card(outcome, "agent_outcomes", agent)
    return [outcome]


async def run_audit_pipeline(data_dir: Path, use_cognee: bool = True) -> AuditRun:
    run_id = new_run_id()
    sessions = build_sessions(run_id)
    memory = MemoryRecorder(enabled=use_cognee)
    run = AuditRun(
        project_id=PROJECT_ID,
        run_id=run_id,
        shared_session_id=sessions["shared"],
        agent_sessions={key: value for key, value in sessions.items() if key != "shared"},
        cognee_enabled=use_cognee,
    )
    tables, findings, outcomes = await run_data_detective(memory, data_dir)
    run.data_sources = [table.source_card for table in tables]
    run.schemas = [table.schema_card for table in tables]
    run.findings = findings
    run.outcomes.extend(outcomes)

    ranked, baselines, outcomes = await run_risk_prioritizer(memory, run.findings)
    run.findings = ranked
    run.baselines = baselines
    run.outcomes.extend(outcomes)

    planned, decisions, outcomes = await run_remediation_planner(memory, run.findings)
    run.findings = sorted(planned, key=lambda item: item.risk_score, reverse=True)
    run.decisions = decisions
    run.outcomes.extend(outcomes)

    insights, report, outcomes = await run_audit_narrator(memory, run.findings, run.patches)
    run.insights = insights
    run.report = report
    run.outcomes.extend(outcomes)

    outcomes = await run_ui_feedback_agent(memory, run)
    run.outcomes.extend(outcomes)

    run.memory_events = [event.__dict__ for event in memory.events]
    run.cognee_errors = memory.errors
    return run
