"""Slack OAuth routes for the web UI."""

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from settings_store import disconnect_slack, save_slack_oauth
from slack_oauth import build_authorize_url, exchange_code, is_oauth_configured, new_oauth_state

from app.auth import get_session_user

SESSION_OAUTH_STATE = "slack_oauth_state"
SESSION_OAUTH_USER_ID = "slack_oauth_user_id"


def _flash(request: Request, message: str, *, level: str = "info") -> None:
    request.session["flash"] = {"message": message, "level": level}


async def slack_install(request: Request) -> RedirectResponse:
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    if not is_oauth_configured():
        _flash(
            request,
            "Slack OAuth is not configured. Set SLACK_CLIENT_ID and SLACK_CLIENT_SECRET in .env.",
            level="error",
        )
        return RedirectResponse("/dashboard", status_code=303)

    state = new_oauth_state()
    request.session[SESSION_OAUTH_STATE] = state
    request.session[SESSION_OAUTH_USER_ID] = user["id"]
    return RedirectResponse(build_authorize_url(state=state), status_code=303)


async def slack_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    if error:
        _flash(request, f"Slack authorization cancelled: {error}", level="error")
        return RedirectResponse("/dashboard", status_code=303)

    expected_state = request.session.pop(SESSION_OAUTH_STATE, None)
    expected_user = request.session.pop(SESSION_OAUTH_USER_ID, None)

    if not code or not state or state != expected_state or expected_user != user["id"]:
        _flash(request, "Slack OAuth failed: invalid state. Try again.", level="error")
        return RedirectResponse("/dashboard", status_code=303)

    try:
        connection = exchange_code(code)
        save_slack_oauth(user["id"], connection)
        channel = connection.get("channel_name") or "your channel"
        team = connection.get("team_name") or "your workspace"
        _flash(request, f"Slack connected to {channel} in {team}.")
    except HTTPException:
        raise
    except Exception as exc:
        _flash(request, f"Slack connection failed: {exc}", level="error")

    return RedirectResponse("/dashboard", status_code=303)


async def slack_disconnect(request: Request) -> RedirectResponse:
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    try:
        disconnect_slack(user["id"])
        _flash(request, "Slack disconnected.")
    except Exception as exc:
        _flash(request, str(exc), level="error")

    return RedirectResponse("/dashboard", status_code=303)
