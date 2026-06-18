# NZ Tribunal Law Chatbot

An AI-powered chatbot that answers questions using content sourced exclusively from the [New Zealand Ministry of Justice Tribunals website](https://www.justice.govt.nz/tribunals/).

---

## Project Overview

This project is split into two phases:

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Scrape & prepare data from justice.govt.nz/tribunals | ✅ This repo |
| **Phase 2** | Embed data into a vector DB and build the chatbot | 🔜 Coming soon |

---

## Phase 1 — Data Collection Pipeline

```
justice.govt.nz/tribunals
        │
        ▼
  1. Crawl all pages       (Scrapy)
        │
        ▼
  2. Render JS pages       (Playwright)
        │
        ▼
  3. Clean raw text        (Python)
        │
        ▼
  4. Chunk for AI          (Python)
        │
        ▼
    chunks.json  ◀── ready for embedding in Phase 2
```

---

## Project Structure

```
nz-tribunal-chatbot/
├── scraper/
│   ├── crawler.py          # Scrapy spider — crawls all tribunal pages
│   ├── dynamic_scraper.py  # Playwright — handles JS-rendered pages
│   ├── clean_data.py       # Cleans and normalises raw scraped text
│   └── chunker.py          # Splits text into chunks for AI retrieval
├── data/                   # Output files (gitignored — generated locally)
│   ├── tribunal_data.json  # Raw scraped data
│   ├── cleaned_data.json   # Cleaned text
│   └── chunks.json         # Final chunked output
├── docs/
│   └── scraping_guide.md   # Detailed step-by-step scraping guide
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Quickstart

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/nz-tribunal-chatbot.git
cd nz-tribunal-chatbot
```

### 2. Set up Python environment
```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt
playwright install chromium
```

### 3. Run the full pipeline
```bash
# Step 1: Crawl all tribunal pages
scrapy runspider scraper/crawler.py -o data/tribunal_data.json

# Step 2: (Optional) Re-scrape JS-heavy pages
python scraper/dynamic_scraper.py

# Step 3: Clean the raw data
python scraper/clean_data.py

# Step 4: Chunk the cleaned data
python scraper/chunker.py
```

After running the pipeline, `data/chunks.json` will be ready for Phase 2 (embedding + chatbot).

---

## Requirements

- Python 3.10+
- See `requirements.txt` for all dependencies

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Scrapy](https://scrapy.org/) | Web crawling framework |
| [Playwright](https://playwright.dev/python/) | JavaScript page rendering |
| [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing |
| Python `re` / `json` | Text cleaning & chunking |

---

## Data Source

All content is sourced from:
> **https://www.justice.govt.nz/tribunals/**
> New Zealand Ministry of Justice — Tribunals, Authorities & Committees

Please review the site's [terms of use](https://www.justice.govt.nz/about/disclaimer/) before deploying this in production.

---

## Roadmap

- [x] Phase 1: Web scraping pipeline
- [ ] Phase 2: Text embeddings (OpenAI / local model)
- [ ] Phase 3: Vector database (ChromaDB / Pinecone)
- [ ] Phase 4: Chatbot interface (Claude API / LangChain)
- [ ] Phase 5: Deploy as a web app

---

## License

MIT
