import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from competitors import load_competitors
from dedupe import has_content_changed, save_snapshots
from profile import load_backlog_tickets, load_user_profile
from scraper import scrape_all_competitors
from security import (
    MAX_GEMINI_CALLS_PER_RUN,
    MAX_PAGE_MARKDOWN_CHARS,
    SYSTEM_INSTRUCTION,
    build_analysis_prompt,
    truncate,
    filter_related_ticket_ids,
    validate_competitor_name,
)
from slack_notify import format_threat_alert, get_threat_threshold, send_slack_alert

# Define the structured matrix layout
class StrategicAnalysis(BaseModel):
    strategic_intent: str = Field(description="What the competitor is strategically trying to achieve with this move.")
    threat_level: int = Field(description="A scale from 1 (no threat) to 10 (critical threat) relative to our company goals.")
    threat_justification: str = Field(description="Detailed reason for the threat score, explicitly referencing our Q3 goal.")
    recommended_roadmap_pivot: str = Field(description="Direct, actionable advice on what the PM should do next with their backlog.")
    related_tickets: list[str] = Field(
        default_factory=list,
        description="IDs of backlog tickets from OUR BACKLOG most affected by this competitor move. Only use IDs from the profile.",
    )

load_dotenv() # Automatically loads your hidden .env variables
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def analyze_competitor_move(user_profile: str, competitor_update: str) -> StrategicAnalysis:
    """Feeds the context into Gemini and demands a structured strategic analysis."""
    user_prompt = build_analysis_prompt(user_profile, competitor_update)

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=StrategicAnalysis,
            temperature=0.2, 
        ),
    )
    return StrategicAnalysis.model_validate_json(response.text)


def format_competitor_update(competitor_name: str, pages: dict[str, str], allowed_names: set[str]) -> str:
    """Combine changelog and pricing markdown into one analysis payload."""
    safe_name = validate_competitor_name(competitor_name, allowed_names)
    changelog = truncate(pages.get("changelog", ""), MAX_PAGE_MARKDOWN_CHARS, label=f"{safe_name} changelog")
    pricing = truncate(pages.get("pricing", ""), MAX_PAGE_MARKDOWN_CHARS, label=f"{safe_name} pricing")
    return (
        f"Competitor: {safe_name}\n\n"
        f"## Changelog / Product Updates\n{changelog}\n\n"
        f"## Pricing\n{pricing}"
    )


def run_pipeline(user_profile: str | None = None) -> None:
    """Scrape → analyze → Slack alert when threat meets threshold."""
    profile = user_profile or load_user_profile()
    backlog_tickets = load_backlog_tickets()
    ticket_map = {ticket.id: ticket.title for ticket in backlog_tickets}
    allowed_ticket_ids = set(ticket_map)
    threshold = get_threat_threshold()
    competitors = load_competitors()
    allowed_names = {c.name for c in competitors}
    print(f"🚀 STEP 1: Scraping {len(competitors)} competitors (changelog + pricing)...")
    all_intel = scrape_all_competitors(competitors)
    gemini_calls = 0

    print(f"\n🧠 STEP 2: Strategic analysis (Slack alerts at threat ≥ {threshold})...")
    for name, pages in all_intel.items():
        validate_competitor_name(name, allowed_names)
        if not has_content_changed(name, pages):
            print(f"\n{'=' * 60}")
            print(f"⏭️  {name} — no page changes since last run, skipping.")
            continue

        competitor_update = format_competitor_update(name, pages, allowed_names)
        print(f"\n{'=' * 60}")
        print(f"Analyzing {name}...")
        gemini_calls += 1
        if gemini_calls > MAX_GEMINI_CALLS_PER_RUN:
            raise RuntimeError(
                f"Exceeded MAX_GEMINI_CALLS_PER_RUN ({MAX_GEMINI_CALLS_PER_RUN}). "
                "Aborting to protect API quota."
            )
        analysis = analyze_competitor_move(profile, competitor_update)
        print(f"\n📊 {name} — threat {analysis.threat_level}/10")
        print(analysis.model_dump_json(indent=2))

        related_tickets = filter_related_ticket_ids(
            analysis.related_tickets, allowed_ticket_ids
        )
        if related_tickets:
            print(f"📋 Related backlog: {', '.join(related_tickets)}")

        if analysis.threat_level >= threshold:
            alert = format_threat_alert(
                competitor_name=name,
                strategic_intent=analysis.strategic_intent,
                threat_level=analysis.threat_level,
                threat_justification=analysis.threat_justification,
                recommended_roadmap_pivot=analysis.recommended_roadmap_pivot,
                related_tickets=related_tickets,
                ticket_map=ticket_map,
            )
            print(f"\n📣 STEP 3: Sending Slack alert for {name}...")
            if send_slack_alert(alert):
                print("✅ Slack alert sent.")
        else:
            print(f"ℹ️  Below threshold ({threshold}) — no Slack alert.")

        save_snapshots(name, pages)


if __name__ == "__main__":
    run_pipeline()