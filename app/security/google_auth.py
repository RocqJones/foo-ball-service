"""
Google OAuth2 id_token verification helper.

Uses ``google-auth`` (google.oauth2.id_token + google.auth.transport.requests)
to verify tokens issued by Google Sign-In / Firebase Auth.

Environment variable:
    GOOGLE_CLIENT_ID  – Your Android OAuth2 client ID (audience claim).
                        If absent, verification will still proceed but the
                        audience is not validated (useful for dev / testing).
"""

from typing import Optional

import requests as _requests
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config.settings import settings
from app.utils.logger import logger


def verify_google_id_token(token: str) -> Optional[dict]:
    """
    Verify a Google id_token and return the decoded payload.

    Returns:
        dict with at least ``sub``, ``email``, ``name``, ``picture`` on success.
        None if the token is invalid / expired.

    Raises:
        Nothing – all exceptions are caught and logged; None is returned.
    """
    try:
        request_session = google_requests.Request(session=_requests.Session())

        # audience can be None (skip audience check) or the client_id string
        audience: Optional[str] = settings.GOOGLE_CLIENT_ID or None

        id_info = id_token.verify_oauth2_token(token, request_session, audience)

        return id_info
    except ValueError as exc:
        # Token is invalid or expired
        logger.warning(f"[google_auth] Invalid id_token: {exc}")
        return None
    except Exception as exc:
        logger.error(f"[google_auth] Unexpected error verifying id_token: {exc}", exc_info=True)
        return None
