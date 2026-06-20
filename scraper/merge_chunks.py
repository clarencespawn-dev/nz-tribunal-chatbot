"""
merge_chunks.py
----------------
Combines chunks from multiple sources (scraped tribunal pages,
legislation PDFs, etc.) into a single chunks.json ready for
chatbot/ingest.py.

Each source file must contain a JSON list of chunk dicts with at least
a "text" field. A "chunk_id" is required to be unique across ALL
sources — this script re-prefixes IDs by source to guarantee that.

Usage:
    python scraper/merge_chunks.py \\
        --sources data/tribunal_chunks.json data/legislation_chunks.json \\
        --output data/chunks.json

If you only have the original chunks.json (tribunal pages, produced by
chunker.py) and want to add legislation on top without re-running the
tribunal scrape, just pass both files in --sources.
"""

import argparse
import json
from pathlib import Path


def load_chunks(path: Path, source_label: str) -> list[dict]:
    if not path.exists():
        print(f"  Skipping {path} (not found)")
        return []

    with open(path) as f:
        chunks = json.load(f)

    # Re-prefix chunk_id with the source label to guarantee uniqueness
    # across files — ChromaDB requires every id to be unique, and two
    # independently-generated files might otherwise both have "00000".
    for chunk in chunks:
        original_id = chunk.get("chunk_id", "")
        chunk["chunk_id"] = f"{source_label}_{original_id}"
        chunk["source_file"] = str(path.name)

    print(f"  Loaded {len(chunks)} chunks from {path}")
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Merge multiple chunk JSON files into one.")
    parser.add_argument(
        "--sources", nargs="+", required=True,
        help="One or more chunk JSON files to merge, in order",
    )
    parser.add_argument("--output", default="data/chunks.json", help="Output path")
    args = parser.parse_args()

    print("Merging chunk sources:")
    all_chunks = []
    seen_ids = set()

    for i, source_path in enumerate(args.sources):
        path = Path(source_path)
        # Use the filename stem as a short label, e.g. "tribunal_chunks" -> "trib"
        label = f"src{i}_{path.stem[:12]}"
        chunks = load_chunks(path, label)

        for chunk in chunks:
            if chunk["chunk_id"] in seen_ids:
                print(f"    WARNING: duplicate chunk_id {chunk['chunk_id']!r}, skipping")
                continue
            seen_ids.add(chunk["chunk_id"])
            all_chunks.append(chunk)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Back up the existing output file if present, so a bad merge
    # doesn't silently destroy prior work.
    if output_path.exists():
        backup_path = output_path.with_suffix(".json.bak")
        output_path.replace(backup_path)
        print(f"\nBacked up existing {output_path} to {backup_path}")

    with open(output_path, "w") as f:
        json.dump(all_chunks, f, indent=2)

    print(f"\nMerged {len(all_chunks)} total chunks into {output_path}")

    # Quick breakdown by source
    from collections import Counter
    by_source = Counter(c.get("source_file", "unknown") for c in all_chunks)
    print("\nBreakdown by source:")
    for source, count in by_source.items():
        print(f"  {source}: {count} chunks")


if __name__ == "__main__":
    main()
