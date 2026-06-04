import hashlib
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

TABLE = "page_snapshots"


def _allowed_competitor_names() -> set[str]:
    from scraper import COMPETITORS

    return {c.name for c in COMPETITORS}


def is_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def _hash_content(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_supabase_url(url: str) -> str:
    """Strip accidental /rest/v1 suffixes and trailing slashes."""
    url = url.strip().strip('"').strip("'")
    for suffix in ("/rest/v1/", "/rest/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url.rstrip("/")


def _get_client():
    from supabase import create_client

    url = _normalize_supabase_url(os.environ["SUPABASE_URL"])
    key = os.environ["SUPABASE_KEY"].strip().strip('"').strip("'")
    return create_client(url, key)


def _fetch_stored_hashes(competitor_name: str) -> dict[str, str]:
    from security import validate_competitor_name

    validate_competitor_name(competitor_name, _allowed_competitor_names())
    client = _get_client()
    response = (
        client.table(TABLE)
        .select("page_type, content_hash")
        .eq("competitor_name", competitor_name)
        .execute()
    )
    return {row["page_type"]: row["content_hash"] for row in response.data}


def has_content_changed(competitor_name: str, pages: dict[str, str]) -> bool:
    """True if any page is new or its content hash differs from Supabase."""
    if not is_configured():
        print("⚠️  Supabase not configured — skipping dedupe check.")
        return True

    stored = _fetch_stored_hashes(competitor_name)
    for page_type, content in pages.items():
        if stored.get(page_type) != _hash_content(content):
            return True
    return False


def save_snapshots(competitor_name: str, pages: dict[str, str]) -> None:
    """Upsert content hashes after a successful analyze pass."""
    if not is_configured():
        return

    from security import validate_competitor_name, validate_page_type

    validate_competitor_name(competitor_name, _allowed_competitor_names())
    client = _get_client()
    now = datetime.now(timezone.utc).isoformat()
    rows = [
        {
            "competitor_name": competitor_name,
            "page_type": validate_page_type(page_type),
            "content_hash": _hash_content(content),
            "updated_at": now,
        }
        for page_type, content in pages.items()
    ]
    client.table(TABLE).upsert(rows, on_conflict="competitor_name,page_type").execute()
    print(f"💾 Saved content hashes for {competitor_name}.")
