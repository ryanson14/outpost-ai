# Outpost — Project Context

## What This Is
An AI-powered **competitive intelligence tool for Product Managers**. It monitors competitors automatically, filters the noise, and delivers only the strategic insights that actually matter — where the PM already works (Slack, Jira, email).

---

## Current Status (May 28, 2026)

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — The Brain | ✅ COMPLETE | Gemini outputs structured `StrategicAnalysis` JSON |
| Phase 2 — The Fuel | 🔶 MOSTLY DONE | 3 competitors scraped; pipeline wired; **cron + dedupe still needed** |
| Phase 3 — The Delivery | 🔶 MOSTLY DONE | Slack live & tested; **cron automation still needed** |

**Repo:** All work pushed to `main` on GitHub (`ryanson14/outpost-ai`).

---

## Session Log

### May 28, 2026
- Expanded scraper from 1 → **3 competitors** (Linear, Jira, Asana), each with changelog + pricing pages
- Built `scrape_all_competitors()` and wired it into `brain.py`
- Added `run_pipeline()` — full scrape → analyze loop for all competitors
- Created `slack_notify.py` — formatted alerts + incoming webhook delivery
- Added **threat threshold filter** (`OUTPOST_THREAT_THRESHOLD`, default 7) so Slack only fires on high-priority threats
- Updated `CONTEXT.md` to reflect Python MVP architecture and current progress
- **Git:** 2 commits pushed — multi-competitor scraper + Slack integration
- **Slack E2E test passed** — live alert delivered to workspace channel

---

## The Three Phases

### Phase 1 — The "Brain" ✅ DONE
The LLM takes two inputs and returns structured JSON:
- **Input A:** Raw competitor update (scraped Markdown — changelog + pricing)
- **Input B:** User Profile (product goals + current roadmap)

Output shape (`brain.py` → `StrategicAnalysis`):
```json
{
  "strategic_intent": "...",
  "threat_level": 7,
  "threat_justification": "...",
  "recommended_roadmap_pivot": "..."
}
```

---

### Phase 2 — The "Fuel" 🔶 MOSTLY DONE

**What's done:**
- [x] Firecrawl set up and working
- [x] **3 competitors** in `scraper.py`: **Linear**, **Jira**, **Asana** (changelog + pricing each)
- [x] `scrape_all_competitors()` returns markdown for all targets
- [x] `brain.py` → `run_pipeline()` runs scrape → analyze for every competitor

**What's left:**
- [ ] **24-hour cron job** — automate `python brain.py` (e.g. GitHub Actions)
- [ ] **Supabase deduplication** — only analyze/alert when page content actually changes

---

### Phase 3 — The "Delivery" 🔶 MOSTLY DONE

**What's done:**
- [x] `slack_notify.py` — webhook posting + alert formatting
- [x] Wired into `run_pipeline()` in `brain.py`
- [x] Alert format:
  - 🚨 Strategic Threat Detected: [Competitor Name]
  - Threat level, strategic intent, So What? (justification), recommended action
- [x] **Threshold filter** — Slack only when `threat_level >= OUTPOST_THREAT_THRESHOLD` (default **7**)

**What's left:**
- [x] **Live end-to-end test** — `python brain.py` confirmed alert in Slack
- [ ] **Cron automation** — daily scheduled run (pairs with Phase 2)
- [ ] Jira ticket references in alerts (post-MVP polish)

---

## Repo Layout (Python MVP)

| File | Role |
|---|---|
| `scraper.py` | Firecrawl — 3 competitors, changelog + pricing |
| `brain.py` | Gemini analysis + `run_pipeline()` orchestration |
| `slack_notify.py` | Slack incoming webhook alerts |
| `requirements.txt` | Python dependencies |
| `.env` | API keys (not committed) |

> **Note:** Long-term stack targets TypeScript + Vercel AI SDK; current MVP is **Python** for speed.

---

## Environment Variables

```bash
FIRECRAWL_API_KEY=...
GEMINI_API_KEY=...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
OUTPOST_THREAT_THRESHOLD=7   # optional; only Slack when threat_level >= this
```

**Slack setup:** Slack app → Incoming Webhooks → add to workspace → copy webhook URL into `.env`.

---

## Run the Pipeline

```bash
source .venv/bin/activate   # only needed for Python, not git
python brain.py
```

Flow: scrape all competitors → Gemini analysis each → print JSON → **Slack alert** if threat ≥ threshold.

---

## Tech Stack

| Layer | Tool (MVP) | Planned |
|---|---|---|
| Language | **Python 3.11** | TypeScript |
| AI | **Google Gemini** (`google-genai`) | Vercel AI SDK |
| Database | — | Supabase (dedupe alerts) |
| Scraping | **Firecrawl.dev** | Same |
| Delivery | **Slack Incoming Webhook** | Same |

---

## MVP — Must-Have Features

| Feature | Status |
|---|---|
| "So What?" Engine | ✅ `strategic_intent` + `threat_justification` |
| Pricing / Changelog Scraper | ✅ Linear, Jira, Asana |
| Slack Delivery | ✅ Live & tested |
| Jira Integration | ❌ Not started |

---

## Immediate Next Step

> **1)** Add GitHub Actions cron for daily runs. **2)** Add Supabase content hashing so unchanged pages don't re-alert.

---

## Key Decisions
- Python for MVP prototyping; TypeScript migration later
- Gemini for structured JSON analysis
- Supabase planned for deduplication (not built yet)
- Firecrawl for scraping
- No frontend — Slack is the delivery layer for MVP
- Threat threshold gates noise before Slack fires
