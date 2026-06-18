"""
chunker.py
----------
Splits cleaned page text into overlapping chunks suitable for
embedding and vector search in Phase 2.

Usage:
    python scraper/chunker.py
"""

import json
from pathlib import Path

INPUT_FILE = Path("data/cleaned_data.json")
OUTPUT_FILE = Path("data/chunks.json")

CHUNK_SIZE = 500    # words per chunk
OVERLAP = 50        # words of overlap between consecutive chunks


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start += chunk_size - overlap  # slide forward with overlap

    return chunks


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        print("Run clean_data.py first.")
        return

    with open(INPUT_FILE) as f:
        pages = json.load(f)

    print(f"Loaded {len(pages)} cleaned pages.")

    all_chunks = []
    for page in pages:
        text_chunks = chunk_text(page["text"])
        for i, chunk in enumerate(text_chunks):
            all_chunks.append({
                "chunk_id": f"{len(all_chunks):05d}",
                "url": page["url"],
                "title": page["title"],
                "chunk_index": i,
                "total_chunks": len(text_chunks),
                "text": chunk,
            })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"Saved {len(all_chunks)} chunks across {len(pages)} pages.")
    print(f"Output: {OUTPUT_FILE}")
    print("\nSample chunk:")
    if all_chunks:
        sample = all_chunks[0]
        print(f"  URL: {sample['url']}")
        print(f"  Title: {sample['title']}")
        print(f"  Text preview: {sample['text'][:150]}...")


if __name__ == "__main__":
    main()
