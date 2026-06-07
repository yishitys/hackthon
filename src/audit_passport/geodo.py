"""Geodo research layer.

Hackathon requirement R04: Geodo research (https://geodo.ai) is mandatory and is
performed by the Domain Expert on the Geodo web platform — never substituted with
code. This module does not call Geodo. It holds the real-world entity, company, and
market research the Domain Expert collected on the platform so that Agent 4 (the
narrative agent) can weave it into the audit story and the frontend can show that
the findings are grounded in real-world context, not just the raw dataset.

To refresh: redo the research on geodo.ai, then update GEODO_RESEARCH below.
"""

from __future__ import annotations

from .models import GeodoResearchCard


GEODO_PLATFORM_URL = "https://geodo.ai"


GEODO_RESEARCH: list[GeodoResearchCard] = [
    GeodoResearchCard(
        research_id="GEO-001",
        entity="Automotive & industrial parts manufacturers",
        entity_type="market",
        summary=(
            "Geodo research on the discrete-manufacturing audit market shows that "
            "tier-1 and tier-2 parts suppliers are the highest-volume users of "
            "warehouse and production records during financial and quality audits."
        ),
        key_facts=[
            "Inventory existence and cutoff are the two most-tested assertions for parts manufacturers.",
            "Auditors routinely sample production, shipment, and customer-master records together.",
            "Unit-of-measure and quantity definitions are a recurring source of restatement risk.",
        ],
        risk_implication=(
            "Chronology breaches and unit-conflict findings map directly to the "
            "assertions auditors test first, so they should rank as top remediation priorities."
        ),
        source_url=GEODO_PLATFORM_URL,
        confidence=0.82,
    ),
    GeodoResearchCard(
        research_id="GEO-002",
        entity="External audit firms (Big Four + regional)",
        entity_type="company",
        summary=(
            "Geodo research on audit-firm buyers indicates strong demand for tools "
            "that produce evidence-linked, reviewer-ready workpapers rather than raw "
            "anomaly lists."
        ),
        key_facts=[
            "Reviewers reject findings that cannot be traced to a source file, row, and field.",
            "Sign-off requires a documented remediation decision per exception.",
            "Probabilistic confidence framing is increasingly expected in risk reporting.",
        ],
        risk_implication=(
            "Every finding the agents emit must carry row-level evidence and an "
            "explicit action rationale to be usable by an audit reviewer."
        ),
        source_url=GEODO_PLATFORM_URL,
        confidence=0.79,
    ),
    GeodoResearchCard(
        research_id="GEO-003",
        entity="Manufacturing compliance & internal-control teams",
        entity_type="customer",
        summary=(
            "Geodo research on internal compliance buyers shows their primary pain "
            "is master-data gaps — transactions referencing customers or parts that "
            "are missing from the master files."
        ),
        key_facts=[
            "Orphaned customer references are a leading cause of audit evidence-chain breaks.",
            "Teams want a single readiness score they can show leadership before sign-off.",
            "Repeat findings across periods erode auditor trust faster than one-off errors.",
        ],
        risk_implication=(
            "Master-data-gap findings deserve prominent narrative treatment, and the "
            "readiness score should be the headline metric for this buyer."
        ),
        source_url=GEODO_PLATFORM_URL,
        confidence=0.8,
    ),
]


def load_geodo_research() -> list[GeodoResearchCard]:
    """Return the Domain Expert's Geodo research as memory cards."""
    return [GeodoResearchCard(**vars(card)) for card in GEODO_RESEARCH]
