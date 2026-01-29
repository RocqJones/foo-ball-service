from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from app.utils.logger import log_api_request, log_security_event


class APILoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all API requests with details including:
    - HTTP method and path
    - Client IP address
    - Response status code
    - Response time
    - User agent
    
    This is useful for monitoring, debugging, and security auditing.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Get request details
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Start timer
        start_time = time.time()
        
        # Process request
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Log the request
            log_api_request(
                method=method,
                path=path,
                client_ip=client_ip,
                status_code=status_code,
                response_time=response_time,
                user_agent=user_agent
            )
            
            # Log security events for suspicious activity
            if status_code == 401:
                log_security_event(
                    event_type="AUTH_FAILURE",
                    details=f"{method} {path} - Unauthorized access attempt",
                    client_ip=client_ip,
                    severity="WARNING"
                )
            elif status_code == 403:
                log_security_event(
                    event_type="FORBIDDEN_ACCESS",
                    details=f"{method} {path} - Forbidden access attempt",
                    client_ip=client_ip,
                    severity="WARNING"
                )
            elif status_code >= 500:
                log_security_event(
                    event_type="SERVER_ERROR",
                    details=f"{method} {path} - Server error occurred",
                    client_ip=client_ip,
                    severity="ERROR"
                )
            
            return response
            
        except Exception as e:
            # Log error
            response_time = time.time() - start_time
            
            log_api_request(
                method=method,
                path=path,
                client_ip=client_ip,
                status_code=500,
                response_time=response_time,
                user_agent=user_agent
            )
            
            log_security_event(
                event_type="REQUEST_EXCEPTION",
                details=f"{method} {path} - Exception: {str(e)}",
                client_ip=client_ip,
                severity="ERROR"
            )
            
            # Re-raise the exception
            raise
