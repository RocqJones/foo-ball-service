from fastapi import FastAPI
from datetime import date
from app.services.prediction import predict_today, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.analysis import analyze_predictions, get_top_picks
from app.jobs.daily_run import run as daily_run

app = FastAPI(title="Foo Ball Service")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/fixtures/ingest")
def ingest_todays_fixtures():
    """
    Trigger the daily ingestion job to fetch today's fixtures from the API.
    This is equivalent to running: python3 -m app.jobs.daily_run
    """
    daily_run()
    return {
        "status": "success",
        "message": f"Daily ingestion complete. Fixtures for {date.today().isoformat()} have been ingested."
    }

@app.get("/predictions/today")
def get_predictions_today(force_refresh: bool = False):
    """
    Get all predictions for today with ranking.
    
    Args:
        force_refresh: If True, recalculates predictions from fixtures. 
                      If False (default), returns cached predictions if available.
    """
    if force_refresh:
        # Force fresh calculation
        top_predictions = predict_today()
    else:
        # Try to get cached predictions first
        cached_predictions = get_persisted_predictions_today()
        if cached_predictions:
            top_predictions = cached_predictions
        else:
            # No cached predictions, calculate fresh
            top_predictions = predict_today()
    
    return {
        "count": len(top_predictions),
        "predictions": top_predictions
    }

@app.get("/predictions/analysis")
def get_predictions_analysis():
    """
    Get enhanced analysis of today's predictions with pandas insights.
    Always uses the latest predictions from the database.
    """
    # Ensure predictions are up-to-date
    predict_today()  # This updates the database with latest predictions
    
    # Now fetch and analyze
    all_predictions = get_persisted_predictions_today()
    
    if not all_predictions:
        return {
            "status": "no_data",
            "message": "No predictions available for today. Try calling /predictions/today first."
        }
    
    analysis = analyze_predictions(all_predictions)
    return analysis

@app.get("/predictions/top-picks")
def get_predictions_top_picks(limit: int = 10):
    """
    Get top picks based on composite scoring.
    Always uses the latest predictions from the database.
    """
    # Ensure predictions are up-to-date
    predict_today()  # This updates the database with latest predictions
    
    # Now fetch and rank
    all_predictions = get_persisted_predictions_today()
    
    if not all_predictions:
        return {
            "status": "no_data",
            "message": "No predictions available for today. Try calling /predictions/today first.",
            "top_picks": []
        }
    
    top_picks = get_top_picks(all_predictions, limit=limit)
    return {
        "count": len(top_picks),
        "top_picks": top_picks
    }
