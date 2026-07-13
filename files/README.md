# RAGnify Media

A retrieval-augmented workspace for your own documents: upload files, ask questions by
typing or by voice, and get answers grounded only in what you uploaded — with sources
cited and a visible "won't guess" fallback when nothing relevant is found.

**This version costs $0 to run.** Everything — database, auth, embeddings, and the LLM
that answers your questions — runs on your own machine. No API keys, no cloud accounts,
no credit card, anywhere.

## Architecture

```
frontend/   React + Vite, served by nginx in Docker. Auth UI, chat UI, document
            library, focus-stack retrieval view, settings panel.

backend/    FastAPI (Python). Handles signup/login itself (no external auth
            provider), parses uploads (incl. OCR), chunks them, embeds them via
            Ollama, runs hybrid search, and asks a local Ollama model for a
            grounded answer.

Postgres    Postgres + pgvector, running in a container on your machine. Holds
            documents, chunks, embeddings, chat history, and user accounts.

Ollama      Runs locally in a container. Serves both the embedding models and the
            chat model — nothing leaves your machine, nothing is billed per call.
```

| Feature (from the original spec)         | Where it lives |
|---|---|
| 1. Login + email verification            | `backend/app/routers/auth.py` (self-hosted — see note below) |
| 2. Light, attractive UI                   | `frontend/src/styles/` |
| 3. Voice input                            | `frontend/src/components/VoiceButton.jsx` (Web Speech API) |
| 4. No hallucination                       | `backend/app/llm_client.py` + refusal path in `backend/app/routers/chat.py` |
| 5. Multi-document format                  | `backend/app/parsing.py` |
| 6. Intelligent chunking                   | `backend/app/chunking.py` |
| 7. Multiple embedding models              | `backend/app/embeddings.py` (via Ollama) |
| 8. Hybrid search                          | `backend/app/retrieval.py` |
| 9. Chat history                           | `chat_sessions` / `chat_messages` tables + `backend/app/routers/chat.py` |
| 10. OCR                                   | `backend/app/parsing.py` (`pytesseract`, incl. scanned-PDF fallback) |

**On email verification:** there's no email service wired up (adding one means
signing up for something, even if free) — signup/login return the 6-digit code
directly in the response, and the frontend just shows it on screen. Functionally
identical flow to real email verification, minus an inbox. If you want real emails
later, `backend/app/routers/auth.py` is a few lines away from calling any SMTP
provider before returning the response.

## Run it with Docker (recommended)

Requires [Docker](https://docs.docker.com/get-docker/) with Compose (bundled with
Docker Desktop). That's it — no Python or Node install needed on your machine.

**1. Configure the backend:**
```bash
cd ragnify-app
cp backend/.env.example backend/.env
```
Open `backend/.env` and replace `JWT_SECRET` with a real random value:
```bash
openssl rand -hex 32
```
(The other values in `backend/.env` — `DATABASE_URL`, `OLLAMA_BASE_URL` — get
overridden automatically by `docker-compose.yml` to point at the other containers,
so you don't need to touch those.)

**2. Start everything:**
```bash
docker compose up -d --build
```
This builds and starts four containers: `db` (Postgres+pgvector), `ollama`,
`backend` (FastAPI), and `frontend` (nginx serving the built React app). The
database schema is applied automatically on first boot.

**3. Pull the models Ollama needs (one-time, ~5-6GB total download):**
```bash
docker compose exec ollama ollama pull all-minilm
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.1:8b
```
`llama3.1:8b` needs roughly 8GB of RAM to run comfortably. If your machine is
lighter on RAM, pull `llama3.2:3b` instead and set `OLLAMA_CHAT_MODEL=llama3.2:3b`
in `backend/.env`, then `docker compose restart backend`.

**4. Open the app:** [http://localhost:5173](http://localhost:5173)

**Useful commands:**
```bash
docker compose logs -f backend      # watch backend logs
docker compose down                 # stop everything
docker compose down -v              # stop and wipe all data (Postgres + Ollama models)
docker compose up -d --build        # rebuild after changing code
```

## Run it without Docker (alternative)

Requires Python 3.11+, Node 18+, a local Postgres with the `vector` extension, and
[Ollama](https://ollama.com) installed directly on your machine.

```bash
# 1. Database
psql "postgresql://youruser@localhost/ragnify" -f backend/sql/schema.sql

# 2. Ollama models
ollama pull all-minilm nomic-embed-text llama3.1:8b

# 3. Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL / JWT_SECRET
uvicorn app.main:app --reload   # http://localhost:8000, docs at /docs

# 4. Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev   # http://localhost:5173
```

Also needs `tesseract-ocr` and `poppler-utils` installed locally for OCR/scanned-PDF
support (the Docker path installs these for you automatically).

## Is this really $0?

Yes, with the caveats worth knowing:

- **No usage caps or API bills** — Postgres and Ollama are open-source software
  running on hardware you already own. There's nothing to meter or bill.
- **Local LLMs are weaker than Claude at strict grounding.** `llama3.1:8b` does
  reasonably well at "only answer from context, say so if you don't know," but
  it will slip up more often than a frontier hosted model would. That's the honest
  tradeoff for $0.
- **Hardware, not money, is the real constraint.** `llama3.1:8b` wants ~8GB RAM;
  `nomic-embed-text` and `all-minilm` are both light. Everything runs on CPU (no
  GPU required), just slower than with one.
- **This isn't set up for the public internet.** No rate limiting, no HTTPS, a
  default `JWT_SECRET` you must change. Fine for local/learning use as-is; treat
  it as a starting point, not a hardened deployment, if you ever expose it beyond
  your own machine.

## Known limitations / good next steps

- No automated test suite yet; `chunking.py`, `retrieval.py`, and `embeddings.py`
  are small and pure enough to unit test easily.
- No rate limiting on `/chat/ask` — fine for solo use, worth adding before sharing
  with anyone else.
- File uploads are read fully into memory before processing — fine for typical
  documents, but very large files would benefit from streaming.
- `chunk_embeddings.embedding` has no fixed dimension (see the comment in
  `sql/schema.sql`), which trades away an ANN index for the flexibility to mix
  embedding models freely. Fine at personal scale; revisit if your document count
  grows into the tens of thousands.
