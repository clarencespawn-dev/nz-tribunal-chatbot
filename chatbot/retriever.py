"""
retriever.py
------------
Given a user question, retrieves the most relevant chunks from ChromaDB
using the same local embedding model used during ingestion.
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

CHROMA_DB_DIR = Path("data/chroma_db")
COLLECTION_NAME = "nz_tribunals"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5


class TribunalRetriever:
    """Wraps a ChromaDB collection for semantic search over tribunal chunks."""

    def __init__(self):
        if not CHROMA_DB_DIR.exists():
            raise FileNotFoundError(
                f"ChromaDB store not found at {CHROMA_DB_DIR}. "
                "Run 'python chatbot/ingest.py' first."
            )

        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embed_fn,
        )

    def retrieve(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
        """
        Retrieve the top_k most relevant chunks for a given query.

        Returns a list of dicts with: text, url, title, distance
        (lower distance = more relevant).
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        retrieved = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            retrieved.append({
                "text": doc,
                "url": meta.get("url", ""),
                "title": meta.get("title", ""),
                "distance": dist,
            })

        return retrieved

    def count(self) -> int:
        """Return the total number of chunks in the collection."""
        return self.collection.count()
