from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from src.cognee_memory import import_cognee, load_project_env, stringify_result

from .lint import lint_card
from .models import card_to_markdown


DATASETS = {
    "sources": "project:audit_passport:sources",
    "schema": "project:audit_passport:schema",
    "findings": "project:audit_passport:findings",
    "baselines": "project:audit_passport:baselines",
    "reconciliation": "project:audit_passport:reconciliation",
    "memory_patches": "project:audit_passport:memory_patches",
    "insights": "project:audit_passport:insights",
    "reports": "project:audit_passport:reports",
    "agent_outcomes": "project:audit_passport:agent_outcomes",
    "user_feedback": "project:audit_passport:user_feedback",
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

    async def remember_card(self, card: Any, dataset_key: str, agent: str) -> bool:
        dataset = DATASETS[dataset_key]
        ok, reason = lint_card(card)
        if not ok:
            self.events.append(MemoryEvent(agent, "lint_reject", dataset, reason, status="rejected"))
            return False
        text = card_to_markdown(card)
        if not self.enabled:
            self.events.append(MemoryEvent(agent, "remember_skipped", dataset, reason, status="local"))
            return True
        try:
            load_project_env()
            cognee = import_cognee()
            result = await cognee.remember(text, dataset_name=dataset, self_improvement=False)
            self.events.append(
                MemoryEvent(agent, "remember", dataset, stringify_result(result)[:240], status="ok")
            )
            return True
        except TypeError:
            try:
                cognee = import_cognee()
                result = await cognee.remember(text, dataset_name=dataset)
                self.events.append(
                    MemoryEvent(agent, "remember", dataset, stringify_result(result)[:240], status="ok")
                )
                return True
            except Exception as exc:  # pragma: no cover - integration dependent
                self._record_error(agent, dataset, exc)
                return False
        except Exception as exc:  # pragma: no cover - integration dependent
            self._record_error(agent, dataset, exc)
            return False

    async def recall(self, query: str, dataset_keys: list[str], agent: str, top_k: int = 5) -> list[str]:
        datasets = [DATASETS[key] for key in dataset_keys]
        if not self.enabled:
            self.events.append(
                MemoryEvent(agent, "recall_skipped", ", ".join(datasets), query[:180], status="local")
            )
            return []
        try:
            load_project_env()
            cognee = import_cognee()
            try:
                result = await cognee.recall(
                    query_text=query,
                    datasets=datasets,
                    top_k=top_k,
                    only_context=True,
                )
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

    def _record_error(self, agent: str, dataset: str, exc: Exception) -> None:
        message = f"{agent} / {dataset}: {exc}"
        self.errors.append(message)
        self.events.append(MemoryEvent(agent, "memory_error", dataset, str(exc), status="error"))


def run_async(coro: Any) -> Any:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return loop.run_until_complete(coro)

