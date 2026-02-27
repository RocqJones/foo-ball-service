"""
User routes
===========

GET /user/me — Return the full profile for the authenticated user.

Requires:
    X-Install-Id:   <uuid>
    X-Client-Id:    <firebase-uid>   (must be an authenticated user)

Anonymous users (is_authenticated = false) receive a 403.
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.services.install_tracking import get_user
from app.utils.logger import logger

router = APIRouter(prefix="/user", tags=["User"])


@router.get("/me")
async def get_user_details(request: Request):
    """
    Return the full user profile for the calling installation.

    Sensitive fields (email, name, picture) are only returned when the user
    is authenticated (``is_authenticated = true``).  Anonymous callers receive
    a 403 rather than leaking a partial profile.

    Required headers:
        X-Install-Id:   <uuid>           — always required (enforced by middleware)
        X-Client-Id:    <firebase-uid>   — required for authenticated users

    Response (authenticated):
    ```json
    {
        "statusCode": 200,
        "status": "success",
        "message": "User profile retrieved",
        "data": {
            "user_id": "...",
            "installation_id": "...",
            "is_authenticated": true,
            "email": "user@example.com",
            "name": "Jane Doe",
            "picture": "https://...",
            "fixtures_ingest_count": 3,
            "total_api_calls": 12,
            "app_version": "1.2.0"
        }
    }
    ```
    """
    installation_id = request.headers.get("X-Install-Id", "").strip()

    if not installation_id:
        return JSONResponse(
            status_code=400,
            content={
                "statusCode": 400,
                "status": "error",
                "message": "Missing X-Install-Id header",
                "data": None,
            },
        )

    user = get_user(installation_id)

    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "statusCode": 404,
                "status": "error",
                "message": "User not found",
                "data": None,
            },
        )

    if not user.get("is_authenticated", False):
        return JSONResponse(
            status_code=403,
            content={
                "statusCode": 403,
                "status": "error",
                "message": "Sign in with Google to view your profile",
                "data": None,
            },
        )

    logger.debug(f"[user/me] profile fetched for installation_id={installation_id}")

    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "status": "success",
            "message": "User profile retrieved",
            "data": {
                "user_id": str(user["_id"]),
                "installation_id": user.get("installation_id"),
                "is_authenticated": user.get("is_authenticated", True),
                "email": user.get("email"),
                "name": user.get("name"),
                "picture": user.get("picture"),
                "fixtures_ingest_count": user.get("fixtures_ingest_count", 0),
                "total_api_calls": user.get("total_api_calls", 0),
                "app_version": user.get("app_version"),
            },
        },
    )
