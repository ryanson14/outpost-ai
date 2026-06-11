from dataclasses import dataclass

import httpx

from db import get_client, is_configured
from security import strip_control_chars, validate_https_url

TABLE = "competitors"


@dataclass(frozen=True)
class CompetitorTarget:
    name: str
    changelog_url: str
    pricing_url: str


# Seeded into Supabase when the table is empty (see supabase/competitors.sql)
DEFAULT_COMPETITORS: tuple[CompetitorTarget, ...] = (
    CompetitorTarget(
        name="Linear",
        changelog_url="https://linear.app/changelog",
        pricing_url="https://linear.app/pricing",
    ),
    CompetitorTarget(
        name="Jira",
        changelog_url="https://www.atlassian.com/software/jira/whats-new",
        pricing_url="https://www.atlassian.com/software/jira/pricing",
    ),
    CompetitorTarget(
        name="Asana",
        changelog_url="https://asana.com/product/updates",
        pricing_url="https://asana.com/pricing",
    ),
)


def _row_to_target(row: dict) -> CompetitorTarget:
    return CompetitorTarget(
        name=strip_control_chars(str(row["name"]).strip()),
        changelog_url=validate_https_url(str(row["changelog_url"])),
        pricing_url=validate_https_url(str(row["pricing_url"])),
    )


def _seed_defaults(client) -> None:
    rows = [
        {
            "name": c.name,
            "changelog_url": c.changelog_url,
            "pricing_url": c.pricing_url,
            "active": True,
        }
        for c in DEFAULT_COMPETITORS
    ]
    client.table(TABLE).upsert(rows, on_conflict="name").execute()
    print("📋 Seeded default competitors into Supabase.")


def load_competitors() -> tuple[CompetitorTarget, ...]:
    """Load active competitors from Supabase. Seeds defaults if table is empty."""
    if not is_configured():
        print("⚠️  Supabase not configured — using built-in default competitors.")
        return DEFAULT_COMPETITORS

    try:
        client = get_client()
        response = (
            client.table(TABLE)
            .select("name, changelog_url, pricing_url")
            .eq("active", True)
            .order("name")
            .execute()
        )

        if not response.data:
            _seed_defaults(client)
            response = (
                client.table(TABLE)
                .select("name, changelog_url, pricing_url")
                .eq("active", True)
                .order("name")
                .execute()
            )

        if not response.data:
            raise RuntimeError("No active competitors found. Add rows to the competitors table.")

        return tuple(_row_to_target(row) for row in response.data)
    except httpx.ConnectError:
        print(
            "⚠️  Cannot reach Supabase (bad SUPABASE_URL or no internet). "
            "Check .env matches Settings → API → API URL (https://xxx.supabase.co, no /rest/v1). "
            "Using built-in default competitors."
        )
        return DEFAULT_COMPETITORS


def load_competitor_names() -> set[str]:
    return {c.name for c in load_competitors()}


def list_all_competitors() -> list[dict]:
    """Return all competitors (active and inactive) for the web UI."""
    if not is_configured():
        return [
            {
                "name": c.name,
                "changelog_url": c.changelog_url,
                "pricing_url": c.pricing_url,
                "active": True,
            }
            for c in DEFAULT_COMPETITORS
        ]

    client = get_client()
    response = (
        client.table(TABLE)
        .select("name, changelog_url, pricing_url, active")
        .order("name")
        .execute()
    )
    return response.data or []


def upsert_competitor(
    name: str,
    changelog_url: str,
    pricing_url: str,
    *,
    active: bool = True,
) -> CompetitorTarget:
    """Create or update a competitor row."""
    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    safe_name = strip_control_chars(name.strip())
    if not safe_name or len(safe_name) > 64:
        raise ValueError("Invalid competitor name.")

    target = CompetitorTarget(
        name=safe_name,
        changelog_url=validate_https_url(changelog_url),
        pricing_url=validate_https_url(pricing_url),
    )

    client = get_client()
    client.table(TABLE).upsert(
        {
            "name": target.name,
            "changelog_url": target.changelog_url,
            "pricing_url": target.pricing_url,
            "active": active,
        },
        on_conflict="name",
    ).execute()
    return target


def set_competitor_active(name: str, active: bool) -> None:
    """Activate or deactivate a competitor without deleting history."""
    if not is_configured():
        raise RuntimeError("Supabase not configured.")

    safe_name = strip_control_chars(name.strip())
    client = get_client()
    client.table(TABLE).update({"active": active}).eq("name", safe_name).execute()
