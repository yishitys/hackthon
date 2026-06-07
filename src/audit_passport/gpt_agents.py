from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from src.cognee_memory import load_project_env

from .models import AgentPromptTraceCard, slug_time


DEFAULT_AGENT_MODEL = "gpt-5.2"
PROMPT_VERSION = "audit-passport-gpt-cognee-v1"


class AgentOutputValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class JsonSchemaSpec:
    name: str
    schema: dict[str, Any]
    required_top_level: tuple[str, ...]


@dataclass(frozen=True)
class AgentCallResult:
    data: dict[str, Any]
    trace: AgentPromptTraceCard


class GptAgentClient:
    def __init__(self, client: AsyncOpenAI | None = None, model: str | None = None) -> None:
        load_project_env()
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model or os.getenv("AGENT_MODEL") or DEFAULT_AGENT_MODEL
        self.max_output_tokens = int(os.getenv("AGENT_MAX_OUTPUT_TOKENS", "5000"))
        self.reasoning_effort = os.getenv("AGENT_REASONING_EFFORT", "medium")
        self.client = client or AsyncOpenAI(api_key=api_key)

    async def run_json(
        self,
        agent_name: str,
        instructions: str,
        payload: dict[str, Any],
        schema: JsonSchemaSpec,
        recalled_datasets: list[str],
        wrote_datasets: list[str],
    ) -> AgentCallResult:
        input_summary = summarize_payload(payload)
        validation_status = "not_run"
        last_error = ""
        response_id = ""
        data: dict[str, Any] | None = None

        for attempt in range(2):
            response = await self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=json.dumps(payload, ensure_ascii=False, default=str),
                max_output_tokens=self.max_output_tokens,
                reasoning={"effort": self.reasoning_effort},
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema.name,
                        "schema": schema.schema,
                        "strict": False,
                    }
                },
                metadata={
                    "agent_name": agent_name,
                    "prompt_version": PROMPT_VERSION,
                    "attempt": str(attempt + 1),
                },
            )
            response_id = getattr(response, "id", "") or ""
            text = response_text(response)
            try:
                parsed = json.loads(text)
                validate_agent_json(parsed, schema)
                data = parsed
                validation_status = "valid"
                break
            except Exception as exc:
                last_error = str(exc)
                validation_status = f"invalid_attempt_{attempt + 1}: {last_error[:180]}"

        if data is None:
            trace = AgentPromptTraceCard(
                trace_id=f"TRACE-{slug_time()}-{agent_name[:8].replace(' ', '-')}",
                agent=agent_name,
                model=self.model,
                prompt_version=PROMPT_VERSION,
                input_summary=input_summary,
                output_validation_status=validation_status,
                recalled_datasets=recalled_datasets,
                wrote_datasets=wrote_datasets,
                response_id=response_id,
            )
            raise AgentOutputValidationError(
                f"{agent_name} failed JSON validation after retry: {last_error}"
            )

        trace = AgentPromptTraceCard(
            trace_id=f"TRACE-{slug_time()}-{agent_name[:8].replace(' ', '-')}",
            agent=agent_name,
            model=self.model,
            prompt_version=PROMPT_VERSION,
            input_summary=input_summary,
            output_validation_status=validation_status,
            recalled_datasets=recalled_datasets,
            wrote_datasets=wrote_datasets,
            response_id=response_id,
        )
        return AgentCallResult(data=data, trace=trace)


def response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    parts: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                parts.append(str(text))
    if parts:
        return "\n".join(parts)
    if hasattr(response, "model_dump"):
        return json.dumps(response.model_dump(), ensure_ascii=False, default=str)
    return str(response)


def summarize_payload(payload: dict[str, Any]) -> str:
    summary = {
        key: (len(value) if isinstance(value, list) else sorted(value.keys()) if isinstance(value, dict) else str(value)[:80])
        for key, value in payload.items()
    }
    return json.dumps(summary, ensure_ascii=False, default=str)[:480]


def validate_agent_json(data: Any, schema: JsonSchemaSpec) -> None:
    if not isinstance(data, dict):
        raise AgentOutputValidationError("top-level response is not an object")
    missing = [key for key in schema.required_top_level if key not in data]
    if missing:
        raise AgentOutputValidationError(f"missing top-level keys: {', '.join(missing)}")
