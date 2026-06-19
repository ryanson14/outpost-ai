"""Workspace settings in Supabase (profile, Slack, backlog)."""

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
WORKSPACES_TABLE = "workspaces"
WORKSPACE_MEMBERS_TABLE = "workspace_members"


@dataclass(frozen=True)
class WorkspaceSettings:
    workspace_id: str
    user_id: str
    product_name: str
    product_description: str
    q3_goal: str
    roadmap_focus: str
    backlog_tickets: tuple[BacklogTicket, ...]
    slack_webhook_url: str | None
    threat_threshold: int
    slack_team_id: str | None = None
    slack_team_name: str | None = None
    slack_channel_id: str | None = None
    slack_channel_name: str | None = None
    slack_connected_at: str | None = None

    def slack_oauth_connected(self) -> bool:
        return bool(self.slack_webhook_url and self.slack_channel_id)


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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = strip_control_chars(str(value).strip())
    return cleaned or None


def _row_to_settings(row: dict) -> WorkspaceSettings:
    return WorkspaceSettings(
        workspace_id=str(row["workspace_id"]),
        user_id=str(row["user_id"]),
        product_name=strip_control_chars(str(row["product_name"]).strip()),
        product_description=strip_control_chars(str(row["product_description"]).strip()),
        q3_goal=strip_control_chars(str(row["q3_goal"]).strip()),
        roadmap_focus=strip_control_chars(str(row["roadmap_focus"]).strip()),
        backlog_tickets=_parse_backlog(row.get("backlog_tickets")),
        slack_webhook_url=_optional_str(row.get("slack_webhook_url")),
        threat_threshold=clamp_threat_threshold(str(row.get("threat_threshold", 7)), 7),
        slack_team_id=_optional_str(row.get("slack_team_id")),
        slack_team_name=_optional_str(row.get("slack_team_name")),
        slack_channel_id=_optional_str(row.get("slack_channel_id")),
        slack_channel_name=_optional_str(row.get("slack_channel_name")),
        slack_connected_at=_optional_str(row.get("slack_connected_at")),
    )


def _yaml_seed_row(user_id: str, workspace_id: str) -> dict:
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
        "workspace_id": workspace_id,
        "user_id": user_id,
        **cleaned,
        "backlog_tickets": _backlog_to_json(tickets),
        "slack_webhook_url": None,
        "threat_threshold": 7,
    }


def get_workspace_id_for_user(user_id: str) -> str | None:
    """Return the user's first workspace id, if one exists."""
    if not is_configured():
        return None

    client = get_client()
    response = (
        client.table(WORKSPACE_MEMBERS_TABLE)
        .select("workspace_id")
        .eq("user_id", user_id)
        .order("created_at")
        .limit(1)
        .execute()
    )
    if not response.data:
        return None
    return str(response.data[0]["workspace_id"])


def get_default_workspace_id() -> str | None:
    """Best-effort workspace id for legacy CLI/GitHub Actions runs."""
    if not is_configured():
        return None

    import os

    env_workspace_id = os.environ.get("OUTPOST_WORKSPACE_ID")
    if env_workspace_id:
        return env_workspace_id.strip()

    client = get_client()
    response = (
        client.table(TABLE)
        .select("workspace_id")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if response.data:
        return str(response.data[0]["workspace_id"])

    response = client.table(WORKSPACES_TABLE).select("id").limit(1).execute()
    if response.data:
        return str(response.data[0]["id"])
    return None


def ensure_workspace_for_user(user_id: str, *, email: str | None = None) -> str:
    """Ensure the user has a v1 workspace and owner membership."""
    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    existing = get_workspace_id_for_user(user_id)
    if existing:
        return existing

    workspace_id = user_id
    name = (email or "").split("@")[0].strip() or "Outpost Workspace"
    client = get_client()
    client.table(WORKSPACES_TABLE).upsert(
        {
            "id": workspace_id,
            "name": strip_control_chars(name),
        },
        on_conflict="id",
    ).execute()
    client.table(WORKSPACE_MEMBERS_TABLE).upsert(
        {
            "workspace_id": workspace_id,
            "user_id": user_id,
            "role": "owner",
        },
        on_conflict="workspace_id,user_id",
    ).execute()
    return workspace_id


def get_settings(
    user_id: str | None = None,
    *,
    workspace_id: str | None = None,
) -> WorkspaceSettings | None:
    if not is_configured():
        return None
    if not user_id and not workspace_id:
        raise ValueError("user_id or workspace_id is required.")

    client = get_client()
    query = client.table(TABLE).select("*")
    if workspace_id:
        query = query.eq("workspace_id", workspace_id)
    else:
        query = query.eq("user_id", user_id)
    response = query.limit(1).execute()
    if not response.data:
        return None
    return _row_to_settings(response.data[0])


def _needs_profile_backfill(settings: WorkspaceSettings) -> bool:
    return not all(getattr(settings, field) for field in REQUIRED_FIELDS)


def _backfill_from_yaml(user_id: str, existing: WorkspaceSettings) -> WorkspaceSettings:
    """Fill empty profile fields from profile.yaml (e.g. manually created auth users)."""
    seed = _yaml_seed_row(user_id, existing.workspace_id)
    row = {
        "workspace_id": existing.workspace_id,
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
        "slack_team_id": existing.slack_team_id,
        "slack_team_name": existing.slack_team_name,
        "slack_channel_id": existing.slack_channel_id,
        "slack_channel_name": existing.slack_channel_name,
        "slack_connected_at": existing.slack_connected_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    client = get_client()
    client.table(TABLE).upsert(row, on_conflict="workspace_id").execute()
    updated = get_settings(workspace_id=existing.workspace_id)
    if not updated:
        raise RuntimeError("Failed to backfill workspace settings.")
    return updated


def ensure_settings(user_id: str, *, email: str | None = None) -> WorkspaceSettings:
    """Return settings for user's workspace, seeding from profile.yaml on first login."""
    workspace_id = ensure_workspace_for_user(user_id, email=email)
    existing = get_settings(workspace_id=workspace_id)
    if existing:
        if _needs_profile_backfill(existing):
            return _backfill_from_yaml(user_id, existing)
        return existing

    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    row = _yaml_seed_row(user_id, workspace_id)
    client = get_client()
    client.table(TABLE).insert(row).execute()
    seeded = get_settings(workspace_id=workspace_id)
    if not seeded:
        raise RuntimeError("Failed to seed workspace settings.")
    return seeded


def save_slack_oauth(user_id: str, connection: dict[str, Any]) -> WorkspaceSettings:
    """Persist Slack OAuth connection (incoming webhook + channel metadata)."""
    settings = ensure_settings(user_id)
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "user_id": user_id,
        "slack_webhook_url": strip_control_chars(str(connection["webhook_url"]).strip()),
        "slack_team_id": _optional_str(connection.get("team_id")),
        "slack_team_name": _optional_str(connection.get("team_name")),
        "slack_channel_id": _optional_str(connection.get("channel_id")),
        "slack_channel_name": _optional_str(connection.get("channel_name")),
        "slack_connected_at": now,
        "updated_at": now,
    }
    client = get_client()
    client.table(TABLE).update(row).eq("workspace_id", settings.workspace_id).execute()
    saved = get_settings(workspace_id=settings.workspace_id)
    if not saved:
        raise RuntimeError("Failed to save Slack connection.")
    return saved


def disconnect_slack(user_id: str) -> WorkspaceSettings:
    """Remove Slack OAuth connection and webhook for this user."""
    settings = ensure_settings(user_id)
    now = datetime.now(timezone.utc).isoformat()
    row = {
        "slack_webhook_url": None,
        "slack_team_id": None,
        "slack_team_name": None,
        "slack_channel_id": None,
        "slack_channel_name": None,
        "slack_connected_at": None,
        "updated_at": now,
    }
    client = get_client()
    client.table(TABLE).update(row).eq("workspace_id", settings.workspace_id).execute()
    saved = get_settings(workspace_id=settings.workspace_id)
    if not saved:
        raise RuntimeError("Failed to disconnect Slack.")
    return saved


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

    existing = ensure_settings(user_id)
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
    # Manual webhook paste: only update if provided; preserve OAuth webhook otherwise.
    if not webhook and existing and existing.slack_webhook_url:
        webhook = existing.slack_webhook_url

    row = {
        "workspace_id": existing.workspace_id,
        "user_id": user_id,
        **cleaned,
        "backlog_tickets": _backlog_to_json(backlog_tickets),
        "slack_webhook_url": webhook,
        "threat_threshold": clamp_threat_threshold(str(threat_threshold), 7),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if existing:
        row["slack_team_id"] = existing.slack_team_id
        row["slack_team_name"] = existing.slack_team_name
        row["slack_channel_id"] = existing.slack_channel_id
        row["slack_channel_name"] = existing.slack_channel_name
        row["slack_connected_at"] = existing.slack_connected_at

    client = get_client()
    client.table(TABLE).upsert(row, on_conflict="workspace_id").execute()
    saved = get_settings(workspace_id=existing.workspace_id)
    if not saved:
        raise RuntimeError("Failed to save workspace settings.")
    return saved
