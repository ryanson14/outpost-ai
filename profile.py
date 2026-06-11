import os
from dataclasses import dataclass
from pathlib import Path

import yaml

from security import (
    MAX_BACKLOG_TICKETS,
    MAX_PROFILE_CHARS,
    strip_control_chars,
    truncate,
    validate_ticket_id,
    validate_ticket_title,
)

DEFAULT_PROFILE_PATH = Path(__file__).parent / "profile.yaml"
REQUIRED_FIELDS = ("product_name", "product_description", "q3_goal", "roadmap_focus")


@dataclass(frozen=True)
class BacklogTicket:
    id: str
    title: str


def _resolve_profile_path(path: Path | str | None = None) -> Path:
    return Path(path or os.environ.get("OUTPOST_PROFILE_PATH", DEFAULT_PROFILE_PATH))


def _load_profile_data(path: Path | str | None = None) -> dict:
    profile_path = _resolve_profile_path(path)

    if not profile_path.is_file():
        raise FileNotFoundError(
            f"Profile not found: {profile_path}. "
            "Create profile.yaml or set OUTPOST_PROFILE_PATH."
        )

    with profile_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid profile format in {profile_path}: expected a YAML mapping.")

    return data


def load_backlog_tickets(path: Path | str | None = None) -> tuple[BacklogTicket, ...]:
    """Load backlog tickets from profile.yaml (optional section)."""
    raw = _load_profile_data(path).get("backlog_tickets") or []
    if not isinstance(raw, list):
        raise ValueError("backlog_tickets must be a list in profile.yaml.")

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
            BacklogTicket(
                id=safe_id,
                title=validate_ticket_title(str(title)),
            )
        )
    return tuple(tickets)


def _format_backlog_section(tickets: tuple[BacklogTicket, ...]) -> str:
    if not tickets:
        return ""
    lines = [f"- {ticket.id}: {ticket.title}" for ticket in tickets]
    return "OUR BACKLOG (Jira tickets):\n" + "\n".join(lines)


def _format_profile(data: dict[str, str], tickets: tuple[BacklogTicket, ...]) -> str:
    sections = [
        (
            f"Product Name: {data['product_name']} ({data['product_description']})\n"
            f"Current Q3 Goal: {data['q3_goal']}\n"
            f"Current Roadmap Focus: {data['roadmap_focus']}"
        )
    ]
    backlog = _format_backlog_section(tickets)
    if backlog:
        sections.append(backlog)
    return "\n\n".join(sections)


def format_user_profile(
    cleaned: dict[str, str],
    tickets: tuple[BacklogTicket, ...],
) -> str:
    """Format validated profile fields + backlog into Gemini prompt text."""
    return truncate(_format_profile(cleaned, tickets), MAX_PROFILE_CHARS, label="user profile")


def load_user_profile(
    path: Path | str | None = None,
    *,
    user_id: str | None = None,
) -> str:
    """Load and format the PM product profile from Supabase or profile.yaml."""
    if user_id:
        from settings_store import get_settings

        settings = get_settings(user_id)
        if not settings:
            raise ValueError(f"No workspace settings for user {user_id}.")
        cleaned = {
            field: getattr(settings, field)
            for field in REQUIRED_FIELDS
        }
        return format_user_profile(cleaned, settings.backlog_tickets)

    data = _load_profile_data(path)

    missing = [field for field in REQUIRED_FIELDS if not data.get(field)]
    if missing:
        raise ValueError(f"Profile missing required fields: {', '.join(missing)}")

    cleaned = {
        field: strip_control_chars(str(data[field]).strip())
        for field in REQUIRED_FIELDS
    }
    tickets = load_backlog_tickets(path)
    return format_user_profile(cleaned, tickets)


def load_backlog_for_user(user_id: str) -> tuple[BacklogTicket, ...]:
    """Load backlog tickets from Supabase workspace settings."""
    from settings_store import get_settings

    settings = get_settings(user_id)
    if not settings:
        return ()
    return settings.backlog_tickets
