"""
ingest.py
---------
Loads chunks.json, generates embeddings using a local sentence-transformers
model, and stores them in a persistent ChromaDB collection.

Run this once whenever chunks.json changes (new scrape, new tribunal added).

Usage:
    python chatbot/ingest.py
"""

import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

CHUNKS_FILE = Path("data/chunks.json")
CHROMA_DB_DIR = Path("data/chroma_db")
COLLECTION_NAME = "nz_tribunals"

# Local, free embedding model — no API key required.
# all-MiniLM-L6-v2 is small, fast, and good enough for this use case.
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def main():
    if not CHUNKS_FILE.exists():
        print(f"Chunks file not found: {CHUNKS_FILE}")
        print("Run the Phase 1 scraping pipeline first.")
        return

    with open(CHUNKS_FILE) as f:
        chunks = json.load(f)

    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    # Set up the local embedding function (downloads the model on first run)
    print(f"Loading embedding model: {EMBEDDING_MODEL} (first run will download it)...")
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )

    # Set up a persistent ChromaDB client — data is saved to disk so you
    # don't need to re-embed every time you restart the app.
    CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    # Fresh start each time ingest.py is run, so stale chunks don't linger
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Cleared existing collection '{COLLECTION_NAME}'")
    except Exception:
        pass  # Collection didn't exist yet — that's fine

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"description": "NZ Ministry of Justice Tribunals content"},
    )

    # ChromaDB needs: ids, documents (the text to embed), and metadatas
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = chunk.get("chunk_id") or f"chunk_{len(ids):05d}"
        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "url": chunk.get("url", ""),
            "title": chunk.get("title", ""),
            "chunk_index": chunk.get("chunk_index", 0),
        })

    print(f"Embedding and storing {len(documents)} chunks...")
    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"\nDone. Collection '{COLLECTION_NAME}' now has {collection.count()} chunks.")
    print(f"Stored at: {CHROMA_DB_DIR}")


if __name__ == "__main__":
    main()
