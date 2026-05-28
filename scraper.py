import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp

load_dotenv() # Automatically loads your hidden .env variables
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

def fetch_competitor_changelog(url: str) -> str:
    """Takes a website URL and uses Firecrawl to scrape it into clean Markdown."""
    print(f"🌐 Firecrawl is scraping target URL: {url}...")
    
    # Firecrawl returns a structured Document object
    scrape_result = app.scrape_url(
        url,
        formats=['markdown'] 
    )
    
    # FIX: Access the markdown property directly using dot notation
    markdown_content = scrape_result.markdown if scrape_result.markdown else ""
    return markdown_content

# Test Harness
if __name__ == "__main__":
    test_url = "https://linear.app/changelog"
    raw_markdown = fetch_competitor_changelog(test_url)
    
    print("\n⚡️ CLEANED MARKDOWN EXTRACTED (First 500 characters):")
    print(raw_markdown[:500] + "\n...[Truncated]...")