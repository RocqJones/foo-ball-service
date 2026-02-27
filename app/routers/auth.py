"""
Authentication routes
=====================

POST /auth/firebase — Firebase Android SDK (the only supported auth flow).

The Android app signs in with Google via FirebaseAuth, receives a Firebase
id_token from ``firebaseUser.getIdToken()``, and sends it here.
This endpoint verifies it, then upserts the user document.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.security.google_auth import verify_firebase_id_token
from app.services.install_tracking import upsert_firebase_user
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Request schema ─────────────────────────────────────────────────────────

class FirebaseAuthRequest(BaseModel):
    id_token: str           # from firebaseUser.getIdToken()
    installation_id: str    # UUID stored on device since first install


# ── Response helper ────────────────────────────────────────────────────────

def _auth_success(user: dict) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "statusCode": 200,
            "status": "success",
            "message": "Authentication successful",
            "data": {
                "user_id": str(user["_id"]),
                "installation_id": user.get("installation_id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "picture": user.get("picture"),
                "is_authenticated": user.get("is_authenticated", True),
                "fixtures_ingest_count": user.get("fixtures_ingest_count", 0),
                "total_api_calls": user.get("total_api_calls", 0),
                "app_version": user.get("app_version"),
            },
        },
    )


# ── POST /auth/firebase ────────────────────────────────────────────────────

@router.post("/firebase")
async def firebase_sign_in(body: FirebaseAuthRequest):
    """
    Verify a Firebase id_token issued by the Firebase Auth Android SDK and
    upsert the user document in MongoDB.

    Android Kotlin flow:
        // 1. Sign in with Google credential inside Firebase
        FirebaseAuth.getInstance()
            .signInWithCredential(GoogleAuthProvider.getCredential(googleIdToken, null))
            .addOnSuccessListener { result ->

                // 2. Get the FIREBASE token (not the Google one)
                result.user?.getIdToken(false)
                    ?.addOnSuccessListener { tokenResult ->

                        // 3. POST here
                        api.postAuthFirebase(
                            idToken = tokenResult.token!!,
                            installationId = storedInstallationId
                        )
                    }
            }

    Behaviour:
    - Verifies the Firebase id_token against Firebase's public keys.
    - Upserts the user — upgrades the existing anonymous user, or creates a
      new document if the installation_id is not yet in the database.
    - Sets is_authenticated = true and stores the Firebase UID.

    After a 200 response the Android app must add:
        X-Client-Id: <uid from data.user_id field — firebase uid stored as google_id>
    to every subsequent request.

    Required headers (same as all endpoints):
        X-Install-Id:   <uuid>
        X-App-Version:  <version>
    """
    # ── 1. Verify Firebase token ─────────────────────────────────────────────
    claims = verify_firebase_id_token(body.id_token)

    if claims is None:
        return JSONResponse(
            status_code=401,
            content={
                "statusCode": 401,
                "status": "error",
                "message": "Invalid or expired Firebase id_token",
                "data": None,
            },
        )

    firebase_uid: str = claims.get("uid", "")
    if not firebase_uid:
        return JSONResponse(
            status_code=400,
            content={
                "statusCode": 400,
                "status": "error",
                "message": "Firebase token missing uid claim",
                "data": None,
            },
        )

    # ── 2. Upsert user ───────────────────────────────────────────────────────
    try:
        user = upsert_firebase_user(
            installation_id=body.installation_id,
            firebase_uid=firebase_uid,
            email=claims.get("email", ""),
            name=claims.get("name", "") or claims.get("display_name", ""),
            picture=claims.get("picture", "") or claims.get("photo_url", ""),
        )
    except Exception as exc:
        logger.error(f"[auth/firebase] DB upsert failed: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "statusCode": 500,
                "status": "error",
                "message": "Failed to update user record",
                "data": None,
            },
        )

    # ── 3. Respond ───────────────────────────────────────────────────────────
    logger.info(
        f"[auth/firebase] authenticated installation_id={body.installation_id} "
        f"uid={firebase_uid} email={claims.get('email')}"
    )
    return _auth_success(user)
