import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config.settings import settings
from app.routes.analytics import router as analytics_router
from app.routes.chat import router as chat_router
from app.routes.knowledge_base import router as knowledge_base_router
from app.routes.workflows import router as workflows_router
from app.security.guard import verify_api_key
from app.tools.company_tools import TOOLS


class RequestIdFilter(logging.Filter):
    """Ensures every log record contains a request_id attribute to prevent format KeyError."""
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


# Configure structured logging
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s (request_id=%(request_id)s): %(message)s")
log_filter = RequestIdFilter()

if not root_logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(log_filter)
    stream_handler.setFormatter(log_formatter)
    root_logger.addHandler(stream_handler)
else:
    for handler in root_logger.handlers:
        handler.addFilter(log_filter)
        handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


PLACEHOLDER_SUBSTRINGS = ["your_", "change", "example", "secret_api_key"]


def validate_startup_security(current_settings=None):
    """
    Validates startup configuration and security guards.
    - Open access (no keys) is strictly prohibited unless ENV is explicitly 'development'.
    - In production, refuses to run if any API key is empty, shorter than 24 characters,
      or contains placeholder patterns ('your_', 'change', 'example', 'secret_api_key').
    - In development, logs a loud warning for open access or insecure keys.
    """
    s = current_settings or settings
    env = s.env.strip().lower()
    is_prod = env == "production"
    valid_keys = s.api_keys

    # Guard 1: Open access (no keys) must only be allowed when ENV is explicitly "development"
    if not valid_keys:
        if is_prod:
            raise RuntimeError("Production mode requires APP_API_KEY to be configured.")
        if env != "development":
            raise RuntimeError(
                f"Open access (no API keys configured) is forbidden in '{s.env}' mode. "
                "Open access is only permitted when ENV is explicitly 'development'."
            )
        logger.warning(
            "⚠️ SECURITY WARNING: Server is running with open access (no API keys configured). "
            "Anyone on your network can access endpoints. Configure APP_API_KEY for production!",
            extra={"request_id": "startup"},
        )
        return

    # Check all configured API keys (and admin keys if provided)
    all_keys = list(valid_keys)
    if s.app_admin_keys:
        for ak in s.admin_keys:
            if ak not in all_keys:
                all_keys.append(ak)

    for key in all_keys:
        stripped_key = key.strip()
        if not stripped_key:
            if is_prod:
                raise RuntimeError("Production API key cannot be empty.")
            logger.warning(
                "⚠️ SECURITY WARNING: Configured API key is empty.",
                extra={"request_id": "startup"},
            )
            continue

        if len(stripped_key) < 24:
            msg = f"API key '{stripped_key[:6]}...' is shorter than 24 characters (length {len(stripped_key)})."
            if is_prod:
                raise RuntimeError(
                    f"Production API key must be at least 24 characters long: {msg} "
                    'Generate a safe key using python -c "import secrets; print(secrets.token_urlsafe(32))".'
                )
            logger.warning(
                f"⚠️ SECURITY WARNING: {msg} Keys should be at least 24 characters in production.",
                extra={"request_id": "startup"},
            )

        key_lower = stripped_key.lower()
        for placeholder in PLACEHOLDER_SUBSTRINGS:
            if placeholder in key_lower:
                msg = f"API key '{stripped_key[:10]}...' contains placeholder pattern '{placeholder}'."
                if is_prod:
                    raise RuntimeError(
                        f"Insecure placeholder API key detected in production: {msg} "
                        "Please configure a cryptographically random secret key."
                    )
                logger.warning(
                    f'⚠️ SECURITY WARNING: {msg} Generate a safe key using python -c "import secrets; print(secrets.token_urlsafe(32))".',
                    extra={"request_id": "startup"},
                )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    validate_startup_security()

    # Production guard: Refuse to run GEMINI_FAKE in production
    is_fake = settings.gemini_fake or os.getenv("GEMINI_FAKE", "").lower() in ("1", "true", "yes")
    if settings.env.lower() == "production" and is_fake:
        raise RuntimeError("GEMINI_FAKE test double is strictly forbidden when ENV=production.")

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
    except Exception:
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
    has_real_key = bool(settings.gemini_api_key or os.getenv("GEMINI_API_KEY"))
    is_fake = settings.gemini_fake or os.getenv("GEMINI_FAKE", "").lower() in ("1", "true", "yes")
    return {
        "status": "healthy",
        "version": app.version,
        "model": settings.gemini_model,
        "gemini_configured": has_real_key,
        "gemini_fake": is_fake,
    }


@app.get("/dashboard")
def dashboard():
    """Serves static dashboard HTML (auth exempt, frontend prompts for API key)."""
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
