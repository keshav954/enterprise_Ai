import os
import time
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.config.settings import settings
from app.security.guard import verify_api_key
from app.routes.chat import router as chat_router
from app.routes.knowledge_base import router as knowledge_base_router
from app.routes.analytics import router as analytics_router
from app.routes.workflows import router as workflows_router
from app.tools.company_tools import TOOLS

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s (request_id=%(request_id)s): %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    # Production guard: Refuse to start if ENV=production and no API key is configured
    if settings.env.lower() == "production" and not settings.api_keys:
        raise RuntimeError("Production mode requires APP_API_KEY to be configured.")

    logger.info(
        "Enterprise AI Employee API starting – %d tools registered. (env=%s)",
        len(TOOLS),
        settings.env,
        extra={"request_id": "startup"},
    )
    yield
    logger.info("Enterprise AI Employee API is shutting down.", extra={"request_id": "shutdown"})


app = FastAPI(
    title="Enterprise AI Employee API",
    version="0.5.0",
    lifespan=lifespan,
)


# --- Request-ID and Structured Logging Middleware --- #
@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = req_id
    start_time = time.time()

    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000.0, 2)
        logger.exception(
            "Unhandled server exception during request [method=%s path=%s duration_ms=%s]",
            request.method,
            request.url.path,
            duration_ms,
            extra={"request_id": req_id},
        )
        return JSONResponse(
            status_code=500,
            content={"detail": f"An internal server error occurred. Request ID: {req_id}"},
            headers={"X-Request-ID": req_id},
        )

    duration_ms = round((time.time() - start_time) * 1000.0, 2)
    response.headers["X-Request-ID"] = req_id

    # Safe structured access log - never log Authorization headers, keys, or message bodies
    logger.info(
        "HTTP %s %s -> %d (%s ms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        extra={"request_id": req_id},
    )
    return response


# --- CORS Middleware Configuration --- #
raw_origins = settings.allowed_origins.strip()
if raw_origins:
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
else:
    origins = ["http://localhost:8000", "http://127.0.0.1:8000"]

# Never combine "*" with allow_credentials=True
if "*" in origins:
    allow_credentials = False
else:
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (static files are open / exempt from API key auth)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers protected with API-key authentication
app.include_router(chat_router, dependencies=[Depends(verify_api_key)])
app.include_router(knowledge_base_router, dependencies=[Depends(verify_api_key)])
app.include_router(analytics_router, dependencies=[Depends(verify_api_key)])
app.include_router(workflows_router, dependencies=[Depends(verify_api_key)])


@app.get("/")
def home(request: Request):
    """
    Root endpoint: serves dashboard for browsers, requires auth for JSON API clients.
    """
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return FileResponse(str(STATIC_DIR / "index.html"))

    # For API clients asking for JSON, verify auth
    verify_api_key(request, request.headers.get("Authorization"))

    return {
        "status": "online",
        "service": "Enterprise AI Employee",
        "version": app.version,
        "dashboard": "/dashboard",
        "knowledge_base": "/knowledge-base/stats",
        "analytics": "/analytics/reports",
        "workflows": "/workflows/tasks",
        "total_tools": len(TOOLS),
        "available_tools": [tool.__name__ for tool in TOOLS],
    }


@app.get("/health")
def health_check():
    """Health check endpoint for Docker / load-balancer probes and monitoring (auth exempt)."""
    from app.config.settings import settings
    return {
        "status": "healthy",
        "version": app.version,
        "model": settings.gemini_model,
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.get("/dashboard")
def dashboard():
    """Serves static dashboard HTML (auth exempt, frontend prompts for API key)."""
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
