import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Define log file paths
APP_LOG_FILE = LOG_DIR / "app.log"
API_LOG_FILE = LOG_DIR / "api_requests.log"
SECURITY_LOG_FILE = LOG_DIR / "security.log"

# Create formatters
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

simple_formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def setup_logger(name: str, log_file: Path, level=logging.INFO, max_bytes=10485760, backup_count=5):
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (default: INFO)
        max_bytes: Maximum size of log file before rotation (default: 10MB)
        backup_count: Number of backup files to keep (default: 5)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(simple_formatter)
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Create main application logger
logger = setup_logger("foo-ball-service", APP_LOG_FILE)

# Create API request logger (for tracking all API calls)
api_logger = setup_logger("api-requests", API_LOG_FILE, level=logging.INFO)

# Create security logger (for security-related events)
security_logger = setup_logger("security", SECURITY_LOG_FILE, level=logging.WARNING)


def log_api_request(method: str, path: str, client_ip: str, status_code: int, 
                   response_time: float = None, user_agent: str = None):
    """
    Log API request details for monitoring and security.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        client_ip: Client IP address
        status_code: Response status code
        response_time: Time taken to process request in seconds
        user_agent: User agent string
    """
    log_msg = f"{method} {path} | IP: {client_ip} | Status: {status_code}"
    
    if response_time is not None:
        log_msg += f" | Time: {response_time:.3f}s"
    
    if user_agent:
        log_msg += f" | UA: {user_agent}"
    
    api_logger.info(log_msg)


def log_security_event(event_type: str, details: str, client_ip: str = None, 
                       severity: str = "WARNING"):
    """
    Log security-related events.
    
    Args:
        event_type: Type of security event (e.g., "SUSPICIOUS_REQUEST", "AUTH_FAILURE")
        details: Detailed description of the event
        client_ip: Client IP address if available
        severity: Severity level (WARNING, ERROR, CRITICAL)
    """
    log_msg = f"[{event_type}] {details}"
    
    if client_ip:
        log_msg += f" | IP: {client_ip}"
    
    if severity == "CRITICAL":
        security_logger.critical(log_msg)
    elif severity == "ERROR":
        security_logger.error(log_msg)
    else:
        security_logger.warning(log_msg)


# Export loggers
__all__ = ['logger', 'api_logger', 'security_logger', 'log_api_request', 'log_security_event']
