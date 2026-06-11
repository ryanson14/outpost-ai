"""Per-user workspace settings in Supabase (profile, Slack, backlog)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from db import get_client, is_configured
from profile import BacklogTicket, load_backlog_tickets as load_yaml_backlog
from security import (
    MAX_BACKLOG_TICKETS,
    clamp_threat_threshold,
    strip_control_chars,
    validate_ticket_id,
    validate_ticket_title,
)

TABLE = "workspace_settings"
REQUIRED_FIELDS = ("product_name", "product_description", "q3_goal", "roadmap_focus")


@dataclass(frozen=True)
class WorkspaceSettings:
    user_id: str
    product_name: str
    product_description: str
    q3_goal: str
    roadmap_focus: str
    backlog_tickets: tuple[BacklogTicket, ...]
    slack_webhook_url: str | None
    threat_threshold: int


def _parse_backlog(raw: Any) -> tuple[BacklogTicket, ...]:
    if not isinstance(raw, list):
        return ()
    tickets: list[BacklogTicket] = []
    seen: set[str] = set()
    for entry in raw[:MAX_BACKLOG_TICKETS]:
        if not isinstance(entry, dict):
            continue
        ticket_id = entry.get("id")
        title = entry.get("title")
        if not ticket_id or not title:
            continue
        safe_id = validate_ticket_id(str(ticket_id))
        if safe_id in seen:
            continue
        seen.add(safe_id)
        tickets.append(
            BacklogTicket(id=safe_id, title=validate_ticket_title(str(title)))
        )
    return tuple(tickets)


def _backlog_to_json(tickets: tuple[BacklogTicket, ...]) -> list[dict[str, str]]:
    return [{"id": t.id, "title": t.title} for t in tickets]


def _row_to_settings(row: dict) -> WorkspaceSettings:
    return WorkspaceSettings(
        user_id=str(row["user_id"]),
        product_name=strip_control_chars(str(row["product_name"]).strip()),
        product_description=strip_control_chars(str(row["product_description"]).strip()),
        q3_goal=strip_control_chars(str(row["q3_goal"]).strip()),
        roadmap_focus=strip_control_chars(str(row["roadmap_focus"]).strip()),
        backlog_tickets=_parse_backlog(row.get("backlog_tickets")),
        slack_webhook_url=(
            strip_control_chars(str(row["slack_webhook_url"]).strip())
            if row.get("slack_webhook_url")
            else None
        ),
        threat_threshold=clamp_threat_threshold(str(row.get("threat_threshold", 7)), 7),
    )


def _yaml_seed_row(user_id: str) -> dict:
    """Build a settings row from profile.yaml for first-time users."""
    from profile import _load_profile_data

    try:
        data = _load_profile_data()
    except (FileNotFoundError, ValueError):
        data = {
            "product_name": "",
            "product_description": "",
            "q3_goal": "",
            "roadmap_focus": "",
        }

    cleaned = {
        field: strip_control_chars(str(data.get(field, "")).strip())
        for field in REQUIRED_FIELDS
    }
    tickets = load_yaml_backlog()
    return {
        "user_id": user_id,
        **cleaned,
        "backlog_tickets": _backlog_to_json(tickets),
        "slack_webhook_url": None,
        "threat_threshold": 7,
    }


def get_settings(user_id: str) -> WorkspaceSettings | None:
    if not is_configured():
        return None
    client = get_client()
    response = (
        client.table(TABLE).select("*").eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        return None
    return _row_to_settings(response.data[0])


def _needs_profile_backfill(settings: WorkspaceSettings) -> bool:
    return not all(getattr(settings, field) for field in REQUIRED_FIELDS)


def _backfill_from_yaml(user_id: str, existing: WorkspaceSettings) -> WorkspaceSettings:
    """Fill empty profile fields from profile.yaml (e.g. manually created auth users)."""
    seed = _yaml_seed_row(user_id)
    row = {
        "user_id": user_id,
        "product_name": existing.product_name or seed["product_name"],
        "product_description": existing.product_description or seed["product_description"],
        "q3_goal": existing.q3_goal or seed["q3_goal"],
        "roadmap_focus": existing.roadmap_focus or seed["roadmap_focus"],
        "backlog_tickets": (
            _backlog_to_json(existing.backlog_tickets)
            if existing.backlog_tickets
            else seed["backlog_tickets"]
        ),
        "slack_webhook_url": existing.slack_webhook_url,
        "threat_threshold": existing.threat_threshold,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = get_client()
    client.table(TABLE).upsert(row, on_conflict="user_id").execute()
    updated = get_settings(user_id)
    if not updated:
        raise RuntimeError("Failed to backfill workspace settings.")
    return updated


def ensure_settings(user_id: str) -> WorkspaceSettings:
    """Return settings for user, seeding from profile.yaml on first login."""
    existing = get_settings(user_id)
    if existing:
        if _needs_profile_backfill(existing):
            return _backfill_from_yaml(user_id, existing)
        return existing

    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    row = _yaml_seed_row(user_id)
    client = get_client()
    client.table(TABLE).insert(row).execute()
    seeded = get_settings(user_id)
    if not seeded:
        raise RuntimeError("Failed to seed workspace settings.")
    return seeded


def save_settings(
    user_id: str,
    *,
    product_name: str,
    product_description: str,
    q3_goal: str,
    roadmap_focus: str,
    backlog_tickets: tuple[BacklogTicket, ...],
    slack_webhook_url: str | None,
    threat_threshold: int,
) -> WorkspaceSettings:
    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    existing = get_settings(user_id)
    cleaned = {
        "product_name": strip_control_chars(product_name.strip()),
        "product_description": strip_control_chars(product_description.strip()),
        "q3_goal": strip_control_chars(q3_goal.strip()),
        "roadmap_focus": strip_control_chars(roadmap_focus.strip()),
    }
    if existing:
        for field in REQUIRED_FIELDS:
            if not cleaned[field]:
                cleaned[field] = getattr(existing, field)
    missing = [f for f, v in cleaned.items() if not v]
    if missing:
        labels = {
            "product_name": "Product name",
            "product_description": "Product description",
            "q3_goal": "Q3 goal",
            "roadmap_focus": "Roadmap focus",
        }
        raise ValueError(
            "Required: " + ", ".join(labels.get(f, f) for f in missing)
            + ". Refresh the page — defaults load from profile.yaml."
        )

    webhook = (
        strip_control_chars(slack_webhook_url.strip())
        if slack_webhook_url and slack_webhook_url.strip()
        else None
    )

    row = {
        "user_id": user_id,
        **cleaned,
        "backlog_tickets": _backlog_to_json(backlog_tickets),
        "slack_webhook_url": webhook,
        "threat_threshold": clamp_threat_threshold(str(threat_threshold), 7),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    client = get_client()
    client.table(TABLE).upsert(row, on_conflict="user_id").execute()
    saved = get_settings(user_id)
    if not saved:
        raise RuntimeError("Failed to save workspace settings.")
    return saved
