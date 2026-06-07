from __future__ import annotations

from dataclasses import replace

from .agents import AGENT_1, AGENT_2, AGENT_3, AGENT_4, AGENT_5, severity_from_score
from .memory import MemoryRecorder
from .models import AgentOutcomeCard, AuditRun, MemoryPatch
from .probabilistic import attach_probabilistic_risk
from .report import generate_pdf


def choose_ripple_target(run: AuditRun) -> str | None:
    for finding in run.findings:
        if finding.type == "Unit conflict":
            return finding.finding_id
    if run.findings:
        return run.findings[0].finding_id
    return None


async def apply_memory_ripple(run: AuditRun, use_cognee: bool = True) -> AuditRun:
    memory = MemoryRecorder(enabled=use_cognee)
    target_id = choose_ripple_target(run)
    if target_id is None:
        return run
    target = next(finding for finding in run.findings if finding.finding_id == target_id)
    before = {
        "risk_score": target.risk_score,
        "severity": target.severity,
        "action": target.suggested_action,
        "interpretation": target.why_broken,
    }
    new_score = max(45, target.risk_score - 21)
    after = {
        "risk_score": new_score,
        "severity": severity_from_score(new_score),
        "action": "Suggested Fix",
        "interpretation": "Partially explained by unit normalization; unresolved records still require review.",
    }
    patch = MemoryPatch(
        patch_id=f"MP-{len(run.patches) + 1:03d}",
        source_agent=AGENT_3,
        change_type="unit_rule_update",
        change_summary=(
            "Supplier manifest measurement units should be interpreted before raw numeric values are treated as contradictions."
        ),
        reason=(
            "New source metadata found by the remediation agent confirms that one source reports grams while another reports milligrams."
        ),
        affected_findings=[target_id],
        before=before,
        after=after,
    )
    await memory.remember_card(patch, "memory_patches", AGENT_3)

    await memory.recall(
        f"Reclassify {target_id} after active MemoryPatch {patch.patch_id}.",
        ["memory_patches", "findings", "schema"],
        AGENT_1,
    )
    await memory.recall(
        f"Re-rank {target_id} after MemoryPatch {patch.patch_id}.",
        ["memory_patches", "findings", "baselines"],
        AGENT_2,
    )
    await memory.recall(
        f"Regenerate report paragraph after MemoryPatch {patch.patch_id}.",
        ["memory_patches", "findings", "reconciliation", "reports"],
        AGENT_4,
    )

    updated_findings = []
    for finding in run.findings:
        if finding.finding_id != target_id:
            updated_findings.append(finding)
            continue
        updated = replace(
            finding,
            risk_score=new_score,
            severity=severity_from_score(new_score),
            suggested_action="Suggested Fix",
            action_rationale=(
                "Normalize units using the new source metadata, then keep only unresolved records in manual review."
            ),
            ranking_reason=(
                f"Risk lowered after {patch.patch_id}; the contradiction is partly explained by unit semantics, "
                "but remaining records still carry audit impact."
            ),
            ripple_note=(
                f"{patch.patch_id} changed risk {before['risk_score']} -> {after['risk_score']} "
                f"and action {before['action']} -> {after['action']}."
            ),
            last_updated_by_agent=AGENT_2,
        )
        updated = attach_probabilistic_risk(updated)
        updated_findings.append(updated)
        await memory.remember_card(updated, "findings", AGENT_2)

    run.findings = sorted(updated_findings, key=lambda item: item.risk_score, reverse=True)
    run.patches.append(patch)
    run.report = generate_pdf(run.findings, run.patches)
    await memory.remember_card(run.report, "reports", AGENT_4)

    outcome = AgentOutcomeCard(
        agent=AGENT_5,
        task="Display Memory Ripple causal chain after a new evidence patch.",
        read_datasets=["memory_patches", "findings", "reports"],
        wrote_datasets=["agent_outcomes"],
        outcome=(
            f"{patch.patch_id} updated {target_id}: risk {before['risk_score']} -> {after['risk_score']}, "
            f"action {before['action']} -> {after['action']}."
        ),
        reason="The demo proves that one agent's memory update changes downstream ranking and narrative.",
        evidence_refs=[target_id, patch.patch_id],
        memory_reads=3,
        memory_writes=2,
    )
    await memory.remember_card(outcome, "agent_outcomes", AGENT_5)
    run.outcomes.append(outcome)
    run.memory_events.extend(event.__dict__ for event in memory.events)
    run.cognee_errors.extend(memory.errors)
    return run
