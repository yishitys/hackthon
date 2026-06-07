from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = "hackathon_slides"
DEFAULT_SLIDES_PATH = Path("C:/Users/10639/OneDrive/Desktop/hackathon slides.pdf")
DEFAULT_OCR_OUTPUT = PROJECT_ROOT / "data" / "hackathon_slides_ocr.md"


def load_project_env() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    for key in ("DATA_ROOT_DIRECTORY", "SYSTEM_ROOT_DIRECTORY"):
        value = os.getenv(key)
        if value and not Path(value).expanduser().is_absolute():
            os.environ[key] = str((PROJECT_ROOT / value).resolve()).replace("\\", "/")


def require_api_key() -> None:
    load_project_env()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key or api_key == "your_openai_api_key":
        raise SystemExit(
            "Missing LLM_API_KEY. Copy .env.example to .env and set your OpenAI API key."
        )


def import_cognee() -> Any:
    load_project_env()
    import cognee

    return cognee


def stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if hasattr(result, "text"):
        return str(result.text)
    if hasattr(result, "model_dump"):
        return json.dumps(result.model_dump(), ensure_ascii=False, indent=2, default=str)
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False, indent=2, default=str)
    return str(result)


async def remember_text(text: str, dataset: str) -> None:
    require_api_key()
    cognee = import_cognee()
    result = await cognee.remember(text, dataset_name=dataset)
    print(stringify_result(result))


async def remember_path(path: Path, dataset: str) -> None:
    require_api_key()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    cognee = import_cognee()
    result = await cognee.remember(str(path), dataset_name=dataset)
    print(stringify_result(result))


def render_pdf_page(page: Any, pymupdf_module: Any, zoom: float = 2.0) -> bytes:
    matrix = pymupdf_module.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    return pixmap.tobytes("png")


def transcribe_slide_image(client: OpenAI, image_bytes: bytes, page_number: int) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    response = client.chat.completions.create(
        model=os.getenv("OCR_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this hackathon slide into clean markdown. "
                            "Preserve visible headings, bullets, labels, diagrams, "
                            "and important relationships. If a diagram is present, "
                            "describe its structure succinctly. Do not add facts that "
                            "are not visible on the slide."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
    )
    content = response.choices[0].message.content or ""
    return f"## Slide {page_number}\n\n{content.strip()}\n"


def ocr_slides(path: Path, output: Path) -> None:
    require_api_key()
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    import pymupdf

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY"))
    output.parent.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(str(path))
    sections: list[str] = [
        "# Hackathon Slides OCR\n",
        f"Source PDF: {path}\n",
    ]

    for index, page in enumerate(document, start=1):
        print(f"OCR slide {index}/{len(document)}...")
        image_bytes = render_pdf_page(page, pymupdf)
        sections.append(transcribe_slide_image(client, image_bytes, index))

    output.write_text("\n".join(sections), encoding="utf-8")
    print(f"Wrote OCR markdown: {output}")


async def recall(query: str, dataset: str, top_k: int = 5) -> None:
    require_api_key()
    cognee = import_cognee()
    results = await cognee.recall(query_text=query, datasets=[dataset], top_k=top_k)

    if not results:
        print("No results returned.")
        return

    for index, result in enumerate(results, start=1):
        print(f"\n[{index}]")
        print(stringify_result(result))


async def forget_everything() -> None:
    cognee = import_cognee()
    await cognee.forget(everything=True)
    print("Cognee memory cleared.")


async def run_smoke(dataset: str) -> None:
    require_api_key()
    cognee = import_cognee()
    await cognee.forget(everything=True)
    await cognee.remember(
        "Cognee is the memory layer for our hackathon multi-agent system.",
        dataset_name=dataset,
    )
    results = await cognee.recall(
        query_text="What is the memory layer for the hackathon system?",
        datasets=[dataset],
        top_k=3,
    )
    for result in results:
        print(stringify_result(result))


def run_check() -> None:
    load_project_env()
    values = {
        "project_root": str(PROJECT_ROOT),
        "python_env": os.getenv("VIRTUAL_ENV", "(not activated)"),
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
        "llm_api_key": (
            "set"
            if os.getenv("LLM_API_KEY", "").strip()
            and os.getenv("LLM_API_KEY", "").strip() != "your_openai_api_key"
            else "missing"
        ),
        "vector_db_provider": os.getenv("VECTOR_DB_PROVIDER", "lancedb"),
        "graph_database_provider": os.getenv("GRAPH_DATABASE_PROVIDER", "kuzu"),
        "data_root_directory": os.getenv("DATA_ROOT_DIRECTORY", "./.cognee/data"),
        "system_root_directory": os.getenv("SYSTEM_ROOT_DIRECTORY", "./.cognee/system"),
        "default_slides_exists": DEFAULT_SLIDES_PATH.exists(),
        "default_slides_path": str(DEFAULT_SLIDES_PATH),
    }
    print(json.dumps(values, indent=2, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cognee memory helper for the hackathon.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check", help="Print resolved local configuration.")

    smoke = subparsers.add_parser("smoke", help="Run a tiny Cognee remember/recall test.")
    smoke.add_argument("--dataset", default="smoke_test")

    ingest = subparsers.add_parser("ingest-slides", help="Ingest the hackathon slides PDF.")
    ingest.add_argument("--path", type=Path, default=DEFAULT_SLIDES_PATH)
    ingest.add_argument("--ocr-output", type=Path, default=DEFAULT_OCR_OUTPUT)
    ingest.add_argument("--dataset", default=DEFAULT_DATASET)

    ocr = subparsers.add_parser("ocr-slides", help="OCR the image-based slides PDF.")
    ocr.add_argument("--path", type=Path, default=DEFAULT_SLIDES_PATH)
    ocr.add_argument("--output", type=Path, default=DEFAULT_OCR_OUTPUT)

    remember = subparsers.add_parser("remember-text", help="Remember one text snippet.")
    remember.add_argument("text")
    remember.add_argument("--dataset", default=DEFAULT_DATASET)

    query = subparsers.add_parser("query", help="Query a Cognee dataset.")
    query.add_argument("query")
    query.add_argument("--dataset", default=DEFAULT_DATASET)
    query.add_argument("--top-k", type=int, default=5)

    subparsers.add_parser("forget", help="Clear all local Cognee memory.")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "check":
        run_check()
    elif args.command == "smoke":
        asyncio.run(run_smoke(args.dataset))
    elif args.command == "ingest-slides":
        source_path = args.ocr_output if args.ocr_output.exists() else args.path
        asyncio.run(remember_path(source_path, args.dataset))
    elif args.command == "ocr-slides":
        ocr_slides(args.path, args.output)
    elif args.command == "remember-text":
        asyncio.run(remember_text(args.text, args.dataset))
    elif args.command == "query":
        asyncio.run(recall(args.query, args.dataset, args.top_k))
    elif args.command == "forget":
        asyncio.run(forget_everything())


if __name__ == "__main__":
    main()
