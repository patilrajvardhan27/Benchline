"""Bearer token checks for the agent, matching the pricing API: HS256 dev tokens locally, OIDC otherwise."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt

from app.core.config import Settings

SCOPE = "agent:run"
MIN_SECRET_BYTES = 32


class AuthError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str]


@lru_cache(maxsize=4)
def _jwks(issuer: str) -> jwt.PyJWKClient:
    discovery = httpx.get(f"{issuer.rstrip('/')}/.well-known/openid-configuration", timeout=5).json()
    return jwt.PyJWKClient(discovery["jwks_uri"], cache_keys=True)


def authenticate(authorization: str | None, settings: Settings) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError(401, "Sign in to use the assistant.")
    token = authorization[7:].strip()
    try:
        if len(settings.dev_jwt_secret.encode()) >= MIN_SECRET_BYTES:
            claims = jwt.decode(token, settings.dev_jwt_secret, algorithms=["HS256"],
                                options={"require": ["exp", "sub"]})
        elif settings.oidc_issuer_uri:
            key = _jwks(settings.oidc_issuer_uri).get_signing_key_from_jwt(token)
            claims = jwt.decode(token, key.key, algorithms=["RS256", "ES256"],
                                issuer=settings.oidc_issuer_uri,
                                options={"require": ["exp", "sub"], "verify_aud": False})
        else:
            raise AuthError(503, "Sign-in is not configured on this server.")
    except jwt.PyJWTError:
        raise AuthError(401, "Your session is not valid. Sign in again.") from None
    raw = claims.get("scope", claims.get("scp", ""))
    scopes = frozenset(raw.split() if isinstance(raw, str) else raw)
    if SCOPE not in scopes:
        raise AuthError(403, "Your account cannot use the assistant.")
    return Principal(str(claims["sub"]), scopes)
