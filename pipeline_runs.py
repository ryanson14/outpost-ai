"""Pipeline run status tracking for dashboard-triggered jobs."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from db import get_client, is_configured
from security import strip_control_chars

TABLE = "pipeline_runs"
MAX_ERROR_MESSAGE_CHARS = 1_000


@dataclass(frozen=True)
class PipelineRun:
    id: str
    workspace_id: str
    user_id: str
    status: str
    error_message: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str
    updated_at: str

    def is_active(self) -> bool:
        return self.status in {"queued", "running"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = strip_control_chars(str(value).strip())
    return cleaned or None


def _row_to_run(row: dict) -> PipelineRun:
    return PipelineRun(
        id=str(row["id"]),
        workspace_id=str(row["workspace_id"]),
        user_id=str(row["user_id"]),
        status=str(row["status"]),
        error_message=_optional_str(row.get("error_message")),
        started_at=_optional_str(row.get("started_at")),
        finished_at=_optional_str(row.get("finished_at")),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def get_latest_run(workspace_id: str) -> PipelineRun | None:
    if not is_configured():
        return None

    response = (
        get_client()
        .table(TABLE)
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return _row_to_run(response.data[0])


def create_run(*, workspace_id: str, user_id: str) -> PipelineRun:
    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    now = _now()
    row = {
        "id": str(uuid4()),
        "workspace_id": workspace_id,
        "user_id": user_id,
        "status": "queued",
        "created_at": now,
        "updated_at": now,
    }
    response = get_client().table(TABLE).insert(row).execute()
    if not response.data:
        raise RuntimeError("Failed to create pipeline run.")
    return _row_to_run(response.data[0])


def mark_run_running(run_id: str) -> None:
    now = _now()
    (
        get_client()
        .table(TABLE)
        .update({"status": "running", "started_at": now, "updated_at": now})
        .eq("id", run_id)
        .execute()
    )


def mark_run_succeeded(run_id: str) -> None:
    now = _now()
    (
        get_client()
        .table(TABLE)
        .update(
            {
                "status": "succeeded",
                "finished_at": now,
                "updated_at": now,
                "error_message": None,
            }
        )
        .eq("id", run_id)
        .execute()
    )


def mark_run_failed(run_id: str, error: str) -> None:
    now = _now()
    message = strip_control_chars(error.strip())[:MAX_ERROR_MESSAGE_CHARS]
    (
        get_client()
        .table(TABLE)
        .update(
            {
                "status": "failed",
                "finished_at": now,
                "updated_at": now,
                "error_message": message or "Unknown error",
            }
        )
        .eq("id", run_id)
        .execute()
    )
