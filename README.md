# NZ Tribunal Law Chatbot

An AI-powered chatbot that answers questions using content sourced exclusively from the [New Zealand Ministry of Justice Tribunals website](https://www.justice.govt.nz/tribunals/).

---

## Project Overview

This project is split into two phases:

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Scrape & prepare data from justice.govt.nz/tribunals | ✅ Done |
| **Phase 2** | Embed data into a vector DB and build the chatbot | ✅ This repo |

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
    chunks.json
```

## Phase 2 — RAG Chatbot Pipeline

```
    chunks.json
        │
        ▼
  1. Embed chunks          (sentence-transformers, local & free)
        │
        ▼
  2. Store in vector DB    (ChromaDB, local & free)
        │
        ▼
  3. Retrieve on query     (semantic search)
        │
        ▼
  4. Generate answer       (Gemini API, free tier)
        │
        ▼
  5. Chat UI               (Streamlit)
```

**Why these tools:**
- **ChromaDB** — runs entirely locally, no account or cloud setup needed, persists to disk
- **sentence-transformers** (`all-MiniLM-L6-v2`) — generates embeddings locally, no API key or cost
- **Gemini API (free tier)** — generates the final conversational answer from retrieved chunks; free tier gives a generous daily quota with no credit card required
- **Streamlit** — quick way to get a working chat UI with minimal code

---

## Project Structure

```
nz-tribunal-chatbot/
├── scraper/
│   ├── crawler.py          # Scrapy spider — crawls tribunal pages
│   ├── dynamic_scraper.py  # Playwright — handles JS-rendered pages
│   ├── clean_data.py       # Cleans and normalises raw scraped text
│   └── chunker.py          # Splits text into chunks for AI retrieval
├── chatbot/
│   ├── ingest.py           # Embeds chunks.json and loads into ChromaDB
│   ├── retriever.py        # Semantic search over the vector store
│   ├── generator.py        # Gemini-powered answer generation
│   └── app.py              # Streamlit chat UI
├── data/                   # Output files (gitignored — generated locally)
│   ├── tribunal_data.json  # Raw scraped data
│   ├── cleaned_data.json   # Cleaned text
│   ├── chunks.json         # Final chunked output
│   └── chroma_db/          # Persistent vector store
├── docs/
│   └── scraping_guide.md   # Detailed step-by-step scraping guide
├── requirements.txt
├── .env.example             # Template for your Gemini API key
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

### 3. Run the scraping pipeline (Phase 1)
```bash
scrapy runspider scraper/crawler.py -o data/tribunal_data.json
python scraper/clean_data.py
python scraper/chunker.py
```

This produces `data/chunks.json`, ready for the chatbot.

### 4. Get a free Gemini API key
Visit https://aistudio.google.com/apikey, sign in with a Google account, and generate a key. No credit card required.

```bash
cp .env.example .env
# Edit .env and paste your key, then load it:
export GEMINI_API_KEY="your-key-here"     # Mac/Linux
set GEMINI_API_KEY=your-key-here          # Windows (cmd)
```

### 5. Embed and index the data (Phase 2)
```bash
python chatbot/ingest.py
```

This downloads the local embedding model (first run only, ~80MB) and builds the ChromaDB vector store at `data/chroma_db/`.

### 6. Launch the chatbot
```bash
streamlit run chatbot/app.py
```

Your browser will open to a chat interface where you can ask questions about NZ tribunals, answered using only the scraped content.

---

## Requirements

- Python 3.10+
- A free Gemini API key (for Phase 2 answer generation)
- See `requirements.txt` for all dependencies

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Scrapy](https://scrapy.org/) | Web crawling framework |
| [Playwright](https://playwright.dev/python/) | JavaScript page rendering |
| [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) | HTML parsing |
| [ChromaDB](https://www.trychroma.com/) | Local vector database |
| [sentence-transformers](https://www.sbert.net/) | Local embedding generation |
| [Gemini API](https://ai.google.dev/) | LLM answer generation (free tier) |
| [Streamlit](https://streamlit.io/) | Chat UI |

---

## Data Source

All content is sourced from:
> **https://www.justice.govt.nz/tribunals/**
> New Zealand Ministry of Justice — Tribunals, Authorities & Committees

Please review the site's [terms of use](https://www.justice.govt.nz/about/disclaimer/) before deploying this in production.

This chatbot is for informational purposes only and does not constitute legal advice.

---

## Roadmap

- [x] Phase 1: Web scraping pipeline
- [x] Phase 2: Embeddings, vector DB, and chatbot UI
- [ ] Widen scraper from Tenancy Tribunal only to all 22 tribunals
- [ ] Deploy as a public web app (e.g. Streamlit Community Cloud)
- [ ] Add conversation memory / follow-up question handling
- [ ] Add citation highlighting in the UI

---

## License

MIT

