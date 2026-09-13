import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes.chat import router as chat_router
from app.tools.company_tools import TOOLS

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Enterprise AI Employee API",
    version="0.3.0",
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
        "dashboard": "/dashboard",
        "available_tools": [tool.__name__ for tool in TOOLS],
    }


@app.get("/dashboard")
def dashboard():
    return FileResponse(str(STATIC_DIR / "index.html"))