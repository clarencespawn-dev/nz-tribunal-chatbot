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


def clean_text(text: str) -> str:
    """Normalise whitespace and remove unwanted characters."""
    # Collapse multiple spaces/newlines into a single space
    text = re.sub(r"\s+", " ", text)
    # Remove non-ASCII characters (e.g. smart quotes, em dashes if unwanted)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    # Remove repeated punctuation
    text = re.sub(r"[.]{3,}", "...", text)
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

    for item in raw_data:
        content = clean_text(item.get("content", ""))
        title = clean_text(item.get("title", ""))

        if len(content) < MIN_CONTENT_LENGTH:
            skipped += 1
            continue

        cleaned.append({
            "url": item.get("url", ""),
            "title": title,
            "text": content,
        })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(cleaned, f, indent=2)

    print(f"Saved {len(cleaned)} cleaned pages. Skipped {skipped} short pages.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
