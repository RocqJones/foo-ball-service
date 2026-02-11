# Foo Ball Service

A football match prediction service powered by **Football-Data.org v4 API** with head-to-head (H2H) enhanced predictions.

## What it does

- **Ingest competitions and matches** from Football-Data.org → stores in MongoDB
- **Generate predictions** using historical head-to-head data combined with recent team form:
  - **Match outcome probabilities** (Home/Draw/Away) with confidence levels
  - **Over/Under 2.5 goals** recommendations
  - **BTTS (Both Teams To Score)** predictions
  - **H2H-enhanced accuracy** using past meeting statistics
- **Smart caching** - prevents duplicate API calls with 24-hour TTL
- **Daily automation** - scheduled ingestion and prediction pipeline
- **RESTful API** - expose predictions via FastAPI endpoints

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

⚡ **Smart Caching**
- Competitions cached 24 hours
- Matches cached 24 hours per competition
- H2H data cached 24 hours per match
- Prevents API rate limit exhaustion (10 req/min on free tier)

> **Migration Note**: This service has been migrated from API-Football to Football-Data.org v4 for enhanced prediction capabilities. See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for complete migration documentation.

## Project Structure

```
app/
├── main.py                         # FastAPI application
├── jobs/
│   └── daily_run.py               # Daily ingestion pipeline
├── services/
│   ├── ingestion.py               # Data ingestion with caching
│   ├── prediction_v2.py           # H2H-enhanced predictions
│   ├── team_stats_v2.py           # Team statistics computation
│   └── ranking.py                 # Prediction ranking logic
├── models/
│   └── rule_based.py              # Prediction algorithms
├── data_sources/
│   └── football_data_api.py       # Football-Data.org API client
├── db/
│   ├── mongo.py                   # MongoDB connection
│   └── schemas.py                 # Database indexes
└── config/
    └── settings.py                # Configuration

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
```

### 3. Initialize Database

```bash
# Create indexes
python scripts/init_db.py

# Or run the setup wizard (recommended for first-time)
python scripts/setup_migration.py
```

### 4. Run Initial Ingestion

```bash
# Ingest data and generate predictions
python app/jobs/daily_run.py
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

## API Endpoints

### Public Endpoints

#### Health Check
```bash
GET /health
```

#### Trigger Data Ingestion
```bash
GET /fixtures/ingest
```
Runs the complete daily pipeline:
1. Ingest competitions
2. Ingest scheduled matches
3. Fetch H2H data for upcoming matches
4. Update team statistics
5. Generate predictions

#### Get Today's Predictions
```bash
GET /predictions/today?force_refresh=false
```
Returns ranked predictions for today's matches.

**Query Parameters:**
- `force_refresh` (optional): Set to `true` to regenerate predictions

**Response:**
```json
{
  "statusCode": 200,
  "status": "success",
  "message": "Retrieved successfully",
  "count": 15,
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
      "created_at": "2026-02-11"
    }
  ]
}
```

#### Get Top Picks
```bash
GET /predictions/top-picks?limit=10
```
Returns top-ranked predictions using composite scoring.

**Query Parameters:**
- `limit` (optional, default: 35): Number of top picks to return

### Admin Endpoints

Requires `X-API-Key` header with admin API key.

#### Database Statistics
```bash
curl http://localhost:8000/database/stats \
  -H "X-API-Key: your_admin_key"
```

#### Cleanup Old Records
```bash
curl -X POST http://localhost:8000/database/cleanup \
  -H "X-API-Key: your_admin_key" \
  -H "Content-Type: application/json" \
  -d '{"days": 7}'
```

See [CLEANUP_API.md](CLEANUP_API.md) for security best practices.

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

The daily job runs a 5-step pipeline:

1. **Ingest competitions** - Fetch available leagues (once per day)
2. **Ingest matches** - Fetch scheduled matches for tracked competitions
3. **Fetch H2H data** - Get head-to-head for matches in next 7 days
4. **Update team stats** - Compute form, goals for/against
5. **Generate predictions** - Create H2H-enhanced predictions

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
- Index: `code` (unique), `id`
- TTL: 24 hours

### `matches`
Stores match fixtures with embedded H2H data
- Indexes: `id` (unique), `competition.code`, `utcDate`, `status`
- Embedded `h2h` object with 24-hour TTL

### `team_stats`
Team performance metrics
- Index: `team_id` (unique)
- Computed from last 15 matches (90 days)

### `predictions`
Daily match predictions
- Indexes: `match_id`, `created_at`
- Includes H2H availability flag

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

### No competitions fetched
- Verify API key: `echo $FOOTBALL_DATA_API_KEY`
- Test API: `curl -H "X-Auth-Token: YOUR_KEY" http://api.football-data.org/v4/competitions`
- Check logs: `tail -f logs/app.log`

### Rate limit exceeded
- Review ingestion frequency
- Verify deduplication is working (check `ingested_at` fields)
- Consider upgrading API plan

### No H2H data
- Run: `python -c "from app.services.ingestion import fetch_h2h_for_upcoming_matches; fetch_h2h_for_upcoming_matches()"`
- Verify matches exist in database
- Check logs for API errors

### Predictions use "Team Stats Only"
- H2H data missing for those matches
- Run daily job to fetch H2H: `python app/jobs/daily_run.py`
- Verify `h2h.last_updated` field in match documents

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

## License

[Add your license here]

## Support

For issues or questions:
- Check logs in `logs/` directory
- Review Football-Data.org API docs: https://www.football-data.org/documentation/api
- Run diagnostics: `python scripts/test_integration.py`
