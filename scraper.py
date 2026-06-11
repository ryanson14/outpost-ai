import os

from dotenv import load_dotenv
from firecrawl import FirecrawlApp

from competitors import CompetitorTarget, load_competitors
from security import MAX_PAGE_MARKDOWN_CHARS, truncate

load_dotenv()
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)


def fetch_page(url: str) -> str:
    """Scrape a URL into clean Markdown via Firecrawl."""
    print(f"🌐 Firecrawl is scraping: {url}")

    scrape_result = app.scrape_url(url, formats=["markdown"])
    raw = scrape_result.markdown if scrape_result.markdown else ""
    return truncate(raw, MAX_PAGE_MARKDOWN_CHARS, label=url)


def fetch_competitor_changelog(url: str) -> str:
    """Backward-compatible alias."""
    return fetch_page(url)


def scrape_competitor(target: CompetitorTarget) -> dict[str, str]:
    """Scrape changelog and pricing for a single competitor."""
    print(f"\n📡 Scraping {target.name}...")
    return {
        "changelog": fetch_page(target.changelog_url),
        "pricing": fetch_page(target.pricing_url),
    }


def scrape_all_competitors(targets: tuple[CompetitorTarget, ...] | None = None) -> dict[str, dict[str, str]]:
    """Scrape changelog + pricing for every active competitor."""
    competitors = targets or load_competitors()
    results: dict[str, dict[str, str]] = {}
    for target in competitors:
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
