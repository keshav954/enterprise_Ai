"""
Enterprise Security Guards: API Key Authentication & Rate Limiting.
"""
import contextvars
import hashlib
import secrets
import time
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import Header, HTTPException, Request

from app.config.settings import settings
from app.tools.workspace_tools import set_current_key_hash

current_admin_status: contextvars.ContextVar[bool] = contextvars.ContextVar("current_admin_status", default=False)


def set_current_admin(is_admin: bool):
    """Sets whether the current caller has admin privileges."""
    return current_admin_status.set(bool(is_admin))


def get_current_admin() -> bool:
    """Returns whether the current caller has admin privileges."""
    return current_admin_status.get()


def is_admin_key_string(provided_key: str) -> bool:
    """Checks whether a given key string is an authorized admin key."""
    if not settings.api_keys and settings.env.lower() == "development":
        return True
    if not provided_key:
        return False
    return any(secrets.compare_digest(provided_key, ak) for ak in settings.admin_keys)


def is_admin_request(request: Request) -> bool:
    """Checks whether the request is authenticated with an admin key."""
    if not settings.api_keys and settings.env.lower() == "development":
        return True
    provided_key = getattr(request.state, "api_key", None)
    return is_admin_key_string(provided_key or "")

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
        set_current_admin(True)
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
    is_admin = is_admin_key_string(provided_key)
    set_current_admin(is_admin)
    return key_hash


def verify_admin_key(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> str:
    """
    Validates that the caller has admin permissions.
    Raises 401 if unauthorized, 403 if valid non-admin key.
    """
    key_hash = verify_api_key(request, authorization)
    if not is_admin_request(request):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Admin privileges required for this operation.",
        )
    return key_hash


# Backward-compatible alias
verify_api_token = verify_api_key


# In-memory sliding window rate limiter: key_hash/client_ip -> list of timestamps
_rate_limits: Dict[str, List[float]] = defaultdict(list)
_heavy_rate_limits: Dict[str, List[float]] = defaultdict(list)


def _check_rate_limit(request: Request, limit: int, tracker: Dict[str, List[float]]) -> bool:
    if limit <= 0:
        return True

    # Identify caller by key_hash or client host
    caller_id = getattr(request.state, "key_hash", None)
    if not caller_id:
        caller_id = request.client.host if request.client else "unknown"

    now = time.time()
    window_start = now - 60.0

    # Prune timestamps outside current 60s window
    timestamps = [t for t in tracker[caller_id] if t > window_start]
    tracker[caller_id] = timestamps

    if len(timestamps) >= limit:
        oldest_in_window = timestamps[0]
        retry_after = max(1, int(oldest_in_window + 60.0 - now + 0.999))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: maximum {limit} requests per minute.",
            headers={"Retry-After": str(retry_after)},
        )

    tracker[caller_id].append(now)
    return True


def rate_limiter(request: Request) -> bool:
    """
    In-memory sliding-window rate limiter per API key (or client IP fallback).
    Returns HTTP 429 with Retry-After header when rate limit is exceeded.
    """
    return _check_rate_limit(request, settings.effective_rate_limit, _rate_limits)


def heavy_rate_limiter(request: Request) -> bool:
    """
    Strict sliding-window rate limiter for expensive operations (upload, rebuild, run-tests).
    Default: RATE_LIMIT_HEAVY_PER_MIN (5/min).
    """
    _check_rate_limit(request, settings.effective_rate_limit, _rate_limits)
    return _check_rate_limit(request, settings.rate_limit_heavy_per_min, _heavy_rate_limits)


def reset_rate_limits():
    """Utility function to clear in-memory rate limit records (used in tests)."""
    _rate_limits.clear()
    _heavy_rate_limits.clear()
