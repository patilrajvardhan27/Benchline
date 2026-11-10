"""Short-lived dev tokens for the loader. Production uses a real identity provider."""

from __future__ import annotations

import os
import time

import jwt

MIN_SECRET_BYTES = 32


def token_from_env() -> str:
    """BENCHLINE_API_TOKEN wins; otherwise mint an HS256 token from DEV_JWT_SECRET."""
    explicit = os.environ.get("BENCHLINE_API_TOKEN")
    if explicit:
        return explicit
    secret = os.environ.get("DEV_JWT_SECRET", "")
    if len(secret.encode()) < MIN_SECRET_BYTES:
        raise RuntimeError(
            "Set BENCHLINE_API_TOKEN, or DEV_JWT_SECRET with at least 32 characters"
        )
    now = int(time.time())
    claims = {"sub": "pipeline-loader", "scope": "prices:write", "iat": now, "exp": now + 3600}
    return jwt.encode(claims, secret, algorithm="HS256")
