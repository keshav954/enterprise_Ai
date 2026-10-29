# ─────────────────────────────────────────────────────────────
# Enterprise AI Employee – Production Docker Image
# Multi-stage build for minimal image size
# ─────────────────────────────────────────────────────────────

FROM python:3.13-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ──
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download SentenceTransformer model into image to avoid cold-start runtime latency
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# ── Copy application source ──
COPY . .

# Create runtime directories that the app expects
RUN mkdir -p workspace data/chroma knowledge_base reports

# Expose the default port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run with gunicorn + uvicorn workers for production
CMD ["python", "-m", "gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
