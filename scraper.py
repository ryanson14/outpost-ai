import os
from dataclasses import dataclass

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv()
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)


@dataclass(frozen=True)
class CompetitorTarget:
    name: str
    changelog_url: str
    pricing_url: str


# Linear: modern issue tracker (baseline). Jira: enterprise eng teams + Jira ecosystem.
# Asana: broad PM competitor for team retention and roadmap overlap.
COMPETITORS: tuple[CompetitorTarget, ...] = (
    CompetitorTarget(
        name="Linear",
        changelog_url="https://linear.app/changelog",
        pricing_url="https://linear.app/pricing",
    ),
    CompetitorTarget(
        name="Jira",
        changelog_url="https://www.atlassian.com/software/jira/whats-new",
        pricing_url="https://www.atlassian.com/software/jira/pricing",
    ),
    CompetitorTarget(
        name="Asana",
        changelog_url="https://asana.com/product/updates",
        pricing_url="https://asana.com/pricing",
    ),
)


def fetch_page(url: str) -> str:
    """Scrape a URL into clean Markdown via Firecrawl."""
    print(f"🌐 Firecrawl is scraping: {url}")

    scrape_result = app.scrape_url(url, formats=["markdown"])
    return scrape_result.markdown if scrape_result.markdown else ""


def fetch_competitor_changelog(url: str) -> str:
    """Backward-compatible alias used by brain.py."""
    return fetch_page(url)


def scrape_competitor(target: CompetitorTarget) -> dict[str, str]:
    """Scrape changelog and pricing for a single competitor."""
    print(f"\n📡 Scraping {target.name}...")
    return {
        "changelog": fetch_page(target.changelog_url),
        "pricing": fetch_page(target.pricing_url),
    }


def scrape_all_competitors() -> dict[str, dict[str, str]]:
    """Scrape changelog + pricing for every configured competitor."""
    results: dict[str, dict[str, str]] = {}
    for target in COMPETITORS:
        results[target.name] = scrape_competitor(target)
    return results


def preview(text: str, length: int = 400) -> str:
    if len(text) <= length:
        return text
    return text[:length] + "\n...[truncated]..."


if __name__ == "__main__":
    all_intel = scrape_all_competitors()

    for name, pages in all_intel.items():
        print(f"\n{'=' * 60}")
        print(f"⚡️ {name}")
        for page_type, markdown in pages.items():
            print(f"\n  [{page_type}] ({len(markdown)} chars)")
            print(preview(markdown, 300))
