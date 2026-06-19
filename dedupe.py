import hashlib
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from competitors import load_competitor_names
from db import get_client, is_configured
from settings_store import get_default_workspace_id

load_dotenv()

TABLE = "page_snapshots"


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fetch_stored_hashes(workspace_id: str, competitor_name: str) -> dict[str, str]:
    from security import validate_competitor_name

    validate_competitor_name(competitor_name, load_competitor_names(workspace_id))
    client = get_client()
    response = (
        client.table(TABLE)
        .select("page_type, content_hash")
        .eq("workspace_id", workspace_id)
        .eq("competitor_name", competitor_name)
        .execute()
    )
    return {row["page_type"]: row["content_hash"] for row in response.data}


def has_content_changed(
    competitor_name: str,
    pages: dict[str, str],
    *,
    workspace_id: str | None = None,
) -> bool:
    """True if any page is new or its content hash differs from Supabase."""
    if not is_configured():
        print("⚠️  Supabase not configured — skipping dedupe check.")
        return True

    workspace_id = workspace_id or get_default_workspace_id()
    if not workspace_id:
        print("⚠️  No workspace found — skipping dedupe check.")
        return True

    stored = _fetch_stored_hashes(workspace_id, competitor_name)
    for page_type, content in pages.items():
        if stored.get(page_type) != _hash_content(content):
            return True
    return False


def save_snapshots(
    competitor_name: str,
    pages: dict[str, str],
    *,
    workspace_id: str | None = None,
) -> None:
    """Upsert content hashes after a successful analyze pass."""
    if not is_configured():
        return

    from security import validate_competitor_name, validate_page_type

    workspace_id = workspace_id or get_default_workspace_id()
    if not workspace_id:
        print("⚠️  No workspace found — skipping snapshot save.")
        return

    validate_competitor_name(competitor_name, load_competitor_names(workspace_id))
    client = get_client()
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "workspace_id": workspace_id,
            "competitor_name": competitor_name,
            "page_type": validate_page_type(page_type),
            "content_hash": _hash_content(content),
            "updated_at": now,
        }
        for page_type, content in pages.items()
    ]
    client.table(TABLE).upsert(
        rows,
        on_conflict="workspace_id,competitor_name,page_type",
    ).execute()
    print(f"💾 Saved content hashes for {competitor_name}.")
