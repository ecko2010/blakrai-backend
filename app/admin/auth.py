"""
Admin panel authentication — cookie-based sessions with HMAC signing.
Brute-force protection via rate limiting.
"""

import hashlib
import hmac
import json
import time
from functools import wraps
from typing import Optional

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse

from app.config import settings

# ─── Rate limiter for login attempts ────────────────────
_login_attempts: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 min


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(ip: str) -> bool:
    """Return True if allowed, False if locked out."""
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    # Clean old attempts
    attempts = [t for t in attempts if now - t < LOCKOUT_SECONDS]
    _login_attempts[ip] = attempts
    return len(attempts) < MAX_LOGIN_ATTEMPTS


def _record_attempt(ip: str):
    now = time.time()
    _login_attempts.setdefault(ip, []).append(now)


def _clear_attempts(ip: str):
    _login_attempts.pop(ip, None)


# ─── Session cookie signing ────────────────────────────

def _sign(payload: str) -> str:
    """Sign a payload with HMAC-SHA256."""
    key = settings.ADMIN_SECRET_KEY.encode()
    sig = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify(token: str) -> Optional[str]:
    """Verify a signed token. Returns payload or None."""
    if "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    key = settings.ADMIN_SECRET_KEY.encode()
    expected = hmac.new(key, payload.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected):
        return payload
    return None


def create_session(username: str) -> str:
    """Create a signed session token."""
    data = json.dumps({"user": username, "ts": int(time.time())})
    return _sign(data)


def verify_session(token: str) -> Optional[dict]:
    """Verify session token. Returns session data or None."""
    payload = _verify(token)
    if not payload:
        return None
    try:
        data = json.loads(payload)
        # Sessions expire after 24 hours
        if time.time() - data.get("ts", 0) > 86400:
            return None
        return data
    except (json.JSONDecodeError, KeyError):
        return None


def verify_login(username: str, password: str) -> bool:
    """Verify admin credentials from env vars."""
    if not settings.ADMIN_PASSWORD:
        return False
    return (
        hmac.compare_digest(username, settings.ADMIN_USERNAME)
        and hmac.compare_digest(password, settings.ADMIN_PASSWORD)
    )


def get_current_admin(request: Request) -> Optional[dict]:
    """Get current admin from session cookie. Returns None if not logged in."""
    token = request.cookies.get("admin_session")
    if not token:
        return None
    return verify_session(token)


def require_admin(request: Request) -> dict:
    """Require admin — raises redirect to login if not authenticated."""
    admin = get_current_admin(request)
    if not admin:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return admin
