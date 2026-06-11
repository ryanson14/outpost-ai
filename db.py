import os

from dotenv import load_dotenv

load_dotenv()


def is_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def _normalize_supabase_url(url: str) -> str:
    url = url.strip().strip('"').strip("'")
    for suffix in ("/rest/v1/", "/rest/v1"):
        if url.endswith(suffix):
            url = url[: -len(suffix)]
    return url.rstrip("/")


def get_client():
    from supabase import create_client

    if not is_configured():
        raise RuntimeError("Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
    url = _normalize_supabase_url(os.environ["SUPABASE_URL"])
    key = os.environ["SUPABASE_KEY"].strip().strip('"').strip("'")
    return create_client(url, key)
