# Enterprise AI Employee: Multidomain Agentic AI Platform

[![CI Pipeline](https://github.com/keshav-sudo/Enterprise-AI-Employee/actions/workflows/ci.yml/badge.svg)](https://github.com/keshav-sudo/Enterprise-AI-Employee/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python 3.13](https://img.shields.io/badge/Python-3.13+-3776AB.svg?logo=python)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)

A production-ready, multidomain agentic AI platform that serves as a general-purpose **AI Employee**. Equipped with **RAG semantic intelligence**, **persistent SQLite memory**, **deterministic data analytics**, and a **human-in-the-loop workflow engine**, it executes knowledge work reliably across business, education, HR, and software engineering domains.

---

## 🌟 Core Architecture & Capabilities

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       CYBER EMERALD WEB DASHBOARD                           │
│     Universal Chat  •  Knowledge Base RAG  •  Workflows  •  Reports & Data   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                        AGENTIC ORCHESTRATION LAYER                          │
│        Plan → Execute → Verify Agentic Pattern with Human Approval Gates    │
└──────┬───────────────────────┬───────────────────────┬──────────────────────┘
       │                       │                       │
┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐        ┌──────▼──────┐
│  KNOWLEDGE  │         │  AI DATA    │         │  WORKFLOW   │        │  WORKSPACE  │
│  BASE (RAG) │         │  ANALYST    │         │  ENGINE     │        │  & CODE     │
│ • ChromaDB  │         │ • Pandas    │         │ • Approval  │        │ • Files CRUD│
│ • MiniLM-L6 │         │ • NumPy     │         │ • Safe Test │        │ • Regex/Tree│
│ • PDF/DOCX/ │         │ • Plotly    │         │   Runner    │        │ • AST/Read  │
│   CSV/MD/TXT│         │ • HTML/MD   │         │ • Pytest TB │        │ • Sandbox   │
└─────────────┘         └─────────────┘         └─────────────┘        └─────────────┘
```

### 1. Universal Document Intelligence (RAG)
- **Multi-Format Ingestion:** Ingests `.md`, `.txt`, `.pdf` (page-by-page via `pypdf`), `.docx` (via `python-docx`), and `.csv` (tabular data).
- **Grounded Semantic Retrieval:** Embeds chunks via `SentenceTransformers (all-MiniLM-L6-v2)` and indexes into **ChromaDB**.
- **Audit-Ready Citations:** Every retrieved fact returns explicit source references, page numbers, and similarity confidence scores. Hallucination guardrail states *"not documented"* when evidence is lacking.
- **Document Comparison:** Built-in `compare_documents` tool detects discrepancies and overlaps between policies.

### 2. AI Data Analyst (Deterministic Computation)
- **Zero Hallucination Arithmetic:** Strict segregation between reasoning and calculation. All sums, averages, medians, and aggregations are computed deterministically via **Pandas** and **NumPy**—never LLM mental arithmetic.
- **Automated Profiling:** Generates column health, missing value counts, unique distributions, and statistical summaries for CSV and Excel files.
- **Interactive Visualizations:** Renders standalone interactive charts using **Plotly** (HTML/JS) saved to `reports/charts/`.
- **Executive Reports:** Generates decision-ready Markdown reports saved to `reports/`.

### 3. Agentic Workflow Engine & Human Approval Gates
- **Plan → Execute → Verify:** Decomposes complex user goals into tracked steps with explicit status tracking (`pending`, `in_progress`, `awaiting_approval`, `verified`, `rejected`).
- **Human-in-the-Loop Safeguards:** Consequential actions (file overwrites, database mutations, purchase orders) trigger approval pauses until explicitly granted by a human reviewer.
- **Developer Execution Tools:** Restricted subprocess test runner (`run_project_tests`) and intelligent failure diagnosis (`summarize_test_failures`).

### 4. Enterprise Security & Multi-Tenant Hardening
- **API Key Authentication (`APP_API_KEY`):** Constant-time comparison (`secrets.compare_digest`) supporting comma-separated authorized keys. Required header: `Authorization: Bearer <key>` on all routes except `GET /health` and static files. Production startup validation enforces strong keys (min 24 chars, non-placeholder, non-empty); development mode defaults to isolated `"dev_default"`.
- **Per-User Workspace Isolation:** Each API key operates inside an isolated sandbox directory (`workspace/<key_hash[:16]>/`). Callers cannot inspect, read, overwrite, search, or delete another user's files. Path traversal (`..`), absolute paths, and sandbox root modifications (`.` / delete / rename) are blocked.
- **Admin Access Control (`APP_ADMIN_KEYS`):** Privileged operations are restricted to keys specified in `APP_ADMIN_KEYS` (or the primary `APP_API_KEY` if none explicitly set). Non-admin keys receive `403 Forbidden` on knowledge base uploads (`POST /knowledge-base/upload`), index rebuilds (`POST /knowledge-base/rebuild`), test runs (`POST /workflows/run-tests`), and corresponding agent tools (`rebuild_knowledge_base`, `run_project_tests`).
- **Conflict Prevention on Uploads:** Uploading duplicate files requires an explicit `?overwrite=true` query parameter, otherwise returning `409 Conflict`.
- **Caller Session Isolation:** Every chat session is scoped to the sha256 hash of the caller's API key in SQLite and memory. `/sessions` lists only the caller's sessions; cross-session read or deletion attempts return `404 Not Found`.
- **Tiered Rate Limiting:** Sliding-window rate limiters per API key returning HTTP `429 Too Many Requests` with dynamic `Retry-After` header:
  - Standard routes (`RATE_LIMIT_PER_MIN`, default 60): chat, analytics profiling, task workflows.
  - Resource-intensive routes (`RATE_LIMIT_HEAVY_PER_MIN`, default 5): document uploads, vector rebuilds, project test runs.
- **Restricted Test Subprocess:** `run_project_tests` strictly accepts relative paths resolving inside `<project>/tests/`, rejecting CLI flag injection (`-*`), absolute paths, and traversal segments. Output is capped at 8,000 characters with a strict 60-second execution timeout.
- **CORS Hardening (`ALLOWED_ORIGINS`):** Origins configured via comma-separated list. Wildcard `*` is strictly forbidden from combining with `allow_credentials=True`.
- **Subresource Integrity (SRI) & XSS Protection:** Web dashboard uses DOMPurify sanitization and enforces SRI sha384 hashes with `crossorigin="anonymous"` on all CDN assets.
- **Request-ID Tracing & Safe Structured Logging:** Middleware assigns a unique `X-Request-ID` to every request. Unhandled exceptions are logged with full stack traces on the server while returning generic sanitized messages (`Internal Server Error. Request ID: ...`) to clients. Sensitive keys and message bodies are never logged.

### Security Model
| Layer | Defense Mechanism | Scope |
|---|---|---|
| **Identity & Auth** | Constant-time bearer token check, production key strength audit | All protected endpoints |
| **Authorization** | Role-based RBAC (`APP_ADMIN_KEYS`) | KB mutations, test executions |
| **Workspace Sandboxing** | ContextVar-scoped folder isolation (`workspace/<hash[:16]>/`) | All file, code, and search tools |
| **Abuse Mitigation** | Dual-tier sliding window rate limits (`RATE_LIMIT_PER_MIN`, `RATE_LIMIT_HEAVY_PER_MIN`) | Per API key hash |
| **Execution Sandbox** | Whitelisted pytest paths inside `tests/`, flag denial, 60s timeout | Developer test runner |
| **Web & Client** | DOMPurify HTML sanitization, SRI CDN integrity, CORS lockdown | Browser dashboard |

### 5. Reliability, Startup Performance & Tool Safety
- **Lazy Initialization:** App starts in milliseconds even without a `GEMINI_API_KEY` configured. `GET /health` reports `gemini_configured=false`; `/chat` returns HTTP 503 Service Unavailable with a clear resolution message.
- **Fast Startup (Lazy Vector Store & PyTorch):** `sentence_transformers` and `chromadb` imports are lazy-loaded on first vector query, reducing `app.main` import time from >14s to <1s.
- **Single-Worker Thread Concurrency:** Server runs with `--workers 1 --threads 4`. Single-process execution prevents ChromaDB embedded database and SQLite file locking conflicts, while in-memory session handles are synchronized using threading locks.
- **Persistent SQLite with WAL Mode:** `MEMORY_DB_PATH` defaults to `data/memory.db` (persistent Docker volume). Configured with `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` with automatic one-time migration from legacy paths.
- **Tool Safety Caps & Traversal Guards:** File reads/writes capped at 1 MB. Tool output returned to the LLM truncated to 20,000 characters. All workspace, search, and code tools strictly reject absolute paths, traversal (`..`), and symlink escapes.
- **Offline Test Double (`GEMINI_FAKE=1`):** Scriptable test double for zero-latency, quota-free CI and integration testing. Strictly forbidden in production (`ENV=production` refuses to start if `GEMINI_FAKE=1`).
- **Verified Model Default:** Documented default model `gemini-2.5-flash` verified via Google GenAI models API.

---

## 🛠️ Complete 38-Tool Registry

| Suite | Count | Tools |
|---|---|---|
| **Company & Core** | 1 | `get_company_info` |
| **Workspace File CRUD** | 10 | `list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `append_workspace_file`, `delete_workspace_file`, `create_workspace_folder`, `delete_workspace_folder`, `rename_workspace_item`, `move_workspace_item`, `copy_workspace_item` |
| **Workspace Inspection** | 4 | `workspace_tree`, `workspace_summary`, `get_file_information`, `count_workspace_files` |
| **Search & Discovery** | 4 | `search_workspace_files`, `search_text_in_workspace`, `search_workspace_text`, `find_workspace_files` |
| **Code Intelligence** | 4 | `read_multiple_workspace_files`, `read_workspace_lines`, `replace_text_in_file`, `list_python_files` |
| **Knowledge Base (RAG)** | 3 | `search_knowledge_base`, `rebuild_knowledge_base`, `compare_documents` |
| **AI Data Analyst** | 5 | `analyze_csv_file`, `analyze_excel_file`, `calculate_data_summary`, `create_data_chart`, `generate_analysis_report` |
| **Workflow & Verification** | 7 | `create_task_plan`, `get_task_status`, `request_task_approval`, `approve_task_step`, `verify_task_result`, `run_project_tests`, `summarize_test_failures` |

---

## 🚀 Quickstart & Setup

### Prerequisites
- Python 3.11+ (Python 3.13 recommended)
- Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 1. Local Installation

```bash
# Clone the repository
git clone https://github.com/keshav-sudo/Enterprise-AI-Employee.git
cd Enterprise-AI-Employee

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Open .env and set GEMINI_API_KEY=your_key_here
```

### 2. Run the Application

```bash
# Launch unified CLI entrypoint
python run.py

# Or with auto-reload for local development:
python run.py --reload --port 8000
```

Open your browser to:
- **Web Dashboard:** `http://localhost:8000/` or `http://localhost:8000/dashboard`
- **Interactive OpenAPI Docs:** `http://localhost:8000/docs`
- **Health Diagnostics:** `http://localhost:8000/health`

---

## 📡 REST API Reference

### Universal Chat
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Send prompt to AI Employee (`message`, optional `session_id`) |
| `GET` | `/chat/{session_id}/history` | Retrieve full message thread for session |
| `DELETE` | `/chat/{session_id}` | Clear and reset a chat session |
| `GET` | `/sessions` | List all active and stored session IDs |
| `GET` | `/tools` | List all 38 registered tools and schema descriptions |

### Knowledge Base & RAG Management
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/knowledge-base/stats` | Document, chunk, and embedding model statistics |
| `GET` | `/knowledge-base/documents` | List stored files with size and modification date |
| `POST` | `/knowledge-base/upload` | **[Admin Only]** Upload `.md`, `.txt`, `.pdf`, `.docx`, or `.csv` (requires `?overwrite=true` for duplicates) |
| `POST` | `/knowledge-base/rebuild` | **[Admin Only]** Force semantic vector store rebuild |

### Analytics & Data Intelligence
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/analytics/datasets` | List `.csv`, `.xlsx` datasets in workspace |
| `POST` | `/analytics/analyze` | Exploratory data profiling on dataset |
| `POST` | `/analytics/calculate` | Deterministic Pandas group-by calculation |
| `GET` | `/analytics/reports` | List generated reports and Plotly charts |
| `GET` | `/analytics/reports/{file}` | Download or view Markdown executive report |
| `GET` | `/analytics/charts/{file}` | Serve interactive Plotly HTML chart |

### Workflows & Agentic Orchestration
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/workflows/plan` | Decompose goal into steps with approval gates |
| `GET` | `/workflows/tasks` | List all active workflows and statuses |
| `GET` | `/workflows/tasks/{id}` | Live workflow execution logs and step breakdown |
| `POST` | `/workflows/tasks/{id}/approve` | Submit human approval decision (`approved: true/false`) |
| `POST` | `/workflows/tasks/{id}/verify` | Verify task deliverables against criteria |
| `POST` | `/workflows/run-tests` | **[Admin Only]** Run pytest test runner in restricted subprocess |
| `POST` | `/workflows/diagnose-failures` | Analyze pytest failure stack traces |

---

## 🐳 Production Deployment

### 1. Single-Server AWS EC2 Production Guide
For full setup on AWS EC2 Ubuntu Linux with Nginx reverse proxy, Certbot SSL, systemd, and automated backups, see:
👉 [Production Deployment Guide (infra/DEPLOY.md)](infra/DEPLOY.md) and [Nginx Configuration (infra/nginx.conf)](infra/nginx.conf).

### 2. Docker Compose (Quickstart)

```bash
docker compose up --build -d
```
Docker Compose configures volume mounts for `workspace/`, `data/`, `knowledge_base/`, and `reports/` to preserve data across container restarts.

> [!NOTE]
> The Dockerfile sets `ENV=production` by default. In production mode, strong API keys (minimum 24 characters, non-placeholder) are strictly required, and offline test doubles (`GEMINI_FAKE=1`) are refused. When running smoke tests or local containers with test keys/fake LLMs, explicitly pass `-e ENV=development` (e.g. `docker run -e ENV=development ...`).

### 3. Container Smoke Test

```bash
python scripts/smoke_test.py --base-url http://localhost:8000 --api-key your_secret_api_key_here
```

### 4. Cloud Deployment (Render / Railway / Heroku)
- **Render:** Connect the repo. Render reads [`render.yaml`](render.yaml) automatically with starter plan, health check, and persistent disk.
- **Railway / Heroku:** Deploys via [`Procfile`](Procfile) with Gunicorn and Uvicorn workers (`--workers 1 --threads 4`).

---

## 🧪 Testing & Verification

The project includes **93 automated tests** with **80%+ statement coverage**, including unit tests, concurrency load tests, Playwright browser end-to-end tests, and container smoke tests:

```bash
# Run the complete test suite
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing --cov-fail-under=80 -m "not slow"

# Code style and lint check
ruff check .

# Run container smoke test against running instance
python scripts/smoke_test.py --base-url http://localhost:8000 --api-key <key>
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
