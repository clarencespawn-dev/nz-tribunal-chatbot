"""
dynamic_scraper.py
------------------
Uses Playwright to scrape pages that rely on JavaScript rendering.
Run this after crawler.py if some pages returned empty content.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python scraper/dynamic_scraper.py
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

# Add any URLs here that Scrapy couldn't fully load
JS_HEAVY_URLS = [
    "https://www.justice.govt.nz/tribunals/",
    # Add more URLs as needed
]

OUTPUT_FILE = Path("data/tribunal_data.json")


def scrape_page(page, url: str) -> dict:
    """Navigate to a URL and extract text content."""
    print(f"Scraping: {url}")
    page.goto(url, timeout=30000)
    page.wait_for_load_state("networkidle")

    title = page.title()
    # Try to grab the main content area; fall back to body
    try:
        content = page.inner_text("main")
    except Exception:
        content = page.inner_text("body")

    return {
        "url": url,
        "title": title,
        "content": content.strip(),
    }


def main():
    # Load existing data if available
    existing = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            existing = json.load(f)

    existing_urls = {item["url"] for item in existing}
    new_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url in JS_HEAVY_URLS:
            if url in existing_urls:
                print(f"Skipping (already scraped): {url}")
                continue
            try:
                result = scrape_page(page, url)
                if result["content"]:
                    new_results.append(result)
            except Exception as e:
                print(f"Error scraping {url}: {e}")

        browser.close()

    # Merge and save
    all_results = existing + new_results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nDone. Total pages saved: {len(all_results)}")


if __name__ == "__main__":
    main()
