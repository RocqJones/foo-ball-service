# Migration Guide: API-Football → Football-Data.org v2

This guide explains the migration from API-Football to Football-Data.org v2 API.

## Overview

The migration introduces:
- **New data source**: Football-Data.org v2 API
- **New collections**: `competitions`, `matches` (replacing/complementing `fixtures`)
- **Head-to-Head (H2H) predictions**: Enhanced prediction accuracy using historical matchups
- **Daily ingestion guards**: Prevents duplicate API calls and rate limit exhaustion
- **Modular architecture**: Separate services for v1 (legacy) and v2 (new)

---

## Configuration Changes

### Environment Variables

Add these to your `.env` file:

```bash
# Football-Data.org API v2
FOOTBALL_DATA_API_KEY=your_api_key_here
FOOTBALL_DATA_BASE_URL=http://api.football-data.org/v2

# Legacy (optional, for backwards compatibility)
API_FOOTBALL_KEY=your_legacy_key
```

### Settings Updates

`app/config/settings.py` now includes:

```python
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE_URL = "http://api.football-data.org/v2"

# Competition codes instead of league names
TRACKED_COMPETITIONS = ["PL", "PD", "BL1", "CL", "SA", "ELC"]
```

**Competition Codes**:
- `PL` = Premier League (England)
- `PD` = La Liga (Spain)
- `BL1` = Bundesliga (Germany)
- `CL` = Champions League
- `SA` = Serie A (Italy)
- `ELC` = Championship (England)
- `BSA` = Campeonato Brasileiro Série A

---

## Database Changes

### New Collections

1. **`competitions`**
   - Stores available competitions/leagues
   - Indexed by: `code` (unique), `id`

2. **`matches`**
   - Stores match fixtures and results
   - Includes embedded H2H data
   - Indexed by: `id` (unique), `competition.code`, `utcDate`, `status`

3. **`team_stats`** (enhanced)
   - Team performance metrics
   - Indexed by: `team_id` (unique)

4. **`predictions`** (enhanced)
   - Includes `h2h_available` and `prediction_method` fields

### Schema Migration

```json
// New match document structure
{
  "id": 538036,
  "utcDate": "2026-02-11T19:30:00Z",
  "status": "TIMED",
  "competition": {
    "id": 2021,
    "name": "Premier League",
    "code": "PL"
  },
  "homeTeam": {
    "id": 58,
    "name": "Aston Villa FC",
    "crest": "https://crests.football-data.org/58.png"
  },
  "awayTeam": {
    "id": 397,
    "name": "Brighton & Hove Albion FC",
    "crest": "https://crests.football-data.org/397.png"
  },
  "h2h": {
    "last_updated": "2026-02-11",
    "aggregates": {
      "numberOfMatches": 10,
      "totalGoals": 32,
      "homeTeam": {"wins": 4, "draws": 2, "losses": 4},
      "awayTeam": {"wins": 4, "draws": 2, "losses": 4}
    },
    "matches": [...]
  },
  "ingested_at": "2026-02-11",
  "last_ingested_date": "2026-02-11"
}
```

### Initialize Database

```bash
# Create indexes
python scripts/init_db.py

# Or drop and recreate indexes
python scripts/init_db.py --drop-indexes

# List current state
python scripts/init_db.py --list
```

---

## New Services

### Data Source: `football_data_api.py`

```python
from app.data_sources.football_data_api import (
    get_competitions,
    get_scheduled_matches,
    get_head_to_head
)

# Fetch competitions
competitions = get_competitions()

# Fetch scheduled matches for Premier League
data = get_scheduled_matches("PL")

# Fetch H2H for a specific match
h2h = get_head_to_head(match_id=538036, limit=10)
```

### Ingestion: `ingestion.py`

```python
from app.services.ingestion import (
    ingest_competitions,
    ingest_all_tracked_matches,
    fetch_h2h_for_upcoming_matches
)

# Ingest competitions (once per day)
count = ingest_competitions()

# Ingest matches for all tracked competitions
results = ingest_all_tracked_matches()

# Fetch H2H for matches in next 7 days
h2h_count = fetch_h2h_for_upcoming_matches(days_ahead=7)
```

### Predictions: `prediction_v2.py`

```python
from app.services.prediction_v2 import get_predictions_today

# Generate predictions using H2H data
predictions = get_predictions_today(use_h2h=True)
```

### Team Stats: `team_stats_v2.py`

```python
from app.services.team_stats_v2 import (
    compute_team_stats_from_matches,
    update_team_stats_for_all_teams
)

# Compute stats for a single team
stats = compute_team_stats_from_matches(team_id=58)

# Update stats for all teams
count = update_team_stats_for_all_teams()
```

---

## Daily Ingestion Flow

### Updated `daily_run.py`

The daily job now executes:

1. **Ingest competitions** (once per day)
2. **Ingest scheduled matches** for tracked competitions
3. **Fetch H2H data** for upcoming matches (next 7 days)
4. **Update team statistics** from recent matches
5. **Generate predictions** using H2H + team stats

### Deduplication Strategy

- **Competitions**: Only fetched if `ingested_at != today`
- **Matches**: Only fetched if `competition.code` + `ingested_at != today`
- **H2H**: Only fetched if `h2h.last_updated != today`

This prevents unnecessary API calls and rate limit exhaustion.

### Run the Daily Job

```bash
# Manual execution
python app/jobs/daily_run.py

# Or via cron (example: daily at 6 AM)
0 6 * * * cd /path/to/foo-ball-service && python app/jobs/daily_run.py >> logs/daily_run.log 2>&1
```

---

## Prediction Model Updates

### H2H-Based Predictions

The new `rule_based.py` includes H2H-aware functions:

```python
from app.models.rule_based import (
    extract_h2h_features,
    predict_match_outcome_from_h2h,
    predict_over_under_from_h2h,
    predict_btts_from_h2h
)

# Extract H2H features
h2h_features = extract_h2h_features(h2h_data, home_team_id, away_team_id)

# Make H2H-based predictions
home_win, draw, away_win = predict_match_outcome_from_h2h(h2h_features, home_stats, away_stats)
over_prob = predict_over_under_from_h2h(h2h_features, line=2.5)
btts_prob = predict_btts_from_h2h(h2h_features)
```

**Features Extracted from H2H**:
- `home_win_ratio`: Historical win rate for home team
- `away_win_ratio`: Historical win rate for away team
- `draw_ratio`: Historical draw rate
- `avg_goals_per_match`: Average total goals in H2H matches
- `home_avg_goals`: Average goals scored by home team
- `away_avg_goals`: Average goals scored by away team

**Blending Strategy**:
- 70% weight on H2H history
- 30% weight on recent team form (last 15 games)

---

## API Rate Limits

Football-Data.org free tier limits:
- **10 requests per minute**
- **Avoid exhausting quota**: Cache competition/match data for 24h
- **Retry logic**: Exponential backoff (max 3 retries)

### Rate Limit Handling

The client automatically:
1. Logs remaining requests via `X-Requests-Available-Minute` header
2. Retries with exponential backoff on `429 Too Many Requests`
3. Handles `403 Forbidden` (invalid API key or tier restrictions)

---

## Testing the Migration

### 1. Test Database Connection

```bash
python scripts/init_db.py --list
```

### 2. Test API Connection

```python
from app.data_sources.football_data_api import get_competitions

competitions = get_competitions()
print(f"Fetched {len(competitions)} competitions")
```

### 3. Run Ingestion

```bash
python app/jobs/daily_run.py
```

### 4. Generate Predictions

```python
from app.services.prediction_v2 import get_predictions_today

predictions = get_predictions_today()
print(f"Generated {len(predictions)} predictions")
```

---

## Backwards Compatibility

Legacy services remain functional:

- `app/data_sources/api_football.py` (unchanged)
- `app/services/prediction.py` (uses `fixtures` collection)
- `app/services/team_stats.py` (uses `fixtures` collection)

You can gradually migrate by:
1. Running both systems in parallel
2. Comparing prediction accuracy
3. Deprecating legacy system after validation

---

## Troubleshooting

### Issue: "No competitions returned"

**Solution**: Check API key and ensure it's set in `.env`:
```bash
echo $FOOTBALL_DATA_API_KEY
```

### Issue: "Rate limit exceeded"

**Solution**: Reduce ingestion frequency or upgrade API plan.

### Issue: "No H2H data for matches"

**Solution**: Run `fetch_h2h_for_upcoming_matches()` or ensure `daily_run.py` executed successfully.

### Issue: "Predictions use 'Team Stats Only'"

**Solution**: H2H data missing. Check:
```python
from app.db.mongo import get_collection

matches_col = get_collection("matches")
match = matches_col.find_one({"id": 538036})
print(match.get("h2h"))
```

---

## Next Steps

1. **Set up monitoring**: Track API usage, prediction accuracy
2. **A/B testing**: Compare H2H vs non-H2H predictions
3. **Expand competitions**: Add more leagues to `TRACKED_COMPETITIONS`
4. **Automate daily runs**: Set up cron jobs or scheduled tasks
5. **API endpoints**: Update FastAPI routes to use `prediction_v2`

---

## Support

For issues or questions:
- Check logs: `logs/app.log`, `logs/api_requests.log`
- Review Football-Data.org docs: https://www.football-data.org/documentation/api
- GitHub Issues: [your-repo-url]

---

**Migration Completed!** 🎉
