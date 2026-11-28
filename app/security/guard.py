"""
Enterprise Security Guards: API Key Authentication & Rate Limiting.
"""
import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import Header, HTTPException, Request

from app.config.settings import settings
from app.tools.workspace_tools import set_current_key_hash

# In-memory sliding window rate limiter: key_hash/client_ip -> list of timestamps
_rate_limits: Dict[str, List[float]] = defaultdict(list)


def verify_api_key(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates API authorization key using constant-time comparison.
    Requires header: 'Authorization: Bearer <key>'
    If settings.env == 'production' and no keys are configured, raises RuntimeError.
    Stores the caller's sha256 key hash in request.state.key_hash for session isolation.
    """
    valid_keys = settings.api_keys
    is_production = settings.env.lower() == "production"

    if is_production and not valid_keys:
        raise RuntimeError("Production mode requires APP_API_KEY to be configured.")

    if not valid_keys:
        # Development mode without keys configured: allow open access with default dev hash
        dev_hash = "dev_default"
        request.state.key_hash = dev_hash
        set_current_key_hash(dev_hash)
        return dev_hash

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Missing or invalid Authorization header. Expected 'Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provided_key = authorization[7:].strip()
    matched = any(secrets.compare_digest(provided_key, vk) for vk in valid_keys)

    if not matched:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    key_hash = hashlib.sha256(provided_key.encode("utf-8")).hexdigest()
    request.state.key_hash = key_hash
    request.state.api_key = provided_key
    set_current_key_hash(key_hash)
    return key_hash


# Backward-compatible alias
verify_api_token = verify_api_key


def rate_limiter(request: Request) -> bool:
    """
    In-memory sliding-window rate limiter per API key (or client IP fallback).
    Returns HTTP 429 with Retry-After header when rate limit is exceeded.
    """
    limit = settings.effective_rate_limit
    if limit <= 0:
        return True

    # Identify caller by key_hash or client host
    caller_id = getattr(request.state, "key_hash", None)
    if not caller_id:
        caller_id = request.client.host if request.client else "unknown"

    now = time.time()
    window_start = now - 60.0

    # Prune timestamps outside current 60s window
    timestamps = [t for t in _rate_limits[caller_id] if t > window_start]
    _rate_limits[caller_id] = timestamps

    if len(timestamps) >= limit:
        oldest_in_window = timestamps[0]
        retry_after = max(1, int(oldest_in_window + 60.0 - now + 0.999))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {limit} requests per minute.",
            headers={"Retry-After": str(retry_after)},
        )

    _rate_limits[caller_id].append(now)
    return True


def reset_rate_limits():
    """Utility function to clear in-memory rate limit records (used in tests)."""
    _rate_limits.clear()
