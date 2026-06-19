"""
clean_data.py
-------------
Cleans and normalises raw scraped text from tribunal_data.json.
Outputs cleaned_data.json, ready for chunking.

Usage:
    python scraper/clean_data.py
"""

import json
import re
from pathlib import Path

INPUT_FILE = Path("data/tribunal_data.json")
OUTPUT_FILE = Path("data/cleaned_data.json")
MIN_CONTENT_LENGTH = 100  # Skip pages with very little text

# Phrases that recur site-wide as navigation/boilerplate noise rather than
# substantive tribunal content. These get stripped out before chunking.
BOILERPLATE_PATTERNS = [
    # Site-wide nav breadcrumb trail, e.g. "justice.govt.nz · Family · Family Court · ..."
    r"justice\.govt\.nz\s*(?:·[^·]+)+·?",
    # Recurring scam warning banner
    r"New Zealanders are warned of scam text messages currently circulating[^.]*\.",
    r"The Ministry does not include any links in our texts\.",
    # "This page was last updated:" footer (date varies, so trim from here onward)
    r"This page was last updated:.*$",
]


def strip_boilerplate(text: str) -> str:
    """Remove recurring site-wide nav/footer/banner text that isn't real content."""
    for pattern in BOILERPLATE_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return text


def clean_text(text: str) -> str:
    """Normalise whitespace and remove unwanted characters."""
    text = strip_boilerplate(text)
    # Collapse multiple spaces/newlines into a single space
    text = re.sub(r"\s+", " ", text)
    # Remove non-ASCII characters (e.g. smart quotes, em dashes if unwanted)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    # Remove repeated punctuation
    text = re.sub(r"[.]{3,}", "...", text)
    # Collapse whitespace again after removals
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        print("Run crawler.py first.")
        return

    with open(INPUT_FILE) as f:
        raw_data = json.load(f)

    print(f"Loaded {len(raw_data)} raw pages.")

    cleaned = []
    skipped = 0
    seen_urls = set()

    for item in raw_data:
        url = item.get("url", "")

        # De-duplicate in case the crawler discovered the same page twice
        # (e.g. via different link paths)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        content = clean_text(item.get("content", ""))
        title = clean_text(item.get("title", ""))

        if len(content) < MIN_CONTENT_LENGTH:
            skipped += 1
            continue

        cleaned.append({
            "url": url,
            "title": title,
            "text": content,
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(cleaned, f, indent=2)

    print(f"Saved {len(cleaned)} cleaned pages. Skipped {skipped} short/duplicate pages.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
