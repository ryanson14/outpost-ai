# Outpost Security

## Checklist evaluation (advisor recommendations)

| Recommendation | Needed now? | Status |
|----------------|-------------|--------|
| RLS on every Supabase table | **Yes** (before multi-tenant / public API) | Run `supabase/rls.sql` |
| `.env` in `.gitignore`, never push secrets | **Yes** | ✅ `.gitignore` includes `.env`; use GitHub Secrets for CI |
| Rate limit auth endpoints (5 / 15 min) | **Not yet** — no HTTP API or auth routes | Add when you build FastAPI/Next.js + login |
| Prompt injection defenses | **Yes** — scraped pages are untrusted | ✅ `security.py` delimiters + system rules |
| Scan for hardcoded secrets | **Yes** | ✅ No secrets in repo; run `git grep` before releases |
| Sanitize inputs / size limits | **Yes** | ✅ `security.py` truncation + validation |

---

## Architecture (current)

- **No public HTTP server** — `python brain.py` + GitHub Actions cron only.
- **Secrets** live in `.env` (local) and GitHub Actions secrets (CI).
- **Supabase** accessed with `service_role` from backend only.

---

## What you must do manually

1. **Run RLS migration:** Supabase SQL Editor → paste `supabase/rls.sql` → Run.
2. **Never commit `.env`** — already gitignored; verify with `git status` before push.
3. **Never use `service_role` in a frontend** — only server-side / CI.
4. **Rotate keys** if `.env` or Slack webhook was ever shared or committed.
5. **GitHub:** Settings → Secrets — restrict who can edit Actions secrets.

---

## Remaining risks (honest audit)

| Risk | Severity | Mitigation |
|------|----------|------------|
| `service_role` key leaked | **Critical** | RLS does not block service_role; keep key server-only, rotate if exposed |
| Slack webhook URL leaked | **High** | Anyone can post to your channel; regenerate webhook in Slack |
| Prompt injection via scraped sites | **Medium** | Delimiters + system rules; scraped content is untrusted by design |
| Firecrawl/Gemini cost runaway | **Medium** | Bounded competitors + `MAX_GEMINI_CALLS_PER_RUN`; cron 1x/day |
| No encryption at rest for hashes in Supabase | **Low** | Hashes only; no PII in `page_snapshots` today |
| Single-tenant pipeline (no auth) | **Low for solo MVP** | **High when productized** — add auth + per-tenant keys |
| Dependency vulnerabilities | **Medium** | Run `pip audit` periodically |
| GitHub Actions secret exposure | **Medium** | Don't log env vars; fork PRs don't get secrets by default |

---

## When you add a web app

- [ ] Auth (Supabase Auth / Clerk) + rate limit login (5 attempts / 15 min)
- [ ] Use **anon** + RLS policies per `workspace_id`, not `service_role` in browser
- [ ] HTTPS only, CORS allowlist, CSRF for cookie sessions
- [ ] Validate all user-supplied URLs before Firecrawl (SSRF protection)
- [ ] Audit logging for alert sends

---

## Verify locally

```bash
# No secrets in tracked files
git grep -E 'sk-|eyJhbG|hooks.slack.com/services/[A-Za-z0-9]' -- ':!*.example' ':!.env.example' || echo "OK: no secret patterns"

# .env not tracked
git check-ignore -v .env
```
