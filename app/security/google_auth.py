"""
Firebase id_token verification helper.

The Android app uses the Firebase Auth SDK to sign in with Google.
The token produced by ``firebaseUser.getIdToken()`` is a Firebase token —
verified here against Firebase's public keys using the ``google-auth`` library.

Environment variable:
    GOOGLE_CLIENT_ID  — not required for Firebase token verification.
                        Firebase tokens carry their own audience (project ID).
                        Kept in settings for any future OAuth2 use.
"""

from typing import Optional

import requests as _requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.utils.logger import logger

_FIREBASE_ISSUER_PREFIX = "https://securetoken.google.com/"


def verify_firebase_id_token(token: str) -> Optional[dict]:
    """
    Verify a Firebase id_token and return the decoded claims.

    The token comes from ``firebaseUser.getIdToken()`` on Android after the
    user has signed in with Google via ``FirebaseAuth.signInWithCredential()``.

    Returns:
        dict with ``uid``, ``email``, ``name``, ``picture`` on success.
        None if the token is invalid or expired.
    """
    try:
        request_session = google_requests.Request(session=_requests.Session())

        # verify_firebase_token checks signature, expiry, and issuer
        claims = id_token.verify_firebase_token(token, request_session)

        # Guard: issuer must be Firebase, not Google OAuth2
        issuer = claims.get("iss", "")
        if not issuer.startswith(_FIREBASE_ISSUER_PREFIX):
            logger.warning(f"[firebase_auth] Unexpected issuer: {issuer!r}")
            return None

        # Normalise: surface uid at the top level (mirrors firebase-admin SDK)
        claims["uid"] = claims.get("sub", "")
        return claims

    except ValueError as exc:
        logger.warning(f"[firebase_auth] Invalid Firebase token: {exc}")
        return None
    except Exception as exc:
        logger.error(
            f"[firebase_auth] Unexpected error verifying Firebase token: {exc}",
            exc_info=True,
        )
        return None
