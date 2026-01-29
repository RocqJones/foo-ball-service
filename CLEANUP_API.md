# Database Cleanup API

This document describes the new database cleanup endpoints added to manage storage.

## Security Notice

⚠️ **IMPORTANT**: The cleanup and stats endpoints are admin-only and require authentication.

- **Authentication Required**: All endpoints in this document require an admin API key
- **Never expose publicly**: These endpoints must not be accessible on public networks
- **Network restrictions**: Consider using firewall rules or network policies to limit access
- **API Key Protection**: Store the admin API key securely and rotate it regularly

### Setting Up Authentication

1. **Set the Admin API Key** in your environment:
   ```bash
   export ADMIN_API_KEY="your-secure-random-key-here"
   ```

2. **Generate a secure key** (example):
   ```bash
   # Generate a random 32-character key
   openssl rand -hex 32
   ```

3. **Include the key in requests** using the `X-API-Key` header:
   ```bash
   curl -H "X-API-Key: your-admin-api-key" ...
   ```

**Without proper authentication configured, these endpoints will return a 503 Service Unavailable error.**

## Endpoints

### 1. POST /database/cleanup

**Authentication Required**: Admin API key via `X-API-Key` header

Deletes all records older than the specified number of days.

**Request Headers:**
```
X-API-Key: your-admin-api-key
Content-Type: application/json
```

**Request Body (JSON):**
```json
{
  "days": 7
}
```

**Parameters:**
- `days` (optional, default: 7): Number of days to retain. Records older than this will be deleted.
  - Common values: 7, 15, 30, 90 days
  - Must be at least 1

**Example Requests:**

```bash
# Clean up records older than 7 days (default)
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "X-API-Key: your-admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'

# Clean up records older than 15 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "X-API-Key: your-admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{"days": 15}'

# Clean up records older than 30 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "X-API-Key: your-admin-api-key" \
  -H "Content-Type: application/json" \
  -d '{"days": 30}'

# Clean up records older than 90 days
curl -X POST "http://localhost:8000/database/cleanup" \
  -H "X-API-Key: your-admin-api-key" \
  -H "Content-Type: application/json" \
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

**Authentication Required**: Admin API key via `X-API-Key` header

Get statistics about database collections including record counts and date ranges.

**Request Headers:**
```
X-API-Key: your-admin-api-key
```

**Example Request:**

```bash
curl "http://localhost:8000/database/stats" \
  -H "X-API-Key: your-admin-api-key"
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

1. **Check current database size:**
   ```bash
   curl "http://localhost:8000/database/stats" \
     -H "X-API-Key: your-admin-api-key"
   ```

2. **Clean up old records (choose your retention period):**
   ```bash
   # Keep only last 7 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "X-API-Key: your-admin-api-key" \
     -H "Content-Type: application/json" \
     -d '{"days": 7}'
   
   # Keep only last 15 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "X-API-Key: your-admin-api-key" \
     -H "Content-Type: application/json" \
     -d '{"days": 15}'
   
   # Keep only last 30 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "X-API-Key: your-admin-api-key" \
     -H "Content-Type: application/json" \
     -d '{"days": 30}'
   
   # Keep only last 90 days
   curl -X POST "http://localhost:8000/database/cleanup" \
     -H "X-API-Key: your-admin-api-key" \
     -H "Content-Type: application/json" \
     -d '{"days": 90}'
   ```

3. **Verify cleanup:**
   ```bash
   curl "http://localhost:8000/database/stats" \
     -H "X-API-Key: your-admin-api-key"
   ```

## Automation

You can automate the cleanup process using a cron job or scheduled task.

**Important**: Store your admin API key securely when automating:

```bash
# Method 1: Use environment variable
export ADMIN_API_KEY="your-admin-api-key"

# Example cron job to clean up every day at 2 AM (keep last 7 days)
0 2 * * * curl -X POST "http://localhost:8000/database/cleanup" -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"days": 7}'

# Example: Weekly cleanup on Sundays at 3 AM (keep last 30 days)
0 3 * * 0 curl -X POST "http://localhost:8000/database/cleanup" -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"days": 30}'

# Example: Monthly cleanup on the 1st at 1 AM (keep last 90 days)
0 1 1 * * curl -X POST "http://localhost:8000/database/cleanup" -H "X-API-Key: $ADMIN_API_KEY" -H "Content-Type: application/json" -d '{"days": 90}'
```

**Security Best Practices for Automation:**
- Never hardcode API keys in cron jobs or scripts
- Use environment variables or secure credential stores
- Run automated tasks from trusted internal networks only
- Monitor logs for unauthorized access attempts
- Rotate API keys regularly

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

All cleanup operations are logged to:
- **`logs/app.log`** - Detailed cleanup operations and results
- **`logs/api_requests.log`** - API request details (who, when, from where)
- **`logs/security.log`** - Security-related events

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

# Check who performed cleanups
grep "cleanup" logs/api_requests.log
```

For complete logging documentation, see **[LOGGING.md](LOGGING.md)**.

## Security Considerations

### Access Control
- **Admin API Key Required**: Both cleanup and stats endpoints require authentication via the `X-API-Key` header
- **503 Error if Not Configured**: If `ADMIN_API_KEY` is not set, endpoints return 503 Service Unavailable
- **401 Error for Invalid Keys**: Invalid or missing API keys result in 401 Unauthorized responses
- **Security Event Logging**: All authentication failures are logged to `logs/security.log`

### Network Security
**These endpoints should NEVER be publicly accessible.** Implement one or more of these protections:

1. **Firewall Rules**: Restrict access to trusted IP addresses only
   ```bash
   # Example: iptables rule to allow only from internal network
   iptables -A INPUT -p tcp --dport 8000 -s 10.0.0.0/8 -j ACCEPT
   iptables -A INPUT -p tcp --dport 8000 -j DROP
   ```

2. **Reverse Proxy**: Use nginx/Apache to block paths for external traffic
   ```nginx
   # Example nginx config
   location /database/ {
       allow 10.0.0.0/8;  # Internal network only
       deny all;
       proxy_pass http://localhost:8000;
   }
   ```

3. **VPN/Internal Network**: Deploy the service on an internal network accessible only via VPN

4. **API Gateway**: Use an API gateway with IP allowlisting for these endpoints

### Threat Model
Without proper access control, an attacker could:
- **Mass Delete Data**: Use `/database/cleanup` with `days=1` to delete most fixtures and predictions
- **Enumerate Database**: Use `/database/stats` to learn collection sizes and data retention patterns
- **Denial of Service**: Repeatedly call cleanup to impact performance and delete data

### Recommendations
1. ✅ Always set `ADMIN_API_KEY` to a strong, random value (minimum 32 characters)
2. ✅ Use HTTPS in production to protect API keys in transit
3. ✅ Implement network-level restrictions (firewall, VPN, or reverse proxy)
4. ✅ Rotate the admin API key regularly (e.g., every 90 days)
5. ✅ Monitor `logs/security.log` for unauthorized access attempts
6. ✅ Use different API keys for different environments (dev, staging, prod)
7. ✅ Store API keys in secure credential management systems (e.g., AWS Secrets Manager, HashiCorp Vault)
8. ✅ Never commit API keys to version control
9. ✅ Document who has access to admin API keys
10. ✅ Revoke and regenerate keys if compromised
