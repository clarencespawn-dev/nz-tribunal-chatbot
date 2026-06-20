"""
generator.py
------------
Takes a user question + retrieved chunks and generates a grounded answer
using the Gemini API (free tier).

Requires a GEMINI_API_KEY environment variable.
Get a free key at: https://aistudio.google.com/apikey

Uses the `google-genai` SDK (the `google-generativeai` package this
originally used has been deprecated and no longer receives updates —
see https://github.com/google-gemini/deprecated-generative-ai-python).
"""

import os

from google import genai
from google.genai import types

GEMINI_MODEL = "gemini-2.5-flash"  # Free-tier model as of mid-2026

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about \
New Zealand's Ministry of Justice Tribunals, using ONLY the information \
provided in the context below. This context is sourced exclusively from \
justice.govt.nz/tribunals.

Rules:
- Only use information found in the provided context. Do not use outside knowledge.
- If the context doesn't contain enough information to answer the question, \
say so clearly and suggest the user check the official website or contact \
the relevant tribunal directly.
- Always be clear that you are not a lawyer and this is not legal advice.
- When relevant, mention which tribunal page(s) the information came from.
- Keep answers concise and easy to understand for someone unfamiliar with \
legal processes.
"""


class AnswerGenerator:
    """Wraps the Gemini API to generate grounded answers from retrieved chunks."""

    def __init__(self, api_key: str | None = None):
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "No Gemini API key found. Set the GEMINI_API_KEY environment "
                "variable, or get a free key at https://aistudio.google.com/apikey"
            )

        self.client = genai.Client(api_key=api_key)
        self.config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)

    def generate_answer(self, question: str, retrieved_chunks: list[dict]) -> str:
        """
        Generate an answer to `question` grounded in `retrieved_chunks`.

        Each chunk dict should have: text, url, title
        """
        if not retrieved_chunks:
            return (
                "I couldn't find any relevant information in the Tenancy "
                "Tribunal content I have access to. Please check "
                "https://www.justice.govt.nz/tribunals/ directly, or "
                "rephrase your question."
            )

        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, start=1):
            context_parts.append(
                f"[Source {i}: {chunk['title']} — {chunk['url']}]\n{chunk['text']}"
            )
        context = "\n\n".join(context_parts)

        prompt = f"""Context from justice.govt.nz/tribunals:

{context}

---

User question: {question}

Answer the question using only the context above."""

        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=self.config,
        )
        return response.text
