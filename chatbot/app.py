"""
app.py
------
Streamlit chat UI for the NZ Tribunals chatbot.

Usage:
    export GEMINI_API_KEY="your-key-here"   # Mac/Linux
    set GEMINI_API_KEY=your-key-here        # Windows (cmd)
    streamlit run chatbot/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st

# Make sure we can import sibling modules (retriever.py, generator.py)
# regardless of where streamlit is launched from.
sys.path.insert(0, str(Path(__file__).parent))

from retriever import TribunalRetriever
from generator import AnswerGenerator

st.set_page_config(
    page_title="NZ Tribunals Assistant",
    page_icon="⚖️",
    layout="centered",
)

st.title("⚖️ NZ Tribunals Assistant")
st.caption(
    "Answers are generated using content from "
    "[justice.govt.nz/tribunals](https://www.justice.govt.nz/tribunals/) only. "
    "This is not legal advice."
)


@st.cache_resource(show_spinner="Loading knowledge base...")
def load_retriever():
    return TribunalRetriever()


@st.cache_resource(show_spinner=False)
def load_generator():
    api_key = os.environ.get("GEMINI_API_KEY") or st.session_state.get("gemini_api_key")
    if not api_key:
        return None
    return AnswerGenerator(api_key=api_key)


# --- Sidebar: API key entry (if not set via environment variable) ---
with st.sidebar:
    st.header("Settings")

    if not os.environ.get("GEMINI_API_KEY"):
        api_key_input = st.text_input(
            "Gemini API Key",
            type="password",
            help="Get a free key at https://aistudio.google.com/apikey",
            value=st.session_state.get("gemini_api_key", ""),
        )
        if api_key_input:
            st.session_state["gemini_api_key"] = api_key_input
    else:
        st.success("Gemini API key loaded from environment.")

    st.divider()

    try:
        retriever = load_retriever()
        st.metric("Chunks in knowledge base", retriever.count())
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()

    top_k = st.slider("Number of sources to retrieve", min_value=1, max_value=10, value=5)

    st.divider()
    st.caption(
        "Built on a RAG pipeline: ChromaDB (local vector store) + "
        "sentence-transformers (local embeddings) + Gemini (answer generation)."
    )


# --- Main chat interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("Sources"):
                for src in message["sources"]:
                    st.markdown(f"- [{src['title']}]({src['url']})")

user_question = st.chat_input("Ask a question about NZ tribunals...")

if user_question:
    st.session_state.messages.append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    with st.chat_message("assistant"):
        api_key = os.environ.get("GEMINI_API_KEY") or st.session_state.get("gemini_api_key")
        if not api_key:
            st.warning("Please enter your Gemini API key in the sidebar to continue.")
            st.stop()

        generator = load_generator()
        if generator is None:
            st.error("Could not initialise the answer generator. Check your API key.")
            st.stop()

        with st.spinner("Searching tribunal content..."):
            retrieved = retriever.retrieve(user_question, top_k=top_k)

        with st.spinner("Generating answer..."):
            answer = generator.generate_answer(user_question, retrieved)

        st.markdown(answer)

        sources = [{"title": c["title"], "url": c["url"]} for c in retrieved]
        if sources:
            with st.expander("Sources"):
                for src in sources:
                    st.markdown(f"- [{src['title']}]({src['url']})")

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
        })
