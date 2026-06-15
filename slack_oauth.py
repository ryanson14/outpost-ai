"""Slack OAuth v2 — incoming-webhook scope (channel picker during install)."""

import os
import secrets
from typing import Any
from urllib.parse import urlencode

import requests

SLACK_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_ACCESS_URL = "https://slack.com/api/oauth.v2.access"
OAUTH_SCOPE = "incoming-webhook"


def is_oauth_configured() -> bool:
    return bool(os.environ.get("SLACK_CLIENT_ID") and os.environ.get("SLACK_CLIENT_SECRET"))


def base_url() -> str:
    return os.environ.get("OUTPOST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def redirect_uri() -> str:
    return os.environ.get("SLACK_REDIRECT_URI", f"{base_url()}/slack/callback")


def new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def build_authorize_url(*, state: str) -> str:
    if not is_oauth_configured():
        raise RuntimeError(
            "Slack OAuth not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in .env"
        )
    params = {
        "client_id": os.environ["SLACK_CLIENT_ID"],
        "scope": OAUTH_SCOPE,
        "redirect_uri": redirect_uri(),
        "state": state,
    }
    return f"{SLACK_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict[str, Any]:
    """Exchange OAuth code for team/channel webhook details."""
    if not is_oauth_configured():
        raise RuntimeError("Slack OAuth not configured.")

    response = requests.post(
        SLACK_ACCESS_URL,
        data={
            "client_id": os.environ["SLACK_CLIENT_ID"],
            "client_secret": os.environ["SLACK_CLIENT_SECRET"],
            "code": code,
            "redirect_uri": redirect_uri(),
        },
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()

    if not payload.get("ok"):
        error = payload.get("error", "unknown_error")
        raise RuntimeError(f"Slack OAuth failed: {error}")

    webhook = payload.get("incoming_webhook") or {}
    webhook_url = webhook.get("url")
    if not webhook_url:
        raise RuntimeError("Slack did not return an incoming webhook URL.")

    team = payload.get("team") or {}
    return {
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "channel_id": webhook.get("channel_id"),
        "channel_name": webhook.get("channel"),
        "webhook_url": webhook_url,
    }
