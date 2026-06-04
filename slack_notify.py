import os

import requests
from dotenv import load_dotenv

from security import clamp_threat_threshold, truncate

load_dotenv()

DEFAULT_THREAT_THRESHOLD = 7


def get_threat_threshold() -> int:
    raw = os.environ.get("OUTPOST_THREAT_THRESHOLD")
    return clamp_threat_threshold(raw, DEFAULT_THREAT_THRESHOLD)


def format_threat_alert(
    competitor_name: str,
    strategic_intent: str,
    threat_level: int,
    threat_justification: str,
    recommended_roadmap_pivot: str,
) -> str:
    """Format a Slack message matching the Outpost alert template."""
    message = (
        f"🚨 *Strategic Threat Detected: {competitor_name}*\n"
        f"*Threat Level:* {threat_level}/10\n\n"
        f"*Strategic Intent:*\n{truncate(strategic_intent, 4000, label='strategic_intent')}\n\n"
        f"*So What?*\n{truncate(threat_justification, 4000, label='threat_justification')}\n\n"
        f"*Recommended Action:*\n{truncate(recommended_roadmap_pivot, 4000, label='recommended_roadmap_pivot')}"
    )
    return truncate(message, 39000, label="slack alert")


def send_slack_alert(message: str, webhook_url: str | None = None) -> bool:
    """Post a message to Slack via incoming webhook. Returns True if sent."""
    url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        print("⚠️  SLACK_WEBHOOK_URL not set — skipping Slack notification.")
        return False

    response = requests.post(url, json={"text": message}, timeout=15)
    response.raise_for_status()
    return True
