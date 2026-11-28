# ─────────────────────────────────────────────────────────────
# Enterprise AI Employee – Hardened Multi-Stage Production Dockerfile
# - Minimal image size via multi-stage build & CPU-only PyTorch
# - Non-root execution under UID 10001 (appuser)
# - Pre-warmed model cache owned by appuser
# - Production dependencies only (dev/test packages excluded)
# ─────────────────────────────────────────────────────────────

# ── Stage 1: Build & Dependencies ──
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build tools required for compiling C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install CPU-only torch first to avoid downloading multi-gigabyte CUDA binaries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --extra-index-url https://download.pytorch.org/whl/cpu

# Install production dependencies (no pytest / dev packages)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer embedding model into builder cache
ENV HF_HOME=/build/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/build/.cache/torch/sentence_transformers
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"


# ── Stage 2: Minimal Non-Root Runtime ──
FROM python:3.13-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV=production \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/torch/sentence_transformers \
    MEMORY_DB_PATH=/app/data/memory.db

WORKDIR /app

# Create dedicated non-root application user and group (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy pre-downloaded embedding model cache from builder
COPY --from=builder --chown=appuser:appgroup /build/.cache /app/.cache

# Copy application source code
COPY --chown=appuser:appgroup . .

# Ensure runtime state directories exist with correct non-root permissions
RUN mkdir -p /app/workspace /app/data /app/data/chroma /app/knowledge_base /app/reports /app/reports/charts && \
    chown -R appuser:appgroup /app/workspace /app/data /app/knowledge_base /app/reports /app/.cache

# Drop root privileges and switch to non-root appuser
USER appuser

EXPOSE 8000

# Health check with 90s start-period to accommodate cold-start model initialization
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production gunicorn entrypoint (1 worker, 4 threads for SQLite & ChromaDB concurrency safety)
CMD ["python", "-m", "gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "1", \
     "--threads", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
