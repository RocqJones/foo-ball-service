import os
import certifi
from pymongo import MongoClient
from app.config.settings import settings


def _build_mongo_client() -> MongoClient:
    """Create a MongoClient with TLS settings that work reliably on PaaS providers.

    Render (and other minimal Linux images) can have missing/outdated CA bundles.
    Using certifi's CA bundle fixes most Atlas TLS handshake errors.

    Env toggles:
      - MONGO_TLS_ALLOW_INVALID_CERTS=true  (NOT recommended; for emergency debugging only)
    """

    mongo_uri = settings.MONGO_URI
    allow_invalid = os.getenv("MONGO_TLS_ALLOW_INVALID_CERTS", "false").lower() in {"1", "true", "yes"}

    kwargs = {
        "tlsCAFile": certifi.where(),
        "serverSelectionTimeoutMS": 30000,
        "connectTimeoutMS": 30000,
        "socketTimeoutMS": 30000,
        "retryWrites": True,
        "appname": "foo-ball-service",
    }

    if allow_invalid:
        # WARNING: Disables certificate validation.
        kwargs["tlsAllowInvalidCertificates"] = True

    # If using mongodb:// without explicit tls/ssl params, enable TLS by default
    if mongo_uri.startswith("mongodb://") and "tls=" not in mongo_uri and "ssl=" not in mongo_uri:
        kwargs["tls"] = True

    return MongoClient(mongo_uri, **kwargs)


client = _build_mongo_client()
db = client[settings.DB_NAME]

def get_collection(name: str):
    return db[name]
