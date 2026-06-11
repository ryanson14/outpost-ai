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


def _supabase_url() -> str:
    return _normalize_supabase_url(os.environ["SUPABASE_URL"])


def get_client():
    from supabase import create_client

    if not is_configured():
        raise RuntimeError("Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY in .env")
    key = os.environ["SUPABASE_KEY"].strip().strip('"').strip("'")
    return create_client(_supabase_url(), key)


def is_auth_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))


def get_auth_client():
    """Supabase client with anon key — for sign-in/sign-up only (server-side)."""
    from supabase import create_client

    if not is_auth_configured():
        raise RuntimeError(
            "Web auth not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY in .env"
        )
    key = os.environ["SUPABASE_ANON_KEY"].strip().strip('"').strip("'")
    return create_client(_supabase_url(), key)
