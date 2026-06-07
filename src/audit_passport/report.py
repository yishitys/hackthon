from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from . import report_charts as charts
from .models import AuditReportCard, FindingCard, MemoryPatch, slug_time
from .probabilistic import score_readiness_with_pymc


ARTIFACT_DIR = Path("runtime/artifacts")
PDF_TEXT_REPLACEMENTS = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "•": "-",
    "…": "...",
    " ": " ",
}

# ---- Theme (RGB) -----------------------------------------------------------
NAVY = (15, 32, 64)
ACCENT = (37, 99, 235)
INK = (31, 41, 55)
MUTED = (107, 114, 128)
HAIRLINE = (229, 231, 235)
CARD_BG = (247, 248, 250)
WHITE = (255, 255, 255)
SEVERITY_RGB = {
    "Critical": (190, 24, 39),
    "High": (234, 88, 12),
    "Medium": (202, 138, 4),
    "Low": (22, 132, 99),
}
PAGE_W = 210
MARGIN = 14
CONTENT_W = PAGE_W - 2 * MARGIN


def readiness_score(findings: list[FindingCard]) -> int:
    if not findings:
        return 100
    penalty = sum(max(0, finding.risk_score - 35) for finding in findings[:8])
    return max(0, min(100, 100 - int(penalty / 8)))


def executive_summary(findings: list[FindingCard], patches: list[MemoryPatch], override: str = "") -> str:
    if override:
        return override
    critical = [item for item in findings if item.severity in {"Critical", "High"}]
    if not findings:
        return "No audit blockers were detected in the current Kaggle data snapshot."
    ripple = " A new-evidence ripple has updated the report." if patches else ""
    return (
        f"Audit Passport reviewed {len(findings)} evidence-backed findings. "
        f"{len(critical)} findings are Critical or High priority and should be addressed before regulatory sign-off."
        f"{ripple}"
    )


def build_report_card(
    findings: list[FindingCard],
    patches: list[MemoryPatch],
    pdf_path: Path,
    narrative_summary: str = "",
    narrative_open_risks: list[str] | None = None,
) -> AuditReportCard:
    score = readiness_score(findings)
    readiness = score_readiness_with_pymc(findings, patch_count=len(patches))
    critical = [finding.finding_id for finding in findings if finding.severity in {"Critical", "High"}]
    open_risks = [
        f"{finding.finding_id}: {finding.why_broken}"
        for finding in findings
        if finding.suggested_action in {"Escalate", "Manual Review Required"}
    ][:8]
    return AuditReportCard(
        report_id=f"AR-{slug_time()}",
        readiness_score=score,
        readiness_probability=readiness.probability,
        readiness_interval_low=readiness.ci_low,
        readiness_interval_high=readiness.ci_high,
        readiness_uncertainty=readiness.uncertainty_level,
        readiness_reason=readiness.reason,
        readiness_method=readiness.method,
        executive_summary=executive_summary(findings, patches, narrative_summary),
        critical_findings=critical,
        ripple_updates=[patch.patch_id for patch in patches],
        open_risks=narrative_open_risks or open_risks,
        pdf_path=str(pdf_path).replace("\\", "/"),
    )


def pdf_safe_text(text: object) -> str:
    safe = str(text)
    for source, replacement in PDF_TEXT_REPLACEMENTS.items():
        safe = safe.replace(source, replacement)
    return safe.encode("latin-1", errors="replace").decode("latin-1")


# ---- Field fallbacks (older runs leave affected_entity / why_broken empty) --
def _affected_text(finding: FindingCard) -> str:
    if finding.affected_entity.strip():
        return finding.affected_entity.strip()
    if finding.evidence:
        ev = finding.evidence[0]
        files = sorted({e.source_file for e in finding.evidence})
        fields = sorted({e.field_name for e in finding.evidence})
        source = files[0] if len(files) == 1 else f"{len(files)} sources"
        field = fields[0] if len(fields) == 1 else f"{len(fields)} fields"
        return f"{source} - {field} ({len(finding.evidence)} rows)"
    return "Not specified"


def _why_text(finding: FindingCard) -> str:
    for candidate in (finding.why_broken, finding.ranking_reason):
        if candidate and candidate.strip():
            return candidate.strip()
    if finding.evidence and finding.evidence[0].explanation:
        return finding.evidence[0].explanation.strip()
    return finding.audit_risk or "Reviewed for audit readiness."


def _action_text(finding: FindingCard) -> str:
    action = finding.suggested_action or "Pending triage"
    rationale = finding.action_rationale.strip()
    return f"{action}. {rationale}" if rationale else action


class ReportPDF(FPDF):
    report_id = ""

    def footer(self) -> None:
        self.set_y(-12)
        self.set_draw_color(*HAIRLINE)
        self.set_line_width(0.2)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-10)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 5, pdf_safe_text(f"Audit Passport  -  {self.report_id}"))
        self.cell(0, 5, f"Page {self.page_no()}", align="R")


def _set_fill(pdf: FPDF, rgb: tuple[int, int, int]) -> None:
    pdf.set_fill_color(*rgb)


def _round_rect(pdf: FPDF, x: float, y: float, w: float, h: float, style: str = "F") -> None:
    try:
        pdf.rect(x, y, w, h, round_corners=True, style=style, corner_radius=1.6)
    except TypeError:  # pragma: no cover - older fpdf2 without corner_radius kw
        pdf.rect(x, y, w, h, style=style)


def _write_block(pdf: FPDF, label: str, value: str, height: float = 4.6) -> None:
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, height, pdf_safe_text(label.upper()), new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, height, pdf_safe_text(value), new_x="LMARGIN", new_y="NEXT")


def _section_title(pdf: FPDF, text: str) -> None:
    if pdf.get_y() > 250:
        pdf.add_page()
    pdf.ln(3)
    y = pdf.get_y()
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(1.2)
    pdf.line(MARGIN, y + 1, MARGIN, y + 6.5)
    pdf.set_xy(MARGIN + 3, y)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, pdf_safe_text(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _cover_header(pdf: FPDF, report: AuditReportCard) -> None:
    _set_fill(pdf, NAVY)
    pdf.rect(0, 0, PAGE_W, 36, style="F")
    _set_fill(pdf, ACCENT)
    pdf.rect(0, 36, PAGE_W, 1.4, style="F")

    pdf.set_xy(MARGIN, 9)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(150, 180, 230)
    pdf.cell(0, 4, "AUDIT PASSPORT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 11, "Audit Readiness Summary", new_x="LMARGIN", new_y="NEXT")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pdf.set_x(MARGIN)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(190, 200, 220)
    pdf.cell(
        0,
        6,
        pdf_safe_text(f"{report.report_id}    -    Generated {generated}    -    Scoring: {report.readiness_method}"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_y(44)


def _kpi_cards(pdf: FPDF, report: AuditReportCard, findings: list[FindingCard]) -> None:
    gap = 4.0
    card_w = (CONTENT_W - 3 * gap) / 4
    card_h = 24.0
    y = pdf.get_y()
    score_color = SEVERITY_RGB["Low"] if report.readiness_score >= 80 else (
        SEVERITY_RGB["Medium"] if report.readiness_score >= 60 else SEVERITY_RGB["Critical"]
    )
    crit_high = sum(1 for f in findings if f.severity in {"Critical", "High"})
    ci = f"{round(report.readiness_interval_low * 100)}-{round(report.readiness_interval_high * 100)}%"
    cards = [
        ("READINESS", f"{report.readiness_score}/100", "rule score", score_color),
        ("PYMC READY", f"{round(report.readiness_probability * 100)}%", f"90% CI {ci}", ACCENT),
        ("CRITICAL / HIGH", str(crit_high), "priority findings", SEVERITY_RGB["High"]),
        ("TOTAL FINDINGS", str(len(findings)), "evidence-backed", NAVY),
    ]
    for idx, (label, value, sub, color) in enumerate(cards):
        x = MARGIN + idx * (card_w + gap)
        _set_fill(pdf, CARD_BG)
        _round_rect(pdf, x, y, card_w, card_h, style="F")
        _set_fill(pdf, color)
        pdf.rect(x, y, card_w, 1.6, style="F")
        pdf.set_xy(x + 3, y + 4)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*MUTED)
        pdf.cell(card_w - 6, 4, pdf_safe_text(label))
        pdf.set_xy(x + 3, y + 9)
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*color)
        pdf.cell(card_w - 6, 9, pdf_safe_text(value))
        pdf.set_xy(x + 3, y + 18.5)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(card_w - 6, 4, pdf_safe_text(sub))
    pdf.set_y(y + card_h + 4)


def _exec_summary_box(pdf: FPDF, report: AuditReportCard) -> None:
    _section_title(pdf, "Executive Summary")
    text = pdf_safe_text(report.executive_summary)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK)
    pdf.set_x(MARGIN + 3)
    pdf.multi_cell(CONTENT_W - 6, 5.2, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _two_donuts(pdf: FPDF, score: int, probability: float, findings: list[FindingCard], chart_dir: Path) -> None:
    if not charts.charts_available:
        return
    gauge = charts.readiness_gauge(score, probability, chart_dir)
    donut = charts.severity_donut(findings, chart_dir)
    half = CONTENT_W / 2
    img_w = 58
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(MARGIN, y)
    pdf.cell(half, 6, "Overall readiness", align="C")
    pdf.set_xy(MARGIN + half, y)
    pdf.cell(half, 6, "Findings by severity", align="C")
    img_y = y + 7
    pdf.image(str(gauge), x=MARGIN + (half - img_w) / 2, y=img_y, w=img_w)
    pdf.image(str(donut), x=MARGIN + half + (half - img_w) / 2, y=img_y, w=img_w)
    pdf.set_y(img_y + img_w + 2)
    _severity_legend(pdf, findings)


def _severity_legend(pdf: FPDF, findings: list[FindingCard]) -> None:
    present = [s for s in ["Critical", "High", "Medium", "Low"]
               if any(f.severity == s for f in findings)]
    if not present:
        return
    chip = 3.0
    pdf.set_font("Helvetica", "", 8)
    total_w = sum(pdf.get_string_width(s) + chip + 8 for s in present)
    x = MARGIN + (CONTENT_W - total_w) / 2
    y = pdf.get_y()
    for sev in present:
        _set_fill(pdf, SEVERITY_RGB[sev])
        _round_rect(pdf, x, y + 1, chip, chip, style="F")
        pdf.set_xy(x + chip + 1.5, y)
        pdf.set_text_color(*MUTED)
        pdf.cell(pdf.get_string_width(sev) + 6, 5, sev)
        x += pdf.get_string_width(sev) + chip + 8
    pdf.set_y(y + 6)


def _charts_page(pdf: FPDF, findings: list[FindingCard], chart_dir: Path) -> None:
    if not charts.charts_available or not findings:
        return
    pdf.add_page()
    _section_title(pdf, "Risk Landscape")
    bars = charts.risk_bars(findings, chart_dir)
    pdf.image(str(bars), x=MARGIN, y=pdf.get_y(), w=CONTENT_W)
    # advance cursor past the embedded image (image() does not move y)
    pdf.set_y(pdf.get_y() + _image_height(bars, CONTENT_W) + 4)

    _section_title(pdf, "Audit-Blocker Probability & Uncertainty")
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*MUTED)
    pdf.set_x(MARGIN)
    pdf.multi_cell(
        CONTENT_W,
        4.6,
        pdf_safe_text(
            "Each dot is the PyMC point estimate that a finding becomes an audit blocker; "
            "the bar shows the 90% credible interval. Wider bars mean more uncertainty."
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    ci = charts.blocker_intervals(findings, chart_dir)
    pdf.image(str(ci), x=MARGIN, y=pdf.get_y(), w=CONTENT_W)


def _image_height(path: Path, target_w: float) -> float:
    """Scaled display height (mm) for an image placed at target_w mm."""
    try:
        from PIL import Image  # bundled with matplotlib's deps / fpdf2

        with Image.open(path) as img:
            w, h = img.size
        return target_w * h / w
    except Exception:
        return target_w * 0.32


def _findings_detail(pdf: FPDF, findings: list[FindingCard]) -> None:
    _section_title(pdf, "Top Audit Findings")
    for finding in findings[:8]:
        color = SEVERITY_RGB.get(finding.severity, NAVY)
        if pdf.get_y() > 235:
            pdf.add_page()
        # severity header band
        y = pdf.get_y()
        _set_fill(pdf, color)
        _round_rect(pdf, MARGIN, y, CONTENT_W, 8, style="F")
        pdf.set_xy(MARGIN + 3, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*WHITE)
        pdf.cell(CONTENT_W * 0.5, 8, pdf_safe_text(f"{finding.finding_id}   {finding.severity}"))
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(
            CONTENT_W * 0.5 - 3,
            8,
            pdf_safe_text(f"Risk {finding.risk_score}   -   blocker {round(finding.audit_blocker_probability * 100)}%"),
            align="R",
        )
        pdf.set_y(y + 9.5)

        _write_block(pdf, "Affected", _affected_text(finding))
        _write_block(pdf, "Why it matters", _why_text(finding))
        _write_block(pdf, "Recommended action", _action_text(finding))

        if finding.evidence:
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*MUTED)
            pdf.cell(0, 4.6, "EVIDENCE", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*INK)
            for ev in finding.evidence[:3]:
                pdf.set_x(MARGIN + 3)
                pdf.multi_cell(
                    CONTENT_W - 3,
                    4.4,
                    pdf_safe_text(
                        f"- {ev.source_file} row {ev.row_number}: {ev.field_name}={ev.observed_value} "
                        f"(expected {ev.expected_or_conflicting_value})"
                    ),
                    new_x="LMARGIN",
                    new_y="NEXT",
                )
        if finding.ripple_note:
            pdf.set_x(MARGIN)
            pdf.set_font("Helvetica", "I", 8.5)
            pdf.set_text_color(*ACCENT)
            pdf.multi_cell(CONTENT_W, 4.4, pdf_safe_text(f"Ripple update: {finding.ripple_note}"),
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        pdf.set_draw_color(*HAIRLINE)
        pdf.set_line_width(0.2)
        pdf.line(MARGIN, pdf.get_y(), PAGE_W - MARGIN, pdf.get_y())
        pdf.ln(3)


def _patches_section(pdf: FPDF, patches: list[MemoryPatch]) -> None:
    if not patches:
        return
    _section_title(pdf, "Updated After New Evidence")
    for patch in patches:
        pdf.set_x(MARGIN)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*ACCENT)
        pdf.multi_cell(CONTENT_W, 5, pdf_safe_text(f"{patch.patch_id}: {patch.change_summary}"),
                       new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*INK)
        pdf.set_x(MARGIN)
        pdf.multi_cell(CONTENT_W, 4.6, pdf_safe_text(f"Reason: {patch.reason}"), new_x="LMARGIN", new_y="NEXT")
        if patch.affected_findings:
            pdf.set_x(MARGIN)
            pdf.set_text_color(*MUTED)
            pdf.multi_cell(CONTENT_W, 4.6, pdf_safe_text(f"Affected findings: {', '.join(patch.affected_findings)}"),
                           new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1.5)


def _signoff(pdf: FPDF) -> None:
    if pdf.get_y() > 250:
        pdf.add_page()
    _section_title(pdf, "Sign-off Note")
    _set_fill(pdf, CARD_BG)
    text = (
        "This report is generated from semantic memory cards, evidence pointers, and agent handoffs. "
        "Probabilities are produced by the PyMC scoring layer and reflect modeled uncertainty, not certified "
        "conclusions. Manual review remains required for unresolved audit blockers."
    )
    pdf.set_font("Helvetica", "", 8.5)
    lines = pdf.multi_cell(CONTENT_W - 6, 4.6, pdf_safe_text(text), dry_run=True, output="LINES")
    box_h = len(lines) * 4.6 + 6
    y = pdf.get_y()
    _round_rect(pdf, MARGIN, y, CONTENT_W, box_h, style="F")
    pdf.set_xy(MARGIN + 3, y + 3)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(CONTENT_W - 6, 4.6, pdf_safe_text(text), new_x="LMARGIN", new_y="NEXT")


def generate_pdf(
    findings: list[FindingCard],
    patches: list[MemoryPatch],
    narrative_summary: str = "",
    narrative_open_risks: list[str] | None = None,
) -> AuditReportCard:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / "audit_passport_summary.pdf"
    report = build_report_card(findings, patches, path, narrative_summary, narrative_open_risks)
    ranked = sorted(findings, key=lambda item: item.risk_score, reverse=True)

    pdf = ReportPDF()
    pdf.report_id = report.report_id
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.add_page()

    with tempfile.TemporaryDirectory() as tmp:
        chart_dir = Path(tmp)
        _cover_header(pdf, report)
        _kpi_cards(pdf, report, ranked)
        _exec_summary_box(pdf, report)
        _two_donuts(pdf, report.readiness_score, report.readiness_probability, ranked, chart_dir)
        _charts_page(pdf, ranked, chart_dir)
        pdf.add_page()
        _findings_detail(pdf, ranked)
        _patches_section(pdf, patches)
        _signoff(pdf)
        pdf.output(str(path))

    return report
