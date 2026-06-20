"""
legislation_chunker.py
-----------------------
Parses an official NZ legislation PDF (downloaded by the user directly
from legislation.govt.nz — this script does NOT scrape that site, since
it actively blocks automated access) and splits it into clean,
section-numbered chunks ready to merge into chunks.json for ChromaDB.

Why a separate chunker for legislation:
Acts are structured very differently from the tribunal web pages in
Phase 1 — they have numbered sections (1, 2, 2A, 22F...) under Parts and
Schedules, and a word-count sliding window would slice mid-section,
which is bad for answering "what does section 56 say" style questions.
This chunker instead produces one chunk per section (or one chunk per
~2-3 short sections if very short), preserving section numbers as
metadata.

Usage:
    python scraper/legislation_chunker.py \\
        --pdf /path/to/act.pdf \\
        --act-name "Residential Tenancies Act 1986" \\
        --source-url "https://www.legislation.govt.nz/act/public/1986/0120/latest/DLM94278.html" \\
        --output data/legislation_chunks.json

Then merge data/legislation_chunks.json into data/chunks.json before
running chatbot/ingest.py (see merge_chunks.py).
"""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

# Matches a section heading at the start of a line, e.g.:
#   "1 Short Title and commencement"
#   "2A Transitional, savings, and related provisions"
#   "22F Restrictions on rent increases"
# Section numbers are digits optionally followed by capital letters
# (NZ legislation convention for inserted sections, e.g. 22F, 138D).
# Title must be at least 2 words and not end with a lone trailing
# period after very few characters (guards against false positives
# from PDF-wrapped date fragments like "3 January.").
SECTION_HEADING_RE = re.compile(
    r"^(?P<num>\d+[A-Z]{0,2})\s+(?P<title>[A-Z][^\n]{2,150})$",
    re.MULTILINE,
)

# Some section titles wrap onto a second physical line in the PDF
# (e.g. "5A Certain excluded long fixed-term tenancies remain subject\nto repealed sections..." or "38 Order may be prepared before
# enactment or commencement of\nCOVID-19 Response..."). Real section
# body text reliably starts with a subsection marker like "(1)" on the
# next line, so anything else short and title-case-ish is treated as a
# title continuation, regardless of upper/lowercase.
BODY_START_RE = re.compile(r"^\(\d+[A-Za-z]*\)")
TITLE_CONTINUATION_RE = re.compile(r"^([^\n(]{2,80})\n")


def is_plausible_section_title(title: str) -> bool:
    """
    Filter out regex matches that are date fragments, not real
    headings. Legitimate single-word titles are common in NZ
    legislation (e.g. "Interpretation", "Costs", "Evidence") so we
    only reject the narrow case of titles that are actually dates that
    got PDF-line-wrapped to look like a heading, e.g. "March 2017; or"
    (from "...ending with 31 March 2017; or") or "January."
    """
    stripped = title.strip().rstrip(".")
    months = {
        "January", "February", "March", "April", "May", "June", "July",
        "August", "September", "October", "November", "December",
    }

    if stripped in months:
        return False

    words = stripped.split()
    # Reject short titles (<=4 words) that contain a month name AND
    # either a 4-digit year or end in a dangling conjunction — the
    # signature of a wrapped date fragment, not a real section title.
    if len(words) <= 4 and any(w in months for w in words):
        has_year = any(re.fullmatch(r"\d{4}", w.rstrip(";,.")) for w in words)
        ends_dangling = words[-1].rstrip(";,.").lower() in ("or", "and")
        if has_year or ends_dangling:
            return False

    return True


def is_plausible_section_number(number: str) -> bool:
    """
    Reject section numbers that are almost certainly NOT real section
    numbers, e.g. 4-digit numbers that are actually years (NZ Acts
    don't have 1000+ sections).
    """
    digits = re.match(r"\d+", number).group()
    if len(digits) >= 4:
        return False
    return True

# Matches "Part N" or "Schedule N" headings to track which part/schedule
# a section belongs to (useful context for the chatbot to cite).
PART_HEADING_RE = re.compile(r"^Part\s+(\d+[A-Z]?)$", re.MULTILINE)
SCHEDULE_HEADING_RE = re.compile(r"^Schedule\s+(\d+[A-Z]{0,2})$", re.MULTILINE)

MIN_CHUNK_LENGTH = 40  # skip near-empty sections (e.g. "[Repealed]")


def extract_full_text(pdf_path: Path) -> str:
    """Extract raw text from every page of the PDF, concatenated."""
    reader = PdfReader(str(pdf_path))
    pages_text = [page.extract_text() for page in reader.pages]
    return "\n".join(pages_text)


# Repeated page header/footer junk inserted by the PDF on every page,
# e.g. "Version as at\n1 December 2025 Residential Tenancies Act 1986 s 2"
# or "Version as at\n1 December 2025". These false-match the section
# heading regex (a line starting with a digit) if not stripped first.
# The date-line variant is generic (works for any Act, any "as at" date)
# rather than hardcoding "Residential Tenancies Act 1986".
PAGE_FURNITURE_PATTERNS = [
    re.compile(
        r"^Version as at\n\d{1,2} \w+ \d{4}(?: [A-Z][^\n]*)?\n?",
        re.MULTILINE,
    ),
    # Standalone page-number lines (1-4 digits alone on a line)
    re.compile(r"^\d{1,4}\n", re.MULTILINE),
]


def strip_page_furniture(text: str) -> str:
    """Remove repeated page headers/footers that interfere with section parsing."""
    for pattern in PAGE_FURNITURE_PATTERNS:
        text = pattern.sub("", text)
    return text


def find_body_start(full_text: str) -> int:
    """
    Find where the real Act body starts (after the table of contents).
    The TOC repeats every section heading followed by a page number, so
    we look for the first occurrence of "1 Short Title and commencement"
    that is NOT followed by a page number on the same line.
    """
    for match in re.finditer(r"^1\s+Short Title and commencement\s*$", full_text, re.MULTILINE):
        return match.start()

    # Fallback: if the short title pattern isn't found (different Act),
    # just use the whole text — better to over-include than crash.
    return 0


def find_body_end(full_text: str) -> int:
    """
    Cut off trailing reprint/amendment-history material that isn't
    substantive legal content (e.g. old repealed COVID schedules,
    full-text reproductions of superseded amendment Acts).

    The Schedule heading also appears in the table of contents near the
    top of the document, so we can't just take the first match — we
    look for the real (body) occurrence, which is immediately followed
    by "[Repealed]" and then a section cross-reference like "s 145(1)"
    (the TOC entry is followed by dense unrelated text instead). We
    take the LAST such match, since later in the document is always
    the real body, never the TOC.
    """
    pattern = re.compile(
        r"^Schedule\s+\d+[A-Z]{0,2}\s*\n[^\n]*\n\[Repealed\]\s*\n\s*s\s*\d+",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(full_text))
    if matches:
        return matches[-1].start()
    return len(full_text)


def find_table_schedule_ranges(body_text: str) -> list[tuple[int, int]]:
    """
    Schedule 1A ("Amounts for unlawful acts") and Schedule 1B ("Fines
    and fees for infringement offences") are pure tables: each row
    looks like "49D Some description 1,800", which matches the section
    heading regex but isn't a real section — it's a cross-reference to
    a section defined elsewhere, paired with a dollar amount. We
    exclude these ranges from per-row section splitting and instead
    keep each table as a single chunk (still useful for "what's the
    fine for X" questions, just not split row-by-row).
    """
    ranges = []
    schedule_starts = list(SCHEDULE_HEADING_RE.finditer(body_text))
    table_schedule_numbers = {"1A", "1B"}

    for i, m in enumerate(schedule_starts):
        if m.group(1) not in table_schedule_numbers:
            continue
        start = m.start()
        end = schedule_starts[i + 1].start() if i + 1 < len(schedule_starts) else len(body_text)
        ranges.append((start, end))

    return ranges


def split_into_sections(body_text: str) -> list[dict]:
    """
    Split the Act body into one chunk per numbered section, tracking
    which Part/Schedule each section falls under.
    """
    table_ranges = find_table_schedule_ranges(body_text)

    def in_table_range(pos: int) -> bool:
        return any(start <= pos < end for start, end in table_ranges)

    # Collect all heading positions: sections, Parts, and Schedules
    headings = []

    for m in SECTION_HEADING_RE.finditer(body_text):
        if in_table_range(m.start()):
            continue  # skip fines-table rows masquerading as section headings

        title = m.group("title").strip()
        number = m.group("num")

        if not is_plausible_section_number(number):
            continue

        # Absorb wrapped continuation lines (titles can wrap across more
        # than one physical PDF line) until we hit real body text,
        # which starts with a subsection marker like "(1)". Capped at
        # 3 continuation lines as a safety guard against runaway loops
        # on malformed input.
        cursor = m.end()
        for _ in range(3):
            if title.rstrip().endswith((".", ":", ";")):
                break
            remainder = body_text[cursor:cursor + 90].lstrip("\n")
            if BODY_START_RE.match(remainder):
                break
            cont_match = TITLE_CONTINUATION_RE.match(remainder)
            if not cont_match:
                break
            title = f"{title} {cont_match.group(1).strip()}"
            cursor += cont_match.end()

        if not is_plausible_section_title(title):
            continue
        headings.append({
            "pos": m.start(),
            "type": "section",
            "number": number,
            "title": title,
        })

    for m in PART_HEADING_RE.finditer(body_text):
        headings.append({"pos": m.start(), "type": "part", "number": m.group(1)})

    for m in SCHEDULE_HEADING_RE.finditer(body_text):
        headings.append({"pos": m.start(), "type": "schedule", "number": m.group(1)})

    headings.sort(key=lambda h: h["pos"])

    sections = []
    current_part = None
    current_schedule = None

    for i, h in enumerate(headings):
        if h["type"] == "part":
            # A "Part" heading only marks a top-level Act Part if we're
            # not currently inside a Schedule. Schedules like 1AA have
            # their own internal "Part 6", "Part 7" sub-divisions (e.g.
            # "Schedule 1AA Part 6: inserted by..."), which should NOT
            # clear current_schedule — otherwise their clause numbers
            # get misattributed to the main Act instead of the schedule.
            if current_schedule is None:
                current_part = h["number"]
            continue
        if h["type"] == "schedule":
            current_schedule = h["number"]
            current_part = None
            continue

        # It's a section heading — grab text up to the next heading
        start = h["pos"]
        end = headings[i + 1]["pos"] if i + 1 < len(headings) else len(body_text)
        raw_text = body_text[start:end].strip()

        if len(raw_text) < MIN_CHUNK_LENGTH:
            continue

        # Clause numbers inside a Schedule restart from 1 and can collide
        # with main-Act section numbers (e.g. Schedule 1AA clause 38 vs
        # the Act's own section 38). Disambiguate with a schedule-prefixed
        # display number, while keeping the bare number too.
        if current_schedule:
            display_number = f"Sch{current_schedule} cl {h['number']}"
        else:
            display_number = f"s {h['number']}"

        sections.append({
            "section_number": h["number"],
            "display_number": display_number,
            "section_title": h["title"],
            "part": current_part,
            "schedule": current_schedule,
            "text": raw_text,
        })

    # Add each fines-table Schedule as one combined reference chunk,
    # rather than splitting it row-by-row (which produces noisy
    # pseudo-sections — see find_table_schedule_ranges()).
    schedule_label_re = re.compile(r"^Schedule\s+(\d+[A-Z]{0,2})\s*\n([^\n]+)", re.MULTILINE)
    for start, end in table_ranges:
        table_text = body_text[start:end].strip()
        label_match = schedule_label_re.match(table_text)
        schedule_num = label_match.group(1) if label_match else "?"
        schedule_title = label_match.group(2).strip() if label_match else "Fines and fees table"

        if len(table_text) < MIN_CHUNK_LENGTH:
            continue

        sections.append({
            "section_number": f"Sch{schedule_num}",
            "display_number": f"Schedule {schedule_num}",
            "section_title": schedule_title,
            "part": None,
            "schedule": schedule_num,
            "text": table_text,
        })

    return sections


def clean_section_text(text: str) -> str:
    """Light cleanup: collapse whitespace, remove soft-hyphen artifacts."""
    text = text.replace("\u2010", "-").replace("\xad", "")  # hyphenation artifacts from PDF extraction
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="Chunk an NZ legislation PDF by section.")
    parser.add_argument("--pdf", required=True, help="Path to the Act PDF")
    parser.add_argument("--act-name", required=True, help="Full name of the Act, e.g. 'Residential Tenancies Act 1986'")
    parser.add_argument("--source-url", required=True, help="Official legislation.govt.nz URL for citation")
    parser.add_argument("--output", default="data/legislation_chunks.json", help="Output JSON path")
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return

    print(f"Reading {pdf_path}...")
    full_text = extract_full_text(pdf_path)
    print(f"Extracted {len(full_text)} characters.")

    full_text = strip_page_furniture(full_text)
    print(f"After stripping page headers/footers: {len(full_text)} characters.")

    body_start = find_body_start(full_text)
    body_end = find_body_end(full_text)
    body_text = full_text[body_start:body_end]
    print(f"Body text: {len(body_text)} characters (trimmed TOC and trailing reprint notes).")

    sections = split_into_sections(body_text)
    print(f"Found {len(sections)} sections/clauses.")

    chunks = []
    for i, sec in enumerate(sections):
        location = f"Part {sec['part']}" if sec["part"] else (
            f"Schedule {sec['schedule']}" if sec["schedule"] else None
        )
        chunks.append({
            "chunk_id": f"leg_{i:05d}",
            "url": args.source_url,
            "title": f"{args.act_name} — {sec['display_number']} {sec['section_title']}",
            "act_name": args.act_name,
            "section_number": sec["section_number"],
            "display_number": sec["display_number"],
            "section_title": sec["section_title"],
            "location": location,
            "chunk_index": 0,
            "total_chunks": 1,
            "text": clean_section_text(sec["text"]),
        })

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"\nSaved {len(chunks)} section chunks to {output_path}")
    if chunks:
        sample = chunks[0]
        print("\nSample chunk:")
        print(f"  Title: {sample['title']}")
        print(f"  Text preview: {sample['text'][:200]}...")


if __name__ == "__main__":
    main()
