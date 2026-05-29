import os

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_THREAT_THRESHOLD = 7


def get_threat_threshold() -> int:
    raw = os.environ.get("OUTPOST_THREAT_THRESHOLD", str(DEFAULT_THREAT_THRESHOLD))
    return int(raw)


def format_threat_alert(
    competitor_name: str,
    strategic_intent: str,
    threat_level: int,
    threat_justification: str,
    recommended_roadmap_pivot: str,
) -> str:
    """Format a Slack message matching the Outpost alert template."""
    return (
        f"🚨 *Strategic Threat Detected: {competitor_name}*\n"
        f"*Threat Level:* {threat_level}/10\n\n"
        f"*Strategic Intent:*\n{strategic_intent}\n\n"
        f"*So What?*\n{threat_justification}\n\n"
        f"*Recommended Action:*\n{recommended_roadmap_pivot}"
    )


def send_slack_alert(message: str, webhook_url: str | None = None) -> bool:
    """Post a message to Slack via incoming webhook. Returns True if sent."""
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("⚠️  SLACK_WEBHOOK_URL not set — skipping Slack notification.")
        return False

    response = requests.post(url, json={"text": message}, timeout=15)
    response.raise_for_status()
    return True
