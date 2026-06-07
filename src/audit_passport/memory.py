from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from typing import Any

from src.cognee_memory import import_cognee, load_project_env, stringify_result

from .lint import lint_card
from .models import (
    AgentOutcomeCard,
    AgentPromptTraceCard,
    AuditReportCard,
    ClassificationBaselineCard,
    DataSourceCard,
    DetectionCandidateCard,
    Evidence,
    FeedbackDigestCard,
    FindingCard,
    GeodoResearchCard,
    InsightCard,
    MemoryPatch,
    ReconciliationDecisionCard,
    SchemaCard,
    UserFeedbackCard,
    card_to_markdown,
)


DATASETS = {
    "sources": "project:audit_passport:sources",
    "schema": "project:audit_passport:schema",
    "detection_candidates": "project:audit_passport:detection_candidates",
    "findings": "project:audit_passport:findings",
    "baselines": "project:audit_passport:baselines",
    "reconciliation": "project:audit_passport:reconciliation",
    "memory_patches": "project:audit_passport:memory_patches",
    "insights": "project:audit_passport:insights",
    "geodo_research": "project:audit_passport:geodo_research",
    "reports": "project:audit_passport:reports",
    "agent_outcomes": "project:audit_passport:agent_outcomes",
    "prompt_traces": "project:audit_passport:prompt_traces",
    "user_feedback": "project:audit_passport:user_feedback",
    "feedback_digests": "project:audit_passport:feedback_digests",
}


CARD_TYPES = {
    "DataSourceCard": DataSourceCard,
    "SchemaCard": SchemaCard,
    "DetectionCandidateCard": DetectionCandidateCard,
    "FindingCard": FindingCard,
    "ClassificationBaseline": ClassificationBaselineCard,
    "ReconciliationDecision": ReconciliationDecisionCard,
    "MemoryPatch": MemoryPatch,
    "InsightCard": InsightCard,
    "GeodoResearch": GeodoResearchCard,
    "AuditReportCard": AuditReportCard,
    "AgentOutcome": AgentOutcomeCard,
    "AgentPromptTrace": AgentPromptTraceCard,
    "UserFeedback": UserFeedbackCard,
    "FeedbackDigest": FeedbackDigestCard,
}


@dataclass
class MemoryEvent:
    agent: str
    event_type: str
    dataset: str
    summary: str
    status: str = "ok"
    error: str = ""


@dataclass
class MemoryRecorder:
    enabled: bool = True
    events: list[MemoryEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    local_store: dict[str, list[str]] = field(default_factory=dict)

    async def remember_cards(
        self,
        cards: list[Any],
        dataset_key: str,
        agent: str,
        session_id: str = "",
        shared_session_id: str = "",
    ) -> bool:
        if not cards:
            return True
        dataset = DATASETS[dataset_key]
        texts: list[str] = []
        for card in cards:
            ok, reason = lint_card(card)
            if not ok:
                self.events.append(MemoryEvent(agent, "lint_reject", dataset, reason, status="rejected"))
                continue
            text = card_to_markdown(card)
            self.local_store.setdefault(dataset, []).append(text)
            texts.append(text)
        if not texts:
            return False
        if not self.enabled:
            self.events.append(
                MemoryEvent(agent, "remember_batch_skipped", dataset, f"{len(texts)} cards", status="local")
            )
            return True
        batch_text = "\n\n---\n\n".join(texts)
        if not await self._remember_text(batch_text, dataset, agent, session_id, event_type="remember_batch"):
            return False
        if shared_session_id and shared_session_id != session_id:
            return await self._remember_text(
                batch_text,
                dataset,
                agent,
                shared_session_id,
                event_type="remember_shared_batch",
            )
        return True

    async def remember_card(
        self,
        card: Any,
        dataset_key: str,
        agent: str,
        session_id: str = "",
        shared_session_id: str = "",
    ) -> bool:
        dataset = DATASETS[dataset_key]
        ok, reason = lint_card(card)
        if not ok:
            self.events.append(MemoryEvent(agent, "lint_reject", dataset, reason, status="rejected"))
            return False
        text = card_to_markdown(card)
        self.local_store.setdefault(dataset, []).append(text)
        if not self.enabled:
            self.events.append(MemoryEvent(agent, "remember_skipped", dataset, reason, status="local"))
            return True
        if not await self._remember_text(text, dataset, agent, session_id):
            return False
        if shared_session_id and shared_session_id != session_id:
            return await self._remember_text(text, dataset, agent, shared_session_id, event_type="remember_shared")
        return True

    async def _remember_text(
        self,
        text: str,
        dataset: str,
        agent: str,
        session_id: str = "",
        event_type: str = "remember",
    ) -> bool:
        try:
            load_project_env()
            cognee = import_cognee()
            kwargs = {"dataset_name": dataset, "self_improvement": False}
            if session_id:
                kwargs["session_id"] = session_id
            result = await cognee.remember(text, **kwargs)
            self.events.append(
                MemoryEvent(agent, event_type, dataset, stringify_result(result)[:240], status="ok")
            )
            return True
        except TypeError:
            try:
                cognee = import_cognee()
                result = await cognee.remember(text, dataset_name=dataset)
                self.events.append(
                    MemoryEvent(
                        agent,
                        event_type,
                        dataset,
                        stringify_result(result)[:240] + ("; session_id unsupported" if session_id else ""),
                        status="ok",
                    )
                )
                return True
            except Exception as exc:  # pragma: no cover - integration dependent
                self._record_error(agent, dataset, exc)
                return False
        except Exception as exc:  # pragma: no cover - integration dependent
            self._record_error(agent, dataset, exc)
            return False

    async def recall(
        self,
        query: str,
        dataset_keys: list[str],
        agent: str,
        top_k: int = 5,
        session_id: str = "",
    ) -> list[str]:
        datasets = [DATASETS[key] for key in dataset_keys]
        if not self.enabled:
            self.events.append(
                MemoryEvent(agent, "recall_skipped", ", ".join(datasets), query[:180], status="local")
            )
            return [item for dataset in datasets for item in self.local_store.get(dataset, [])][-top_k:]
        try:
            load_project_env()
            cognee = import_cognee()
            try:
                kwargs = {
                    "query_text": query,
                    "datasets": datasets,
                    "top_k": top_k,
                    "only_context": True,
                }
                if session_id:
                    kwargs["session_id"] = session_id
                result = await cognee.recall(**kwargs)
            except TypeError:
                result = await cognee.recall(query_text=query, datasets=datasets, top_k=top_k)
            if isinstance(result, list):
                context = [stringify_result(item) for item in result]
            else:
                context = [stringify_result(result)]
            self.events.append(MemoryEvent(agent, "recall", ", ".join(datasets), query[:180], status="ok"))
            return context
        except Exception as exc:  # pragma: no cover - integration dependent
            self._record_error(agent, ", ".join(datasets), exc)
            return []

    async def recall_cards(
        self,
        query: str,
        dataset_keys: list[str],
        agent: str,
        card_types: tuple[type, ...] = (),
        top_k: int = 20,
        session_id: str = "",
        required: bool = False,
    ) -> list[Any]:
        context = await self.recall(query, dataset_keys, agent, top_k=top_k, session_id=session_id)
        cards = self._cards_from_texts(context, card_types)
        if not cards:
            datasets = [DATASETS[key] for key in dataset_keys]
            local_context = [item for dataset in datasets for item in self.local_store.get(dataset, [])][-top_k:]
            cards = self._cards_from_texts(local_context, card_types)
            if cards:
                self.events.append(
                    MemoryEvent(
                        agent,
                        "recall_local_fallback",
                        ", ".join(datasets),
                        f"Used {len(cards)} cards from current run local memory after Cognee recall returned no parseable cards.",
                        status="local",
                    )
                )
        if required and not cards:
            raise RuntimeError(
                f"{agent} could not recall required cards from {', '.join(dataset_keys)} for query: {query}"
            )
        return cards

    def _cards_from_texts(self, texts: list[str], card_types: tuple[type, ...] = ()) -> list[Any]:
        cards: list[Any] = []
        for text in texts:
            for data in extract_card_json(text):
                card = card_from_dict(data)
                if card is None:
                    continue
                if card_types and not isinstance(card, card_types):
                    continue
                cards.append(card)
        return cards

    def _record_error(self, agent: str, dataset: str, exc: Exception) -> None:
        message = f"{agent} / {dataset}: {exc}"
        self.errors.append(message)
        self.events.append(MemoryEvent(agent, "memory_error", dataset, str(exc), status="error"))


def extract_card_json(text: str) -> list[dict[str, Any]]:
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if not blocks:
        blocks = [text]
    parsed: list[dict[str, Any]] = []
    for block in blocks:
        try:
            value = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            parsed.append(value)
        elif isinstance(value, list):
            parsed.extend(item for item in value if isinstance(item, dict))
    return parsed


def _evidence_list(values: list[Any]) -> list[Evidence]:
    evidence: list[Evidence] = []
    for value in values or []:
        if isinstance(value, Evidence):
            evidence.append(value)
        elif isinstance(value, dict):
            evidence.append(Evidence(**value))
    return evidence


def card_from_dict(data: dict[str, Any]) -> Any | None:
    normalized = dict(data)
    if normalized.get("finding_id"):
        normalized["evidence"] = _evidence_list(normalized.get("evidence", []))
        return FindingCard(**normalized)
    if normalized.get("candidate_id"):
        normalized["evidence"] = _evidence_list(normalized.get("evidence", []))
        return DetectionCandidateCard(**normalized)
    card_type = normalized.get("type")
    cls = CARD_TYPES.get(card_type)
    if cls is None:
        return None
    if cls in {DataSourceCard, SchemaCard, ClassificationBaselineCard, ReconciliationDecisionCard, MemoryPatch,
               InsightCard, GeodoResearchCard, AuditReportCard, AgentOutcomeCard, AgentPromptTraceCard, UserFeedbackCard,
               FeedbackDigestCard}:
        return cls(**normalized)
    return None


def run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)
