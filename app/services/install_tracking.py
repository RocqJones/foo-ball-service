"""
Installation tracking service.

Responsibilities:
- Find-or-create anonymous users by installation_id.
- Increment usage counters (total_api_calls, fixtures_ingest_count).
- Persist every request in the api_usage_logs collection.
"""

from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.config.settings import settings
from app.db.mongo import get_collection
from app.utils.logger import logger

# ── Free-tier limit before Google auth is required ──────────────────────────
FREE_INGEST_LIMIT = settings.FREE_INGEST_LIMIT


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_or_create_user(installation_id: str, app_version: Optional[str] = None) -> dict:
    """
    Return the user document for *installation_id*, creating it if absent.

    The upsert is atomic: no race condition between concurrent requests from
    the same device.
    """
    users = get_collection("users")
    now = datetime.now(timezone.utc)

    user = users.find_one_and_update(
        {"installation_id": installation_id},
        {
            "$setOnInsert": {
                "installation_id": installation_id,
                "google_id": None,
                "email": None,
                "name": None,
                "is_authenticated": False,
                "fixtures_ingest_count": 0,
                "total_api_calls": 0,
                "created_at": now,
            },
            "$set": {
                "last_seen": now,
                "app_version": app_version or "unknown",
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return user


def increment_total_calls(installation_id: str) -> None:
    """Bump total_api_calls and refresh last_seen."""
    users = get_collection("users")
    users.update_one(
        {"installation_id": installation_id},
        {
            "$inc": {"total_api_calls": 1},
            "$set": {"last_seen": datetime.now(timezone.utc)},
        },
    )


def increment_ingest_count(installation_id: str) -> int:
    """
    Atomically increment fixtures_ingest_count.

    Returns the *new* count after the increment.
    """
    users = get_collection("users")
    updated = users.find_one_and_update(
        {"installation_id": installation_id},
        {"$inc": {"fixtures_ingest_count": 1}},
        return_document=ReturnDocument.AFTER,
    )
    return updated["fixtures_ingest_count"] if updated else 1


def get_user(installation_id: str) -> Optional[dict]:
    """Return the user document or None."""
    return get_collection("users").find_one({"installation_id": installation_id})


def upsert_firebase_user(
    installation_id: str,
    firebase_uid: str,
    email: str,
    name: str,
    picture: str,
    app_version: Optional[str] = None,
) -> dict:
    """
    Upsert a user by ``installation_id`` after Firebase authentication.

    - If the document exists → update Google/Firebase fields and mark authenticated.
    - If it does NOT exist (e.g. fresh install that skipped anonymous tracking)
      → create a full user document so nothing breaks downstream.

    Returns the final document after the upsert.
    """
    users = get_collection("users")
    now = datetime.now(timezone.utc)

    user = users.find_one_and_update(
        {"installation_id": installation_id},
        {
            "$setOnInsert": {
                "installation_id": installation_id,
                "fixtures_ingest_count": 0,
                "total_api_calls": 0,
                "created_at": now,
            },
            "$set": {
                "google_id": firebase_uid,
                "email": email,
                "name": name,
                "picture": picture,
                "is_authenticated": True,
                "last_seen": now,
                "app_version": app_version or "unknown",
            },
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return user


# ---------------------------------------------------------------------------
# Usage logging
# ---------------------------------------------------------------------------

def log_api_usage(
    installation_id: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
) -> None:
    """Insert a record into api_usage_logs (fire-and-forget, never raises)."""
    try:
        get_collection("api_usage_logs").insert_one(
            {
                "installation_id": installation_id,
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "response_time_ms": response_time_ms,
                "created_at": datetime.now(timezone.utc),
            }
        )
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[install_tracking] Failed to write api_usage_log: {exc}")
