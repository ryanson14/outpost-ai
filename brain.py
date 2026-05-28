import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# NEW IMPORT: Look in scraper.py and bring in our web fetching function
from scraper import fetch_competitor_changelog

# Define the structured matrix layout
class StrategicAnalysis(BaseModel):
    strategic_intent: str = Field(description="What the competitor is strategically trying to achieve with this move.")
    threat_level: int = Field(description="A scale from 1 (no threat) to 10 (critical threat) relative to our company goals.")
    threat_justification: str = Field(description="Detailed reason for the threat score, explicitly referencing our Q3 goal.")
    recommended_roadmap_pivot: str = Field(description="Direct, actionable advice on what the PM should do next with their backlog.")

load_dotenv() # Automatically loads your hidden .env variables
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

def analyze_competitor_move(user_profile: str, competitor_update: str) -> str:
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
    return response.text

# Test Harness
if __name__ == "__main__":
    # Our constant PM Context
    mock_user_profile = """
    Product Name: TaskFlow AI (Project management for AI startups)
    Current Q3 Goal: Increase retention of enterprise engineering teams.
    Current Roadmap Focus: Building a deep 'Jira-to-GitHub' automated synchronization engine.
    """
    
    # Target URL we want to analyze live
    live_target_url = "https://linear.app/changelog"
    
    print("🚀 STEP 1: Running the Firecrawl Scraper...")
    # This calls our scraper.py script automatically and returns live data
    live_competitor_data = fetch_competitor_changelog(live_target_url)
    
    print("\n🧠 STEP 2: Feeding live data into the Outpost Analysis Engine...")
    analysis_result = analyze_competitor_move(mock_user_profile, live_competitor_data)
    
    print("\n📊 LIVE STRATEGIC ANALYSIS OUTPUT (JSON):")
    print(analysis_result)