"""Outpost web UI — settings, competitors, and manual pipeline runs."""

import asyncio
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    check_login_rate_limit,
    clear_login_attempts,
    clear_session,
    get_session_secret,
    get_session_user,
    login,
    set_session,
    signup,
)
from brain import run_pipeline
from competitors import list_all_competitors, set_competitor_active, upsert_competitor
from profile import BacklogTicket
from security import clamp_threat_threshold, validate_ticket_id, validate_ticket_title
from settings_store import ensure_settings, save_settings
from slack_oauth import is_oauth_configured

from app.slack_routes import slack_callback, slack_disconnect, slack_install

APP_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=APP_DIR / "templates")

app = FastAPI(title="Outpost", docs_url=None, redoc_url=None)
app.add_middleware(SessionMiddleware, secret_key=get_session_secret(), https_only=False)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")


def _redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def _flash(request: Request, message: str, *, level: str = "info") -> None:
    request.session["flash"] = {"message": message, "level": level}


def _error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        detail = exc.detail
        return detail if isinstance(detail, str) else str(detail)
    return str(exc)


def _pop_flash(request: Request) -> dict | None:
    flash = request.session.pop("flash", None)
    return flash if isinstance(flash, dict) else None


def _parse_backlog_form(ticket_ids: list[str], ticket_titles: list[str]) -> tuple[BacklogTicket, ...]:
    tickets: list[BacklogTicket] = []
    seen: set[str] = set()
    for raw_id, raw_title in zip(ticket_ids, ticket_titles):
        raw_id = (raw_id or "").strip()
        raw_title = (raw_title or "").strip()
        if not raw_id and not raw_title:
            continue
        if not raw_id or not raw_title:
            raise ValueError("Each backlog ticket needs both an ID and a title.")
        ticket_id = validate_ticket_id(raw_id)
        if ticket_id in seen:
            continue
        seen.add(ticket_id)
        tickets.append(BacklogTicket(id=ticket_id, title=validate_ticket_title(raw_title)))
    return tuple(tickets)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if get_session_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"flash": _pop_flash(request)},
    )


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    check_login_rate_limit(request)
    try:
        result = login(email.strip(), password)
        set_session(
            request,
            user_id=result["id"],
            email=result["email"],
            session=result["session"],
        )
        clear_login_attempts(request)
        return RedirectResponse("/dashboard", status_code=303)
    except HTTPException as exc:
        _flash(request, _error_message(exc), level="error")
        return RedirectResponse("/login", status_code=303)
    except Exception as exc:
        _flash(request, f"Sign in failed: {exc}", level="error")
        return RedirectResponse("/login", status_code=303)


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "signup.html",
        {"flash": _pop_flash(request)},
    )


@app.post("/signup")
async def signup_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    try:
        result = signup(email.strip(), password)
        set_session(
            request,
            user_id=result["id"],
            email=result["email"],
            session=result["session"],
        )
        _flash(request, "Account created. Welcome to Outpost!")
        return RedirectResponse("/dashboard", status_code=303)
    except HTTPException as exc:
        _flash(request, _error_message(exc), level="error")
        return RedirectResponse("/signup", status_code=303)
    except Exception as exc:
        _flash(request, f"Sign up failed: {exc}", level="error")
        return RedirectResponse("/signup", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    clear_session(request)
    return RedirectResponse("/login", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    settings = ensure_settings(user["id"], email=user.get("email"))
    backlog_rows = [{"id": t.id, "title": t.title} for t in settings.backlog_tickets]
    if not backlog_rows:
        backlog_rows = [{"id": "", "title": ""}]

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user,
            "settings": settings,
            "backlog_rows": backlog_rows,
            "slack_oauth_available": is_oauth_configured(),
            "flash": _pop_flash(request),
        },
    )


@app.post("/dashboard")
async def dashboard_save(
    request: Request,
    product_name: str = Form(...),
    product_description: str = Form(...),
    q3_goal: str = Form(...),
    roadmap_focus: str = Form(...),
    slack_webhook_url: str = Form(""),
    threat_threshold: int = Form(7),
    ticket_id: list[str] = Form(default=[]),
    ticket_title: list[str] = Form(default=[]),
):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    try:
        tickets = _parse_backlog_form(ticket_id, ticket_title)
        save_settings(
            user["id"],
            product_name=product_name,
            product_description=product_description,
            q3_goal=q3_goal,
            roadmap_focus=roadmap_focus,
            backlog_tickets=tickets,
            slack_webhook_url=slack_webhook_url or None,
            threat_threshold=clamp_threat_threshold(str(threat_threshold), 7),
        )
        _flash(request, "Settings saved.")
    except Exception as exc:
        _flash(request, str(exc), level="error")

    return RedirectResponse("/dashboard", status_code=303)


@app.get("/competitors", response_class=HTMLResponse)
async def competitors_page(request: Request):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    settings = ensure_settings(user["id"], email=user.get("email"))
    return templates.TemplateResponse(
        request,
        "competitors.html",
        {
            "user": user,
            "competitors": list_all_competitors(settings.workspace_id),
            "flash": _pop_flash(request),
        },
    )


@app.post("/competitors")
async def competitors_save(
    request: Request,
    name: str = Form(...),
    changelog_url: str = Form(...),
    pricing_url: str = Form(...),
):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    try:
        settings = ensure_settings(user["id"], email=user.get("email"))
        upsert_competitor(
            settings.workspace_id,
            name,
            changelog_url,
            pricing_url,
            active=True,
        )
        _flash(request, f"Saved competitor {name.strip()}.")
    except Exception as exc:
        _flash(request, str(exc), level="error")

    return RedirectResponse("/competitors", status_code=303)


@app.post("/competitors/toggle")
async def competitors_toggle(
    request: Request,
    name: str = Form(...),
    active: str = Form(...),
):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    try:
        settings = ensure_settings(user["id"], email=user.get("email"))
        set_competitor_active(settings.workspace_id, name, active.lower() == "true")
        _flash(request, f"Updated {name}.")
    except Exception as exc:
        _flash(request, str(exc), level="error")

    return RedirectResponse("/competitors", status_code=303)


@app.get("/slack/install")
async def route_slack_install(request: Request):
    return await slack_install(request)


@app.get("/slack/callback")
async def route_slack_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
):
    return await slack_callback(request, code=code, state=state, error=error)


@app.post("/slack/disconnect")
async def route_slack_disconnect(request: Request):
    return await slack_disconnect(request)


@app.post("/run-pipeline")
async def run_pipeline_now(request: Request):
    user = get_session_user(request)
    if not user:
        return _redirect_login()

    try:
        settings = ensure_settings(user["id"], email=user.get("email"))
        await asyncio.to_thread(
            run_pipeline,
            user_id=user["id"],
            workspace_id=settings.workspace_id,
        )
        _flash(request, "Pipeline finished. Check Slack for high-threat alerts.")
    except Exception as exc:
        message = str(exc)
        if "503" in message and "UNAVAILABLE" in message:
            message = (
                "Gemini is temporarily overloaded (503). Wait a minute and click Run now again."
            )
        else:
            message = f"Pipeline failed: {message}"
        _flash(request, message, level="error")

    return RedirectResponse("/dashboard", status_code=303)


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
