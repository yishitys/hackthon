from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

from .models import AuditReportCard, FindingCard, MemoryPatch, slug_time


ARTIFACT_DIR = Path("runtime/artifacts")


def readiness_score(findings: list[FindingCard]) -> int:
    if not findings:
        return 100
    penalty = sum(max(0, finding.risk_score - 35) for finding in findings[:8])
    return max(0, min(100, 100 - int(penalty / 8)))


def executive_summary(findings: list[FindingCard], patches: list[MemoryPatch]) -> str:
    critical = [item for item in findings if item.severity in {"Critical", "High"}]
    if not findings:
        return "No audit blockers were detected in the current Kaggle data snapshot."
    ripple = " A new-evidence ripple has updated the report." if patches else ""
    return (
        f"Audit Passport reviewed {len(findings)} evidence-backed findings. "
        f"{len(critical)} findings are Critical or High priority and should be addressed before regulatory sign-off."
        f"{ripple}"
    )


def build_report_card(findings: list[FindingCard], patches: list[MemoryPatch], pdf_path: Path) -> AuditReportCard:
    score = readiness_score(findings)
    critical = [finding.finding_id for finding in findings if finding.severity in {"Critical", "High"}]
    open_risks = [
        f"{finding.finding_id}: {finding.why_broken}"
        for finding in findings
        if finding.suggested_action in {"Escalate", "Manual Review Required"}
    ][:8]
    return AuditReportCard(
        report_id=f"AR-{slug_time()}",
        readiness_score=score,
        executive_summary=executive_summary(findings, patches),
        critical_findings=critical,
        ripple_updates=[patch.patch_id for patch in patches],
        open_risks=open_risks,
        pdf_path=str(pdf_path).replace("\\", "/"),
    )


def write_line(pdf: FPDF, text: str, height: int = 5) -> None:
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, height, str(text), new_x="LMARGIN", new_y="NEXT")


def generate_pdf(findings: list[FindingCard], patches: list[MemoryPatch]) -> AuditReportCard:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / "audit_passport_summary.pdf"
    report = build_report_card(findings, patches, path)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Audit Passport Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Readiness score: {report.readiness_score}/100", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    write_line(pdf, report.executive_summary, 6)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Top Audit Passports", new_x="LMARGIN", new_y="NEXT")
    for finding in findings[:8]:
        pdf.set_font("Helvetica", "B", 10)
        write_line(
            pdf,
            f"{finding.finding_id} | {finding.severity} | Risk {finding.risk_score} | {finding.type}",
            6,
        )
        pdf.set_font("Helvetica", "", 9)
        write_line(pdf, f"Affected: {finding.affected_entity}")
        write_line(pdf, f"Why it matters: {finding.why_broken}")
        write_line(pdf, f"Action: {finding.suggested_action}. {finding.action_rationale}")
        for evidence in finding.evidence[:3]:
            write_line(
                pdf,
                f"Evidence: {evidence.source_file} row {evidence.row_number}, {evidence.field_name}={evidence.observed_value}",
            )
        if finding.ripple_note:
            write_line(pdf, f"Ripple update: {finding.ripple_note}")
        pdf.ln(2)

    if patches:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "Updated After New Evidence", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        for patch in patches:
            write_line(pdf, f"{patch.patch_id}: {patch.change_summary}")
            write_line(pdf, f"Reason: {patch.reason}")
            write_line(pdf, f"Affected findings: {', '.join(patch.affected_findings)}")
            pdf.ln(1)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Sign-off Note", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    write_line(
        pdf,
        "This report is generated from semantic memory cards, evidence pointers, and agent handoffs. "
        "Manual review remains required for unresolved audit blockers.",
    )
    pdf.output(str(path))
    return report
