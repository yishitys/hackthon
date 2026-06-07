from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.audit_passport import agents
from src.audit_passport.gpt_agents import AgentCallResult, AgentOutputValidationError, JsonSchemaSpec, validate_agent_json
from src.audit_passport.memory import card_from_dict, extract_card_json
from src.audit_passport.models import AgentPromptTraceCard, DetectionCandidateCard, Evidence, card_to_markdown
from src.audit_passport.probabilistic import attach_probabilistic_risk


class FakeGptAgentClient:
    def __init__(self) -> None:
        self.model = "fake-model"

    async def run_json(self, agent_name, instructions, payload, schema, recalled_datasets, wrote_datasets):
        trace = AgentPromptTraceCard(
            trace_id=f"TRACE-{schema.name}",
            agent=agent_name,
            model=self.model,
            prompt_version="test",
            input_summary="test",
            output_validation_status="valid",
            recalled_datasets=recalled_datasets,
            wrote_datasets=wrote_datasets,
        )
        if schema.name == "ingestion_agent_output":
            findings = []
            for idx, candidate in enumerate(payload["detection_candidates"][:3], start=1):
                findings.append(
                    {
                        "finding_id": f"F-{idx:03d}",
                        "type": candidate["candidate_type"],
                        "severity": "High",
                        "risk_score": candidate["suggested_risk_score"],
                        "confidence": 0.82,
                        "affected_entity": candidate["affected_entity"],
                        "audit_risk": "Audit readiness risk.",
                        "why_broken": candidate["detector_reason"],
                        "suggested_action": "Pending triage",
                        "status": "Open",
                        "evidence": candidate["evidence"],
                        "created_by_agent": agent_name,
                    }
                )
            data = {
                "findings": findings,
                "outcome": {
                    "task": "ingest",
                    "outcome": "created findings",
                    "reason": "used candidates",
                    "evidence_refs": [finding["finding_id"] for finding in findings],
                },
            }
        elif schema.name == "risk_agent_output":
            updates = [
                {
                    "finding_id": finding["finding_id"],
                    "risk_score": min(100, finding["risk_score"] + 3),
                    "severity": "Critical" if finding["risk_score"] + 3 >= 85 else "High",
                    "confidence": 0.88,
                    "ranking_reason": "fake ranking",
                }
                for finding in payload["recalled_findings"]
            ]
            data = {
                "baseline": {
                    "baseline_id": "BL-001",
                    "critical_fields": ["quantity"],
                    "audit_sensitive_issue_types": ["Unit conflict"],
                    "severity_rules": {"High": "review"},
                    "unit_rules": {"mg_to_g": "normalize"},
                    "confidence": 0.8,
                },
                "ranking_updates": updates,
                "outcome": {
                    "task": "rank",
                    "outcome": "ranked",
                    "reason": "used Cognee handoff",
                    "evidence_refs": [update["finding_id"] for update in updates],
                },
            }
        elif schema.name == "remediation_agent_output":
            updates = [
                {
                    "finding_id": finding["finding_id"],
                    "suggested_action": "Manual Review Required",
                    "action_rationale": "fake action",
                }
                for finding in payload["recalled_ranked_findings"]
            ]
            decisions = [
                {
                    "decision_id": "RD-" + update["finding_id"][2:],
                    "finding_id": update["finding_id"],
                    "conflict": "conflict",
                    "chosen_resolution": update["suggested_action"],
                    "evidence_refs": [],
                    "affected_agents": [agents.AGENT_2, agents.AGENT_4],
                    "rationale": update["action_rationale"],
                }
                for update in updates
            ]
            data = {
                "action_updates": updates,
                "decisions": decisions,
                "outcome": {
                    "task": "plan",
                    "outcome": "planned",
                    "reason": "used rankings",
                    "evidence_refs": [update["finding_id"] for update in updates],
                },
            }
        elif schema.name == "narrative_agent_output":
            data = {
                "insights": [
                    {
                        "insight_id": "IN-001",
                        "claim": "fake claim",
                        "evidence_refs": ["F-001"],
                        "confidence": 0.8,
                        "caveats": ["manual review"],
                    }
                ],
                "report_narrative": {
                    "executive_summary": "GPT narrative summary",
                    "open_risks": ["F-001 needs review"],
                },
                "outcome": {
                    "task": "narrate",
                    "outcome": "reported",
                    "reason": "used full memory chain",
                    "evidence_refs": ["F-001"],
                },
            }
        else:
            data = {
                "feedback_digest": {
                    "digest_id": "FD-001",
                    "summary": "timeline ok",
                    "recommended_next_action": "review",
                    "memory_timeline_health": "healthy",
                    "evidence_refs": ["IN-001"],
                },
                "outcome": {
                    "task": "ui",
                    "outcome": "digested",
                    "reason": "used timeline",
                    "evidence_refs": ["IN-001"],
                },
            }
        return AgentCallResult(data=data, trace=trace)


class GptMultiAgentTests(unittest.TestCase):
    def test_validate_agent_json_requires_top_level_keys(self) -> None:
        spec = JsonSchemaSpec("test", {"type": "object"}, ("findings", "outcome"))
        validate_agent_json({"findings": [], "outcome": {}}, spec)
        with self.assertRaises(AgentOutputValidationError):
            validate_agent_json({"findings": []}, spec)

    def test_extract_card_json_round_trips_detection_candidate(self) -> None:
        candidate = DetectionCandidateCard(
            "DC-001",
            "source",
            "Missing evidence",
            "source",
            "missing audit field",
            74,
            [Evidence("file.csv", "2", "field", "", "non-empty", "missing")],
        )
        parsed = [card_from_dict(data) for data in extract_card_json(card_to_markdown(candidate))]
        self.assertEqual(parsed[0].candidate_id, "DC-001")

    def test_fixed_detectors_generate_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            pd.DataFrame(
                [
                    {"customer_id": "C-1", "quantity": -1, "production_date": "2026-01-02", "ship_date": "2026-01-01"},
                    {"customer_id": "C-2", "quantity": 2, "production_date": "2026-01-02", "ship_date": "2026-01-03"},
                ]
            ).to_csv(path / "track01_data_rescue.csv", index=False)
            pd.DataFrame([{"customer_id": "C-2"}]).to_csv(path / "track01_customers.csv", index=False)
            tables = agents.load_kaggle_tables(path)
            candidates = agents.build_detection_candidates(tables)
            self.assertGreaterEqual(len(candidates), 2)

    def test_probabilistic_script_attaches_probability(self) -> None:
        finding = agents.make_finding(
            1,
            "Impossible values",
            "entity",
            "bad quantity",
            [Evidence("file.csv", "2", "quantity", "-1", "positive", "bad")],
            86,
        )
        scored = attach_probabilistic_risk(finding)
        self.assertGreater(scored.audit_blocker_probability, 0)
        self.assertNotEqual(scored.uncertainty_level, "unscored")

    def test_pipeline_uses_five_fake_gpt_agents(self) -> None:
        original = agents.GptAgentClient
        agents.GptAgentClient = FakeGptAgentClient
        try:
            run = asyncio.run(agents.run_audit_pipeline(Path("data/kaggle"), use_cognee=False))
        finally:
            agents.GptAgentClient = original
        self.assertEqual(len(run.outcomes), 5)
        self.assertEqual(len(run.prompt_traces), 5)
        self.assertEqual(run.report.executive_summary, "GPT narrative summary")
        self.assertEqual(run.feedback_digest.summary, "timeline ok")


if __name__ == "__main__":
    unittest.main()
