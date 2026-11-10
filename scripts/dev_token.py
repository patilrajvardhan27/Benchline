# /// script
# requires-python = ">=3.12"
# dependencies = ["pyjwt>=2.9"]
# ///
"""Print a short-lived development token for the local API.

    export DEV_JWT_SECRET=...            # the same value the API was started with
    uv run scripts/dev_token.py          # prints a token

Use it with curl (-H "Authorization: Bearer $TOKEN") or as VITE_DEV_TOKEN for `pnpm dev`.
It only works against an API started with DEV_JWT_SECRET, never against production.
"""

import os
import time

import jwt

SCOPES = "prices:write members:read insights:read insights:write"
LIFETIME_SECONDS = 8 * 3600


def main() -> None:
    secret = os.environ.get("DEV_JWT_SECRET", "")
    if len(secret.encode()) < 32:
        raise SystemExit("Set DEV_JWT_SECRET to the same 32+ character value the API uses")
    now = int(time.time())
    claims = {"sub": "local-dev", "scope": SCOPES, "iat": now, "exp": now + LIFETIME_SECONDS}
    print(jwt.encode(claims, secret, algorithm="HS256"))


if __name__ == "__main__":
    main()
