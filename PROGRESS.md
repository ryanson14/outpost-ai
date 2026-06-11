# Outpost — Progress Tracker

> Chronological build log. For architecture, roadmap, and how to run the pipeline see [CONTEXT.md](CONTEXT.md).

**Repo:** `ryanson14/outpost-ai` · **Branch:** `main`

---

## Day 1

### **1. Competitor selection (`scraper.py`)**

Added three PM competitors (Linear was already the baseline):

| **Competitor** | **Changelog / updates** | **Pricing** |
| --- | --- | --- |
| **Linear** | `linear.app/changelog` | `linear.app/pricing` |
| **Jira** | Atlassian Jira whats-new | Jira pricing |
| **Asana** | `asana.com/product/updates` | `asana.com/pricing` |

**Rationale:** Linear = modern issue tracker; Jira = enterprise eng + your TaskFlow "Jira-to-GitHub" angle; Asana = broad PM / retention overlap.

---

### **2. Multi-competitor scraper (`scraper.py`)**

Refactored from a single-URL test script into a small pipeline:

- **`CompetitorTarget`** — dataclass with `name`, `changelog_url`, `pricing_url`
- **`COMPETITORS`** — tuple of all three targets
- **`fetch_page(url)`** — core Firecrawl scrape (replaces inline logic)
- **`fetch_competitor_changelog(url)`** — alias kept for backward compatibility
- **`scrape_competitor(target)`** — scrapes one competitor's changelog + pricing
- **`scrape_all_competitors()`** — returns `{ "Linear": { "changelog": "...", "pricing": "..." }, ... }`
- **`preview()`** — truncates output for the CLI test harness
- **`__main__`** — runs all competitors and prints previews per page

---

### **3. Brain wired to full scrape (`brain.py`)**

Connected the analysis engine to the multi-competitor scraper:

- **Import** — `fetch_competitor_changelog` → `scrape_all_competitors`
- **`format_competitor_update(name, pages)`** — merges changelog + pricing into one labeled blob for Gemini
- **`__main__` flow:**
    1. `scrape_all_competitors()` (6 Firecrawl calls)
    2. Loop each competitor → `format_competitor_update()` → `analyze_competitor_move()` (3 Gemini calls)
    3. Print JSON analysis per competitor

---

## Day 2

**Phase 2 — Data gathering (mostly done)**

- Expanded competitor monitoring from 1 → **3 competitors**: Linear, Jira, Asana
- Each competitor scrapes **changelog + pricing** (6 Firecrawl calls per run)
- Added `scrape_all_competitors()` and wired it into the analysis pipeline

**Phase 1 + 2 — Pipeline orchestration**

- Built `run_pipeline()` in `brain.py`: scrape all → analyze all → deliver alerts
- Gemini returns structured JSON per competitor (`strategic_intent`, `threat_level`, `threat_justification`, `recommended_roadmap_pivot`)

**Phase 3 — Slack delivery (mostly done)**

- Created `slack_notify.py` for formatted Slack alerts via incoming webhook
- Alerts only fire when `threat_level >= 7` (configurable via `OUTPOST_THREAT_THRESHOLD`)
- Full flow: **Scrape → Analyze → Slack** (when threat is high enough)

**Docs & git**

- Updated `CONTEXT.md` to match current architecture and progress
- Pushed 2 commits to GitHub: multi-competitor scraper + Slack integration

---

### **Slack delivery — live & tested ✅**

- Created Slack app and configured **Incoming Webhooks**
- Added `SLACK_WEBHOOK_URL` and `OUTPOST_THREAT_THRESHOLD=5` to `.env` for testing
- Fixed initial 404 error (placeholder webhook URL replaced with real Slack URL)
- Ran full pipeline (`python brain.py`) — scrape → analyze → **Slack alert delivered successfully**
- Confirmed alert format in Slack: competitor name, threat level, strategic intent, So What?, recommended action
- Example: Linear scored **9/10** and triggered a real alert in workspace channel

### **Git & docs**

- Pushed code to GitHub (`main` on `ryanson14/outpost-ai`)
- Updated `CONTEXT.md` with session log, phase status, and Slack E2E success
- Committed latest `CONTEXT.md` progress doc to repo

### **Current MVP status (end of day)**

| **Component** | **Status** |
| --- | --- |
| AI analysis (Brain) | ✅ Done |
| Multi-competitor scraping | ✅ Done |
| Scrape → Analyze pipeline | ✅ Done |
| Slack alerts | ✅ **Live & tested** |
| Daily cron automation | ❌ Not started |
| Supabase deduplication | ❌ Not started |
| Jira integration | ❌ Not started |

---

## Day 3

### **GitHub Actions — daily automation ✅**

- Added `.github/workflows/daily-pipeline.yml`
- Pipeline runs **daily at 9 AM ET** + manual **Run workflow**
- Added GitHub secrets: `FIRECRAWL_API_KEY`, `GEMINI_API_KEY`, `SLACK_WEBHOOK_URL`, `SUPABASE_URL`, `SUPABASE_KEY`
- **First cloud run:** green check — full pipeline works on GitHub's servers
- **Second cloud run:** green check — dedupe skips unchanged pages (no duplicate Slack spam)
- Updated actions to `checkout@v6` and `setup-python@v6` (Node 24 deprecation warning fix)

---

### **Supabase deduplication ✅**

- Created `dedupe.py` — hashes scraped content per competitor + page type
- Added `supabase/schema.sql` — `page_snapshots` table
- Wired into `brain.py`: skip analyze/alert if content unchanged → save hashes after analysis
- Fixed `websockets` dependency conflict in `requirements.txt` (`16.0` → `15.0.1`)
- Fixed Supabase URL handling (strip `/rest/v1`, quotes, etc.)
- **Local test:** first run saves 6 rows; second run skips all 3 competitors
- **Cloud test:** GitHub Actions second run confirms dedupe in production

---

### **Slack (continued from prior session)**

- Set up Slack app + Incoming Webhook
- Fixed 404 (placeholder URL → real webhook)
- Live E2E test: alerts land in Slack channel
- Threshold testing with `OUTPOST_THREAT_THRESHOLD=5`, then back to `7` for production

---

### **Git & docs**

- Pushed: multi-competitor scraper, Slack integration, CONTEXT.md updates
- Pushed: GitHub Actions workflow
- Pushed: Supabase dedupe (`dedupe.py`, `schema.sql`, `brain.py`, `requirements.txt`)
- Pushed: Node 24 action version bump
- `.env` stays local only (secrets never on GitHub)

---

### **Current MVP status (end of session)**

| **Component** | **Status** |
| --- | --- |
| AI analysis (Brain) | ✅ Done |
| Multi-competitor scraping | ✅ Done |
| Scrape → Analyze pipeline | ✅ Done |
| Slack alerts | ✅ Live & tested |
| Daily automation (GitHub Actions) | ✅ Live & tested |
| Supabase deduplication | ✅ Live & tested |
| Jira integration | ❌ Not started |
| More competitors / polish | ❌ Optional |

---

### **Bugs / issues resolved**

- Slack webhook placeholder URL (404)
- Supabase `ConnectError` (bad hostname in URL)
- Supabase `PGRST125` (URL had `/rest/v1` or wrong format)
- `pip install` conflict (`websockets` vs Supabase `realtime`)
- Empty Table Editor (expected until first run; data in `page_snapshots`)

---

### **One-liner for tracker**

> *Completed production MVP: automated daily competitive intel (Firecrawl → Gemini → deduped Slack alerts) via GitHub Actions + Supabase. Verified locally and in cloud with back-to-back runs confirming skip-on-unchanged behavior.*

---

## Day 4

### **Security audit & hardening**

- Reviewed advisor security checklist against the codebase and implemented what applies to the current CLI/cron architecture (no web API yet).
- Added **`security.py`**: prompt-injection defenses (`<<<UNTRUSTED_...>>>` delimiters + system rules), input size limits, competitor/page validation, Gemini call cap, Slack message truncation.
- Hardened **`brain.py`**, **`scraper.py`**, **`dedupe.py`**, **`slack_notify.py`** to use validation and truncation before paid API calls.

### **Supabase RLS**

- Added **`supabase/rls.sql`** — enabled Row Level Security on `page_snapshots` and explicit deny policies for `anon` (public API) access.
- Ran RLS migration in Supabase SQL Editor; verified `rowsecurity = true`.

### **Secrets & docs**

- Confirmed **no hardcoded API keys** in repo; secrets load from env only.
- Strengthened **`.gitignore`** (`.env`, `.env.local`, etc.); added **`.env.example`** template.
- Added **`SECURITY.md`** — checklist evaluation, remaining risks, and what to add when building a web app (auth rate limiting, SSRF protection, etc.).

### **Git**

- **Committed & pushed:** `Add security hardening: RLS, prompt guards, and input limits`

### **Deferred (not needed until web app)**

- Auth endpoint rate limiting (5 attempts / 15 min) — no login routes exist yet.

---

### **One-liner for tracker**

> *Hardened Outpost security: Supabase RLS, prompt-injection guards on scraped content, input size limits, secret hygiene, and full security audit doc — pushed to GitHub.*

---

## Day 5

### **User profile config (`profile.yaml` + `profile.py`) ✅**

- Moved hardcoded PM context out of `brain.py` into **`profile.yaml`** — edit product goals/roadmap without code changes
- Added **`profile.py`**: loads + validates YAML (`product_name`, `product_description`, `q3_goal`, `roadmap_focus`)
- Optional **`OUTPOST_PROFILE_PATH`** env var for custom profile location
- Wired into pipeline: `run_pipeline()` calls `load_user_profile()` before scrape/analyze
- **Git:** committed & pushed — `Move product profile to profile.yaml allow for profile configuration`

---

### **Configurable competitors in Supabase (`competitors.py` + `db.py`) ✅**

- Added **`supabase/competitors.sql`** — `competitors` table with seed rows (Linear, Jira, Asana)
- Created **`db.py`** — shared Supabase client (`get_client()`, `is_configured()`)
- Created **`competitors.py`** — `load_competitors()` reads active competitors from DB; **`DEFAULT_COMPETITORS`** fallback on transient `httpx.ConnectError`
- Refactored **`scraper.py`** to accept competitor list from DB instead of hardcoded tuple
- Extended **`supabase/rls.sql`** — RLS deny policies on `competitors` table (anon blocked)
- **Git:** committed & pushed — `Load competitors from Supabase with shared db client`

---

### **Backlog ticket references in Slack alerts ✅**

- Extended **`profile.yaml`** with optional **`backlog_tickets`** list (Jira-style IDs + titles):
  - `PROJ-402` — Jira-to-GitHub automated sync
  - `PROJ-118` — Enterprise onboarding and retention dashboard
- Extended **`profile.py`**: `BacklogTicket` dataclass, `load_backlog_tickets()`, backlog section injected into Gemini prompt as `OUR BACKLOG (Jira tickets):`
- Extended **`brain.py`**: `StrategicAnalysis.related_tickets` field; pipeline filters model output to allowlisted ticket IDs only
- Extended **`security.py`**: `validate_ticket_id`, `validate_ticket_title`, `filter_related_ticket_ids`; system prompt instructs Gemini to only use profile backlog IDs
- Extended **`slack_notify.py`**: new *Related Backlog* section on high-threat alerts
- **Live E2E test:** Linear scored **9/10** → Slack alert included both tickets in *Related Backlog*; recommended action explicitly referenced `PROJ-118`
- **Git:** committed & pushed — `Add backlog ticket references to analysis and Slack alerts`

---

### **Docs & architecture**

- Updated **`CONTEXT.md`**: Phase A Steps 1–3 marked complete; session log; MVP checklist; next step = Phase B web UI
- Documented architecture split: `profile.yaml` = PM context, Supabase `competitors` = scrape targets, `page_snapshots` = dedupe hashes

---

### **Bugs / issues resolved**

- Transient Supabase **`ConnectError`** on `load_competitors()` — DNS blip; added fallback to `DEFAULT_COMPETITORS` so pipeline doesn't hard-fail
- Gemini **503 UNAVAILABLE** (high demand) on one run — transient; retry succeeded
- Jira changelog still huge — existing 80k truncation in `security.py` continues to handle it

---

### **Current MVP status (end of session)**

| **Component** | **Status** |
| --- | --- |
| AI analysis (Brain) | ✅ Done |
| Multi-competitor scraping | ✅ Done |
| Scrape → Analyze pipeline | ✅ Done |
| Slack alerts | ✅ Live & tested |
| Daily automation (GitHub Actions) | ✅ Live & tested |
| Supabase deduplication | ✅ Live & tested |
| Security hardening + RLS | ✅ Done |
| Configurable PM profile (`profile.yaml`) | ✅ Done |
| Configurable competitors (Supabase) | ✅ Done |
| Backlog ticket refs in Slack | ✅ Live & tested |
| Web UI | ❌ Not started (Phase B next) |
| Real Jira API integration | ❌ Not started (mock/config only today) |
| Multi-tenant / Slack OAuth | ❌ Phase B |

**Phase A (config polish): complete.** Ready for Phase B Step 5 — simple web UI.

---

### **One-liner for tracker**

> *Finished Phase A productization: PM profile in `profile.yaml`, competitors in Supabase, and Gemini-linked backlog tickets (`PROJ-402`, `PROJ-118`) in live Slack alerts — verified E2E with Linear 9/10 threat. Pushed to GitHub; next up is web UI.*
