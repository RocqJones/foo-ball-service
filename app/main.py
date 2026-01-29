from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from datetime import date
from app.config.settings import Settings
from app.services.prediction import predict_today, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.analysis import analyze_predictions, get_top_picks
from app.jobs.daily_run import run as daily_run

app = FastAPI(title="Foo Ball Service")

@app.get("/health")
def health():
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "statusCode": 200,
            "status": "success",
            "message": "Service is healthy"
        }
    )

@app.get("/fixtures/ingest")
def ingest_todays_fixtures():
    """
    Trigger the daily ingestion job to fetch today's fixtures from the API.
    This is equivalent to running: python3 -m app.jobs.daily_run
    """
    try:
        daily_run()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": f"Daily ingestion complete. Fixtures for {date.today().isoformat()} have been ingested."
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Ingestion failed: {str(e)}"
            }
        )

@app.get("/predictions/today")
def get_predictions_today(force_refresh: bool = False):
    """
    Get all predictions for today with ranking.
    
    Args:
        force_refresh: If True, recalculates predictions from fixtures. 
                      If False (default), returns cached predictions if available.
    """
    try:
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
        
        if not top_predictions:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "statusCode": 204,
                    "status": "no_data",
                    "message": "No predictions available for today. No fixtures found for tracked leagues.",
                    "count": 0,
                    "predictions": []
                }
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": "Retrieved successfully",
                "count": len(top_predictions),
                "predictions": top_predictions
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Failed to generate predictions: {str(e)}",
                "count": 0,
                "predictions": []
            }
        )

@app.get("/predictions/analysis")
def get_predictions_analysis():
    """
    Get enhanced analysis of today's predictions with pandas insights.
    Always uses the latest predictions from the database.
    """
    try:
        # Ensure predictions are up-to-date
        predict_today()  # This updates the database with latest predictions
        
        # Now fetch and analyze
        all_predictions = get_persisted_predictions_today()
        
        if not all_predictions:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "statusCode": 204,
                    "status": "no_data",
                    "message": "No predictions available for today. No fixtures found for tracked leagues."
                }
            )
        
        analysis = analyze_predictions(all_predictions)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": "Retrieved successfully",
                **analysis
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Failed to analyze predictions: {str(e)}"
            }
        )

@app.get("/predictions/top-picks")
def get_predictions_top_picks(limit: int = Settings.DEFAULT_LIMIT):
    """
    Get top picks based on composite scoring.
    Always uses the latest predictions from the database.
    """
    try:
        # Ensure predictions are up-to-date
        predict_today()  # This updates the database with latest predictions
        
        # Now fetch and rank
        all_predictions = get_persisted_predictions_today()
        
        if not all_predictions:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "statusCode": 204,
                    "status": "no_data",
                    "message": "No predictions available for today. No fixtures found for tracked leagues.",
                    "count": 0,
                    "top_picks": []
                }
            )
        
        top_picks = get_top_picks(all_predictions, limit=limit)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": "Retrieved successfully",
                "count": len(top_picks),
                "top_picks": top_picks
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Failed to get top picks: {str(e)}",
                "count": 0,
                "top_picks": []
            }
        )
