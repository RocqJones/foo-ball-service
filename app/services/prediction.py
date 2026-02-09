from datetime import date, datetime, timezone, timedelta
from app.db.mongo import get_collection
from app.models.rule_based import predict_match_outcome, predict_over_under, predict_btts
from app.services.ranking import rank_predictions
from app.config.settings import settings
from app.utils.logger import logger
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


def _get_smart_fallback_stats(team_id: int, league_name: str = None) -> dict:
    """
    Generate smarter fallback stats based on league context and team ID.
    
    Uses league-specific baselines and consistent seeding for reproducibility.
    Better than random stats because it reflects league characteristics.
    
    Args:
        team_id: Team ID for consistent seeding
        league_name: League name to determine baseline stats
    
    Returns:
        Dictionary with form, goals_for, goals_against, games_played
    """
    # League-specific baselines (based on real football statistics)
    league_baselines = {
        "Premier League": {"avg_goals": 1.35, "avg_form": 1.45, "variance": 0.4},
        "La Liga": {"avg_goals": 1.25, "avg_form": 1.40, "variance": 0.35},
        "Bundesliga": {"avg_goals": 1.55, "avg_form": 1.50, "variance": 0.45},
        "Serie A": {"avg_goals": 1.20, "avg_form": 1.35, "variance": 0.30},
        "Ligue 1": {"avg_goals": 1.25, "avg_form": 1.38, "variance": 0.35},
        "UEFA Champions League": {"avg_goals": 1.45, "avg_form": 1.70, "variance": 0.40},
        "Championship": {"avg_goals": 1.30, "avg_form": 1.40, "variance": 0.38},
        "DEFAULT": {"avg_goals": 1.30, "avg_form": 1.40, "variance": 0.38}
    }
    
    # Get league baseline or use default
    baseline = league_baselines.get(league_name, league_baselines["DEFAULT"])
    
    # Use team_id as seed for consistency (same team always gets same fallback)
    random.seed(team_id)
    
    # Generate stats around league baseline with variance
    goals_for = max(0.5, random.gauss(baseline["avg_goals"], baseline["variance"]))
    goals_against = max(0.5, random.gauss(baseline["avg_goals"], baseline["variance"]))
    form = max(0.3, min(2.8, random.gauss(baseline["avg_form"], baseline["variance"] * 0.8)))
    
    return {
        "form": round(form, 2),
        "goals_for": round(goals_for, 2),
        "goals_against": round(goals_against, 2),
        "games_played": 5,  # Indicate limited data
        "is_fallback": True
    }


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
    
    logger.info(f"Found {len(fixtures)} fixtures for {date_prefix} after filtering by tracked leagues")

    if not fixtures:
        logger.warning(f"No fixtures found for {date_prefix} in tracked leagues")
        return []

    # Pre-fetch all team stats (one query instead of 2N queries)
    team_ids = set()
    for f in fixtures:
        team_ids.add(f["teams"]["home"]["id"])
        team_ids.add(f["teams"]["away"]["id"])
    
    team_stats_col = get_collection("team_stats")
    team_stats_list = list(team_stats_col.find({"team_id": {"$in": list(team_ids)}}))
    team_stats_map = {ts["team_id"]: ts for ts in team_stats_list}
    
    logger.info(f"Retrieved stats for {len(team_stats_map)}/{len(team_ids)} teams from database")

    predictions = []

    for f in fixtures:
        home = f["teams"]["home"]
        away = f["teams"]["away"]
        league_name = f.get("league", {}).get("name", "Unknown")

        # Get stats from pre-fetched map or use smart fallback
        home_stats = team_stats_map.get(home["id"])
        if not home_stats:
            home_stats = _get_smart_fallback_stats(home["id"], league_name)
            logger.debug(f"Using fallback stats for home team: {home['name']} (ID: {home['id']})")
        
        away_stats = team_stats_map.get(away["id"])
        if not away_stats:
            away_stats = _get_smart_fallback_stats(away["id"], league_name)
            logger.debug(f"Using fallback stats for away team: {away['name']} (ID: {away['id']})")

        # Compute probabilities for all match outcomes (home win, draw, away win)
        home_win_prob, draw_prob, away_win_prob = predict_match_outcome(home_stats, away_stats)
        
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

        # Confidence levels for all outcomes
        home_win_confidence = "HIGH" if home_win_prob >= 0.6 else "MEDIUM" if home_win_prob >= 0.45 else "LOW"
        away_win_confidence = "HIGH" if away_win_prob >= 0.6 else "MEDIUM" if away_win_prob >= 0.45 else "LOW"
        draw_confidence = "HIGH" if draw_prob >= 0.4 else "MEDIUM" if draw_prob >= 0.30 else "LOW"
        btts_confidence = "HIGH" if btts_prob >= 0.75 else "MEDIUM" if btts_prob >= 0.60 else "LOW"

        # Determine the most likely outcome
        outcomes = {
            "home_win": home_win_prob,
            "draw": draw_prob,
            "away_win": away_win_prob
        }
        best_outcome = max(outcomes, key=outcomes.get)
        best_outcome_prob = outcomes[best_outcome]

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
            "league_logo": f["league"].get("logo"),
            "league_flag": f["league"].get("flag"),
            "home_team": home['name'],
            "home_team_logo": home.get("logo"),
            "away_team": away['name'],
            "away_team_logo": away.get("logo"),
            "home_win_probability": round(home_win_prob, 3),
            "home_win_confidence": home_win_confidence,
            "away_win_probability": round(away_win_prob, 3),
            "away_win_confidence": away_win_confidence,
            "draw_probability": round(draw_prob, 3),
            "draw_confidence": draw_confidence,
            "predicted_outcome": best_outcome.replace("_", " ").title(),
            "predicted_outcome_probability": round(best_outcome_prob, 3),
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
        today_str = date.today().isoformat()
        
        # Remove all existing predictions for today's date to prevent duplicates
        # The delete_many operation won't crash if no records exist (deleted_count will be 0)
        delete_result = predictions_col.delete_many({"created_at": today_str})
        print(f"Deleted {delete_result.deleted_count} existing predictions for {today_str}")
        
        bulk_operations = [
            UpdateOne(
                {"fixture_id": pred["fixture_id"]},
                {"$set": pred},
                upsert=True
            )
            for pred in predictions
        ]
        predictions_col.bulk_write(bulk_operations)
        print(f"Saved {len(predictions)} predictions for {today_str}")

    # Return ranked predictions (with configurable limit)
    return rank_predictions(predictions, limit=settings.PREDICTION_LIMIT)
