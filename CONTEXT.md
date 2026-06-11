# Outpost — Project Context

> **Resume here:** MVP engine is production-ready. Phase 1 product polish in progress (`profile.yaml` done). See **Roadmap** and **Refactor when scaling** below.

## What This Is
An AI-powered **competitive intelligence tool for Product Managers**. It monitors competitors automatically, filters the noise, and delivers only the strategic insights that actually matter — where the PM already works (Slack, Jira, email).

**GitHub:** `ryanson14/outpost-ai` · **Branch:** `main`

---

## Current Status (updated — post-security + profile.yaml)

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — The Brain | ✅ COMPLETE | Gemini + `profile.yaml` for PM context |
| Phase 2 — The Fuel | ✅ COMPLETE | 3 competitors, cron, Supabase dedupe |
| Phase 3 — The Delivery | ✅ COMPLETE | Slack live; GitHub Actions daily @ 9 AM ET |
| Security | ✅ COMPLETE | RLS, prompt guards, input limits — see `SECURITY.md` |
| Productization | 🔶 IN PROGRESS | Profile + competitors in Supabase; Jira links next |

---

## Session Log

### May 28, 2026 (initial MVP)
- 3 competitors (Linear, Jira, Asana) · scrape → analyze → Slack pipeline
- GitHub Actions cron · Slack E2E verified

### Later sessions (production hardening)
- **Supabase dedupe** — `page_snapshots` table, skip unchanged pages (local + cloud verified)
- **GitHub Actions** — Node 24 action versions (`checkout@v6`, `setup-python@v6`)
- **Security hardening** — `security.py`, `SECURITY.md`, `supabase/rls.sql`, `.env.example`
- **Profile config (Step 1)** — `profile.yaml` + `profile.py`; removed hardcoded profile from `brain.py`

---

## Roadmap — Do these in order

### Phase A — Config polish (before multi-user)
- [x] **1. User profile in `profile.yaml`** — edit goals/roadmap without code changes
- [x] **2. Configurable competitors in Supabase** — `competitors` table + `competitors.py`
- [ ] **3. Jira-style ticket references in Slack alerts** — e.g. "Review PROJ-402"
- [ ] **4. Keep this file updated** after each major session

### Phase B — Sellable product (startup PMs)
- [ ] **5. Simple web UI** — signup, add competitors, connect Slack
- [ ] **6. Slack OAuth** — replace single incoming webhook per customer
- [ ] **7. Multi-tenant Supabase** — `workspaces`, `users`, per-tenant data + RLS policies
- [ ] **8. Move cron off personal GitHub** — Vercel Cron / Inngest per workspace
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

Structure is **fine for solo MVP / portfolio / 1–5 design partners**. Refactor these **before 50+ customers or a web app**:

| Issue | Where | Fix when productizing |
|---|---|---|
| `brain.py` does too much | orchestration + Gemini client + Pydantic models | Split → `pipeline.py` + `analysis.py` |
| ~~Competitors hardcoded~~ | `competitors.py` + Supabase | ✅ Done; add `workspace_id` when multi-tenant |
| Single-tenant everything | one profile, one webhook, one cron | Multi-tenant schema + per-workspace runs |
| CLI script, no HTTP API | `python brain.py` only | FastAPI/Next.js API for web UI |
| `service_role` Supabase key | `dedupe.py` | Per-workspace RLS + anon key in browser; service_role server-only |
| No automated tests | — | Add tests before charging money |
| Auth rate limiting (5/15 min) | N/A today | Add when login routes exist — see `SECURITY.md` |

**Code health verdict (May 2026):** Not messy vibe-code — clear file split (`scraper`, `brain`, `dedupe`, `slack_notify`, `security`, `profile`). Good enough to keep building.

---

## Repo Layout

| File | Role |
|---|---|
| `brain.py` | Pipeline orchestration + Gemini analysis |
| `competitors.py` | Load active competitors from Supabase |
| `db.py` | Shared Supabase client |
| `scraper.py` | Firecrawl — scrapes competitors from DB |
| `profile.yaml` | **PM product context** — edit this, not code |
| `profile.py` | Loads + validates `profile.yaml` |
| `dedupe.py` | Supabase content hashing |
| `slack_notify.py` | Slack webhook alerts |
| `security.py` | Prompt guards, size limits, validation |
| `supabase/schema.sql` | `page_snapshots` table |
| `supabase/rls.sql` | RLS policies (run once in SQL Editor) |
| `SECURITY.md` | Security audit + remaining risks |
| `.github/workflows/daily-pipeline.yml` | Daily cron + manual run |
| `.env.example` | Secret template (never commit `.env`) |

---

## Environment Variables

```bash
FIRECRAWL_API_KEY=...
GEMINI_API_KEY=...
SLACK_WEBHOOK_URL=...
OUTPOST_THREAT_THRESHOLD=7      # optional
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=...                # service_role — server/CI only
# OUTPOST_PROFILE_PATH=profile.yaml   # optional custom profile path
```

**GitHub Actions secrets:** same keys as above (no `.env` in repo).

---

## Run the Pipeline

```bash
source .venv/bin/activate
pip install -r requirements.txt
python brain.py
```

**Flow:** load `profile.yaml` → scrape competitors → skip if unchanged (Supabase) → Gemini analysis → Slack if threat ≥ threshold → save hashes.

**Edit profile:** change `profile.yaml` → run again (no code edit needed).

**Verify dedupe:** run twice back-to-back; second run should skip all competitors.

---

## MVP Feature Checklist

| Feature | Status |
|---|---|
| "So What?" Engine | ✅ |
| Changelog + pricing scraper | ✅ |
| Slack delivery | ✅ |
| Daily automation | ✅ |
| Content deduplication | ✅ |
| Security hardening + RLS | ✅ |
| Configurable PM profile | ✅ `profile.yaml` |
| Configurable competitors | ✅ Supabase `competitors` table |
| Jira ticket references | ❌ Step 3 |
| Multi-tenant / web UI | ❌ Phase B |

---

## Key Decisions
- Python for MVP speed; TypeScript migration later if needed
- Gemini for structured JSON (`StrategicAnalysis` Pydantic schema)
- Slack = delivery layer (no frontend yet)
- Threat threshold (default 7) gates alert noise
- Scraped competitor pages = **untrusted** (prompt injection defenses in `security.py`)
- `service_role` Supabase key only in `.env` / GitHub Secrets — never in frontend

---

## Immediate Next Step

> **Step 3:** Jira-style ticket references in Slack alerts. **Manual:** Run `supabase/competitors.sql` in SQL Editor if table doesn't exist yet.
