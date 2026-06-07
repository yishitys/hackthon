"""Matplotlib chart rendering for the Audit Passport PDF report.

All charts are rendered headlessly to PNG files inside a caller-provided
directory and embedded into the PDF by ``report.py``. Charts degrade
gracefully: if matplotlib is unavailable, ``charts_available`` is False and
the report falls back to a text-only layout.
"""
from __future__ import annotations

from pathlib import Path

try:  # matplotlib is an optional-but-preferred dependency
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Wedge

    charts_available = True
except Exception:  # pragma: no cover - exercised only when matplotlib is missing
    charts_available = False


# ---- Shared palette (RGB 0-255 mirrored as hex for matplotlib) -------------
NAVY = "#0f2040"
ACCENT = "#2563eb"
MUTED = "#6b7280"
GRID = "#e5e7eb"
PAPER = "#ffffff"

SEVERITY_HEX = {
    "Critical": "#be1827",
    "High": "#ea580c",
    "Medium": "#ca8a04",
    "Low": "#16a463",
}
SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]


def _score_color(value_0_100: float) -> str:
    if value_0_100 >= 80:
        return SEVERITY_HEX["Low"]
    if value_0_100 >= 60:
        return SEVERITY_HEX["Medium"]
    if value_0_100 >= 40:
        return SEVERITY_HEX["High"]
    return SEVERITY_HEX["Critical"]


def _finding_label(finding: object) -> str:
    return str(getattr(finding, "finding_id", "") or "?")


def _apply_clean_axes(ax) -> None:
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)


def readiness_gauge(score: int, probability: float, out_dir: Path) -> Path:
    """Donut gauge: rule readiness score with the PyMC probability beneath."""
    path = out_dir / "chart_readiness.png"
    fig, ax = plt.subplots(figsize=(2.8, 2.8), dpi=200, subplot_kw={"aspect": "equal"})
    color = _score_color(score)
    sweep = 360.0 * max(0, min(100, score)) / 100.0

    ax.add_patch(Wedge((0, 0), 1.0, 0, 360, width=0.26, facecolor=GRID, edgecolor="none"))
    ax.add_patch(Wedge((0, 0), 1.0, 90, 90 - sweep, width=0.26, facecolor=color, edgecolor="none"))

    ax.text(0, 0.12, f"{score}", ha="center", va="center", fontsize=34, color=NAVY, fontweight="bold")
    ax.text(0, -0.22, "/ 100", ha="center", va="center", fontsize=11, color=MUTED)
    ax.text(
        0,
        -0.62,
        f"PyMC ready: {round(probability * 100)}%",
        ha="center",
        va="center",
        fontsize=9.5,
        color=color,
        fontweight="bold",
    )
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    fig.tight_layout(pad=0.1)
    fig.savefig(path, transparent=True)
    plt.close(fig)
    return path


def severity_donut(findings: list, out_dir: Path) -> Path:
    """Composition donut of findings by severity."""
    path = out_dir / "chart_severity.png"
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for finding in findings:
        sev = str(getattr(finding, "severity", "")).title()
        counts[sev] = counts.get(sev, 0) + 1
    labels = [sev for sev in SEVERITY_ORDER if counts.get(sev)]
    values = [counts[sev] for sev in labels]
    colors = [SEVERITY_HEX[sev] for sev in labels]

    fig, ax = plt.subplots(figsize=(2.8, 2.8), dpi=200, subplot_kw={"aspect": "equal"})
    if values:
        ax.pie(
            values,
            colors=colors,
            startangle=90,
            counterclock=False,
            wedgeprops={"width": 0.42, "edgecolor": PAPER, "linewidth": 2},
        )
        ax.text(0, 0.1, f"{sum(values)}", ha="center", va="center", fontsize=26, color=NAVY, fontweight="bold")
        ax.text(0, -0.2, "findings", ha="center", va="center", fontsize=10, color=MUTED)
    else:
        ax.text(0, 0, "No findings", ha="center", va="center", fontsize=12, color=MUTED)
    ax.axis("off")
    fig.tight_layout(pad=0.1)
    fig.savefig(path, transparent=True)
    plt.close(fig)
    return path


def risk_bars(findings: list, out_dir: Path, limit: int = 8) -> Path:
    """Horizontal bar chart of risk scores, colored by severity."""
    path = out_dir / "chart_risk_bars.png"
    items = list(findings)[:limit][::-1]  # reverse so highest sits on top
    labels = [_finding_label(f) for f in items]
    scores = [int(getattr(f, "risk_score", 0)) for f in items]
    colors = [SEVERITY_HEX.get(str(getattr(f, "severity", "")).title(), ACCENT) for f in items]

    height = max(1.6, 0.42 * len(items) + 0.6)
    fig, ax = plt.subplots(figsize=(6.6, height), dpi=200)
    bars = ax.barh(labels, scores, color=colors, height=0.62, zorder=3)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Rule risk score", fontsize=8.5, color=MUTED)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    _apply_clean_axes(ax)
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_width() - 2,
            bar.get_y() + bar.get_height() / 2,
            str(score),
            ha="right",
            va="center",
            fontsize=8,
            color=PAPER,
            fontweight="bold",
        )
    fig.tight_layout(pad=0.3)
    fig.savefig(path, transparent=True)
    plt.close(fig)
    return path


def blocker_intervals(findings: list, out_dir: Path, limit: int = 8) -> Path:
    """Point estimate + 90% credible interval for audit-blocker probability."""
    path = out_dir / "chart_blocker_ci.png"
    items = list(findings)[:limit][::-1]
    labels = [_finding_label(f) for f in items]
    point = [float(getattr(f, "audit_blocker_probability", 0.0)) * 100 for f in items]
    low = [float(getattr(f, "credible_interval_low", 0.0)) * 100 for f in items]
    high = [float(getattr(f, "credible_interval_high", 0.0)) * 100 for f in items]
    colors = [SEVERITY_HEX.get(str(getattr(f, "severity", "")).title(), ACCENT) for f in items]

    y = list(range(len(items)))
    height = max(1.6, 0.42 * len(items) + 0.6)
    fig, ax = plt.subplots(figsize=(6.6, height), dpi=200)
    for yi, p, lo, hi, color in zip(y, point, low, high, colors):
        ax.plot([lo, hi], [yi, yi], color=color, linewidth=2.4, alpha=0.45, zorder=2,
                solid_capstyle="round")
        ax.scatter([p], [yi], s=46, color=color, zorder=4, edgecolor=PAPER, linewidth=1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Audit-blocker probability  (point + 90% credible interval)", fontsize=8.5, color=MUTED)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    _apply_clean_axes(ax)
    fig.tight_layout(pad=0.3)
    fig.savefig(path, transparent=True)
    plt.close(fig)
    return path
