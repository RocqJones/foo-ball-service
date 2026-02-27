"""
InstallTrackingMiddleware
=========================

Intercepts every request and:

1. Requires ``X-Install-Id`` header → 400 if missing.
2. Finds or creates the anonymous user document in MongoDB.
3. Increments ``total_api_calls`` on every request.
4. For authenticated users: enforces ``X-Client-Id`` header on protected routes.
   - X-Client-Id must match the stored google_id / firebase uid.
   - Missing or mismatched → 401.
5. For ``/fixtures/ingest``:
   - Checks the free-usage quota **before** passing to the route handler.
   - If quota exhausted and not authenticated → 403 AUTH_REQUIRED.
   - Increments ``fixtures_ingest_count`` only on 2xx responses.
6. Writes a row to ``api_usage_logs`` regardless of outcome.

Required headers (all API routes):
    X-Install-Id    : <uuid>          — anonymous device identity
    X-App-Version   : <version>       — app version string (optional but recommended)

Additional header (authenticated users only):
    X-Client-Id     : <firebase-uid>  — must match stored google_id after sign-in

Order matters: this middleware must be added **after** APILoggingMiddleware so
that it runs as the *inner* (closer to the route) middleware.
"""

import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.services.install_tracking import (
    FREE_INGEST_LIMIT,
    get_or_create_user,
    increment_ingest_count,
    increment_total_calls,
    log_api_usage,
)
from app.utils.logger import logger

# Endpoint subject to the free-usage quota
_TRACKED_INGEST_PATH = "/fixtures/ingest"

# Routes that require X-Client-Id once the user is authenticated.
# Auth endpoints themselves are excluded so sign-in is always reachable.
_CLIENT_ID_EXEMPT_PREFIXES = (
    "/auth/",   # sign-in endpoints must stay open
)


class InstallTrackingMiddleware(BaseHTTPMiddleware):
    """Anonymous installation tracking + auth-gate middleware."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # ── 1. Extract installation ID ───────────────────────────────────────
        installation_id = request.headers.get("X-Install-Id", "").strip()

        if not installation_id:
            return JSONResponse(
                status_code=400,
                content={
                    "statusCode": 400,
                    "status": "error",
                    "message": "Installation ID missing",
                    "data": None,
                },
            )

        # ── 2. Find / create user ─────────────────────────────────────────────
        app_version = request.headers.get("X-App-Version", "").strip() or None
        try:
            user = get_or_create_user(installation_id, app_version)
        except Exception as exc:
            logger.error(f"[tracking] DB error on get_or_create_user: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "statusCode": 500,
                    "status": "error",
                    "message": "Internal server error during install tracking",
                    "data": None,
                },
            )

        # ── 3. Increment total_api_calls ──────────────────────────────────────
        try:
            increment_total_calls(installation_id)
        except Exception as exc:
            logger.warning(f"[tracking] Could not increment total_api_calls: {exc}")

        # ── 4. X-Client-Id enforcement for authenticated users ───────────────
        is_authenticated = user.get("is_authenticated", False)
        is_exempt = any(path.startswith(p) for p in _CLIENT_ID_EXEMPT_PREFIXES)

        if is_authenticated and not is_exempt:
            client_id = request.headers.get("X-Client-Id", "").strip()
            stored_uid = user.get("google_id", "")

            if not client_id:
                _log_safely(installation_id, path, request.method, 401, 0)
                return JSONResponse(
                    status_code=401,
                    content={
                        "statusCode": 401,
                        "status": "error",
                        "message": "X-Client-Id header required for authenticated users",
                        "data": None,
                    },
                )

            if client_id != stored_uid:
                _log_safely(installation_id, path, request.method, 401, 0)
                return JSONResponse(
                    status_code=401,
                    content={
                        "statusCode": 401,
                        "status": "error",
                        "message": "X-Client-Id mismatch",
                        "data": None,
                    },
                )

        # ── 5. Pre-flight quota check for /fixtures/ingest ───────────────────
        is_ingest = path == _TRACKED_INGEST_PATH

        if is_ingest:
            current_count = user.get("fixtures_ingest_count", 0)

            if current_count >= FREE_INGEST_LIMIT and not is_authenticated:
                _log_safely(installation_id, path, request.method, 403, 0)
                return JSONResponse(
                    status_code=403,
                    content={
                        "statusCode": 403,
                        "status": "error",
                        "message": "AUTH_REQUIRED",
                        "data": {
                            "reason": f"Sign-in required after {FREE_INGEST_LIMIT} free usages."
                        },
                    },
                )

        # ── 6. Call the actual route ─────────────────────────────────────────
        start_ms = time.monotonic()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_ms) * 1000)
            _log_safely(installation_id, path, request.method, 500, elapsed_ms)
            raise

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        status_code = response.status_code

        # ── 7. Post-response: increment ingest count on success ──────────────
        if is_ingest and 200 <= status_code < 300:
            try:
                new_count = increment_ingest_count(installation_id)
                logger.debug(
                    "[tracking] Incremented fixtures_ingest_count for %s to %s",
                    installation_id,
                    new_count,
                )
            except Exception as exc:
                logger.warning(f"[tracking] Could not increment fixtures_ingest_count: {exc}")

        # ── 8. Log to api_usage_logs ─────────────────────────────────────────
        _log_safely(installation_id, path, request.method, status_code, elapsed_ms)

        return response


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _log_safely(
    installation_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
) -> None:
    """Write to api_usage_logs, swallowing any DB error."""
    try:
        log_api_usage(installation_id, endpoint, method, status_code, response_time_ms)
    except Exception as exc:
        logger.warning(f"[tracking] api_usage_logs write failed: {exc}")
