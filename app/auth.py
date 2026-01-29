from fastapi import Header, HTTPException, status
from app.config.settings import settings
from app.utils.logger import log_security_event


async def verify_admin_api_key(x_admin_api_key: str = Header(None)):
    """
    Dependency to verify admin API key for protected endpoints.
    
    Args:
        x_admin_api_key: Admin API key passed via X-Admin-API-Key header
        
    Raises:
        HTTPException: 401 if key is missing, 403 if key is invalid or not configured
        
    Returns:
        True if authentication successful
    """
    # Check if admin API key is configured
    if not settings.ADMIN_API_KEY:
        log_security_event(
            event_type="AUTH_NOT_CONFIGURED",
            details="Admin API key not configured but protected endpoint was accessed",
            client_ip="unknown",
            severity="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin authentication is not configured. Set ADMIN_API_KEY environment variable."
        )
    
    # Check if API key was provided
    if not x_admin_api_key:
        log_security_event(
            event_type="AUTH_MISSING",
            details="Protected endpoint accessed without admin API key",
            client_ip="unknown",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin API key required. Provide X-Admin-API-Key header."
        )
    
    # Verify API key
    if x_admin_api_key != settings.ADMIN_API_KEY:
        log_security_event(
            event_type="AUTH_INVALID",
            details="Protected endpoint accessed with invalid admin API key",
            client_ip="unknown",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key"
        )
    
    # Authentication successful
    return True
