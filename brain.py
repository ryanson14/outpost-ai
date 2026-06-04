import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from dedupe import has_content_changed, save_snapshots
from scraper import scrape_all_competitors
from slack_notify import format_threat_alert, get_threat_threshold, send_slack_alert

# Define the structured matrix layout
class StrategicAnalysis(BaseModel):
    strategic_intent: str = Field(description="What the competitor is strategically trying to achieve with this move.")
    threat_level: int = Field(description="A scale from 1 (no threat) to 10 (critical threat) relative to our company goals.")
    threat_justification: str = Field(description="Detailed reason for the threat score, explicitly referencing our Q3 goal.")
    recommended_roadmap_pivot: str = Field(description="Direct, actionable advice on what the PM should do next with their backlog.")

load_dotenv() # Automatically loads your hidden .env variables
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def analyze_competitor_move(user_profile: str, competitor_update: str) -> StrategicAnalysis:
    """Feeds the context into Gemini and demands a structured strategic analysis."""
    system_instruction = (
        "You are Outpost, an elite Product Strategy Analyst AI. Your job is to analyze "
        "competitor updates against a user's specific product profile and goals. "
        "Do not just summarize the news. Provide deep, brutal, strategic analysis."
    )
    
    user_prompt = f"""
    OUR PRODUCT PROFILE & GOALS:
    {user_profile}
    
    COMPETITOR UPDATE DETECTED:
    {competitor_update}
    
    Analyze this update and populate the required structure.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=StrategicAnalysis,
            temperature=0.2, 
        ),
    )
    return StrategicAnalysis.model_validate_json(response.text)


def format_competitor_update(competitor_name: str, pages: dict[str, str]) -> str:
    """Combine changelog and pricing markdown into one analysis payload."""
    return (
        f"Competitor: {competitor_name}\n\n"
        f"## Changelog / Product Updates\n{pages.get('changelog', '')}\n\n"
        f"## Pricing\n{pages.get('pricing', '')}"
    )


DEFAULT_USER_PROFILE = """
Product Name: TaskFlow AI (Project management for AI startups)
Current Q3 Goal: Increase retention of enterprise engineering teams.
Current Roadmap Focus: Building a deep 'Jira-to-GitHub' automated synchronization engine.
"""


def run_pipeline(user_profile: str = DEFAULT_USER_PROFILE) -> None:
    """Scrape → analyze → Slack alert when threat meets threshold."""
    threshold = get_threat_threshold()
    print(f"🚀 STEP 1: Scraping all competitors (changelog + pricing)...")
    all_intel = scrape_all_competitors()

    print(f"\n🧠 STEP 2: Strategic analysis (Slack alerts at threat ≥ {threshold})...")
    for name, pages in all_intel.items():
        if not has_content_changed(name, pages):
            print(f"\n{'=' * 60}")
            print(f"⏭️  {name} — no page changes since last run, skipping.")
            continue

        competitor_update = format_competitor_update(name, pages)
        print(f"\n{'=' * 60}")
        print(f"Analyzing {name}...")
        analysis = analyze_competitor_move(user_profile, competitor_update)
        print(f"\n📊 {name} — threat {analysis.threat_level}/10")
        print(analysis.model_dump_json(indent=2))

        if analysis.threat_level >= threshold:
            alert = format_threat_alert(
                competitor_name=name,
                strategic_intent=analysis.strategic_intent,
                threat_level=analysis.threat_level,
                threat_justification=analysis.threat_justification,
                recommended_roadmap_pivot=analysis.recommended_roadmap_pivot,
            )
            print(f"\n📣 STEP 3: Sending Slack alert for {name}...")
            if send_slack_alert(alert):
                print("✅ Slack alert sent.")
        else:
            print(f"ℹ️  Below threshold ({threshold}) — no Slack alert.")

        save_snapshots(name, pages)


if __name__ == "__main__":
    run_pipeline()