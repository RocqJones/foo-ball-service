from fastapi import Header, HTTPException, status
from app.config.settings import Settings
from app.utils.logger import log_security_event


async def verify_admin_key(x_api_key: str = Header(..., description="Admin API key for authentication")):
    """
    Dependency to verify admin API key for protected endpoints.
    
    This should be used on all admin/sensitive endpoints like database cleanup
    and statistics to prevent unauthorized access.
    
    Args:
        x_api_key: API key provided in the X-API-Key header
        
    Raises:
        HTTPException: 401 if API key is missing or invalid,
                      503 if ADMIN_API_KEY is not configured
                      
    Usage:
        @app.post("/admin/endpoint", dependencies=[Depends(verify_admin_key)])
        def admin_endpoint():
            ...
    """
    # Check if admin key is configured
    if not Settings.ADMIN_API_KEY:
        log_security_event(
            event_type="ADMIN_KEY_NOT_CONFIGURED",
            details="Admin endpoint accessed but ADMIN_API_KEY not configured in environment",
            severity="CRITICAL"
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": "ADMIN_KEY_NOT_CONFIGURED",
                "message": "Admin authentication not configured. Set ADMIN_API_KEY environment variable."
            }
        )
    
    # Verify the provided key
    if x_api_key != Settings.ADMIN_API_KEY:
        log_security_event(
            event_type="ADMIN_AUTH_FAILURE",
            details="Invalid admin API key provided",
            severity="WARNING"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_ADMIN_KEY",
                "message": "Invalid API key"
            }
        )
    
    # Authentication successful
    return True
