from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


PROMOTABLE_TYPES = {
    "DataSourceCard",
    "SchemaCard",
    "DetectionCandidateCard",
    "FindingCard",
    "ClassificationBaseline",
    "ReconciliationDecision",
    "MemoryPatch",
    "InsightCard",
    "GeodoResearch",
    "AuditReportCard",
    "AgentOutcome",
    "AgentPromptTrace",
    "UserFeedback",
    "FeedbackDigest",
}


def lint_card(card: Any) -> tuple[bool, str]:
    data = asdict(card) if is_dataclass(card) else dict(card)
    card_type = "FindingCard" if data.get("finding_id") else data.get("type", card.__class__.__name__)
    if card_type not in PROMOTABLE_TYPES:
        return False, f"unsupported memory type: {card_type}"
    serialized = str(data).lower()
    if "llm_api_key" in serialized or "openai_api_key" in serialized:
        return False, "secret-like key detected"
    if card_type == "FindingCard" and not data.get("evidence"):
        return False, "finding lacks evidence pointer"
    if card_type == "DetectionCandidateCard" and not data.get("evidence"):
        return False, "candidate lacks evidence pointer"
    if card_type in {"DataSourceCard", "SchemaCard"} and not data.get("source_id"):
        return False, "source card lacks source_id"
    if data.get("status") in {"rejected", "expired"}:
        return False, f"memory status is {data.get('status')}"
    return True, "active"
