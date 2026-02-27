"""
InstallTrackingMiddleware
=========================

Intercepts every request and:

1. Requires ``X-Install-Id`` header → 400 if missing.
2. Finds or creates the anonymous user document in MongoDB.
3. Increments ``total_api_calls`` on every request.
4. For ``/fixtures/ingest``:
   - Checks the free-usage quota **before** passing to the route handler.
   - If quota exhausted and not authenticated → 403 AUTH_REQUIRED.
   - Increments ``fixtures_ingest_count`` only on 2xx responses.
5. Writes a row to ``api_usage_logs`` regardless of outcome.

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

# Endpoint that is subject to the free-usage quota
_TRACKED_INGEST_PATH = "/fixtures/ingest"


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

        # ── 4. Pre-flight quota check for /fixtures/ingest ───────────────────
        is_ingest = path == _TRACKED_INGEST_PATH

        if is_ingest:
            current_count = user.get("fixtures_ingest_count", 0)
            is_auth = user.get("is_authenticated", False)

            if current_count >= FREE_INGEST_LIMIT and not is_auth:
                _log_safely(installation_id, path, request.method, 403, 0)
                return JSONResponse(
                    status_code=403,
                    content={
                        "statusCode": 403,
                        "status": "error",
                        "message": "AUTH_REQUIRED",
                        "data": {
                            "reason": "Sign-in required after 2 free usages."
                        },
                    },
                )

        # ── 5. Call the actual route ─────────────────────────────────────────
        start_ms = time.monotonic()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start_ms) * 1000)
            _log_safely(installation_id, path, request.method, 500, elapsed_ms)
            raise

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        status_code = response.status_code

        # ── 6. Post-response: increment ingest count on success ──────────────
        if is_ingest and 200 <= status_code < 300:
            try:
                increment_ingest_count(installation_id)
            except Exception as exc:
                logger.warning(f"[tracking] Could not increment fixtures_ingest_count: {exc}")

        # ── 7. Log to api_usage_logs ─────────────────────────────────────────
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
