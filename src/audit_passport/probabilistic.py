from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np

from .models import FindingCard


@dataclass(frozen=True)
class ProbabilisticRisk:
    probability: float
    ci_low: float
    ci_high: float
    uncertainty_level: str
    reason: str
    method: str


@dataclass(frozen=True)
class ProbabilisticReadiness:
    probability: float
    ci_low: float
    ci_high: float
    uncertainty_level: str
    reason: str
    method: str


TYPE_BOOST = {
    "Contradictory numbers": 2.8,
    "Impossible dates": 2.4,
    "Impossible values": 2.2,
    "Unit conflict": 1.6,
    "Orphaned reference": 1.4,
    "Duplicate records": 0.4,
    "Missing evidence": 1.5,
}

TYPE_DOUBT = {
    "Contradictory numbers": 0.4,
    "Impossible dates": 0.5,
    "Impossible values": 0.6,
    "Unit conflict": 1.2,
    "Orphaned reference": 1.4,
    "Duplicate records": 2.2,
    "Missing evidence": 1.7,
}


def _seed_for(finding: FindingCard) -> int:
    digest = hashlib.sha256(finding.finding_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _uncertainty_level(width: float) -> str:
    if width >= 0.32:
        return "high"
    if width >= 0.2:
        return "medium"
    return "low"


def beta_parameters(finding: FindingCard) -> tuple[float, float, list[str]]:
    evidence_count = len(finding.evidence)
    alpha = 2.0 + finding.risk_score / 8.0 + TYPE_BOOST.get(finding.type, 1.0)
    beta = 2.0 + (100 - finding.risk_score) / 8.0 + TYPE_DOUBT.get(finding.type, 1.0)
    reasons = [
        f"rule score {finding.risk_score}/100",
        f"{evidence_count} evidence pointer{'s' if evidence_count != 1 else ''}",
        f"{finding.type} issue prior",
    ]
    if evidence_count >= 3:
        alpha += 1.2
        reasons.append("multiple evidence pointers narrow uncertainty")
    elif evidence_count <= 1:
        beta += 1.8
        reasons.append("limited evidence widens uncertainty")
    if finding.suggested_action in {"Escalate", "Manual Review Required"}:
        alpha += 1.0
        reasons.append("requires human review or escalation")
    if finding.suggested_action == "Safe Auto-Fix":
        beta += 1.4
        reasons.append("safe auto-fix reduces blocker probability")
    if finding.ripple_note:
        beta += 2.0
        reasons.append("Memory Ripple explains part of the conflict")
    return alpha, beta, reasons


def score_finding_with_pymc(finding: FindingCard, draws: int = 3000) -> ProbabilisticRisk:
    alpha, beta, reasons = beta_parameters(finding)
    seed = _seed_for(finding)
    try:
        import pymc as pm

        with pm.Model():
            probability = pm.Beta("audit_blocker_probability", alpha=alpha, beta=beta)
            samples = pm.draw(probability, draws=draws, random_seed=seed)
        method = "pymc_beta"
    except Exception:
        rng = np.random.default_rng(seed)
        samples = rng.beta(alpha, beta, size=draws)
        method = "numpy_beta_fallback"
    mean = float(np.mean(samples))
    ci_low, ci_high = np.quantile(samples, [0.05, 0.95])
    width = float(ci_high - ci_low)
    level = _uncertainty_level(width)
    return ProbabilisticRisk(
        probability=round(mean, 3),
        ci_low=round(float(ci_low), 3),
        ci_high=round(float(ci_high), 3),
        uncertainty_level=level,
        reason="; ".join(reasons),
        method=method,
    )


def attach_probabilistic_risk(finding: FindingCard) -> FindingCard:
    risk = score_finding_with_pymc(finding)
    finding.audit_blocker_probability = risk.probability
    finding.credible_interval_low = risk.ci_low
    finding.credible_interval_high = risk.ci_high
    finding.uncertainty_level = risk.uncertainty_level
    finding.probabilistic_reason = risk.reason
    finding.scoring_method = risk.method
    return finding


def _action_residual_weight(action: str) -> float:
    return {
        "Escalate": 1.0,
        "Manual Review Required": 0.9,
        "Suggested Fix": 0.55,
        "Safe Auto-Fix": 0.25,
    }.get(action, 0.75)


def score_readiness_with_pymc(findings: list[FindingCard], patch_count: int = 0, draws: int = 3000) -> ProbabilisticReadiness:
    if not findings:
        return ProbabilisticReadiness(
            probability=1.0,
            ci_low=0.96,
            ci_high=1.0,
            uncertainty_level="low",
            reason="No evidence-backed findings were detected.",
            method="pymc_beta",
        )
    residual_blocker_load = sum(
        (finding.audit_blocker_probability or finding.risk_score / 100)
        * _action_residual_weight(finding.suggested_action)
        for finding in findings
    )
    ready_actions = sum(1 for finding in findings if finding.suggested_action in {"Suggested Fix", "Safe Auto-Fix"})
    critical_count = sum(1 for finding in findings if finding.severity == "Critical")
    lower_risk_count = sum(1 for finding in findings if finding.severity in {"Medium", "Low"})

    alpha = 2.0 + ready_actions * 1.45 + patch_count * 1.2 + lower_risk_count * 0.65
    beta = 2.0 + residual_blocker_load * 1.15 + critical_count * 0.82
    try:
        import pymc as pm

        with pm.Model():
            readiness = pm.Beta("audit_readiness_probability", alpha=alpha, beta=beta)
            samples = pm.draw(readiness, draws=draws, random_seed=20260607 + patch_count)
        method = "pymc_beta"
    except Exception:
        rng = np.random.default_rng(20260607 + patch_count)
        samples = rng.beta(alpha, beta, size=draws)
        method = "numpy_beta_fallback"

    mean = float(np.mean(samples))
    ci_low, ci_high = np.quantile(samples, [0.05, 0.95])
    width = float(ci_high - ci_low)
    return ProbabilisticReadiness(
        probability=round(mean, 3),
        ci_low=round(float(ci_low), 3),
        ci_high=round(float(ci_high), 3),
        uncertainty_level=_uncertainty_level(width),
        reason=(
            f"aggregated {len(findings)} finding blocker probabilities; "
            f"residual blocker load {residual_blocker_load:.2f}; "
            f"{ready_actions} findings have fixable actions; "
            f"{critical_count} critical blockers remain; "
            f"{patch_count} Memory Patch update{'s' if patch_count != 1 else ''} applied"
        ),
        method=method,
    )
