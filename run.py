"""
Enterprise AI Employee - Application Entrypoint
Run locally:
    python run.py
Or with custom options:
    python run.py --host 0.0.0.0 --port 8000 --reload
"""
import argparse
import sys
import uvicorn
from app.config.settings import settings


def main():
    parser = argparse.ArgumentParser(
        description="Enterprise AI Employee Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--host",
        default=settings.host,
        help="Network interface to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.port,
        help="Port to listen on",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=settings.debug,
        help="Enable auto-reload on code changes (development)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (production)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  Enterprise AI Employee API & Dashboard")
    print(f"  URL: http://{args.host}:{args.port}")
    print(f"  Dashboard: http://{args.host}:{args.port}/dashboard")
    print(f"  Model: {settings.gemini_model}")
    print(f"  Gemini Configured: {'Yes' if settings.gemini_api_key else 'No (set GEMINI_API_KEY in .env)'}")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
    )


if __name__ == "__main__":
    main()

