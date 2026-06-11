"""Supabase Auth session helpers for the web UI."""

import os
import time
from typing import Any

from fastapi import HTTPException, Request
from supabase_auth.errors import AuthApiError

from db import get_auth_client, is_auth_configured
from settings_store import ensure_settings

SESSION_USER_ID = "user_id"
SESSION_EMAIL = "email"
SESSION_ACCESS_TOKEN = "access_token"
SESSION_REFRESH_TOKEN = "refresh_token"

# Simple in-memory login rate limit (per IP): 5 attempts / 15 min
_LOGIN_ATTEMPTS: dict[str, tuple[int, float]] = {}
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 15 * 60


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_login_rate_limit(request: Request) -> None:
    ip = _client_ip(request)
    now = time.time()
    count, started = _LOGIN_ATTEMPTS.get(ip, (0, now))
    if now - started > _WINDOW_SECONDS:
        count, started = 0, now
    if count >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in 15 minutes.",
        )
    _LOGIN_ATTEMPTS[ip] = (count + 1, started)


def clear_login_attempts(request: Request) -> None:
    _LOGIN_ATTEMPTS.pop(_client_ip(request), None)


def set_session(request: Request, *, user_id: str, email: str, session: Any) -> None:
    request.session[SESSION_USER_ID] = user_id
    request.session[SESSION_EMAIL] = email
    request.session[SESSION_ACCESS_TOKEN] = session.access_token
    request.session[SESSION_REFRESH_TOKEN] = session.refresh_token


def clear_session(request: Request) -> None:
    request.session.clear()


def get_session_user(request: Request) -> dict[str, str] | None:
    user_id = request.session.get(SESSION_USER_ID)
    email = request.session.get(SESSION_EMAIL)
    access_token = request.session.get(SESSION_ACCESS_TOKEN)
    if not user_id or not access_token:
        return None

    if not is_auth_configured():
        return None

    try:
        client = get_auth_client()
        client.auth.set_session(access_token, request.session.get(SESSION_REFRESH_TOKEN, ""))
        user_response = client.auth.get_user()
        user = user_response.user
        if not user or str(user.id) != str(user_id):
            clear_session(request)
            return None
        return {"id": str(user.id), "email": email or (user.email or "")}
    except Exception:
        clear_session(request)
        return None


def require_user(request: Request) -> dict[str, str]:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def _raise_auth_error(exc: AuthApiError) -> None:
    message = getattr(exc, "message", None) or str(exc)
    raise HTTPException(status_code=400, detail=message) from exc


def signup(email: str, password: str) -> dict[str, Any]:
    client = get_auth_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
    except AuthApiError as exc:
        _raise_auth_error(exc)
    if not response.user:
        raise HTTPException(status_code=400, detail="Sign up failed. Check email format.")
    if not response.session:
        raise HTTPException(
            status_code=400,
            detail="Check your email to confirm your account, then sign in.",
        )
    user_id = str(response.user.id)
    ensure_settings(user_id)
    return {
        "id": user_id,
        "email": response.user.email or email,
        "session": response.session,
    }


def login(email: str, password: str) -> dict[str, Any]:
    client = get_auth_client()
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
    except AuthApiError as exc:
        _raise_auth_error(exc)
    if not response.user or not response.session:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    user_id = str(response.user.id)
    ensure_settings(user_id)
    return {
        "id": user_id,
        "email": response.user.email or email,
        "session": response.session,
    }


def get_session_secret() -> str:
    secret = os.environ.get("OUTPOST_SESSION_SECRET")
    if not secret:
        raise RuntimeError(
            "OUTPOST_SESSION_SECRET is required to run the web UI. "
            "Generate one: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret
