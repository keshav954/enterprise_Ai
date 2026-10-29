# Enterprise AI Employee

A FastAPI backend that exposes a Gemini-powered "AI employee" chat agent with
persistent memory and a workspace tool suite (file read/write/search/edit),
plus a lightweight static dashboard.

## Status

Early-stage, working prototype. Core chat loop, tool execution, and
persistent memory are functional and covered by tests.

## Architecture

```
app/
  main.py              FastAPI app entrypoint, mounts routes + static dashboard
  config/settings.py   Pydantic settings (reads .env)
  models/chat_models.py  Request schema (ChatRequest)
  prompts/system_prompt.py  System prompt for the agent
  routes/chat.py       API routes: /chat, /tools, /sessions, /chat/{id}/history
  services/gemini_service.py  Gemini client, session mgmt, tool-call loop
  memory/memory_service.py    SQLite-backed chat history (memory.db)
  rag/                  Retrieval-augmented generation: document loading,
                         vector store, and RAG service (in progress)
  tools/
    workspace_tools.py   File/folder CRUD within a sandboxed workspace dir
    search_tools.py      Keyword / text / filename search across the workspace
    code_tools.py        Multi-file read, line-range read, find/replace, list .py files
    company_tools.py     Aggregates all tools into TOOLS list + company info tool
  static/               Dashboard UI (index.html, app.js, style.css)
knowledge_base/         Source documents for RAG (e.g. company_handbook.md)
data/chroma/            Chroma vector store (gitignored, regenerated at runtime)
tests/                  pytest suite: API, memory, tools, function-execution loop
scripts/
  list_models.py               Lists models available to your Gemini API key
  check_gemini_connection.py   Minimal sanity check that your API key/model work
```

## Setup & Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and set GEMINI_API_KEY

# Start the application:
python run.py
# Or with auto-reload for local development:
python run.py --reload
```

Visit `http://localhost:8000/` for API status, or
`http://localhost:8000/dashboard` for the UI.

To verify your API key and see which models are available to it:

```bash
python scripts/check_gemini_connection.py
python scripts/list_models.py
```

## API

| Method | Path | Description |
|---|---|---|
| GET | `/` | Service status + registered tool names |
| GET | `/health` | Health-check endpoint for load-balancers & containers |
| GET | `/dashboard` | Static dashboard UI |
| POST | `/chat` | Send a message (`message`, optional `session_id`) |
| GET | `/tools` | List registered tools + descriptions |
| GET | `/sessions` | List active + stored session IDs |
| GET | `/chat/{session_id}/history` | Full history for a session |
| DELETE | `/chat/{session_id}` | Clear a session's history |

## Tools available to the agent

**Workspace file ops:** list, read, write, append, delete files; create/delete
folders; rename, move, copy items; workspace tree/summary; file info; file
count.

**Search:** search filenames by keyword, search text content across the
workspace, find files by glob pattern.

**Code-oriented:** read multiple files at once, read a specific line range,
find-and-replace text in a file, list all `.py` files.

**Company info:** static company info lookup.

**Knowledge base (RAG):** semantic search over knowledge_base/ via `search_knowledge_base`; rebuild the vector index on demand via `rebuild_knowledge_base` after editing knowledge-base files.

## Deployment

### 1. Docker Compose (Recommended for Local / VPS)

```bash
docker compose up --build
```
This runs the containerized service with volume mounts preserving `workspace/`, `data/`, `knowledge_base/`, and `reports/`.

### 2. Docker Standalone

```bash
docker build -t enterprise-ai-employee .
docker run -p 8000:8000 --env-file .env enterprise-ai-employee
```

### 3. Cloud Platforms (Render, Railway, Heroku)

- **Render**: Connect the repository and Render detects [`render.yaml`](file:///c:/Users/kesha/OneDrive/Desktop/VS%20CODE/Enterprise-AI-Employee/render.yaml) automatically to deploy as a Web Service.
- **Railway / Heroku / Dokku**: Deploys via [`Procfile`](file:///c:/Users/kesha/OneDrive/Desktop/VS%20CODE/Enterprise-AI-Employee/Procfile) and [`Dockerfile`](file:///c:/Users/kesha/OneDrive/Desktop/VS%20CODE/Enterprise-AI-Employee/Dockerfile) with Gunicorn and Uvicorn workers.

### 4. Continuous Integration

Automated CI is configured via GitHub Actions in [`.github/workflows/ci.yml`](file:///c:/Users/kesha/OneDrive/Desktop/VS%20CODE/Enterprise-AI-Employee/.github/workflows/ci.yml) to run test suites and verify container builds on pull requests and pushes to `main`.

## Testing

```bash
pytest tests/ -q
```

## Notes / known limitations

- Chat sessions are kept in an in-memory dict capped by `MAX_SESSIONS`
  (default 100); the oldest session is evicted first. Restarting the server
  loses in-memory (but not SQLite-persisted) session state.
- `app/memory/memory.db` and `data/chroma/` are local runtime data and are
  gitignored — don't commit them.
- The tool loop caps at 5 automatic tool-call iterations per turn
  (`MAX_TOOL_LOOPS` in `gemini_service.py`).