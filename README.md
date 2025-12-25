---
title: Fulbright Nôm Library RAG
emoji: 📚
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# Poetry Chef assistant

A full-stack assistant that lets readers explore historical Vietnamese culinary actions. The backend uses a FastAPI pipeline to pick random historical cooking context and uses OpenAI chat completions to "re-cook" user emotions into poetic recipes.

---

## Highlights

- **Poetic Recipe Generation** – Transforms abstract emotions into culinary metaphors based on historical Vietnamese texts.
- **Random Context Selection** – Picks a unique historical recipe from a curated CSV database for every interaction.
- **Luxurious frontend** – Custom Vite/React UI with aurora-inspired theming, highlight animations, and smooth scrolling.
- **Simplified Stack** – Minimalist backend with direct CSV parsing and OpenAI integration, no heavy vector databases required.

---

## Architecture Overview

```text
├── app/                # FastAPI service and Poetry Chef pipeline
│   ├── main.py         # API entry-point (`/ask` endpoint)
│   ├── rag/            # Prompting and random selection logic
│   ├── deps.py         # Dependency wiring
│   └── settings.py     # Pydantic settings (reads `config/.env`)
├── data/               # Curated historical recipe database (CSV)
├── frontend/           # Vite + React spa (chat experience)
│   ├── src/App.tsx     # Main UI logic
│   ├── src/client.ts   # API fetch client
│   └── src/styles.css  # Theme and animations
├── config/
│   ├── .env.example    # Sample configuration
│   └── .env            # Your actual secrets (ignored from VCS)
├── requirements.txt    # Backend dependencies
└── README.md           # You are here
```

---

## Prerequisites

- **Python 3.10+** (tested with CPython, conda or venv recommended)
- **Node.js 18+** and npm for the frontend
- An **OpenAI API key** (or compatible endpoint) with access to the configured chat model
- Optional: GPU-enabled PyTorch environment if you plan to run large rerankers locally

---

## Quick Start

### 1. Clone & prepare environments

```powershell
# In PowerShell
cd AI-chatbot-2
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
cd frontend
npm install
cd ..
```

### 2. Configure environment variables

```powershell
Copy-Item config/.env.example config/.env
notepad config/.env    # fill in OPENAI_API_KEY and other options
```

Key variables (see `config/.env.example` for full list):

- `OPENAI_API_KEY` – required for chat completions
- `EMBEDDING_MODEL` – Hugging Face embedding checkpoint (default `BAAI/bge-m3`)
- `RERANK_MODEL` – Optional cross-encoder reranker (default `BAAI/bge-reranker-large`)
- `CHAT_MODEL` – OpenAI chat model identifier (default `gpt-4o-mini`)
- `PERSIST_DIR` – Vector-store folder (defaults to `chroma_db`)
- Retrieval knobs: `RETRIEVER_K`, `POOL_SIZE`, `RERANK_TOP_K`, `CHUNK_SIZE`, `CHUNK_OVERLAP`

### 3. Run the FastAPI backend

```powershell
uvicorn app.main:app --reload --port 8000
```

The service exposes:

- `GET /health` – Basic health probe
- `POST /ask` – Accepts an `AskRequest` (question, top_k, pool_size, rerank toggle) and returns an `AskResponse` with answer text plus ordered source chunks.

### 5. Start the React frontend

```powershell
cd frontend
npm run dev
```

Open the printed URL (typically <http://localhost:5173>). Ensure the backend is reachable at <http://localhost:8000>; set `VITE_API_BASE` in `frontend/.env` if you deploy the API elsewhere.

---

## User Experience

- Prompt the model via the textarea and submit to trigger `/ask`.
- The interface auto-scrolls to the freshly generated answer and briefly highlights the response card.
- Citations list every retrieved chunk; use **Xem trích đoạn** to expand the passage or **Xem nhanh** to sync the built-in PDF preview.
- The preview pane loads the best-matching document page, with a convenient “Mở toàn văn” button to open the full PDF in a new tab.

---

## Development Workflow

### Testing & Troubleshooting

- **Backend imports failing**: run commands from the project root and export `PYTHONPATH` as shown above.
- **Missing models**: the first ingestion may download multi-hundred MB checkpoints; keep the process running until it completes.
- **Frontend network errors**: verify the backend base URL, or adjust `frontend/vite.config.ts` proxy if you introduce HTTPS or a different port.
- **Refresh vector store**: `Remove-Item chroma_db -Recurse -Force` then re-run `scripts.ingest`.

### Formatting & Linting

- Backend adheres to standard `black`/`ruff` style (optional but recommended).
- Frontend uses TypeScript + eslint presets from Vite (configurable via `frontend/eslint.config.js`).

### Useful npm scripts (`frontend/package.json`)

- `npm run dev` – Vite dev server with hot reload
- `npm run build` – Production bundle (outputs to `frontend/dist/`)
- `npm run preview` – Serve the production build locally

---

## Deployment Notes

- Backend can be containerized with Uvicorn + Gunicorn (check `uvicorn-gunicorn` images) and served behind a reverse proxy.
- Persist `chroma_db/` on durable storage (e.g., Azure Files, AWS EFS, or local volume) so embeddings survive restarts.
- Inject `OPENAI_API_KEY` and other secrets via your orchestration platform (GitHub Actions, Azure App Service, etc.).
- Build the frontend with `npm run build` and host the static assets on a CDN or alongside the FastAPI app using `StaticFiles` if desired.

---

## Roadmap Ideas

1. Add streaming responses for incremental answer rendering.
2. Introduce citation-based highlighting inside the PDF viewer.
3. Expand ingestion to handle Markdown/HTML scraping pipelines.
4. Implement authentication and usage analytics for multi-user deployments.

