"""
POST /auth/google
=================

Accepts a Google id_token + installation_id, verifies the token, and
upgrades the anonymous user to an authenticated one.

Request body:
    {
        "id_token":        "<google-id-token>",
        "installation_id": "<uuid>"
    }

Response (200):
    {
        "statusCode": 200,
        "status":     "success",
        "message":    "Authentication successful",
        "data": {
            "user_id": "...",
            "email":   "...",
            "name":    "..."
        }
    }
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.mongo import get_collection
from app.security.google_auth import verify_google_id_token
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request schema ─────────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    id_token: str
    installation_id: str


# ── Route ──────────────────────────────────────────────────────────────────

@router.post("/google")
async def google_sign_in(body: GoogleAuthRequest):
    """
    Verify a Google id_token and link it to the anonymous user identified by
    ``installation_id``.

    Steps:
    1. Verify token with Google's public keys.
    2. Extract ``sub``, ``email``, ``name``, ``picture``.
    3. Find user by ``installation_id``.
    4. Update user: google_id, email, name, is_authenticated = True.
    5. Return structured success response.
    """

    # ── 1. Verify the Google id_token ────────────────────────────────────────
    id_info = verify_google_id_token(body.id_token)

    if id_info is None:
        return JSONResponse(
            status_code=401,
            content={
                "statusCode": 401,
                "status": "error",
                "message": "Invalid or expired Google id_token",
                "data": None,
            },
        )

    google_id: str = id_info.get("sub", "")
    email: str = id_info.get("email", "")
    name: str = id_info.get("name", "")
    picture: str = id_info.get("picture", "")

    if not google_id:
        return JSONResponse(
            status_code=400,
            content={
                "statusCode": 400,
                "status": "error",
                "message": "Google token missing 'sub' claim",
                "data": None,
            },
        )

    # ── 2. Look up user by installation_id ───────────────────────────────────
    users = get_collection("users")
    user = users.find_one({"installation_id": body.installation_id})

    if user is None:
        return JSONResponse(
            status_code=404,
            content={
                "statusCode": 404,
                "status": "error",
                "message": "Installation ID not found. Launch the app at least once before signing in.",
                "data": None,
            },
        )

    # ── 3. Update user document ─────────────────────────────────────────────
    try:
        users.update_one(
            {"installation_id": body.installation_id},
            {
                "$set": {
                    "google_id": google_id,
                    "email": email,
                    "name": name,
                    "picture": picture,
                    "is_authenticated": True,
                    "last_seen": datetime.now(timezone.utc),
                }
            },
        )
    except Exception as exc:
        logger.error(f"[auth/google] DB update failed: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "statusCode": 500,
                "status": "error",
                "message": "Failed to update user record",
                "data": None,
            },
        )

    # ── 4. Return success ────────────────────────────────────────────────────
    user_id = str(user["_id"])
    logger.info(f"[auth/google] User {user_id} authenticated via Google (email={email})")

    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "status": "success",
            "message": "Authentication successful",
            "data": {
                "user_id": user_id,
                "email": email,
                "name": name,
            },
        },
    )
