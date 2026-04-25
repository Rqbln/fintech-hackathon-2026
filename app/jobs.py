"""In-memory job store for background pipeline tasks.

Keyed by job_id (8-char hex). Each entry:
  status: "running" | "done" | "error"
  contract_id: str
  result: dict | None   (populated on done)
  error: str | None     (populated on error)
  started_at: str (ISO)
  finished_at: str | None
"""

from datetime import datetime, timezone

_jobs: dict[str, dict] = {}


def create(job_id: str, contract_id: str) -> dict:
    entry = {
        "job_id": job_id,
        "status": "running",
        "contract_id": contract_id,
        "result": None,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
    }
    _jobs[job_id] = entry
    return entry


def complete(job_id: str, result: dict) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["result"] = result
        _jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


def fail(job_id: str, error: str) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = "error"
        _jobs[job_id]["error"] = error
        _jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


def get(job_id: str) -> dict | None:
    return _jobs.get(job_id)


def list_all() -> list[dict]:
    return list(_jobs.values())
