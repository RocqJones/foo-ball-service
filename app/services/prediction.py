from datetime import date, datetime, timezone, timedelta
from app.db.mongo import get_collection
from app.models.rule_based import predict_home_win, predict_over_under, predict_btts
from app.services.ranking import rank_predictions
from app.config.settings import settings
from pymongo import UpdateOne
import math
import random

def get_persisted_predictions_today():
    """
    Retrieve persisted predictions for today from the database.
    This avoids expensive regeneration of predictions on every API call.
    
    Returns:
        List of prediction documents for today. Returns empty list if no predictions
        are found in the database. Callers should handle empty results appropriately
        (e.g., by calling predict_today() first to generate predictions).
    """
    predictions_col = get_collection("predictions")
    today = date.today().isoformat()
    
    predictions = list(predictions_col.find(
        {"created_at": today},
        {"_id": 0}  # Exclude MongoDB's _id field
    ))
    
    return predictions

def predict_today():
    fixtures_col = get_collection("fixtures")
    date_prefix = date.today().strftime("%Y-%m-%d")

    # Build league name and country filters from settings.TRACKED_LEAGUES
    league_names = []
    league_countries = []
    for item in settings.TRACKED_LEAGUES:
        if isinstance(item, str):
            league_names.append(item)
        elif isinstance(item, dict):
            name = item.get("name")
            country = item.get("country")
            if name:
                league_names.append(name)
            if country:
                league_countries.append(country)

    # Build per-league ($and) filters so we match both name AND country 
    seen = set()
    league_entry_filters = []
    for item in settings.TRACKED_LEAGUES:
        if isinstance(item, dict):
            name = item.get("name")
            country = item.get("country")
            key = (name, country)
            if key in seen:
                continue
            seen.add(key)
            if name and country:
                league_entry_filters.append({"$and": [{"league.name": name}, {"league.country": country}]})
            elif name:
                league_entry_filters.append({"league.name": name})
        elif isinstance(item, str):
            if item in seen:
                continue
            seen.add(item)
            league_entry_filters.append({"league.name": item})

    # Filter by date regex AND (one of the league name+country pairs)
    query = {"fixture.date": {"$regex": f"^{date_prefix}"}}
    if league_entry_filters:
        query["$or"] = league_entry_filters

    fixtures = list(fixtures_col.find(query))

    if not fixtures:
        return []

    # Pre-fetch all team stats (one query instead of 2N queries)
    team_ids = set()
    for f in fixtures:
        team_ids.add(f["teams"]["home"]["id"])
        team_ids.add(f["teams"]["away"]["id"])
    
    team_stats_col = get_collection("team_stats")
    team_stats_list = list(team_stats_col.find({"team_id": {"$in": list(team_ids)}}))
    team_stats_map = {ts["team_id"]: ts for ts in team_stats_list}

    predictions = []

    for f in fixtures:
        home = f["teams"]["home"]
        away = f["teams"]["away"]

        # Get stats from pre-fetched map or use seeded random fallback
        home_stats = team_stats_map.get(home["id"])
        if not home_stats:
            # Use seeded randomization based on team_id for consistency
            # Realistic football stats: avg team scores ~1.3 goals/game, concedes ~1.3
            random.seed(home["id"])
            home_stats = {
                "form": round(random.uniform(0.8, 2.5), 2),
                "goals_for": round(random.uniform(0.6, 2.2), 2),    # Average ~1.4
                "goals_against": round(random.uniform(0.6, 2.2), 2)  # Average ~1.4
            }
        
        away_stats = team_stats_map.get(away["id"])
        if not away_stats:
            # Use seeded randomization based on team_id for consistency
            random.seed(away["id"])
            away_stats = {
                "form": round(random.uniform(0.8, 2.5), 2),
                "goals_for": round(random.uniform(0.6, 2.2), 2),    # Average ~1.4
                "goals_against": round(random.uniform(0.6, 2.2), 2)  # Average ~1.4
            }

        # Compute probabilities
        home_win_prob = predict_home_win(home_stats, away_stats)
        over_2_5_prob = predict_over_under(home_stats, away_stats, line=2.5)
        under_2_5_prob = 1 - over_2_5_prob  # Complement probability
        btts_prob = predict_btts(home_stats, away_stats)

        # Determine best over/under bet
        if over_2_5_prob > under_2_5_prob:
            goals_prediction = {
                "bet": "Over 2.5",
                "probability": round(over_2_5_prob, 3),
                "confidence": "HIGH" if over_2_5_prob >= 0.75 else "MEDIUM" if over_2_5_prob >= 0.60 else "LOW"
            }
        else:
            goals_prediction = {
                "bet": "Under 2.5",
                "probability": round(under_2_5_prob, 3),
                "confidence": "HIGH" if under_2_5_prob >= 0.75 else "MEDIUM" if under_2_5_prob >= 0.60 else "LOW"
            }

        # Confidence levels
        home_confidence = "HIGH" if home_win_prob >= 0.8 else "MEDIUM" if home_win_prob >= 0.65 else "LOW"
        btts_confidence = "HIGH" if btts_prob >= 0.75 else "MEDIUM" if btts_prob >= 0.60 else "LOW"

        # Optional value score (market probability vs model) - only when market odds are available
        odds = f.get("odds")
        if odds and "home_win" in odds:
            market_home_prob = odds["home_win"]
            value_score = round(home_win_prob - market_home_prob, 3)
        else:
            market_home_prob = None
            value_score = None

        prediction_doc = {
            "fixture_id": f["fixture"]["id"],
            "match": f"{home['name']} vs {away['name']}",
            "league": f["league"]["name"],
            "home_team": home['name'],
            "away_team": away['name'],
            "home_win_probability": round(home_win_prob, 3),
            "home_win_confidence": home_confidence,
            "goals_prediction": goals_prediction,
            "btts_probability": round(btts_prob, 3),
            "btts_confidence": btts_confidence,
            "value_score": value_score,
            "created_at": date.today().isoformat()
        }

        predictions.append(prediction_doc)

    # Persist all predictions to Mongo using bulk write for better performance
    if predictions:
        predictions_col = get_collection("predictions")
        bulk_operations = [
            UpdateOne(
                {"fixture_id": pred["fixture_id"]},
                {"$set": pred},
                upsert=True
            )
            for pred in predictions
        ]
        predictions_col.bulk_write(bulk_operations)

    # Return ranked predictions (with configurable limit)
    return rank_predictions(predictions, limit=settings.PREDICTION_LIMIT)
