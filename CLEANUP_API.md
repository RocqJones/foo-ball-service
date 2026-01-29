# Database Cleanup API

This document describes the new database cleanup endpoints added to manage storage.

## Authentication

**⚠️ Security Notice:** These endpoints require admin authentication to prevent unauthorized access.

To use these endpoints, you must:
1. Set the `ADMIN_API_KEY` environment variable in your `.env` file
2. Include the API key in the `X-Admin-API-Key` header with every request

Generate a secure admin API key:
```bash
# Using openssl (recommended)
openssl rand -hex 32

# Or using Python
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Add to your `.env` file:
```env
ADMIN_API_KEY=your_generated_secure_key_here
```

## Endpoints

### 1. POST /database/cleanup

Deletes all records older than the specified number of days.

**Authentication:** Required via `X-Admin-API-Key` header

**Request Body (JSON):**
```json
{
  "days": 7
}
```

**Headers:**
```
Content-Type: application/json
X-Admin-API-Key: your_admin_api_key_here
```

**Parameters:**
- `days` (optional, default: 7): Number of days to retain. Records older than this will be deleted.
  - Common values: 7, 15, 30, 90 days
  - Must be at least 1

**Example Requests:**

```bash
# Set your admin API key
export ADMIN_API_KEY="your_admin_api_key_here"

# Clean up records older than 7 days (default)
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -d '{"days": 7}'

# Clean up records older than 15 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -d '{"days": 15}'

# Clean up records older than 30 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -d '{"days": 30}'

# Clean up records older than 90 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY" \
  -d '{"days": 90}'
```

**Example Response:**

```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Successfully cleaned up records older than 7 days",
  "cutoff_date": "2026-01-22",
  "days_retained": 7,
  "collections_cleaned": {
    "fixtures": 150,
    "predictions": 200,
    "team_stats": "skipped - no date field found"
  },
  "total_records_deleted": 350
}
```

### 2. GET /database/stats

Get statistics about database collections including record counts and date ranges.

**Authentication:** Required via `X-Admin-API-Key` header

**Headers:**
```
X-Admin-API-Key: your_admin_api_key_here
```

**Example Request:**

```bash
# Set your admin API key
export ADMIN_API_KEY="your_admin_api_key_here"

curl "http://localhost:8000/database/stats" \
  -H "X-Admin-API-Key: $ADMIN_API_KEY"
```

**Example Response:**

```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Database statistics retrieved successfully",
  "stats": {
    "fixtures": {
      "total_count": 450,
      "oldest_date": "2026-01-15",
      "newest_date": "2026-01-29"
    },
    "predictions": {
      "total_count": 300,
      "oldest_date": "2026-01-15",
      "newest_date": "2026-01-29"
    },
    "team_stats": {
      "total_count": 120
    }
  }
}
```

## Usage Workflow

**Note:** All commands require authentication via the `X-Admin-API-Key` header.

```bash
# Set your admin API key (do this once)
export ADMIN_API_KEY="your_admin_api_key_here"
```

1. **Check current database size:**
   ```bash
   curl "http://localhost:8000/database/stats" \
     -H "X-Admin-API-Key: $ADMIN_API_KEY"
   ```

2. **Clean up old records (choose your retention period):**
   ```bash
   # Keep only last 7 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "Content-Type: application/json" \
     -H "X-Admin-API-Key: $ADMIN_API_KEY" \
     -d '{"days": 7}'
   
   # Keep only last 15 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "Content-Type: application/json" \
     -H "X-Admin-API-Key: $ADMIN_API_KEY" \
     -d '{"days": 15}'
   
   # Keep only last 30 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "Content-Type: application/json" \
     -H "X-Admin-API-KEY: $ADMIN_API_KEY" \
     -d '{"days": 30}'
   
   # Keep only last 90 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "Content-Type: application/json" \
     -H "X-Admin-API-Key: $ADMIN_API_KEY" \
     -d '{"days": 90}'
   ```

3. **Verify cleanup:**
   ```bash
   curl "http://localhost:8000/database/stats" \
     -H "X-Admin-API-Key: $ADMIN_API_KEY"
   ```

## Automation

You can automate the cleanup process using a cron job or scheduled task.

**Important:** Store your admin API key securely and use it in automated scripts:

```bash
# Example cron job to clean up every day at 2 AM (keep last 7 days)
# Add ADMIN_API_KEY to your crontab environment or source from secure file
0 2 * * * curl -X POST "http://localhost:8000/database/cleanup" -H "Content-Type: application/json" -H "X-Admin-API-Key: $ADMIN_API_KEY" -d '{"days": 7}'

# Example: Weekly cleanup on Sundays at 3 AM (keep last 30 days)
0 3 * * 0 curl -X POST "http://localhost:8000/database/cleanup" -H "Content-Type: application/json" -H "X-Admin-API-Key: $ADMIN_API_KEY" -d '{"days": 30}'

# Example: Monthly cleanup on the 1st at 1 AM (keep last 90 days)
0 1 1 * * curl -X POST "http://localhost:8000/database/cleanup" -H "Content-Type: application/json" -H "X-Admin-API-Key: $ADMIN_API_KEY" -d '{"days": 90}'
```

**Security Best Practices for Automation:**
- Store the `ADMIN_API_KEY` in a secure environment variable or secrets management system
- Never commit the API key to version control
- Use restricted file permissions for scripts containing the key (e.g., `chmod 600`)
- Consider using a secrets manager or environment file with restricted access

## Collections Cleaned

The cleanup process handles these collections:

1. **fixtures** - Deletes fixtures where `fixture.date` is older than the cutoff date
2. **predictions** - Deletes predictions where `created_at` is older than the cutoff date
3. **team_stats** - Attempts to clean if a date field exists (currently skipped if no date field is found)

## Notes

- The cleanup operation is idempotent - running it multiple times with the same parameters is safe
- Records are permanently deleted - make sure you have backups if needed
- The `days` parameter must be at least 1
- All dates are compared using ISO format strings (YYYY-MM-DD)
- The operation logs all actions for audit purposes

## Logging and Security

### Authentication and Authorization

These endpoints are protected with admin API key authentication to prevent unauthorized access:
- **401 Unauthorized**: Returned when no API key is provided
- **403 Forbidden**: Returned when an invalid API key is provided or when admin auth is not configured
- All authentication failures are logged to `logs/security.log` for audit purposes

### Audit Logging

All cleanup operations are logged to:
- **`logs/app.log`** - Detailed cleanup operations and results
- **`logs/api_requests.log`** - API request details (who, when, from where)
- **`logs/security.log`** - Security-related events (auth failures, configuration issues)

Example log entries:
```
2026-01-29 14:30:45 - INFO - Cleanup requested with days=7
2026-01-29 14:30:45 - INFO - Starting cleanup of records older than 7 days (before 2026-01-22)
2026-01-29 14:30:46 - INFO - Deleted 150 fixtures older than 2026-01-22
2026-01-29 14:30:46 - INFO - Deleted 200 predictions older than 2026-01-22
2026-01-29 14:30:46 - INFO - Cleanup complete. Total records deleted: 350
```

To monitor cleanup operations:
```bash
# Watch cleanup logs in real-time
tail -f logs/app.log | grep -i cleanup

# View all cleanup operations today
grep "cleanup" logs/app.log | grep "$(date +%Y-%m-%d)"

# Check who performed cleanups (includes IP addresses)
grep "cleanup" logs/api_requests.log

# Monitor authentication failures
tail -f logs/security.log | grep -i auth
```

For complete logging documentation, see **[LOGGING.md](LOGGING.md)**.
