from datetime import date
from app.db.mongo import get_collection
from app.models.rule_based import predict_home_win, predict_over_under, predict_btts
from app.services.ranking import rank_predictions
import math

def predict_today():
    fixtures_col = get_collection("fixtures")
    today = date.today().isoformat()

    fixtures = fixtures_col.find({
        "fixture.date": {"$regex": f"^{today}"}
    })

    predictions = []

    for f in fixtures:
        home = f["teams"]["home"]
        away = f["teams"]["away"]

        # Fetch stats from DB if available
        team_stats_col = get_collection("team_stats")
        home_stats = team_stats_col.find_one({"team_id": home["id"]}) or {"form":3, "goals_for":2, "goals_against":1}
        away_stats = team_stats_col.find_one({"team_id": away["id"]}) or {"form":1, "goals_for":1, "goals_against":2}

        # Compute probabilities
        home_win_prob = predict_home_win(home_stats, away_stats)
        over_under_prob = predict_over_under(home_stats, away_stats)
        btts_prob = predict_btts(home_stats, away_stats)

        # Confidence
        home_confidence = "HIGH" if home_win_prob >= 0.8 else "MEDIUM"
        over_under_conf = "HIGH" if over_under_prob >= 0.75 else "MEDIUM"
        btts_conf = "HIGH" if btts_prob >= 0.7 else "MEDIUM"

        # Optional value score placeholder (market probability vs model)
        market_home_prob = f.get("odds", {}).get("home_win", 0.5)  # fallback if missing
        value_score = round(home_win_prob - market_home_prob, 3)

        prediction_doc = {
            "fixture_id": f["fixture"]["id"],
            "match": f"{home['name']} vs {away['name']}",
            "home_win_probability": round(home_win_prob, 3),
            "over_2_5_probability": round(over_under_prob, 3),
            "btts_probability": round(btts_prob, 3),
            "home_win_confidence": home_confidence,
            "over_2_5_confidence": over_under_conf,
            "btts_confidence": btts_conf,
            "value_score": value_score,
            "created_at": date.today().isoformat()
        }

        predictions.append(prediction_doc)

        # Persist prediction to Mongo
        predictions_col = get_collection("predictions")
        predictions_col.update_one(
            {"fixture_id": f["fixture"]["id"]},
            {"$set": prediction_doc},
            upsert=True
        )

    # Return ranked top 10
    return rank_predictions(predictions, limit=10)
