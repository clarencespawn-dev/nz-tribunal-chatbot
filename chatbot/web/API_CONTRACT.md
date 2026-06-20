# Web UI — API Contract

This frontend (`index.html`) is a static, dependency-free page that calls a
single backend endpoint. It works against any backend that implements this
contract — a local Flask/FastAPI dev server today, a Lambda Function URL
once deployed to AWS.

## Endpoint

```
POST <API_BASE_URL>/ask
Content-Type: application/json
```

### Request body
```json
{
  "question": "What's the penalty for a retaliatory notice of termination?",
  "top_k": 5
}
```

### Response body (200 OK)
```json
{
  "answer": "Under section 54(6) of the Residential Tenancies Act 1986...",
  "sources": [
    {
      "title": "Residential Tenancies Act 1986 — s 54 Termination by tenant",
      "url": "https://www.legislation.govt.nz/act/public/1986/0120/latest/DLM94278.html",
      "type": "legislation"
    },
    {
      "title": "Rehearings, appeals & stay of proceedings",
      "url": "https://www.justice.govt.nz/tribunals/tenancy/rehearings-appeals/",
      "type": "tribunal"
    }
  ]
}
```

### Error response (4xx/5xx)
```json
{
  "error": "A human-readable message safe to show the user"
}
```

## Configuring the frontend

Set the backend URL in `config.js`:

```js
window.CHATBOT_CONFIG = {
  apiBaseUrl: "http://localhost:8000",   // local dev
  // apiBaseUrl: "https://abc123.lambda-url.ap-southeast-2.on.aws", // production
};
```

The frontend never reads environment variables directly (it's a static
file with no build step) — `config.js` is the single place to point it
at a different backend.

## Local dev server

A minimal FastAPI shim (`dev_server.py`) wraps the existing
`retriever.py` + `generator.py` so you can run the real UI against the
real ChromaDB + Gemini pipeline without deploying anything:

```bash
pip install fastapi uvicorn
export GEMINI_API_KEY="your-key-here"
python chatbot/web/dev_server.py
```

Then open `chatbot/web/index.html` directly in a browser (or serve it
with `python -m http.server` from within `chatbot/web/`).
