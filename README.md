# Foo Ball Service - prod

A football match prediction service powered by **Football-Data.org v4 API** with head-to-head (H2H) enhanced predictions.

## 🚀 Key Features (v2 Architecture)

✅ **Smart Auto-Fetch** - Endpoints transparently fetch from source when needed  
✅ **Lazy H2H Loading** - H2H data fetched on-demand, not during ingestion (10/day limit)  
✅ **Protected Caching** - Competitions & matches permanently cached, never cleaned  
✅ **Clean API Design** - No source implementation details exposed to frontend  
✅ **Rate Limit Protection** - Built-in safeguards prevent API exhaustion  
✅ **Frontend-Friendly** - No manual ingestion required, everything auto-fetches  
✅ **Anonymous Install Tracking** - Device fingerprinting via installation ID, no login required  
✅ **Firebase Google Auth** - Seamless sign-in upgrade after free-tier limit  

> **Migration Note**: This service has been migrated from API-Football to Football-Data.org v4 with a completely redesigned architecture. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for details.

## What it does

- **Smart auto-fetch** - GET /competitions and POST /matches automatically fetch from source if needed
- **Generate predictions** using historical head-to-head data combined with recent team form:
  - **Match outcome probabilities** (Home/Draw/Away) with confidence levels
  - **Over/Under 2.5 goals** recommendations
  - **BTTS (Both Teams To Score)** predictions
  - **H2H-enhanced accuracy** using past meeting statistics
- **Lazy H2H loading** - Fetches head-to-head data on-demand (max 10/day) only when predictions requested
- **Protected caching** - Competitions and matches permanently cached, never cleaned
- **RESTful API** - Clean endpoints that mask data source implementation
- **Anonymous tracking** - Every Android install is tracked by UUID; users get 2 free `/fixtures/ingest` calls before sign-in is required
- **Firebase Auth** - Google sign-in via Firebase upgrades anonymous users to authenticated

## Architecture Overview

```
Frontend Request Flow:
┌─────────────────────────────────────────────────────────────┐
│  1. GET /competitions                                       │
│     ↓ Auto-fetches from Football-Data.org if DB empty      │
│     ↓ Returns cached competitions (permanent cache)        │
├─────────────────────────────────────────────────────────────┤
│  2. POST /matches {"competition_code": "PL"}                │
│     ↓ Validates competition exists                          │
│     ↓ Auto-fetches matches if empty for competition         │
│     ↓ Returns cached matches (smart cache, never cleaned)   │
├─────────────────────────────────────────────────────────────┤
│  3. GET /predictions/today                                  │
│     ↓ Lazy-loads H2H for today's matches (max 10/day)      │
│     ↓ Generates predictions with H2H enhancement            │
│     ↓ Returns only matches with H2H available               │
└─────────────────────────────────────────────────────────────┘

Install Tracking & Auth Flow (Android):
┌─────────────────────────────────────────────────────────────┐
│  Every request must include:                                │
│    X-Install-Id: <uuid>      ← generated once on install   │
│    X-App-Version: <version>  ← e.g. "1.0.0"               │
│                                                             │
│  Anonymous (calls 1–2):                                     │
│    GET /fixtures/ingest  → 200 OK + user snapshot          │
│                                                             │
│  On 3rd call (unauthenticated):                             │
│    GET /fixtures/ingest  → 403 AUTH_REQUIRED               │
│                                                             │
│  After Google sign-in via Firebase:                         │
│    POST /auth/firebase   → 200 OK + user snapshot          │
│                                                             │
│  Authenticated (all subsequent calls):                      │
│    X-Install-Id: <uuid>                                     │
│    X-Client-Id: <firebase-uid>  ← required after sign-in  │
│    GET /fixtures/ingest  → 200 OK (unlimited)              │
└─────────────────────────────────────────────────────────────┘

Data Protection:
- 🛡️  Competitions: PROTECTED (permanent cache)
- 🛡️  Matches: PROTECTED (smart cache with H2H)
- 🧹 Predictions: Cleanable after 7 days
- 🧹 Team Stats: Cleanable after 7 days
- 🧹 Fixtures (legacy): Cleanable after 7 days
```

### Key Features

🎯 **H2H-Enhanced Predictions**
- Uses historical head-to-head data when available
- Analyzes past meetings: win ratios, goal averages, draw frequency
- Blends H2H history (70%) with recent form (30%)
- Falls back to team statistics when H2H unavailable

📊 **Prediction Metrics**
- **Match Outcome**: Home win, Draw, Away win probabilities (sum to 100%)
- **Goals**: Over/Under 2.5 with confidence levels
- **BTTS**: Both teams to score probability
- **Confidence Levels**:
  - HIGH: ≥ 75% (goals/BTTS) or ≥ 60% (outcomes)
  - MEDIUM: ≥ 60% (goals/BTTS) or ≥ 45% (outcomes)  
  - LOW: Below medium threshold

⚡ **Smart Caching & Auto-Fetch**
- **Competitions**: Permanent cache, auto-fetches if empty
- **Matches**: Smart cache per competition, auto-fetches if needed
- **H2H**: Lazy loading (only when predictions requested), 24h TTL, 10/day limit
- **Protection**: Competitions & matches NEVER cleaned, only predictions/stats
- **Prevents**: Duplicate API calls, rate limit exhaustion

> **Migration Note**: This service has been migrated from API-Football to Football-Data.org v4 for enhanced prediction capabilities. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for complete migration documentation.

## Project Structure

```
app/
├── main.py                         # FastAPI application
├── jobs/
│   └── daily_run.py               # Daily ingestion pipeline
├── services/
│   ├── ingestion.py               # Data ingestion with caching
│   ├── install_tracking.py        # Install tracking + user upsert logic
│   ├── prediction_v2.py           # H2H-enhanced predictions
│   ├── team_stats_v2.py           # Team statistics computation
│   └── ranking.py                 # Prediction ranking logic
├── middleware/
│   ├── __init__.py                # Exports APILoggingMiddleware
│   └── install_tracking.py       # InstallTrackingMiddleware (auth gate)
├── routers/
│   └── auth.py                   # POST /auth/firebase (Firebase Android SDK)
├── security/
│   ├── auth.py                   # Admin key verification
│   └── google_auth.py            # Firebase id_token verification
├── models/
│   └── rule_based.py              # Prediction algorithms
├── data_sources/
│   └── football_data_api.py       # Football-Data.org API client
├── db/
│   ├── mongo.py                   # MongoDB connection
│   └── schemas.py                 # Database indexes (incl. users, api_usage_logs)
└── config/
    └── settings.py                # Configuration (incl. FREE_INGEST_LIMIT)

scripts/
├── init_db.py                     # Database initialization
├── test_integration.py            # Integration tests
└── setup_migration.py             # Migration setup wizard

logs/                              # Application logs
```

## Prerequisites

- **Python 3.11+**
- **MongoDB** (local or remote)
- **Football-Data.org API key** (free tier: 10 req/min)
- **Google Cloud project** with OAuth2 Web Client ID (for Firebase Auth)

Get your API key: https://www.football-data.org/client/register

## Quick Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# Football-Data.org API v4 (Required)
FOOTBALL_DATA_API_KEY=your_api_key_here
FOOTBALL_DATA_BASE_URL=http://api.football-data.org/v4

# MongoDB (Required)
MONGO_URI=mongodb://localhost:27017
DB_NAME=foo_ball_service

# Admin API Key (Required for database management)
# Generate: openssl rand -hex 32
ADMIN_API_KEY=your_secure_admin_key_here

# Google / Firebase Auth (Required for Android sign-in)
# Use the Web Client ID from Google Cloud Console (not the Android Client ID)
GOOGLE_CLIENT_ID=your_web_client_id.apps.googleusercontent.com
```

### 3. Initialize Database

```bash
# Create indexes
python scripts/init_db.py

# Or run the setup wizard (recommended for first-time)
python scripts/setup_migration.py
```

### 4. Test the API

```bash
# 1. Get competitions (auto-fetches if needed)
curl http://localhost:8000/competitions

# 2. Get matches for Premier League
curl -X POST http://localhost:8000/matches \
  -H "Content-Type: application/json" \
  -d '{"competition_code": "PL", "status_filter": "SCHEDULED"}'

# 3. Get today's predictions (lazy H2H fetch)
curl http://localhost:8000/predictions/today
```

### 5. Start the API Server

```bash
# Start server
uvicorn app.main:app --reload

# Or use the start script
./start_server.sh
```

Open the interactive docs:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### 6. (Optional) Set Up Daily Automation

```bash
# Run daily job manually
python app/jobs/daily_run.py

# Or set up cron (see Daily Automation section)
```

## API Endpoints

---

## 📱 Android Install Tracking & Authentication

Every request from the Android app **must** include these headers:

| Header | Required | Description |
|---|---|---|
| `X-Install-Id` | ✅ Always | UUID generated once on first install |
| `X-App-Version` | Recommended | e.g. `"1.0.0"` |
| `X-Client-Id` | ✅ After sign-in | Firebase UID — required once `is_authenticated = true` |

Missing `X-Install-Id` → `400`. Wrong or missing `X-Client-Id` for an authenticated user → `401`.

### Free-tier quota

Anonymous users get **2 free** `/fixtures/ingest` calls. On the 3rd call the middleware returns:

```json
{
  "statusCode": 403,
  "status": "error",
  "message": "AUTH_REQUIRED",
  "data": { "reason": "Sign-in required after 2 free usages." }
}
```

The Android app should trigger the Firebase Google sign-in flow and then call `POST /auth/firebase`.

---

### Authentication Endpoints

#### POST /auth/firebase

The **only** auth endpoint. Called after the user signs in with Google via the Firebase Auth Android SDK.

> **Why Firebase, not Google?**  
> Even though the user picks a Google account, the Firebase SDK wraps it in a
> Firebase session and issues its own short-lived token from
> `firebaseUser.getIdToken()`. That token is signed by Firebase's keys — not
> Google's OAuth2 keys — so it must be verified differently. Your backend
> never needs to touch a raw Google OAuth2 token.

**Android Kotlin flow:**
```kotlin
// Step 1 — build credential from Google Sign-In result
val googleCredential = GoogleAuthProvider.getCredential(googleIdToken, null)

// Step 2 — hand it to Firebase
FirebaseAuth.getInstance()
    .signInWithCredential(googleCredential)
    .addOnSuccessListener { result ->

        // Step 3 — get the FIREBASE token (not the Google one)
        result.user?.getIdToken(false)
            ?.addOnSuccessListener { tokenResult ->

                // Step 4 — call your backend
                api.postAuthFirebase(
                    idToken = tokenResult.token!!,
                    installationId = prefs.getString("installation_id")
                )
            }
    }
```

**Request:**
```bash
POST /auth/firebase
Content-Type: application/json
X-Install-Id: <uuid>
X-App-Version: 1.0.0
```
```json
{
  "id_token": "<firebaseUser.getIdToken() result>",
  "installation_id": "<uuid stored on device>"
}
```

**Behaviour:**
- Verifies the Firebase id_token against Firebase's public keys
- **Upserts** the user — upgrades the existing anonymous user document, or
  creates a brand-new one if the `installation_id` was never seen before
- Sets `is_authenticated = true` and stores the Firebase UID

**Response (200):**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Authentication successful",
  "data": {
    "user_id": "507f1f77bcf86cd799439011",
    "installation_id": "a1b2c3d4-...",
    "email": "user@gmail.com",
    "name": "John Doe",
    "picture": "https://...",
    "is_authenticated": true,
    "fixtures_ingest_count": 2,
    "total_api_calls": 5,
    "app_version": "1.0.0"
  }
}
```

> ⚠️ After a 200 response, store `data.user_id` (which is the Firebase UID
> stored as `google_id` in the DB) and include it as `X-Client-Id` in **every
> subsequent request**.

---

### Public Endpoints

#### Health Check
```bash
GET /health
```

Returns service health status.

---

#### Get Competitions
```bash
GET /competitions
```

Returns all available competitions with smart auto-fetch.

**Smart Behavior:**
- Automatically fetches from Football-Data.org if database is empty
- Returns cached data if available (permanent cache)
- No manual ingestion required from frontend

**Response:**
```json
{
  "status": "success",
  "count": 123,
  "competitions": [
    {
      "code": "PL",
      "name": "Premier League",
      "emblem": "https://crests.football-data.org/PL.png",
      "area": {
        "name": "England",
        "code": "ENG"
      },
      "currentSeason": {
        "id": 2403,
        "startDate": "2025-08-15",
        "endDate": "2026-05-24",
        "currentMatchday": 26
      },
      "type": "LEAGUE",
      "numberOfAvailableSeasons": 33
    }
  ]
}
```

---

#### Get Matches
```bash
POST /matches
Content-Type: application/json

{
  "competition_code": "PL",
  "status_filter": "SCHEDULED",
  "date_from": "2026-02-11",
  "date_to": "2026-02-15",
  "limit": 100
}
```

Returns matches for a specific competition with smart auto-fetch.

**Request Body:**
- `competition_code` (required): Competition code from `/competitions` (e.g., "PL", "CL")
- `status_filter` (optional): Filter by status - SCHEDULED, TIMED, FINISHED, LIVE (comma-separated)
- `date_from` (optional): Start date filter (YYYY-MM-DD)
- `date_to` (optional): End date filter (YYYY-MM-DD)
- `limit` (optional): Max results (default: 100, max: 500)

**Smart Behavior:**
- Validates competition exists
- Auto-fetches matches from source if empty for that competition
- Returns clean response without exposing source implementation
- Prevents duplicate API calls

**Response:**
```json
{
  "status": "success",
  "count": 6,
  "competition": {
    "code": "PL",
    "name": "Premier League"
  },
  "matches": [
    {
      "id": 538036,
      "utcDate": "2026-02-11T19:30:00Z",
      "status": "TIMED",
      "matchday": 26,
      "homeTeam": {
        "id": 58,
        "name": "Aston Villa FC",
        "shortName": "Aston Villa",
        "crest": "https://crests.football-data.org/58.png"
      },
      "awayTeam": {
        "id": 397,
        "name": "Brighton & Hove Albion FC",
        "shortName": "Brighton Hove",
        "crest": "https://crests.football-data.org/397.png"
      },
      "competition": {
        "id": 2021,
        "name": "Premier League",
        "code": "PL",
        "emblem": "https://crests.football-data.org/PL.png"
      },
      "score": {
        "fullTime": {"home": null, "away": null}
      }
    }
  ]
}
```

**Error Handling:**
```json
{
  "status": "error",
  "message": "Competition 'INVALID' not found. Use GET /competitions to see available competitions."
}
```

---

#### Get Today's Predictions
```bash
GET /predictions/today?fetch_h2h_on_demand=true
```

Returns H2H-enhanced predictions for today's matches with lazy H2H loading.

**Query Parameters:**
- `fetch_h2h_on_demand` (optional, default: true): Fetch H2H data on-demand for today's matches

**Smart Behavior:**
- Lazy H2H loading: Only fetches H2H when predictions are requested
- Rate-limited: Maximum 10 H2H requests per day
- Returns predictions only for matches with H2H data available
- Caches H2H data for 24 hours

**Response:**
```json
{
  "status": "success",
  "count": 6,
  "predictions": [
    {
      "match_id": 538036,
      "match": "Aston Villa FC vs Brighton & Hove Albion FC",
      "competition": "Premier League",
      "competition_code": "PL",
      "utc_date": "2026-02-11T19:30:00Z",
      "home_win_probability": 0.523,
      "home_win_confidence": "MEDIUM",
      "draw_probability": 0.267,
      "draw_confidence": "LOW",
      "away_win_probability": 0.210,
      "away_win_confidence": "LOW",
      "predicted_outcome": "Home Win",
      "goals_prediction": {
        "bet": "Over 2.5",
        "probability": 0.678,
        "confidence": "MEDIUM"
      },
      "btts_probability": 0.687,
      "btts_confidence": "MEDIUM",
      "prediction_method": "H2H + Team Stats",
      "h2h_available": true,
      "h2h_matches_analyzed": 5,
      "created_at": "2026-02-11"
    }
  ]
}
```

---

#### Get Top Picks
```bash
GET /predictions/top-picks?limit=10
```

Returns top-ranked predictions using composite scoring.

**Query Parameters:**
- `limit` (optional, default: 35): Number of top picks to return

---

### Admin Endpoints

Requires `X-API-Key` header with admin API key.

#### Trigger Manual Ingestion (Admin Only)
```bash
GET /fixtures/ingest
X-API-Key: your_admin_key
```

**Note:** This endpoint is now admin-only. Frontend should use `/competitions` and `/matches` endpoints which auto-fetch transparently.

Runs the complete daily pipeline:
1. Ingest competitions
2. Ingest scheduled matches for tracked competitions
3. Update team statistics

**H2H Note:** H2H data is now fetched lazily when `/predictions/today` is called (not during ingestion).

---

#### Database Statistics
```bash
curl http://localhost:8000/database/stats \
  -H "X-API-Key: your_admin_key"
```

Returns comprehensive database statistics with collection protection status.

**Response:**
```json
{
  "competitions": {
    "total": 123,
    "status": "PROTECTED - permanent cache, never cleaned"
  },
  "matches": {
    "total": 757,
    "with_h2h": 41,
    "status": "PROTECTED - smart cached, never cleaned"
  },
  "predictions": {
    "total": 6,
    "status": "Cleanable after 7 days (configurable)"
  },
  "team_stats": {
    "total": 0,
    "status": "Cleanable after 7 days (configurable)"
  }
}
```

---

#### Cleanup Old Records
```bash
curl -X POST http://localhost:8000/database/cleanup \
  -H "X-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'
```

Cleans old records while protecting critical collections.

**Protected Collections (Never Cleaned):**
- `competitions` - Permanent cache
- `matches` - Smart cache with H2H data

**Cleanable Collections:**
- `fixtures` - Legacy data
- `predictions` - Old predictions
- `team_stats` - Outdated statistics

See [CLEANUP_API.md](CLEANUP_API.md) for security best practices.

---

## Frontend Integration Guide

### Step-by-Step Usage

**1. Get Available Competitions**
```bash
GET /competitions
```
- Returns all competitions (auto-fetches if empty)
- Extract `code` field for filtering matches

**2. Get Matches for Selected Competition**
```bash
POST /matches
Content-Type: application/json

{
  "competition_code": "PL",      # From step 1
  "status_filter": "SCHEDULED",
  "date_from": "2026-02-11",
  "date_to": "2026-02-15",
  "limit": 100
}
```
- Auto-fetches matches if empty for that competition
- Filters by status, date range
- No manual ingestion required

**3. Get Predictions**
```bash
GET /predictions/today
```
- Returns H2H-enhanced predictions
- Lazy-loads H2H data on-demand (max 10/day)
- Only returns matches with H2H available

**Example Frontend Flow:**
```javascript
// 1. Load competitions for dropdown
const competitions = await fetch('/competitions').then(r => r.json());

// 2. User selects "Premier League" (code: "PL")
const matches = await fetch('/matches', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    competition_code: 'PL',
    status_filter: 'SCHEDULED',
    date_from: '2026-02-11',
    date_to: '2026-02-15'
  })
}).then(r => r.json());

// 3. Get predictions for today
const predictions = await fetch('/predictions/today').then(r => r.json());
```

### Key Benefits

✅ **No Manual Ingestion** - Endpoints auto-fetch transparently  
✅ **Smart Caching** - Prevents duplicate API calls  
✅ **Source Protection** - Frontend doesn't know about Football-Data.org  
✅ **Rate Limiting** - Built-in protection (10 H2H/day)  
✅ **Fast Load Times** - Only fetch what's needed  
✅ **Clean Separation** - Backend handles data management

---

## Configuration

Edit `app/config/settings.py`:

### Tracked Competitions

```python
TRACKED_COMPETITIONS = ["PL", "PD", "BL1", "CL", "SA", "ELC"]
```

**Competition Codes:**
- `PL` - Premier League (England)
- `ELC` - Championship (England)
- `PD` - La Liga (Spain)
- `BL1` - Bundesliga (Germany)
- `SA` - Serie A (Italy)
- `CL` - Champions League (Europe)
- `BSA` - Série A (Brazil)

### Other Settings

```python
PREDICTION_LIMIT = 30           # Max predictions to return
MAX_FIXTURES = 15               # Max matches for team stats
MAX_DAYS_BACK = 90              # Days to look back for stats
DEFAULT_LIMIT = 35              # Default limit for top picks
```

## Daily Automation

The daily job runs a **simplified 3-step pipeline**:

1. **Ingest competitions** - Fetch available leagues (if not cached)
2. **Ingest matches** - Fetch scheduled matches for tracked competitions (if needed)
3. **Update team stats** - Compute form, goals for/against

**Note:** H2H data is now fetched **lazily** when `/predictions/today` is called, not during ingestion. This prevents overwhelming the API and respects the 10 H2H/day rate limit.

### Manual Execution

```bash
python app/jobs/daily_run.py
```

### Cron Setup

```bash
# Run daily at 6:00 AM
crontab -e

# Add:
0 6 * * * cd /path/to/foo-ball-service && /usr/bin/python3 app/jobs/daily_run.py >> logs/daily_run.log 2>&1
```

## Database Collections

### `competitions`
Stores available competitions/leagues
- **Index**: `code` (unique), `id`
- **Cache**: Permanent (never cleaned)
- **Auto-fetch**: Via GET /competitions if empty

### `matches`
Stores match fixtures with embedded H2H data
- **Indexes**: `id` (unique), `competition.code`, `utcDate`, `status`
- **Cache**: Smart cache per competition (never cleaned)
- **H2H**: Embedded object with 24-hour TTL, max 10 fetches/day
- **Auto-fetch**: Via POST /matches if empty for competition

### `team_stats`
Team performance metrics
- **Index**: `team_id` (unique)
- **Computed from**: Last 15 matches (90 days)
- **Cleanup**: Auto-deleted after 7 days (configurable)

### `predictions`
Daily match predictions with H2H enhancement
- **Indexes**: `match_id`, `created_at`
- **Includes**: H2H availability flag, matches analyzed count
- **Cleanup**: Auto-deleted after 7 days (configurable)

### `fixtures` (Legacy)
Old fixture data from API-Football
- **Status**: Deprecated, maintained for backwards compatibility
- **Cleanup**: Auto-deleted after 7 days (configurable)

## Testing

### Integration Tests

```bash
# Run comprehensive tests
python scripts/test_integration.py
```

Tests:
1. ✅ API Connection
2. ✅ Data Ingestion
3. ✅ Head-to-Head Fetching
4. ✅ Team Statistics
5. ✅ Prediction Generation

### Manual Testing

```bash
# Check database state
python scripts/init_db.py --list

# Verify predictions
python -c "
from app.services.prediction_v2 import get_predictions_today
preds = get_predictions_today()
print(f'{len(preds)} predictions generated')
"
```

## Logging

Logs are stored in the `logs/` directory:
- `logs/app.log` - Application logs
- `logs/api_requests.log` - API request tracking
- `logs/security.log` - Security events

```bash
# View logs in real-time
tail -f logs/app.log

# Search for errors
grep "ERROR" logs/app.log

# Monitor API requests
tail -f logs/api_requests.log
```

See [LOGGING.md](LOGGING.md) for complete documentation.

## Troubleshooting

### No competitions returned
- **First call**: Auto-fetches from source (may take a few seconds)
- **Verify API key**: `echo $FOOTBALL_DATA_API_KEY`
- **Test API**: `curl -H "X-Auth-Token: YOUR_KEY" http://api.football-data.org/v4/competitions`
- **Check logs**: `tail -f logs/app.log`

### No matches returned
- **First call per competition**: Auto-fetches from source
- **Verify competition code**: Use GET /competitions to see valid codes
- **Check logs**: `tail -f logs/app.log` for fetch errors

### Rate limit exceeded (429 errors)
- **H2H limit**: Maximum 10 H2H requests per day (by design)
- **Review logs**: Check `logs/app.log` for H2H fetch attempts
- **Wait**: H2H quota resets daily
- **Upgrade API plan**: Consider paid tier if needed

### No predictions available
- **Run**: `curl http://localhost:8000/predictions/today`
- **H2H required**: Predictions only generated for matches with H2H data
- **Check quota**: May have hit 10 H2H/day limit
- **Verify matches**: Use POST /matches to confirm matches exist

### "Competition not found" error
- **Get valid codes**: `curl http://localhost:8000/competitions`
- **Use exact code**: Must match (case-insensitive, e.g., "PL", "CL")
- **Check tracked list**: See `TRACKED_COMPETITIONS` in settings.py

### Database connection errors
- Confirm MongoDB is running
- Verify `MONGO_URI` in `.env`
- Check IP allowlist (if using MongoDB Atlas)

## Migration from API-Football

This service has been migrated from API-Football to Football-Data.org v4 API. The migration adds:

- Head-to-head predictions (70% H2H + 30% recent form)
- Smart caching to prevent API exhaustion
- Better data structure with embedded H2H
- Improved prediction accuracy

**Backwards Compatibility:**
- Legacy services remain functional
- Old `fixtures` collection still supported
- Can run both systems in parallel

For complete migration guide, see [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## Development Notes

- Predictions use **rule-based algorithms** with H2H enhancement
- ML dependencies exist but not yet integrated with H2H
- Future: ML model training on H2H features
- Architecture: Clean separation of concerns (data sources, services, models)

## Response Format

All endpoints return standardized responses:

**Success with data:**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Retrieved successfully",
  ...
}
```

**Success without data:**
```json
{
  "statusCode": 204,
  "status": "no_data",
  "message": "No predictions available for today",
  ...
}
```

**Error:**
```json
{
  "statusCode": 500,
  "status": "error",
  "message": "Error details"
}
```

## Glossary

| Term | Meaning |
|------|---------|
| **H2H** | Head-to-Head (historical meetings between two teams) |
| **BTTS** | Both Teams To Score (at least 1 goal each) |
| **Over 2.5** | Match will have 3+ total goals |
| **Under 2.5** | Match will have 2 or fewer total goals |
| **Form** | Points per game average (0-3 scale) |
| **TTL** | Time To Live (cache expiration time) |

## Documentation

- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Complete migration documentation
- **[CLEANUP_API.md](CLEANUP_API.md)** - Database management guide
- **[LOGGING.md](LOGGING.md)** - Logging and monitoring guide

## Quick Reference Card

### Essential Endpoints

| Endpoint | Method | Auth required | Purpose |
|---|---|---|---|
| `/health` | GET | No | Service health check |
| `/competitions` | GET | `X-Install-Id` | Get all competitions |
| `/matches` | POST | `X-Install-Id` | Get matches by competition |
| `/predictions/today` | GET | `X-Install-Id` | Get H2H predictions |
| `/predictions/top-picks` | GET | `X-Install-Id` | Get ranked predictions |
| `/fixtures/ingest` | GET | `X-Install-Id` (2 free, then sign-in) | Trigger ingestion pipeline |
| `/auth/firebase` | POST | `X-Install-Id` | Firebase sign-in / upsert user |
| `/user/me` | GET | `X-Install-Id` + `X-Client-Id` | Full user profile (authenticated only) |

### Android Request Headers

```
# Anonymous (before sign-in)
X-Install-Id:   a1b2c3d4-uuid-generated-on-first-install
X-App-Version:  1.0.0

# Authenticated (after POST /auth/firebase succeeds)
X-Install-Id:   a1b2c3d4-uuid-generated-on-first-install
X-App-Version:  1.0.0
X-Client-Id:    <firebase-uid from auth response data.user_id>
```

### Data Protection Rules

| Collection | Status | Cleanup |
|---|---|---|
| `competitions` | 🛡️ PROTECTED | Never |
| `matches` | 🛡️ PROTECTED | Never |
| `users` | 🛡️ PROTECTED | Never |
| `api_usage_logs` | 🛡️ PROTECTED | Never |
| `predictions` | 🧹 Cleanable | After 7 days |
| `team_stats` | 🧹 Cleanable | After 7 days |
| `fixtures` (legacy) | 🧹 Cleanable | After 7 days |

### Rate Limits

- **H2H Requests**: 10 per day (enforced by service)
- **Free Tier**: 10 requests/minute (Football-Data.org)
- **Smart Caching**: Prevents duplicate calls

### Confidence Levels

| Metric | HIGH | MEDIUM | LOW |
|--------|------|--------|-----|
| Goals/BTTS | ≥75% | ≥60% | <60% |
| Outcomes | ≥60% | ≥45% | <45% |

## License

[Add your license here]

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review Football-Data.org API docs: https://www.football-data.org/documentation/api
- Run diagnostics: `python scripts/test_integration.py`
