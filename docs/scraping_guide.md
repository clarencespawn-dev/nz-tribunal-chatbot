# Scraping Guide — NZ Tribunal Website

A detailed step-by-step guide for collecting data from `justice.govt.nz/tribunals`.

---

## Step 1: Understand the Website Structure

Before writing any code, manually explore the site:

1. Visit **https://www.justice.govt.nz/tribunals/**
2. Note the main sections — each tribunal has its own page with descriptions, legislation, contacts, and decisions
3. Right-click → **Inspect Element** (Chrome DevTools) to identify the HTML tags containing the text content you want
4. Check **https://www.justice.govt.nz/robots.txt** to see what paths the site permits crawlers to access

**Tool:** Chrome or Firefox browser (built-in DevTools)

---

## Step 2: Set Up Your Python Environment

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

---

## Step 3: Crawl All Pages with Scrapy

Scrapy is a full crawling framework that automatically follows links and respects `robots.txt`.

```bash
scrapy runspider scraper/crawler.py -o data/tribunal_data.json
```

What it does:
- Starts at `justice.govt.nz/tribunals/`
- Follows every internal link under `/tribunals/`
- Extracts the page title and all paragraph/list text
- Saves to `data/tribunal_data.json`

---

## Step 4: Re-scrape JavaScript-Rendered Pages (If Needed)

Some pages load content dynamically via JavaScript and Scrapy may return empty content for those.
Use Playwright to render them fully:

```bash
python scraper/dynamic_scraper.py
```

Add any problematic URLs to the `JS_HEAVY_URLS` list in `dynamic_scraper.py`.

---

## Step 5: Clean the Raw Data

```bash
python scraper/clean_data.py
```

What it does:
- Removes excessive whitespace and non-ASCII characters
- Filters out pages with fewer than 100 characters of content
- Saves to `data/cleaned_data.json`

---

## Step 6: Chunk the Text

```bash
python scraper/chunker.py
```

What it does:
- Splits each page into 500-word chunks with 50-word overlaps
- Assigns each chunk a unique ID, source URL, and title
- Saves to `data/chunks.json`

The overlapping chunks ensure that sentences near chunk boundaries aren't split mid-thought during retrieval.

---

## Output Files

| File | Description |
|------|-------------|
| `data/tribunal_data.json` | Raw scraped content (URL, title, text) |
| `data/cleaned_data.json` | Normalised, filtered text |
| `data/chunks.json` | Final chunked data ready for embedding |

---

## What's Next — Phase 2

Once `chunks.json` is ready, Phase 2 will:

1. **Embed** each chunk using an embedding model (e.g. `text-embedding-3-small`)
2. **Store** embeddings in a vector database (ChromaDB or Pinecone)
3. **Query** the vector DB at chat time to retrieve the most relevant chunks
4. **Pass** those chunks as context to Claude (or another LLM) to generate answers
