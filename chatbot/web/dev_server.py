"""
dev_server.py
--------------
Minimal local API server so the production-grade web UI (index.html)
can be developed and tested against the real retrieval + generation
pipeline, without needing AWS deployed yet.

Implements the same contract the Lambda backend will implement later
(see API_CONTRACT.md), so swapping config.js's apiBaseUrl is the only
change needed when moving from local dev to production.

Usage:
    pip install fastapi uvicorn
    export GEMINI_API_KEY="your-key-here"
    python chatbot/web/dev_server.py

Then open chatbot/web/index.html in a browser (or serve it statically).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # chatbot/

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from retriever import TribunalRetriever
from generator import AnswerGenerator

app = FastAPI(title="NZ Tribunal Chatbot — Dev API")

# Allow the static HTML file (opened via file:// or a local http.server
# on any port) to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

_retriever = None
_generator = None


def get_retriever() -> TribunalRetriever:
    global _retriever
    if _retriever is None:
        _retriever = TribunalRetriever()
    return _retriever


def get_generator() -> AnswerGenerator:
    global _generator
    if _generator is None:
        _generator = AnswerGenerator()  # reads GEMINI_API_KEY from env
    return _generator


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class Source(BaseModel):
    title: str
    url: str
    type: str  # "tribunal" or "legislation"


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


def classify_source(chunk: dict) -> str:
    """Distinguish tribunal web content from legislation chunks for the UI."""
    return "legislation" if "act_name" in chunk or "section_number" in chunk else "tribunal"


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if len(question) > 2000:
        raise HTTPException(status_code=400, detail="Question is too long.")

    try:
        retriever = get_retriever()
        generator = get_generator()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=503, detail=str(e))

    retrieved = retriever.retrieve(question, top_k=req.top_k)
    answer = generator.generate_answer(question, retrieved)

    sources = [
        Source(
            title=c.get("title", "Untitled"),
            url=c.get("url", ""),
            type=classify_source(c),
        )
        for c in retrieved
    ]

    return AskResponse(answer=answer, sources=sources)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
