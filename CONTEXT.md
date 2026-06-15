# Outpost — Project Context

> **Resume here:** Phase B Step 6 done (Slack OAuth). Next: **Step 7 — multi-tenant**. Run web UI: `python -m app.main` → http://127.0.0.1:8000. **Manual:** run `supabase/slack_oauth.sql` if `workspace_settings` already exists.

## What This Is
An AI-powered **competitive intelligence tool for Product Managers**. It monitors competitors automatically, filters the noise, and delivers only the strategic insights that actually matter — where the PM already works (Slack, Jira, email).

**GitHub:** `ryanson14/outpost-ai` · **Branch:** `main`  
**Build log:** day-by-day progress in [`PROGRESS.md`](PROGRESS.md)

---

## Current Status (updated — post Day 7 Slack OAuth)

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — The Brain | ✅ COMPLETE | Gemini + profile context (`profile.yaml` + dashboard) |
| Phase 2 — The Fuel | ✅ COMPLETE | Competitors in Supabase (Linear, Jira, Asana, Monday+); dedupe |
| Phase 3 — The Delivery | ✅ COMPLETE | Slack live (webhook + OAuth); GitHub Actions daily @ 9 AM ET |
| Security | ✅ COMPLETE | RLS, prompt guards, input limits — see `SECURITY.md` |
| Productization | 🔶 IN PROGRESS | Phase A complete; Phase B Steps 5–6 complete |

---

## Session Log

> Full day-by-day notes (Days 1–7) live in [`PROGRESS.md`](PROGRESS.md). Summary below.

### May 28, 2026 (initial MVP)
- 3 competitors (Linear, Jira, Asana) · scrape → analyze → Slack pipeline
- GitHub Actions cron · Slack E2E verified

### Later sessions (production hardening + config)
- **Supabase dedupe** — `page_snapshots` table, skip unchanged pages (local + cloud verified)
- **GitHub Actions** — Node 24 action versions (`checkout@v6`, `setup-python@v6`)
- **Security hardening** — `security.py`, `SECURITY.md`, `supabase/rls.sql`, `.env.example`
- **Profile config (Step 1)** — `profile.yaml` + `profile.py`
- **Competitors in Supabase (Step 2)** — `competitors` table + `competitors.py`
- **Backlog ticket refs (Step 3)** — `backlog_tickets` in profile; `related_tickets` → Slack *Related Backlog*

### Day 6 — Web UI (Phase B Step 5)
- **FastAPI dashboard** — `app/` with Supabase Auth, settings, competitor CRUD, **Run now**
- **`workspace_settings`** table — per-user profile, backlog, Slack webhook, threshold
- **Live E2E** — added Monday competitor; Run now → scrape → Gemini → Slack alert from browser
- **Bug fixes** — auth error handling, `save_settings` locals() bug, profile backfill, Gemini 503 retry

### Day 7 — Slack OAuth (Phase B Step 6)
- **`slack_oauth.py`** + **`app/slack_routes.py`** — OAuth v2 with `incoming-webhook` scope
- Dashboard **Add to Slack** / **Disconnect** — channel picker during install; webhook stored automatically
- **`supabase/slack_oauth.sql`** — migration for team/channel metadata columns on `workspace_settings`
- Manual webhook paste kept as advanced fallback; GitHub Actions cron still uses `.env` until Step 8
- **Live E2E verified:** Add to Slack → Jira/Linear/Monday alerts (9/10 each) delivered via OAuth webhook

---

## Roadmap — Do these in order

### Phase A — Config polish (before multi-user)
- [x] **1. User profile in `profile.yaml`** — edit goals/roadmap without code changes
- [x] **2. Configurable competitors in Supabase** — `competitors` table + `competitors.py`
- [x] **3. Jira-style ticket references in Slack alerts** — `backlog_tickets`; Gemini `related_tickets` → Slack
- [x] **4. Keep this file updated** after each major session

### Phase B — Sellable product (startup PMs)
- [x] **5. Simple web UI (v1)** — FastAPI + Supabase Auth: signup, profile/settings, competitors, run pipeline
- [x] **6. Slack OAuth** — `Add to Slack` on dashboard (`incoming-webhook` scope); webhook stored automatically
- [ ] **7. Multi-tenant Supabase** — `workspaces`, `users`, per-tenant data + RLS policies
- [ ] **8. Move cron off personal GitHub** — Vercel Cron / Inngest per workspace; cron reads dashboard settings
- [ ] **9. Five design partner PM interviews** — validate alert quality
- [ ] **10. Landing page + waitlist**
- [ ] **11. Stripe billing** — when someone says they'd pay

### Phase C — Post-MVP features (don't block on these)
- [ ] Weekly digest email
- [ ] G2 / review scraping
- [ ] TypeScript + Vercel AI SDK migration
- [ ] Jira API integration (real ticket matching)

---

## Refactor when scaling — DON'T FORGET

Structure is **fine for solo MVP / portfolio / 1–5 design partners**. Refactor these **before 50+ customers**:

| Issue | Where | Fix when productizing |
|---|---|---|
| `brain.py` does too much | orchestration + Gemini client + Pydantic models | Split → `pipeline.py` + `analysis.py` |
| ~~Competitors hardcoded~~ | `competitors.py` + Supabase | ✅ Done; add `workspace_id` when multi-tenant |
| Single-tenant everything | one profile, one webhook, one cron | Multi-tenant schema + per-workspace runs (Steps 7–8) |
| ~~CLI only~~ | `python brain.py` | ✅ FastAPI web UI; cron still CLI until Step 8 |
| `service_role` Supabase key | `db.py`, `settings_store.py` | Per-workspace RLS + anon key in browser; service_role server-only |
| Cron vs dashboard split | GitHub Actions uses `profile.yaml` + `.env` | Step 8: per-workspace cron reads `workspace_settings` |
| No automated tests | — | Add tests before charging money |
| ~~Auth rate limiting~~ | `app/auth.py` | ✅ 5 attempts / 15 min on login |

**Code health verdict (May 2026):** Clear file split (`scraper`, `brain`, `dedupe`, `slack_notify`, `security`, `profile`, `app/`). Good enough to keep building.

---

## Repo Layout

| File | Role |
|---|---|
| `brain.py` | Pipeline orchestration + Gemini analysis (+ 503 retry) |
| `competitors.py` | Load/CRUD competitors from Supabase |
| `db.py` | Shared Supabase client (`service_role` + `anon` for auth) |
| `scraper.py` | Firecrawl — scrapes competitors from DB |
| `profile.yaml` | PM product context — used by CLI/cron + seeds dashboard |
| `profile.py` | Loads profile from YAML or Supabase (`user_id`) |
| `settings_store.py` | Per-user `workspace_settings` in Supabase |
| `dedupe.py` | Supabase content hashing |
| `slack_notify.py` | Slack webhook alerts |
| `security.py` | Prompt guards, size limits, validation |
| `app/main.py` | Web UI — auth, settings, competitors, run pipeline |
| `app/auth.py` | Supabase Auth sessions + login rate limit |
| `app/slack_routes.py` | Slack OAuth install / callback / disconnect |
| `slack_oauth.py` | Slack OAuth v2 helpers |
| `supabase/schema.sql` | `page_snapshots` table |
| `supabase/competitors.sql` | `competitors` table + seed data |
| `supabase/workspace_settings.sql` | Per-user settings table + RLS |
| `supabase/slack_oauth.sql` | Slack OAuth columns on `workspace_settings` (run if table already exists) |
| `supabase/rls.sql` | RLS policies (run once in SQL Editor) |
| `SECURITY.md` | Security audit + remaining risks |
| `PROGRESS.md` | Day-by-day build log |
| `.github/workflows/daily-pipeline.yml` | Daily cron + manual run |
| `.env.example` | Secret template (never commit `.env`) |

---

## Environment Variables

```bash
FIRECRAWL_API_KEY=...
GEMINI_API_KEY=...
SLACK_WEBHOOK_URL=...              # CLI/cron path; dashboard stores its own webhook
OUTPOST_THREAT_THRESHOLD=7         # optional; dashboard has per-user threshold
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=...                   # service_role — server/CI only
SUPABASE_ANON_KEY=...              # web UI auth (server-side only)
OUTPOST_SESSION_SECRET=...         # web UI cookie signing
SLACK_CLIENT_ID=...                # Slack OAuth (dashboard "Add to Slack")
SLACK_CLIENT_SECRET=...
# OUTPOST_BASE_URL=http://127.0.0.1:8000
# SLACK_REDIRECT_URI=http://127.0.0.1:8000/slack/callback
# OUTPOST_PROFILE_PATH=profile.yaml   # optional custom profile path
```

**GitHub Actions secrets:** `FIRECRAWL_API_KEY`, `GEMINI_API_KEY`, `SLACK_WEBHOOK_URL`, `SUPABASE_URL`, `SUPABASE_KEY` (no web UI secrets needed for cron).

---

## Run the Pipeline

### CLI / cron path
```bash
source .venv/bin/activate
pip install -r requirements.txt
python brain.py
```

**Flow:** load `profile.yaml` → scrape active competitors → skip if unchanged (Supabase) → Gemini analysis → Slack if threat ≥ threshold → save hashes.

### Web UI path
```bash
python -m app.main   # → http://127.0.0.1:8000
```

**Flow:** sign in → dashboard settings (`workspace_settings`) → **Run now** → same pipeline with per-user profile + Slack webhook.

**First-time web setup:**
1. Supabase SQL Editor → run `supabase/workspace_settings.sql` (+ `supabase/slack_oauth.sql` if table already existed)
2. Authentication → Providers → Email (disable confirm-email for local dev)
3. `.env`: `SUPABASE_ANON_KEY`, `OUTPOST_SESSION_SECRET`
4. **Slack OAuth:** [api.slack.com/apps](https://api.slack.com/apps) → create app → OAuth & Permissions → Redirect URL `http://127.0.0.1:8000/slack/callback` → scope `incoming-webhook` → copy Client ID/Secret to `.env`

**Important:** GitHub Actions cron still uses `profile.yaml` + `SLACK_WEBHOOK_URL` from secrets until Step 8.

---

## MVP Feature Checklist

| Feature | Status |
|---|---|
| "So What?" Engine | ✅ |
| Changelog + pricing scraper | ✅ |
| Slack delivery | ✅ |
| Daily automation (GitHub Actions) | ✅ |
| Content deduplication | ✅ |
| Security hardening + RLS | ✅ |
| Configurable PM profile | ✅ `profile.yaml` + dashboard |
| Configurable competitors | ✅ Supabase + dashboard CRUD |
| Jira ticket references | ✅ `backlog_tickets` + Slack *Related Backlog* |
| Web UI (auth, settings, run pipeline) | ✅ `app/` FastAPI — E2E verified Day 6 |
| Slack OAuth (Add to Slack) | ✅ Step 6 — E2E verified |
| Multi-tenant / per-workspace cron | ❌ Steps 7–8 |

---

## Key Decisions
- Python for MVP speed; TypeScript migration later if needed
- Gemini 2.5 Flash for structured JSON (`StrategicAnalysis` Pydantic schema)
- Slack: OAuth `Add to Slack` on dashboard (preferred); manual webhook + env var fallback for cron
- FastAPI + Jinja templates for web UI (no separate frontend build step yet)
- Threat threshold (default 7) gates alert noise
- Scraped competitor pages = **untrusted** (prompt injection defenses in `security.py`)
- `service_role` Supabase key only in `.env` / GitHub Secrets — never in browser

---

## Immediate Next Step

> **Step 7: Multi-tenant Supabase** — `workspaces` table, per-tenant data + RLS. **Before testing OAuth:** run `supabase/slack_oauth.sql` and set `SLACK_CLIENT_ID` / `SLACK_CLIENT_SECRET` in `.env`.
