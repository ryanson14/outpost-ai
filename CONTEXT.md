# Outpost — Project Context

## What This Is
An AI-powered **competitive intelligence tool for Product Managers**. It monitors competitors automatically, filters the noise, and delivers only the strategic insights that actually matter — where the PM already works (Slack, Jira, email).

---

## Current Status (as of session migration)

| Phase | Status | Notes |
|---|---|---|
| Phase 1 — The Brain | ✅ COMPLETE | LLM successfully outputs structured strategic JSON |
| Phase 2 — The Fuel | 🔶 IN PROGRESS | Firecrawl working for 1 competitor (Linear). Need 2 more + cron job. |
| Phase 3 — The Delivery | ✅ AHEAD OF SCHEDULE | Slack Webhook code written and alert format defined |

---

## The Three Phases

### Phase 1 — The "Brain" ✅ DONE
The LLM takes two inputs and returns a structured JSON analysis:
- **Input A:** Raw competitor update (scraped text/Markdown)
- **Input B:** User Profile (product goals + current roadmap)

Output JSON shape:
```json
{
  "strategic_intent": "...",
  "threat_level_1_to_10": 7,
  "recommended_roadmap_pivot": "..."
}
```

---

### Phase 2 — The "Fuel" 🔶 IN PROGRESS — RESUME HERE

**What's done:**
- [x] Firecrawl set up and working
- [x] Scraping Linear's `/pricing` and `/changelog` pages

**What's left:**
- [ ] **Expand to 3 competitors total** — add 2 more to the target list (Linear is #1)
- [ ] **Build the Cron Job** — automated 24-hour timer that runs the scraper and feeds new data into Phase 1

**How to pick the other 2 competitors:**
Target their `/pricing` or `/changelog` pages, same pattern as Linear.

---

### Phase 3 — The "Delivery" ✅ CODE WRITTEN (needs wiring)
- [x] Slack Webhook set up
- [x] Alert format defined:
  - 🚨 Strategic Threat Detected: [Competitor Name]
  - Analysis: [So What? from Phase 1]
  - Action: "Check ticket #123 in Jira"
- [ ] **Wire Phase 2 → Phase 1 → Phase 3** end-to-end so the full pipeline runs automatically

---

## Tech Stack

| Layer | Tool |
|---|---|
| Language | **TypeScript** |
| AI Framework | **Vercel AI SDK** |
| Database | **Supabase** (PostgreSQL) — deduplicates alerts so nothing fires twice |
| Scraping | **Firecrawl.dev** — turns websites into clean Markdown for AI |
| Delivery | **Slack Webhook** |

---

## MVP — Must-Have Features

1. **"So What?" Engine** — AI writes a 2-sentence strategic summary per alert.
   > *"Competitor X added Team Workspace. This directly targets your Growth OKR. Potential impact: increased churn for Pro users."*

2. **Jira Integration** — Syncs with your backlog, labels competitor updates against relevant tickets.
   > *"This conflicts with Ticket #402: Add Slack Integration."*

3. **Pricing / G2 Scraper** — Monitors competitor pricing pages + G2/Capterra reviews for frustration clusters.

---

## Full Feature Vision (Post-MVP)

### The Observer (Data Gathering)
- **Shadow Pricing Tracker** — Pricing pages + Reddit/G2/Discord for unlisted deals
- **Feature Diff Engine** — Detects new UI elements or docs signaling a feature launch
- **Sentiment Arbitrage** — Scrapes G2/Capterra "Dislikes" for recurring competitor pain points
- **Hiring Signal Monitor** — Job board tracking (e.g., hiring "Data Privacy Engineers" = SOC2 push)

### The Analyst (Strategic Filtering)
- **Roadmap Alignment** — Jira/Linear sync; auto-label competitor updates against your backlog
- **Tier-One Filtering** — "Noise Slider" to surface only pricing/architecture/API changes
- **Executive Briefing Creator** — One-click "Competitive Landscape" slide or PDF

### The Strategist (Actionable Responses)
- **Counter-PRD Drafter** — Auto-drafts a response PRD when a competitor launches something
- **Sales Battlecard Sync** — Updates Notion/Slack with "How to beat [Competitor's New Feature]" talk tracks
- **"Vibe-Code" Sandbox** — AI clones a competitor's new feature so the PM can explore its flaws

### Integration & Delivery
- **Slack/Teams War Room** — Dedicated alert channel with threaded team discussion
- **Browser Sidebar (Chrome Extension)** — Historical pricing + tech stack visible while browsing competitor sites
- **Bi-Weekly Pulse Email** — Sunday summary: "3 things that changed this week that matter for your roadmap"

---

## Key Decisions
- TypeScript as the primary language
- Vercel AI SDK for AI calls
- Supabase for storage and deduplication
- Firecrawl for scraping
- No frontend yet — Slack is the delivery layer for MVP

---

## Immediate Next Step
> **Finish Phase 2:** Add 2 more competitors to the Firecrawl scraper (same pattern as Linear), then build the 24-hour cron job that runs the full pipeline automatically.
