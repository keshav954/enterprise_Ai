import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes.chat import router as chat_router
from app.tools.company_tools import TOOLS

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup / shutdown lifecycle."""
    logger.info(
        "Enterprise AI Employee API is starting – %d tools registered.",
        len(TOOLS),
    )
    yield
    logger.info("Enterprise AI Employee API is shutting down.")


app = FastAPI(
    title="Enterprise AI Employee API",
    version="0.4.0",
    lifespan=lifespan,
)

# Enable CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(chat_router)


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "Enterprise AI Employee",
        "version": app.version,
        "dashboard": "/dashboard",
        "available_tools": [tool.__name__ for tool in TOOLS],
    }


@app.get("/health")
def health_check():
    """Health check endpoint for Docker / load-balancer probes and monitoring."""
    from app.config.settings import settings
    return {
        "status": "healthy",
        "version": app.version,
        "model": settings.gemini_model,
        "gemini_configured": bool(settings.gemini_api_key),
    }


@app.get("/dashboard")
def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    from app.config.settings import settings
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
