# Foo Ball Service

## What it does

- **Ingest fixtures** for a given date from API-Football → stores documents in MongoDB `fixtures` collection.
- **Predict today's matches** from stored fixtures:
  - **Match outcome probabilities** with confidence levels (HIGH/MEDIUM/LOW):
    - Home win probability
    - Draw probability
    - Away win probability
    - Plus a `predicted_outcome` field showing the most likely result
  - **Smart over/under 2.5 goals recommendation** (automatically picks best bet: Over or Under)
  - **BTTS (Both Teams To Score)** probability - predicts if both teams will score at least 1 goal each
  - Value score (model probability vs market odds)
- **Pandas-powered analysis** to extract best bets by category
- **Filter by league name** using a configurable allow-list (example: Premier League, UCL).
- Expose results via REST endpoints.

### Prediction Metrics Explained

- **Match outcome probabilities (Home/Draw/Away)**: Likelihood of each result.
  - These three probabilities are normalized to sum to $1.0$ (100%).
  - Home advantage is still baked into the model.
- **Goals Prediction**: Automatically recommends either "Over 2.5" or "Under 2.5" goals based on:
  - Both teams' attacking strength (goals_for)
  - Both teams' defensive weakness (goals_against)
  - Expected total goals in the match
- **BTTS (Both Teams To Score)**: Probability that BOTH teams score at least 1 goal each
  - High probability = Expect both teams to find the net
  - Based on the weakest link principle (minimum scoring potential of both teams)
- **Confidence Levels**:
  - For **Home Win** / **Away Win**:
    - HIGH: ≥ 60%
    - MEDIUM: 45–59%
    - LOW: < 45%
  - For **Draw**:
    - HIGH: ≥ 40%
    - MEDIUM: 30–39%
    - LOW: < 30%
  - For **Goals (Over/Under)** and **BTTS**, the previous HIGH/MEDIUM/LOW thresholds still apply.

It ingests fixtures from the **API-Football** API into **MongoDB**, then generates **rule-based predictions** for today’s matches and serves them via a **FastAPI** API.

> This repo currently focuses on “good enough” automation (scheduled ingestion + predictions API). There’s no GUI—configuration lives in `app/config/settings.py` and/or `.env`.

## Project layout

- `app/main.py` — FastAPI entrypoint
- `app/jobs/daily_run.py` — daily ingestion job (fixtures for today)
- `app/services/ingestion.py` — fixture ingestion logic
- `app/services/prediction.py` — prediction pipeline (reads fixtures → writes predictions)
- `app/services/ranking.py` — ranks predictions
- `app/models/rule_based.py` — rule-based probability functions
- `app/data_sources/api_football.py` — API-Football client
- `app/db/mongo.py` — MongoDB connection helper
- `app/config/settings.py` — configuration

## Prerequisites

- Python 3.11+
- MongoDB (local or remote)
- API-Football API key

## Setup

1) Create & activate a virtualenv

```bash
python3 -m venv venv
source venv/bin/activate
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Create a `.env` file at the repo root

```bash
touch .env
```

Add:

```env
# Required
API_FOOTBALL_KEY=your_key_here

# Optional (defaults shown)
MONGO_URI=mongodb://localhost:27017
DB_NAME=foo_ball_service

# Present but not fully wired through yet
ODDS_API_KEY=
```

## Configuration

### League filtering (no GUI)

Today’s predictions are filtered by league name using this MongoDB clause:

```js
{ "league.name": { $in: ["UEFA Champions League", "Premier League"] } }
```

Update the allow-list in `app/config/settings.py`:

- `settings.TRACKED_LEAGUES`: list of league names to include
- `settings.PREDICTION_LIMIT`: how many ranked predictions to return

## Running the ingestion job

This job ingests **today’s** fixtures into MongoDB:

```bash
python -m app.jobs.daily_run
```

Notes:

- Run from the repo root.
- Using `-m` ensures imports work correctly (package execution).

## Running the API

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

Open the interactive docs:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

### Endpoints

- `GET /health` — basic health check
- `GET /fixtures/ingest` — triggers ingestion for today's fixtures (same as the daily job)
- `GET /predictions/today` — generates + returns ranked predictions for today
- `GET /predictions/analysis` — pandas-powered analysis with best bets by category
- `GET /predictions/top-picks?limit=10` — top picks using composite scoring

Example response shape for `/predictions/today`:

```json
{
  "count": 30,
  "predictions": [{
    "fixture_id": 1482325,
    "match": "Welwalo Adigrat Uni vs Sheger Ketema",
    "league": "Premier League",
    "league_logo": "https://media.api-sports.io/football/leagues/39.png",
    "league_flag": "https://media.api-sports.io/flags/gb.svg",
    "home_team": "Welwalo Adigrat Uni",
    "home_team_logo": "https://media.api-sports.io/football/teams/123.png",
    "away_team": "Sheger Ketema",
    "away_team_logo": "https://media.api-sports.io/football/teams/456.png",
    "home_win_probability": 0.741,
    "home_win_confidence": "HIGH",
    "draw_probability": 0.144,
    "draw_confidence": "LOW",
    "away_win_probability": 0.115,
    "away_win_confidence": "LOW",
    "predicted_outcome": "Home Win",
    "predicted_outcome_probability": 0.741,
    "goals_prediction": {
      "bet": "Under 2.5",
      "probability": 0.682,
      "confidence": "MEDIUM"
    },
    "btts_probability": 0.592,
    "btts_confidence": "MEDIUM",
    "value_score": 0.488,
    "created_at": "2026-01-21"
  }]
}
```

The `/predictions/analysis` endpoint provides:
- `best_home_wins` — top 5 high-confidence home win predictions (includes team/league logos)
- `best_goals_bets` — top 5 over/under 2.5 predictions with clear recommendations (includes team/league logos)
- `best_btts` — top 5 both teams to score predictions (includes team/league logos)
- `best_value_bets` — top 5 predictions with positive value scores (includes team/league logos)
- `summary` — statistics including league distribution, confidence levels, etc.

All prediction endpoints now include visual assets for beautiful frontend displays:
- `league_logo` — League logo URL (e.g., Premier League crest)
- `league_flag` — Country flag URL for the league
- `home_team_logo` — Home team logo/crest URL
- `away_team_logo` — Away team logo/crest URL

## Data & collections

MongoDB database: `settings.DB_NAME`

Collections currently used:

- `fixtures` — raw fixture docs from API-Football (stored with upsert on `fixture_id`)
- `predictions` — stored predictions (upsert on `fixture_id`)
- `team_stats` — **optional**; if present, used for predictions; otherwise, seeded random stats are generated per team

### About team stats fallback

When `team_stats` collection is empty (no historical data), the prediction service generates **seeded random stats** for each team based on their `team_id`. This ensures:

- Predictions are **diverse** (not identical)
- Predictions are **consistent** (same team always gets the same stats until you populate real data)

To populate real stats, you can:
1. Build a backfill job that calls `compute_team_stats_from_fixtures()` (see `app/services/team_stats.py`)
2. Manually insert team performance data into the `team_stats` collection
3. Integrate live team statistics from API-Football

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`

Run scripts as modules from the repo root:

```bash
python -m app.jobs.daily_run
```

### Empty predictions

Common causes:

- You haven’t ingested fixtures for today yet.
- Your `TRACKED_LEAGUES` list doesn’t match the exact league names in fixture docs.
- Fixtures are stored under a different date/time format than expected.

### API-Football errors (401/403)

- Confirm `API_FOOTBALL_KEY` is set in `.env`.
- Restart the process after updating `.env`.

### Mongo connection errors

- Confirm MongoDB is running and `MONGO_URI` is correct.
- If using Mongo Atlas, ensure your IP allow-list and credentials are set.

## Development notes

- Predictions are currently **rule-based** (`app/models/rule_based.py`).
- ML dependencies exist in `requirements.txt` (e.g., scikit-learn, xgboost), but the default `/predictions/today` endpoint uses the rule-based approach.

## Roadmap ideas

- Load `TRACKED_LEAGUES` from `.env` (comma-separated) instead of editing code
- Add a CLI command for ingestion and backfills (date ranges)
- Enrich `team_stats` ingestion and remove fallback defaults
- Add tests (ranking, prediction edge cases)

## Glossary

| Term | Meaning |
|------|---------|
| **BTTS** | Both Teams To Score (at least 1 goal each) |
| **Over 2.5** | Match will have 3 or more total goals |
| **Under 2.5** | Match will have 2 or fewer total goals |
| **HIGH** | High confidence (see thresholds above; differs by metric) |
| **MEDIUM** | Medium confidence (see thresholds above; differs by metric) |
| **LOW** | Low confidence (see thresholds above; differs by metric) |
| **Value Score** | Difference between model probability and market odds |
| **Form** | Team's recent performance (points per game average) |
