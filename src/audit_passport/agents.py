from __future__ import annotations

import math
from dataclasses import asdict
from dataclasses import replace
from pathlib import Path
from typing import Any

import pandas as pd

from .data_loader import LoadedTable, evidence_for_rows, load_kaggle_tables, value_preview
from .memory import MemoryRecorder
from .models import (
    AgentOutcomeCard,
    AgentPromptTraceCard,
    AuditRun,
    ClassificationBaselineCard,
    DataSourceCard,
    DetectionCandidateCard,
    Evidence,
    FeedbackDigestCard,
    FindingCard,
    InsightCard,
    PROJECT_ID,
    ReconciliationDecisionCard,
    SchemaCard,
    build_sessions,
    new_run_id,
    slug_time,
)
from .gpt_agents import GptAgentClient, JsonSchemaSpec
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


def card_dict(card: Any) -> dict[str, Any]:
    return asdict(card)


def evidence_from_dict(value: dict[str, Any]) -> Evidence:
    return Evidence(
        source_file=str(value.get("source_file", "")),
        row_number=str(value.get("row_number", "")),
        field_name=str(value.get("field_name", "")),
        observed_value=str(value.get("observed_value", "")),
        expected_or_conflicting_value=str(value.get("expected_or_conflicting_value", "")),
        explanation=str(value.get("explanation", "")),
    )


def dict_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def insight_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            items.append(item)
        elif isinstance(item, str) and item.strip():
            items.append({"claim": item.strip(), "evidence_refs": [], "confidence": 0.7, "caveats": []})
    return items


def dict_value(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def candidate_from_rule_finding(index: int, table: LoadedTable, finding: FindingCard) -> DetectionCandidateCard:
    return DetectionCandidateCard(
        candidate_id=f"DC-{index:03d}",
        source_id=table.source_card.source_id,
        candidate_type=finding.type,
        affected_entity=finding.affected_entity,
        detector_reason=finding.why_broken,
        suggested_risk_score=finding.risk_score,
        evidence=finding.evidence,
    )


def build_detection_candidates(tables: list[LoadedTable]) -> list[DetectionCandidateCard]:
    candidates: list[DetectionCandidateCard] = []
    detectors = (
        detect_impossible_dates,
        detect_impossible_values,
        detect_unit_conflicts,
        detect_contradictory_numbers,
        detect_duplicate_rows,
        detect_missing_evidence,
    )
    for table in tables:
        rule_findings = detect_orphaned_references(table, len(candidates) + 1, tables)
        for detector in detectors:
            rule_findings.extend(detector(table, len(candidates) + len(rule_findings) + 1))
        for finding in rule_findings:
            candidates.append(candidate_from_rule_finding(len(candidates) + 1, table, finding))
    return candidates


def latest_findings(cards: list[FindingCard]) -> list[FindingCard]:
    by_id: dict[str, FindingCard] = {}
    for card in cards:
        by_id[card.finding_id] = card
    return list(by_id.values())


async def remember_many(
    memory: MemoryRecorder,
    cards: list[Any],
    dataset_key: str,
    agent: str,
    session_id: str,
    shared_session_id: str,
) -> None:
    await memory.remember_cards(cards, dataset_key, agent, session_id=session_id, shared_session_id=shared_session_id)


async def remember_trace(
    memory: MemoryRecorder,
    trace: AgentPromptTraceCard,
    agent: str,
    session_id: str,
    shared_session_id: str,
) -> None:
    await memory.remember_card(trace, "prompt_traces", agent, session_id=session_id, shared_session_id=shared_session_id)


def finding_from_agent(data: dict[str, Any], agent: str) -> FindingCard:
    score = int(data.get("risk_score", 50))
    evidence = [evidence_from_dict(item) for item in dict_items(data.get("evidence", []))]
    return FindingCard(
        finding_id=str(data.get("finding_id") or f"F-{slug_time()}"),
        type=str(data.get("type") or data.get("candidate_type") or "Audit finding"),
        severity=str(data.get("severity") or severity_from_score(score)),
        risk_score=max(0, min(100, score)),
        confidence=float(data.get("confidence", 0.78)),
        affected_entity=str(data.get("affected_entity", "")),
        audit_risk=str(data.get("audit_risk", "May weaken audit readiness.")),
        why_broken=str(data.get("why_broken", "")),
        suggested_action=str(data.get("suggested_action", "Pending triage")),
        status=str(data.get("status", "Open")),
        evidence=evidence,
        created_by_agent=str(data.get("created_by_agent", AGENT_1)),
        last_updated_by_agent=agent,
        ranking_reason=str(data.get("ranking_reason", "")),
        action_rationale=str(data.get("action_rationale", "")),
    )


def baseline_from_agent(data: dict[str, Any]) -> ClassificationBaselineCard:
    return ClassificationBaselineCard(
        baseline_id=str(data.get("baseline_id", "BL-001")),
        critical_fields=[str(item) for item in data.get("critical_fields", [])],
        audit_sensitive_issue_types=[str(item) for item in data.get("audit_sensitive_issue_types", [])],
        severity_rules={str(key): str(value) for key, value in data.get("severity_rules", {}).items()},
        unit_rules={str(key): str(value) for key, value in data.get("unit_rules", {}).items()},
        confidence=float(data.get("confidence", 0.8)),
    )


def outcome_from_agent(data: dict[str, Any], agent: str, read: list[str], wrote: list[str]) -> AgentOutcomeCard:
    return AgentOutcomeCard(
        agent=agent,
        task=str(data.get("task", "")),
        read_datasets=read,
        wrote_datasets=wrote,
        outcome=str(data.get("outcome", "")),
        reason=str(data.get("reason", "")),
        evidence_refs=[str(item) for item in data.get("evidence_refs", [])],
        memory_reads=len(read),
        memory_writes=len(wrote),
    )


def agent_schema(name: str, required: tuple[str, ...], properties: dict[str, Any]) -> JsonSchemaSpec:
    return JsonSchemaSpec(
        name=name,
        required_top_level=required,
        schema={
            "type": "object",
            "additionalProperties": True,
            "required": list(required),
            "properties": properties,
        },
    )


INGEST_SCHEMA = agent_schema(
    "ingestion_agent_output",
    ("findings", "outcome"),
    {"findings": {"type": "array"}, "outcome": {"type": "object"}},
)
RISK_SCHEMA = agent_schema(
    "risk_agent_output",
    ("baseline", "ranking_updates", "outcome"),
    {"baseline": {"type": "object"}, "ranking_updates": {"type": "array"}, "outcome": {"type": "object"}},
)
REMEDIATION_SCHEMA = agent_schema(
    "remediation_agent_output",
    ("action_updates", "decisions", "outcome"),
    {"action_updates": {"type": "array"}, "decisions": {"type": "array"}, "outcome": {"type": "object"}},
)
NARRATIVE_SCHEMA = agent_schema(
    "narrative_agent_output",
    ("insights", "report_narrative", "outcome"),
    {"insights": {"type": "array"}, "report_narrative": {"type": "object"}, "outcome": {"type": "object"}},
)
FEEDBACK_SCHEMA = agent_schema(
    "feedback_agent_output",
    ("feedback_digest", "outcome"),
    {"feedback_digest": {"type": "object"}, "outcome": {"type": "object"}},
)


async def run_data_detective(
    memory: MemoryRecorder,
    llm: GptAgentClient,
    data_dir: Path,
    sessions: dict[str, str],
) -> tuple[list[LoadedTable], list[DetectionCandidateCard], list[FindingCard], list[AgentOutcomeCard], list[AgentPromptTraceCard]]:
    agent = AGENT_1
    session_id = sessions["ingest"]
    shared_session_id = sessions["shared"]
    prior_context = await memory.recall(
        "Find prior data source, schema, active memory patches, and past ingestion decisions before ingesting Kaggle audit data.",
        ["sources", "schema", "memory_patches"],
        agent,
        session_id=shared_session_id,
    )
    tables = load_kaggle_tables(data_dir)
    candidates = build_detection_candidates(tables)
    await remember_many(memory, [table.source_card for table in tables], "sources", agent, session_id, shared_session_id)
    await remember_many(memory, [table.schema_card for table in tables], "schema", agent, session_id, shared_session_id)
    await remember_many(memory, candidates, "detection_candidates", agent, session_id, shared_session_id)

    result = await llm.run_json(
        agent,
        "You are Agent 1, the ingestion and data detective agent. Promote deterministic detector candidates into evidence-backed FindingCard JSON. Do not invent raw rows. Use only evidence pointers provided.",
        {
            "agent_setting": {"role": agent, "goal": "turn script candidates into audit findings"},
            "prior_cognee_context": prior_context,
            "sources": [card_dict(table.source_card) for table in tables],
            "schemas": [card_dict(table.schema_card) for table in tables],
            "detection_candidates": [card_dict(candidate) for candidate in candidates],
            "output_contract": "Return findings[] as FindingCard-shaped objects and outcome as AgentOutcome-shaped fields.",
        },
        INGEST_SCHEMA,
        ["sources", "schema", "memory_patches"],
        ["findings", "agent_outcomes", "prompt_traces"],
    )
    findings = [finding_from_agent(item, agent) for item in dict_items(result.data.get("findings", []))]
    outcome = outcome_from_agent(
        dict_value(result.data.get("outcome", {})),
        agent,
        ["sources", "schema", "memory_patches"],
        ["sources", "schema", "detection_candidates", "findings", "agent_outcomes", "prompt_traces"],
    )
    await remember_many(memory, findings, "findings", agent, session_id, shared_session_id)
    await memory.remember_card(outcome, "agent_outcomes", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_trace(memory, result.trace, agent, session_id, shared_session_id)
    return tables, candidates, findings, [outcome], [result.trace]


async def run_risk_prioritizer(
    memory: MemoryRecorder,
    llm: GptAgentClient,
    sessions: dict[str, str],
) -> tuple[list[FindingCard], list[ClassificationBaselineCard], list[AgentOutcomeCard], list[AgentPromptTraceCard]]:
    agent = AGENT_2
    session_id = sessions["classify"]
    shared_session_id = sessions["shared"]
    findings = await memory.recall_cards(
        "Recall every active FindingCard created by Agent 1 for risk ranking.",
        ["findings"],
        agent,
        (FindingCard,),
        top_k=60,
        session_id=shared_session_id,
        required=True,
    )
    findings = latest_findings(findings)
    sources = await memory.recall_cards("Recall source cards for ranking context.", ["sources"], agent, (DataSourceCard,), top_k=20, session_id=shared_session_id)
    schemas = await memory.recall_cards("Recall schema cards for ranking context.", ["schema"], agent, (SchemaCard,), top_k=20, session_id=shared_session_id)
    result = await llm.run_json(
        agent,
        "You are Agent 2, the classification and risk prioritizer. Read recalled FindingCards from Cognee, create a baseline, and rank/update each finding. Return only updates for recalled finding IDs.",
        {
            "agent_setting": {"role": agent, "goal": "rank audit findings by regulatory risk"},
            "recalled_findings": [card_dict(item) for item in findings],
            "recalled_sources": [card_dict(item) for item in sources],
            "recalled_schemas": [card_dict(item) for item in schemas],
            "output_contract": "Return baseline, ranking_updates[{finding_id,risk_score,severity,confidence,ranking_reason}], and outcome.",
        },
        RISK_SCHEMA,
        ["sources", "schema", "findings"],
        ["baselines", "findings", "agent_outcomes", "prompt_traces"],
    )
    baseline = baseline_from_agent(dict_value(result.data.get("baseline", {})))
    by_id = {finding.finding_id: finding for finding in findings}
    ranked: list[FindingCard] = []
    for update in dict_items(result.data.get("ranking_updates", [])):
        finding = by_id.get(str(update.get("finding_id")))
        if finding is None:
            continue
        score = max(0, min(100, int(update.get("risk_score", finding.risk_score))))
        ranked.append(
            attach_probabilistic_risk(
                replace(
                    finding,
                    risk_score=score,
                    severity=str(update.get("severity") or severity_from_score(score)),
                    confidence=float(update.get("confidence", finding.confidence)),
                    ranking_reason=str(update.get("ranking_reason", "")),
                    last_updated_by_agent=agent,
                )
            )
        )
    if not ranked:
        raise RuntimeError(f"{agent} produced no ranking updates for recalled findings.")
    ranked.sort(key=lambda item: item.risk_score, reverse=True)
    outcome = outcome_from_agent(dict_value(result.data.get("outcome", {})), agent, ["sources", "schema", "findings"], ["baselines", "findings", "agent_outcomes", "prompt_traces"])
    await memory.remember_card(baseline, "baselines", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_many(memory, ranked, "findings", agent, session_id, shared_session_id)
    await memory.remember_card(outcome, "agent_outcomes", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_trace(memory, result.trace, agent, session_id, shared_session_id)
    return ranked, [baseline], [outcome], [result.trace]


async def run_remediation_planner(
    memory: MemoryRecorder,
    llm: GptAgentClient,
    sessions: dict[str, str],
) -> tuple[list[FindingCard], list[ReconciliationDecisionCard], list[AgentOutcomeCard], list[AgentPromptTraceCard]]:
    agent = AGENT_3
    session_id = sessions["reconcile"]
    shared_session_id = sessions["shared"]
    findings = await memory.recall_cards(
        "Recall ranked FindingCards with probability fields for remediation planning.",
        ["findings"],
        agent,
        (FindingCard,),
        top_k=80,
        session_id=shared_session_id,
        required=True,
    )
    findings = latest_findings(findings)
    baselines = await memory.recall_cards("Recall classification baseline.", ["baselines"], agent, (ClassificationBaselineCard,), top_k=10, session_id=shared_session_id)
    result = await llm.run_json(
        agent,
        "You are Agent 3, the reconciliation and remediation agent. Use only recalled ranked findings and baselines. Choose action: Safe Auto-Fix, Suggested Fix, Manual Review Required, or Escalate.",
        {
            "agent_setting": {"role": agent, "goal": "choose auditable remediation actions"},
            "recalled_ranked_findings": [card_dict(item) for item in findings],
            "recalled_baselines": [card_dict(item) for item in baselines],
            "output_contract": "Return action_updates and decisions. Each decision must reference a recalled finding_id.",
        },
        REMEDIATION_SCHEMA,
        ["findings", "baselines"],
        ["reconciliation", "findings", "agent_outcomes", "prompt_traces"],
    )
    by_id = {finding.finding_id: finding for finding in findings}
    planned: list[FindingCard] = []
    for update in dict_items(result.data.get("action_updates", [])):
        finding = by_id.get(str(update.get("finding_id")))
        if finding is None:
            continue
        planned.append(
            replace(
                finding,
                suggested_action=str(update.get("suggested_action", finding.suggested_action)),
                action_rationale=str(update.get("action_rationale", "")),
                last_updated_by_agent=agent,
            )
        )
    decisions = [
        ReconciliationDecisionCard(
            decision_id=str(item.get("decision_id", f"RD-{idx:03d}")),
            finding_id=str(item.get("finding_id", "")),
            conflict=str(item.get("conflict", "")),
            chosen_resolution=str(item.get("chosen_resolution", "")),
            evidence_refs=[str(ref) for ref in item.get("evidence_refs", [])],
            affected_agents=[str(ref) for ref in item.get("affected_agents", [AGENT_2, AGENT_4])],
            rationale=str(item.get("rationale", "")),
        )
        for idx, item in enumerate(dict_items(result.data.get("decisions", [])), start=1)
        if str(item.get("finding_id", "")) in by_id
    ]
    if not planned:
        raise RuntimeError(f"{agent} produced no action updates for recalled findings.")
    planned.sort(key=lambda item: item.risk_score, reverse=True)
    outcome = outcome_from_agent(dict_value(result.data.get("outcome", {})), agent, ["findings", "baselines"], ["reconciliation", "findings", "agent_outcomes", "prompt_traces"])
    await remember_many(memory, decisions, "reconciliation", agent, session_id, shared_session_id)
    await remember_many(memory, planned, "findings", agent, session_id, shared_session_id)
    await memory.remember_card(outcome, "agent_outcomes", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_trace(memory, result.trace, agent, session_id, shared_session_id)
    return planned, decisions, [outcome], [result.trace]


async def run_audit_narrator(
    memory: MemoryRecorder,
    llm: GptAgentClient,
    sessions: dict[str, str],
    patches: list,
) -> tuple[list[InsightCard], object, list[AgentOutcomeCard], list[AgentPromptTraceCard]]:
    agent = AGENT_4
    session_id = sessions["narrative"]
    shared_session_id = sessions["shared"]
    findings = latest_findings(await memory.recall_cards("Recall final remediated findings for the report.", ["findings"], agent, (FindingCard,), top_k=80, session_id=shared_session_id, required=True))
    decisions = await memory.recall_cards("Recall remediation decisions for the report.", ["reconciliation"], agent, (ReconciliationDecisionCard,), top_k=80, session_id=shared_session_id)
    baselines = await memory.recall_cards("Recall baselines for the report.", ["baselines"], agent, (ClassificationBaselineCard,), top_k=10, session_id=shared_session_id)
    result = await llm.run_json(
        agent,
        "You are Agent 4, the narrative and audit report agent. Write compliance-officer readable claims from recalled memory cards only. The PDF renderer will render your narrative.",
        {
            "agent_setting": {"role": agent, "goal": "produce evidence-backed audit narrative"},
            "recalled_findings": [card_dict(item) for item in findings],
            "recalled_decisions": [card_dict(item) for item in decisions],
            "recalled_baselines": [card_dict(item) for item in baselines],
            "patches": [card_dict(item) for item in patches],
            "output_contract": "Return insights, report_narrative{executive_summary,open_risks[]}, and outcome.",
        },
        NARRATIVE_SCHEMA,
        ["findings", "baselines", "reconciliation", "memory_patches", "agent_outcomes"],
        ["insights", "reports", "agent_outcomes", "prompt_traces"],
    )
    insights = [
        InsightCard(
            insight_id=str(item.get("insight_id", f"IN-{idx:03d}")),
            claim=str(item.get("claim", "")),
            evidence_refs=[str(ref) for ref in item.get("evidence_refs", [])],
            confidence=float(item.get("confidence", 0.78)),
            caveats=[str(ref) for ref in item.get("caveats", [])],
        )
        for idx, item in enumerate(insight_items(result.data.get("insights", [])), start=1)
    ]
    narrative = dict_value(result.data.get("report_narrative", {}))
    report = generate_pdf(
        sorted(findings, key=lambda item: item.risk_score, reverse=True),
        patches,
        narrative_summary=str(narrative.get("executive_summary", "")),
        narrative_open_risks=[str(item) for item in narrative.get("open_risks", [])],
    )
    outcome = outcome_from_agent(dict_value(result.data.get("outcome", {})), agent, ["findings", "baselines", "reconciliation", "memory_patches", "agent_outcomes"], ["insights", "reports", "agent_outcomes", "prompt_traces"])
    await remember_many(memory, insights, "insights", agent, session_id, shared_session_id)
    await memory.remember_card(report, "reports", agent, session_id=session_id, shared_session_id=shared_session_id)
    await memory.remember_card(outcome, "agent_outcomes", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_trace(memory, result.trace, agent, session_id, shared_session_id)
    return insights, report, [outcome], [result.trace]


async def run_ui_feedback_agent(
    memory: MemoryRecorder,
    llm: GptAgentClient,
    run: AuditRun,
    sessions: dict[str, str],
    feedback: str = "",
) -> tuple[FeedbackDigestCard, list[AgentOutcomeCard], list[AgentPromptTraceCard]]:
    agent = AGENT_5
    session_id = sessions["ui"]
    shared_session_id = sessions["shared"]
    outcomes = await memory.recall_cards("Recall all agent outcomes for UI timeline digest.", ["agent_outcomes"], agent, (AgentOutcomeCard,), top_k=80, session_id=shared_session_id, required=True)
    insights = await memory.recall_cards("Recall insights for UI digest.", ["insights"], agent, (InsightCard,), top_k=30, session_id=shared_session_id)
    result = await llm.run_json(
        agent,
        "You are Agent 5, the UI demo and feedback agent. Summarize memory timeline health and what a compliance officer should do next.",
        {
            "agent_setting": {"role": agent, "goal": "make the multi-agent handoff inspectable"},
            "recalled_outcomes": [card_dict(item) for item in outcomes],
            "recalled_insights": [card_dict(item) for item in insights],
            "memory_event_count": len(memory.events),
            "explicit_user_feedback": feedback,
            "output_contract": "Return feedback_digest and outcome.",
        },
        FEEDBACK_SCHEMA,
        ["agent_outcomes", "memory_patches", "insights", "user_feedback"],
        ["feedback_digests", "agent_outcomes", "prompt_traces"],
    )
    digest_data = dict_value(result.data.get("feedback_digest", {}))
    digest = FeedbackDigestCard(
        digest_id=str(digest_data.get("digest_id", "FD-001")),
        summary=str(digest_data.get("summary", "")),
        recommended_next_action=str(digest_data.get("recommended_next_action", "")),
        memory_timeline_health=str(digest_data.get("memory_timeline_health", "")),
        evidence_refs=[str(ref) for ref in digest_data.get("evidence_refs", [])],
    )
    outcome = outcome_from_agent(dict_value(result.data.get("outcome", {})), agent, ["agent_outcomes", "memory_patches", "insights", "user_feedback"], ["feedback_digests", "agent_outcomes", "prompt_traces"])
    await memory.remember_card(digest, "feedback_digests", agent, session_id=session_id, shared_session_id=shared_session_id)
    await memory.remember_card(outcome, "agent_outcomes", agent, session_id=session_id, shared_session_id=shared_session_id)
    await remember_trace(memory, result.trace, agent, session_id, shared_session_id)
    return digest, [outcome], [result.trace]


async def run_audit_pipeline(data_dir: Path, use_cognee: bool = True) -> AuditRun:
    run_id = new_run_id()
    sessions = build_sessions(run_id)
    memory = MemoryRecorder(enabled=use_cognee)
    llm = GptAgentClient()
    run = AuditRun(
        project_id=PROJECT_ID,
        run_id=run_id,
        shared_session_id=sessions["shared"],
        agent_sessions={key: value for key, value in sessions.items() if key != "shared"},
        cognee_enabled=use_cognee,
    )
    tables, candidates, findings, outcomes, traces = await run_data_detective(memory, llm, data_dir, sessions)
    run.data_sources = [table.source_card for table in tables]
    run.schemas = [table.schema_card for table in tables]
    run.candidates = candidates
    run.findings = findings
    run.outcomes.extend(outcomes)
    run.prompt_traces.extend(traces)

    ranked, baselines, outcomes, traces = await run_risk_prioritizer(memory, llm, sessions)
    run.findings = ranked
    run.baselines = baselines
    run.outcomes.extend(outcomes)
    run.prompt_traces.extend(traces)

    planned, decisions, outcomes, traces = await run_remediation_planner(memory, llm, sessions)
    run.findings = sorted(planned, key=lambda item: item.risk_score, reverse=True)
    run.decisions = decisions
    run.outcomes.extend(outcomes)
    run.prompt_traces.extend(traces)

    insights, report, outcomes, traces = await run_audit_narrator(memory, llm, sessions, run.patches)
    run.insights = insights
    run.report = report
    run.outcomes.extend(outcomes)
    run.prompt_traces.extend(traces)

    digest, outcomes, traces = await run_ui_feedback_agent(memory, llm, run, sessions)
    run.feedback_digest = digest
    run.outcomes.extend(outcomes)
    run.prompt_traces.extend(traces)

    run.memory_events = [event.__dict__ for event in memory.events]
    run.cognee_errors = memory.errors
    return run
