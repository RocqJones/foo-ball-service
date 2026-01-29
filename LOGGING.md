# Logging System

This application includes a comprehensive logging system for monitoring, debugging, and security auditing.

## Table of Contents
- [Quick Reference](#quick-reference)
- [Log Files](#log-files)
- [Log Rotation](#log-rotation)
- [Viewing Logs](#viewing-logs)
- [Security Monitoring](#security-monitoring)
- [Daily Review Checklist](#daily-review-checklist)
- [Troubleshooting](#troubleshooting)

---

## Quick Reference

### Log Files Location
```
logs/
├── app.log              # General application logs
├── api_requests.log     # All API requests (who, what, when, where)
└── security.log         # Security events (unauthorized, errors, etc.)
```

### Quick Commands
```bash
# Real-time monitoring
tail -f logs/app.log              # Application logs
tail -f logs/api_requests.log     # API requests
tail -f logs/security.log         # Security events
tail -f logs/*.log                # All logs

# Search logs
grep "cleanup" logs/app.log                    # Find cleanup operations
grep "ERROR" logs/app.log                      # Find all errors
grep "192.168.1.100" logs/api_requests.log     # Find requests from IP
grep "$(date +%Y-%m-%d)" logs/*.log            # Today's logs

# Count requests
grep "$(date +%Y-%m-%d)" logs/api_requests.log | wc -l  # Total today
grep "Status: 200" logs/api_requests.log | wc -l        # Count 200s
grep "Status: 500" logs/api_requests.log | wc -l        # Count 500s
```

---

## Log Files

All log files are stored in the `logs/` directory (automatically created on startup):

### 1. `app.log`
**General application logs** including:
- Application startup/shutdown events
- Service operations (predictions, ingestion, cleanup)
- General information and debug messages
- Application errors and warnings

### 2. `api_requests.log`
**All API request logs** including:
- HTTP method and path
- Client IP address
- Response status code
- Response time
- User agent

**Format:**
```
2026-01-29 14:30:45 - INFO - POST /database/cleanup | IP: 192.168.1.100 | Status: 200 | Time: 0.523s | UA: curl/7.68.0
2026-01-29 14:31:12 - INFO - GET /predictions/today | IP: 192.168.1.101 | Status: 200 | Time: 1.234s | UA: Mozilla/5.0...
```

### 3. `security.log`
**Security-related events** including:
- Unauthorized access attempts (401)
- Forbidden access attempts (403)
- Server errors (500+)
- Request exceptions
- Suspicious activity patterns

**Format:**
```
2026-01-29 14:35:22 - WARNING - [AUTH_FAILURE] POST /database/cleanup - Unauthorized access attempt | IP: 192.168.1.200
2026-01-29 14:36:10 - ERROR - [SERVER_ERROR] GET /predictions/today - Server error occurred | IP: 192.168.1.150
```

### What Gets Logged Automatically

**API Requests:**
- ✅ Every API call with method, path, IP, status, response time, and user agent

**Security Events:**
- ✅ 401 Unauthorized attempts
- ✅ 403 Forbidden access
- ✅ 500+ Server errors
- ✅ Request exceptions

**Application Events:**
- ✅ Startup/shutdown
- ✅ Cleanup operations
- ✅ Predictions generation
- ✅ Data ingestion
- ✅ Errors and warnings

## Log Rotation

All log files use **rotating file handlers** to prevent unlimited growth:
- **Maximum file size:** 10MB per file
- **Backup count:** 5 files
- **Total storage:** ~60MB per log type (6 files × 10MB)
- Old log files are automatically archived with extensions: `.log.1`, `.log.2`, etc.

## Log Levels

The logging system supports standard Python log levels:

- **DEBUG:** Detailed information for diagnosing problems
- **INFO:** General informational messages
- **WARNING:** Warning messages (potential issues)
- **ERROR:** Error messages (something failed)
- **CRITICAL:** Critical issues (application may fail)

## Viewing Logs

### Real-time monitoring (tail)
```bash
# Watch application logs
tail -f logs/app.log

# Watch API requests
tail -f logs/api_requests.log

# Watch security events
tail -f logs/security.log

# Watch all logs simultaneously
tail -f logs/*.log
```

### Search logs
```bash
# Find all cleanup operations
grep "cleanup" logs/app.log

# Find all failed requests
grep "Status: 5" logs/api_requests.log

# Find security events from specific IP
grep "192.168.1.100" logs/security.log

# Find errors in the last hour
find logs/ -name "*.log" -mmin -60 -exec grep "ERROR" {} \;
```

### Count requests by status code
```bash
# Count 200 responses
grep "Status: 200" logs/api_requests.log | wc -l

# Count 500 errors
grep "Status: 5" logs/api_requests.log | wc -l

# Count today's API requests
grep "$(date +%Y-%m-%d)" logs/api_requests.log | wc -l

# Count errors today
grep "$(date +%Y-%m-%d)" logs/app.log | grep "ERROR" | wc -l
```

### Monitor specific operations
```bash
# Cleanup operations
grep -i "cleanup" logs/app.log | tail -20

# Database operations
grep -i "database\|fixtures\|predictions" logs/app.log | tail -20

# Failed requests (4xx and 5xx)
grep "Status: [45]" logs/api_requests.log | tail -20

# Slow requests (>2 seconds)
grep "$(date +%Y-%m-%d)" logs/api_requests.log | grep -E "Time: [2-9]\.[0-9]+s|Time: [0-9]{2,}\.[0-9]+s"
```

## Security Monitoring

### Track suspicious activity
The security log automatically captures:
1. **Authentication failures** - Multiple attempts may indicate brute force
2. **Forbidden access** - Attempts to access restricted resources
3. **Server errors** - May indicate attacks or system issues
4. **Request exceptions** - Malformed requests or exploit attempts

### Find repeated failed attempts from same IP
```bash
grep "AUTH_FAILURE" logs/security.log | cut -d'|' -f2 | sort | uniq -c | sort -rn
```

### Most active IPs
```bash
awk '{print $7}' logs/api_requests.log | sort | uniq -c | sort -rn | head -10
```

### Recent security events
```bash
tail -50 logs/security.log
```

### Monitor for potential DDoS
```bash
# Count requests per IP
awk '{print $7}' logs/api_requests.log | sort | uniq -c | sort -rn | head -10

# Requests in last 5 minutes per IP
grep "$(date +%Y-%m-%d)" logs/api_requests.log | tail -1000 | awk '{print $7}' | sort | uniq -c | sort -rn
```

---

## Daily Review Checklist

Run these commands daily to monitor your application:

```bash
# 1. Check error count
grep "$(date +%Y-%m-%d)" logs/app.log | grep "ERROR" | wc -l

# 2. Check security events
grep "$(date +%Y-%m-%d)" logs/security.log | wc -l

# 3. Check total requests
grep "$(date +%Y-%m-%d)" logs/api_requests.log | wc -l

# 4. Check recent errors
grep "$(date +%Y-%m-%d)" logs/app.log | grep "ERROR" | tail -10

# 5. Check slow requests (>2 seconds)
grep "$(date +%Y-%m-%d)" logs/api_requests.log | grep -E "Time: [2-9]\.[0-9]+s|Time: [0-9]{2,}\.[0-9]+s"

# 6. Top 5 most requested endpoints
grep "$(date +%Y-%m-%d)" logs/api_requests.log | awk '{print $6}' | sort | uniq -c | sort -rn | head -5
```

---

## API Request Logging

The `APILoggingMiddleware` automatically logs **every API request** with:
- ✅ Request method and path
- ✅ Client IP address
- ✅ Response status code
- ✅ Response time (performance monitoring)
- ✅ User agent (client identification)

This middleware is useful for:
- **Performance monitoring:** Track slow endpoints
- **Usage analytics:** See which endpoints are most used
- **Security auditing:** Identify suspicious patterns
- **Debugging:** Trace request flows

---

## Integration with Application

### In your code
```python
from app.utils.logger import logger, log_api_request, log_security_event

# General logging
logger.info("Processing started")
logger.error("An error occurred", exc_info=True)

# Manual API logging (usually automatic via middleware)
log_api_request(
    method="POST",
    path="/custom/endpoint",
    client_ip="192.168.1.100",
    status_code=200,
    response_time=0.523
)

# Security event logging
log_security_event(
    event_type="SUSPICIOUS_REQUEST",
    details="Multiple failed login attempts",
    client_ip="192.168.1.200",
    severity="WARNING"
)
```

## Best Practices

1. **Regular monitoring:** Check logs daily for errors and security issues
2. **Set up alerts:** Use tools like `logwatch` or `fail2ban` to monitor logs
3. **Archive old logs:** Move old `.log.N` files to long-term storage
4. **Analyze patterns:** Look for trends in API usage and errors
5. **Protect log files:** Ensure logs directory has proper permissions

## Log Analysis Tools

### Simple log viewer
```bash
# View last 100 lines of app log
tail -n 100 logs/app.log

# View logs with line numbers
cat -n logs/app.log | tail -n 50
```

### Using grep for patterns
```bash
# Find all database cleanup operations
grep -i "cleanup" logs/app.log

# Find all errors and warnings
grep -E "ERROR|WARNING" logs/app.log

# Find logs from today
grep "$(date +%Y-%m-%d)" logs/app.log
```

### Count log entries
```bash
# Total API requests today
grep "$(date +%Y-%m-%d)" logs/api_requests.log | wc -l

# Errors in the last hour
find logs/app.log -mmin -60 | xargs grep "ERROR" | wc -l
```

---

## Troubleshooting

### Logs not appearing?
```bash
# Check directory exists and is writable
ls -la logs/

# Check application is running
ps aux | grep python

# Check for permission errors
tail -20 logs/app.log | grep -i permission

# Verify log directory was created
ls -la | grep logs
```

### Logs too large?
```bash
# Check current log sizes
du -h logs/*

# Delete old backup logs
find logs/ -name "*.log.*" -mtime +30 -delete

# Or compress them
find logs/ -name "*.log.*" -mtime +7 -exec gzip {} \;
```

**To adjust log rotation settings**, edit `app/utils/logger.py`:
```python
# Change max_bytes (default: 10MB)
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10485760,  # 10MB - increase or decrease
    backupCount=5        # Number of backup files
)
```

### Need more detail?
Change log level from INFO to DEBUG in `app/utils/logger.py`:
```python
logger = setup_logger("foo-ball-service", APP_LOG_FILE, level=logging.DEBUG)
```

---

## Advanced Features

### Integration with Monitoring Tools

**Send logs to external service:**
```bash
# Example: Send to Logstash
tail -f logs/api_requests.log | nc logstash-server 5000

# Example: Send to Papertrail
tail -f logs/*.log | logger -t foo-ball-service -n logs.papertrailapp.com -P 12345
```

**Set up automated alerts** (using cron):
```bash
# Create alert script: /usr/local/bin/check_errors.sh
#!/bin/bash
ERRORS=$(find logs/app.log -mmin -60 | xargs grep "ERROR" | wc -l)
if [ $ERRORS -gt 100 ]; then
    echo "High error count: $ERRORS in last hour" | mail -s "Alert: foo-ball-service" admin@example.com
fi

# Add to crontab (check every hour)
0 * * * * /usr/local/bin/check_errors.sh
```

### Clean Up Old Logs

```bash
# Delete logs older than 30 days
find logs/ -name "*.log.*" -mtime +30 -delete

# Compress logs older than 7 days
find logs/ -name "*.log.*" -mtime +7 -exec gzip {} \;

# Archive logs to backup location
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/*.log.* && \
  mv logs_backup_*.tar.gz /path/to/backup/
```

---

## Example: Daily Log Review Script

Create a script to review important log events:

```bash
#!/bin/bash
# daily_log_review.sh

echo "=== Daily Log Review for $(date +%Y-%m-%d) ==="
echo ""

echo "Total API Requests:"
grep "$(date +%Y-%m-%d)" logs/api_requests.log | wc -l

echo ""
echo "Errors:"
grep "$(date +%Y-%m-%d)" logs/app.log | grep "ERROR" | wc -l

echo ""
echo "Security Events:"
grep "$(date +%Y-%m-%d)" logs/security.log | wc -l

echo ""
echo "Top 5 Most Requested Endpoints:"
grep "$(date +%Y-%m-%d)" logs/api_requests.log | awk '{print $6}' | sort | uniq -c | sort -rn | head -5

echo ""
echo "Recent Errors:"
grep "$(date +%Y-%m-%d)" logs/app.log | grep "ERROR" | tail -5

echo ""
echo "Top 5 Most Active IPs:"
grep "$(date +%Y-%m-%d)" logs/api_requests.log | awk '{print $7}' | sort | uniq -c | sort -rn | head -5

echo ""
echo "Slow Requests (>2s):"
grep "$(date +%Y-%m-%d)" logs/api_requests.log | grep -E "Time: [2-9]\.[0-9]+s|Time: [0-9]{2,}\.[0-9]+s" | wc -l
```

Run with: `bash daily_log_review.sh`

---
