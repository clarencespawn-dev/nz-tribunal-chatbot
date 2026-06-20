# ⚖️ NZ Tribunal Law Chatbot

A retrieval-augmented chatbot that answers questions about New Zealand tenancy law — grounded **only** in official government sources: the [Ministry of Justice Tribunals website](https://www.justice.govt.nz/tribunals/) and the full text of the **Residential Tenancies Act 1986**.

Built end-to-end: a custom web scraper, a section-aware legal document parser, a local vector database, and a chat interface — no paid APIs required to run it.

<!-- Replace with a real screenshot once the app is running locally -->
<!-- ![Chat interface](docs/screenshots/chat-interface.png) -->


---

## Why this project

Most "ask an AI about the law" demos either hallucinate or pull from the open web. This one doesn't — every answer is retrieved from a fixed, verifiable set of sources (official tribunal pages + the actual Act), and the chatbot is instructed to say so when it doesn't know.

It also doubles as a practical exercise in the messy reality of working with government data: the tribunal site needed a real crawler (not just `requests.get`), and the legislation PDF needed a custom parser to handle 360+ numbered sections, nested schedules, and PDF text-extraction artifacts — a sliding-window chunker alone wasn't good enough for legal text where "what does section 56 say" needs a clean, complete answer.

---

## How it works

```
┌──────────────────────────┐     ┌────────────────────────────────┐
│   justice.govt.nz/        │     │  Residential Tenancies Act      │
│   tribunals/tenancy/      │     │  1986 (official PDF)            │
└────────────┬───────────────┘     └──────────────┬───────────────────┘
             │ Scrapy crawler                      │ Section-aware
             │ + Playwright (JS pages)              │ PDF parser
             ▼                                     ▼
     tribunal chunks                      357 legislation chunks
             │                                     │
             └─────────────────┬───────────────────┘
                                ▼
                        merge_chunks.py
                                │
                                ▼
                      365 chunks (chunks.json)
                                │
                                ▼
                sentence-transformers embeddings
                         (local, free)
                                │
                                ▼
                      ChromaDB vector store
                         (local, free)
                                │
                ┌───────────────┴────────────────┐
                │      user asks a question        │
                ▼                                   │
         semantic retrieval                         │
         (top-k relevant chunks)                    │
                │                                   │
                ▼                                   │
         Gemini API (free tier)              Streamlit chat UI
         generates grounded answer  ◀────────────────┘
```

---

## Screenshots

<!-- Replace with a real screenshot: a question + answer with the Sources panel expanded -->
<!-- ![Question with sources](docs/screenshots/answer-with-sources.png) -->
*Every answer cites which tribunal page or Act section it came from.*

<!-- Replace with a real screenshot: the sidebar showing chunk count and retrieval settings -->
<!-- ![Sidebar settings](docs/screenshots/sidebar-settings.png) -->
*Knowledge base size and retrieval settings, visible at a glance.*

<!-- Optional: terminal output of ingest.py or legislation_chunker.py running -->
<!-- ![Ingestion pipeline](docs/screenshots/ingest-terminal.png) -->
*357 sections of the Residential Tenancies Act parsed and embedded automatically.*

---

## The hard part: parsing real legislation

Legal PDFs are not clean data. Section headings can wrap across lines, schedules re-use section numbers that collide with the main Act, fines tables look identical to section headings, and every page repeats header/footer junk that breaks naive regex. `scraper/legislation_chunker.py` handles all of this:

- Splits the Act into one chunk per section (not arbitrary word-count windows), so "what does s 56 say" retrieves the *whole*, *correct* section
- Disambiguates schedule clauses from main-Act sections that share the same number (e.g. `Schedule 1AA cl 38` vs `s 38`)
- Strips repeated PDF page furniture without deleting real content
- Filters out date strings and table rows that pattern-match like section headings
- Keeps fee/fine tables intact as reference chunks instead of shredding them row-by-row

This isn't a hypothetical edge case list — every one of these was a real bug found by inspecting actual output, not assumed in advance.

---

## Project structure

```
nz-tribunal-chatbot/
├── scraper/
│   ├── crawler.py             # Scrapy spider — crawls tribunal pages
│   ├── dynamic_scraper.py     # Playwright — handles JS-rendered pages
│   ├── clean_data.py          # Cleans and normalises scraped text
│   ├── chunker.py             # Word-window chunking for web pages
│   ├── legislation_chunker.py # Section-aware chunking for the Act PDF
│   └── merge_chunks.py        # Combines all sources into one chunks.json
├── chatbot/
│   ├── ingest.py               # Embeds chunks.json into ChromaDB
│   ├── retriever.py            # Semantic search over the vector store
│   ├── generator.py            # Gemini-powered grounded answer generation
│   └── app.py                  # Streamlit chat UI
├── data/                       # Generated outputs (gitignored)
├── docs/
│   ├── scraping_guide.md       # Step-by-step scraping walkthrough
│   └── screenshots/            # README images
├── requirements.txt
├── .env.example
└── README.md
```

---

## Run it yourself

```bash
git clone https://github.com/YOUR_USERNAME/nz-tribunal-chatbot.git
cd nz-tribunal-chatbot

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

**1. Scrape the tribunal pages**
```bash
scrapy runspider scraper/crawler.py -o data/tribunal_data.json
python scraper/clean_data.py
python scraper/chunker.py
```

**2. Parse the legislation** — download the [Residential Tenancies Act 1986 PDF](https://www.legislation.govt.nz/act/public/1986/0120/latest/DLM94278.html) from legislation.govt.nz yourself (the script does not scrape that site — see [the note below](#a-note-on-legislationgovtnz)), then:
```bash
python scraper/legislation_chunker.py \
  --pdf path/to/act.pdf \
  --act-name "Residential Tenancies Act 1986" \
  --source-url "https://www.legislation.govt.nz/act/public/1986/0120/latest/DLM94278.html" \
  --output data/legislation_chunks.json
```

**3. Merge everything**
```bash
python scraper/merge_chunks.py \
  --sources data/chunks.json data/legislation_chunks.json \
  --output data/chunks.json
```

**4. Get a free Gemini API key** at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — no credit card required.
```bash
export GEMINI_API_KEY="your-key-here"   # Windows: set GEMINI_API_KEY=your-key-here
```

**5. Embed and launch**
```bash
python chatbot/ingest.py
streamlit run chatbot/app.py
```

---

## Tech stack

| Tool | Role | Why |
|---|---|---|
| [Scrapy](https://scrapy.org/) | Web crawling | Handles link discovery, scoping, and politeness (rate limiting, robots.txt) |
| [Playwright](https://playwright.dev/python/) | JS rendering | Fallback for any pages that load content dynamically |
| [pypdf](https://pypdf.readthedocs.io/) | PDF parsing | Extracts raw text from the Act PDF for section-aware chunking |
| [ChromaDB](https://www.trychroma.com/) | Vector store | Local, free, persists to disk — no cloud account needed |
| [sentence-transformers](https://www.sbert.net/) | Embeddings | Local `all-MiniLM-L6-v2` model — free, no API key |
| [Gemini API](https://ai.google.dev/) | Answer generation | Free tier is generous enough for a project like this |
| [Streamlit](https://streamlit.io/) | Chat UI | Fast way to ship a working interface |

---

## A note on legislation.govt.nz

This project does **not** scrape legislation.govt.nz — that site actively blocks automated requests. Instead, the official PDF reprint (which legislation.govt.nz publishes specifically so people don't have to scrape the site) is downloaded manually and parsed locally. This keeps the data pipeline both effective and respectful of the source site's access controls.

---

## Data sources & disclaimer

- [justice.govt.nz/tribunals/tenancy/](https://www.justice.govt.nz/tribunals/tenancy/) — Ministry of Justice
- [Residential Tenancies Act 1986](https://www.legislation.govt.nz/act/public/1986/0120/latest/DLM94278.html) — New Zealand Legislation

This chatbot is a portfolio project for informational purposes only. It is **not legal advice**. For real tenancy disputes, contact the [Tenancy Tribunal](https://www.justice.govt.nz/tribunals/tenancy/) directly or seek professional legal advice.

---

## Roadmap

- [x] Tribunal web scraping pipeline (Scrapy + Playwright)
- [x] Section-aware legislation PDF parser
- [x] Local embeddings + ChromaDB vector store
- [x] Gemini-powered grounded chat UI (Streamlit)
- [ ] Widen scraper to all 22 tribunals (currently Tenancy Tribunal only)
- [ ] Deploy publicly (Streamlit Community Cloud)
- [ ] Add conversation memory for follow-up questions
- [ ] Add inline citation highlighting in the UI

---

## License

MIT
