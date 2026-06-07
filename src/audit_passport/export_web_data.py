from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from .agents import run_audit_pipeline
from .data_loader import DATA_DIR
from .ripple import apply_memory_ripple


WEB_DATA_DIR = Path("web/data")


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(val) for key, val in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(val) for key, val in value.items()}
    if isinstance(value, Path):
        return str(value).replace("\\", "/")
    return value


def run_to_payload(run: Any) -> dict[str, Any]:
    payload = to_jsonable(run)
    payload["checkpoints"] = [
        {
            "phase": "Agent 1",
            "label": "Found",
            "checkpoint": "Kaggle source cards, schema cards, and evidence-backed findings created.",
        },
        {
            "phase": "Agent 2",
            "label": "Ranked",
            "checkpoint": "Findings sorted by audit risk with visible ranking reasons.",
        },
        {
            "phase": "Agent 3",
            "label": "Planned",
            "checkpoint": "Each finding has a fix, flag, manual review, or escalation rationale.",
        },
        {
            "phase": "Agent 4",
            "label": "Explained",
            "checkpoint": "A compliance-readable report was generated from Cognee-style memory cards.",
        },
        {
            "phase": "Agent 5",
            "label": "Shown",
            "checkpoint": "The interface exposes handoffs, evidence, report status, and feedback state.",
        },
    ]
    return payload


async def export_web_data(use_cognee: bool = False, output_dir: Path = WEB_DATA_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    initial_run = await run_audit_pipeline(DATA_DIR, use_cognee=use_cognee)
    initial_payload = run_to_payload(initial_run)
    ripple_run = await apply_memory_ripple(initial_run, use_cognee=use_cognee)
    ripple_payload = run_to_payload(ripple_run)

    (output_dir / "audit_run.json").write_text(
        json.dumps(initial_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "audit_ripple.json").write_text(
        json.dumps(ripple_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    pdf_path = Path(ripple_payload.get("report", {}).get("pdf_path", ""))
    if pdf_path.exists():
        shutil.copy2(pdf_path, output_dir / "audit_passport_summary.pdf")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Audit Passport web frontend data.")
    parser.add_argument("--use-cognee", action="store_true", help="Write semantic cards to Cognee while exporting.")
    parser.add_argument("--output-dir", type=Path, default=WEB_DATA_DIR)
    args = parser.parse_args()
    asyncio.run(export_web_data(use_cognee=args.use_cognee, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
