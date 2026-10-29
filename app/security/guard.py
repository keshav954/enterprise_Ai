"""
Enterprise Security Guards: Token Authentication & Rate Limiting.
"""
import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import Depends, Header, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import settings

security = HTTPBearer(auto_error=False)

# In-memory sliding window rate limiter: client_ip -> list of timestamps
_rate_limits: Dict[str, List[float]] = defaultdict(list)


def verify_api_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Validates API authorization token if configured in settings.
    If settings.api_auth_token is not set, access is permitted (open dev mode).
    Accepts:
      - Authorization: Bearer <token>
      - X-API-Key: <token>
    """
    expected_token = settings.api_auth_token.strip() if settings.api_auth_token else ""
    if not expected_token:
        return True

    provided_token = None
    if credentials and credentials.credentials:
        provided_token = credentials.credentials.strip()
    elif x_api_key:
        provided_token = x_api_key.strip()

    if not provided_token or provided_token != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid or missing API authentication token.",
        )
    return True


def rate_limiter(request: Request):
    """
    Lightweight sliding-window rate limiter per client IP.
    """
    limit = settings.rate_limit_per_minute
    if limit <= 0:
        return True

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60.0

    # Prune old timestamps
    timestamps = [t for t in _rate_limits[client_ip] if t > window_start]
    _rate_limits[client_ip] = timestamps

    if len(timestamps) >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {limit} requests per minute.",
        )

    _rate_limits[client_ip].append(now)
    return True


def reset_rate_limits():
    """Utility function to clear in-memory rate limit records (used in tests)."""
    _rate_limits.clear()

