from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from traceback import format_exc, format_exception_only
from urllib.parse import parse_qs, unquote, urlparse

from .export_web_data import WEB_DATA_DIR, export_web_data


ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = ROOT / "web"


@dataclass
class RunJob:
    job_id: str
    use_cognee: bool
    include_ripple: bool = False
    status: str = "queued"
    message: str = "Queued live agent run."
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result: dict | None = None
    error: str = ""


JOBS: dict[str, RunJob] = {}
JOBS_LOCK = threading.Lock()


def parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def serialize_job(job: RunJob) -> dict:
    payload = {
        "ok": job.status != "failed",
        "job_id": job.job_id,
        "status": job.status,
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "use_cognee": job.use_cognee,
        "include_ripple": job.include_ripple,
    }
    if job.result is not None:
        payload.update(job.result)
    if job.error:
        payload["error"] = job.error
    return payload


def update_job(job_id: str, **changes: object) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        for key, value in changes.items():
            setattr(job, key, value)
        job.updated_at = datetime.now(timezone.utc).isoformat()


def run_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
        use_cognee = job.use_cognee
        include_ripple = job.include_ripple
    update_job(job_id, status="running", message="Running GPT agents and Cognee memory handoff.")
    try:
        result = asyncio.run(
            export_web_data(use_cognee=use_cognee, output_dir=WEB_DATA_DIR, include_ripple=include_ripple)
        )
    except Exception as exc:
        message = "".join(format_exception_only(type(exc), exc)).strip()
        trace = format_exc()
        print(trace, flush=True)
        update_job(
            job_id,
            status="failed",
            message="Live run failed.",
            error=(
                f"{message} Check OPENAI_API_KEY/LLM_API_KEY, Cognee configuration, and data/kaggle CSV files.\n"
                f"{trace}"
            ),
        )
        return
    update_job(job_id, status="succeeded", message="Live run complete.", result=result)


class AuditPassportHandler(BaseHTTPRequestHandler):
    server_version = "AuditPassportWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self.send_json({"status": "ok"})
            return
        if parsed.path == "/api/run-status":
            query = parse_qs(parsed.query)
            job_id = query.get("id", [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            if job is None:
                self.send_json({"ok": False, "error": f"Unknown job id: {job_id}"}, status=HTTPStatus.NOT_FOUND)
                return
            self.send_json(serialize_job(job))
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/run":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        query = parse_qs(parsed.query)
        use_cognee = parse_bool(query.get("use_cognee", [None])[0], default=True)
        include_ripple = parse_bool(query.get("include_ripple", [None])[0], default=False)
        job_id = uuid.uuid4().hex
        with JOBS_LOCK:
            JOBS[job_id] = RunJob(job_id=job_id, use_cognee=use_cognee, include_ripple=include_ripple)
        thread = threading.Thread(target=run_job, args=(job_id,), daemon=True)
        thread.start()
        self.send_json(serialize_job(JOBS[job_id]), status=HTTPStatus.ACCEPTED)

    def serve_static(self, request_path: str) -> None:
        relative = unquote(request_path.lstrip("/")) or "index.html"
        target = (WEB_ROOT / relative).resolve()
        try:
            target.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        body = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve Audit Passport web UI with live multi-agent API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5173)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), AuditPassportHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Audit Passport live server running at {url}")
    print("Open the URL and click Start demo to run the GPT + Cognee pipeline.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Audit Passport live server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
