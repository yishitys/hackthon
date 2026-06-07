from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


PROJECT_ID = "audit_passport"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slug_time() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


@dataclass
class Evidence:
    source_file: str
    row_number: str
    field_name: str
    observed_value: str
    expected_or_conflicting_value: str
    explanation: str


@dataclass
class DataSourceCard:
    source_id: str
    uri: str
    content_hash: str
    row_count: int
    columns: list[str]
    grain: str
    quality_summary: dict[str, Any]
    status: str = "active"
    type: str = "DataSourceCard"


@dataclass
class SchemaCard:
    source_id: str
    entity_columns: list[str]
    numeric_columns: list[str]
    unit_columns: list[str]
    date_columns: list[str]
    inferred_entities: list[str]
    status: str = "active"
    type: str = "SchemaCard"


@dataclass
class FindingCard:
    finding_id: str
    type: str
    severity: str
    risk_score: int
    confidence: float
    affected_entity: str
    audit_risk: str
    why_broken: str
    suggested_action: str
    status: str
    evidence: list[Evidence]
    created_by_agent: str
    last_updated_by_agent: str
    ranking_reason: str = ""
    action_rationale: str = ""
    ripple_note: str = ""
    audit_blocker_probability: float = 0.0
    credible_interval_low: float = 0.0
    credible_interval_high: float = 0.0
    uncertainty_level: str = "unscored"
    probabilistic_reason: str = ""
    scoring_method: str = "rules"
    memory_status: str = "active"


@dataclass
class ClassificationBaselineCard:
    baseline_id: str
    critical_fields: list[str]
    audit_sensitive_issue_types: list[str]
    severity_rules: dict[str, str]
    unit_rules: dict[str, str]
    confidence: float
    status: str = "active"
    type: str = "ClassificationBaseline"


@dataclass
class ReconciliationDecisionCard:
    decision_id: str
    finding_id: str
    conflict: str
    chosen_resolution: str
    evidence_refs: list[str]
    affected_agents: list[str]
    rationale: str
    status: str = "active"
    type: str = "ReconciliationDecision"


@dataclass
class MemoryPatch:
    patch_id: str
    source_agent: str
    change_type: str
    change_summary: str
    reason: str
    affected_findings: list[str]
    before: dict[str, Any]
    after: dict[str, Any]
    status: str = "active"
    written_at: str = field(default_factory=utc_now)
    type: str = "MemoryPatch"


@dataclass
class InsightCard:
    insight_id: str
    claim: str
    evidence_refs: list[str]
    confidence: float
    caveats: list[str]
    status: str = "candidate"
    type: str = "InsightCard"


@dataclass
class AuditReportCard:
    report_id: str
    readiness_score: int
    readiness_probability: float
    readiness_interval_low: float
    readiness_interval_high: float
    readiness_uncertainty: str
    readiness_reason: str
    readiness_method: str
    executive_summary: str
    critical_findings: list[str]
    ripple_updates: list[str]
    open_risks: list[str]
    pdf_path: str
    status: str = "active"
    type: str = "AuditReportCard"


@dataclass
class AgentOutcomeCard:
    agent: str
    task: str
    read_datasets: list[str]
    wrote_datasets: list[str]
    outcome: str
    reason: str
    evidence_refs: list[str]
    memory_reads: int
    memory_writes: int
    status: str = "active"
    written_at: str = field(default_factory=utc_now)
    type: str = "AgentOutcome"


@dataclass
class UserFeedbackCard:
    finding_id: str
    feedback: str
    note: str
    status: str = "active"
    written_at: str = field(default_factory=utc_now)
    type: str = "UserFeedback"


@dataclass
class AuditRun:
    project_id: str
    run_id: str
    shared_session_id: str
    agent_sessions: dict[str, str]
    data_sources: list[DataSourceCard] = field(default_factory=list)
    schemas: list[SchemaCard] = field(default_factory=list)
    findings: list[FindingCard] = field(default_factory=list)
    baselines: list[ClassificationBaselineCard] = field(default_factory=list)
    decisions: list[ReconciliationDecisionCard] = field(default_factory=list)
    patches: list[MemoryPatch] = field(default_factory=list)
    insights: list[InsightCard] = field(default_factory=list)
    report: AuditReportCard | None = None
    outcomes: list[AgentOutcomeCard] = field(default_factory=list)
    memory_events: list[dict[str, Any]] = field(default_factory=list)
    cognee_enabled: bool = True
    cognee_errors: list[str] = field(default_factory=list)


def new_run_id() -> str:
    return f"run-{slug_time()}"


def build_sessions(run_id: str) -> dict[str, str]:
    return {
        "shared": f"ap:{PROJECT_ID}:{run_id}:shared",
        "ingest": f"ap:{PROJECT_ID}:{run_id}:ingest",
        "classify": f"ap:{PROJECT_ID}:{run_id}:classify",
        "reconcile": f"ap:{PROJECT_ID}:{run_id}:reconcile",
        "narrative": f"ap:{PROJECT_ID}:{run_id}:narrative",
        "ui": f"ap:{PROJECT_ID}:{run_id}:ui",
    }


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    return asdict(value)


def card_to_markdown(card: Any) -> str:
    data = dataclass_to_dict(card)
    title = "FindingCard" if data.get("finding_id") else data.get("type", card.__class__.__name__)
    identity = (
        data.get("finding_id")
        or data.get("source_id")
        or data.get("baseline_id")
        or data.get("decision_id")
        or data.get("patch_id")
        or data.get("insight_id")
        or data.get("report_id")
        or data.get("agent")
        or "memory-card"
    )
    return (
        f"# {title}: {identity}\n\n"
        "```json\n"
        f"{json.dumps(data, ensure_ascii=False, indent=2, default=str)}\n"
        "```\n"
    )
