from fastapi import FastAPI, status, Body, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from datetime import date
from typing import Annotated
from app.config.settings import Settings
from app.services.prediction_v2 import get_predictions_today as predict_today_v2, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.cleanup import cleanup_old_records, get_database_stats
from app.jobs.daily_run import run as daily_run
from app.middleware import APILoggingMiddleware
from app.utils.logger import logger
from app.security.auth import verify_admin_key

app = FastAPI(title="Foo Ball Service")

# Add API logging middleware for security and monitoring
app.add_middleware(APILoggingMiddleware)

# Custom exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with consistent response format including statusCode
    """
    errors = exc.errors()
    
    # Extract the first error for a clear message
    first_error = errors[0] if errors else {}
    field_name = " -> ".join(str(loc) for loc in first_error.get("loc", []))
    error_msg = first_error.get("msg", "Validation error")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "statusCode": 422,
            "status": "error",
            "message": f"Validation error: {error_msg}",
            "field": field_name,
            "details": errors
        }
    )

# Custom exception handler for HTTPExceptions
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handle HTTP exceptions with consistent response format including statusCode
    """
    # If detail is already a dict with error_code, use it
    if isinstance(exc.detail, dict):
        content = {
            "statusCode": exc.status_code,
            "status": "error",
            **exc.detail
        }
    else:
        content = {
            "statusCode": exc.status_code,
            "status": "error",
            "message": exc.detail
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Foo Ball Service starting up...")
    logger.info("Application startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")

@app.get("/health")
def health():
    logger.debug("Health check requested")
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
    Trigger the daily data ingestion pipeline (competitions + matches only).
    
    This endpoint runs:
    1. Ingest competitions from Football-Data.org (smart caching - only if DB empty)
    2. Ingest scheduled matches for tracked competitions (smart caching - only if needed)
    3. Update team statistics from recent matches
    
    NOTE: H2H data is fetched on-demand when /predictions/today is called (lazy loading).
          This keeps ingestion fast and only fetches H2H when predictions are actually needed.
    
    Returns:
        Summary of ingestion results including:
        - competitions_ingested: Number of competitions updated
        - matches_ingested: Dict of matches per competition
        - teams_updated: Number of team stats updated
        - note: Reminder that H2H is lazy-loaded
        - errors: List of any errors encountered
    """
    try:
        today = date.today().isoformat()
        logger.info(f"Starting manual ingestion run for {today}")
        
        results = daily_run()
        
        total_matches = sum(results.get('matches_ingested', {}).values())
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": f"Daily ingestion complete for {today}",
                "date": today,
                "summary": {
                    "competitions": results.get('competitions_ingested', 0),
                    "matches": total_matches,
                    "h2h_datasets": results.get('h2h_fetched', 0),
                    "teams_updated": results.get('teams_updated', 0),
                    "predictions": results.get('predictions_generated', 0)
                },
                "details": results,
                "errors": results.get('errors', [])
            }
        )
    except Exception as e:
        logger.error(f"Daily run failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Ingestion failed: {str(e)}"
            }
        )

@app.get("/predictions/today")
def get_predictions_today_endpoint(force_refresh: bool = False):
    """
    Get predictions for today's matches with H2H enhancement (lazy-loaded).
    
    **LAZY LOADING:** This endpoint automatically fetches H2H data for today's matches
    if not already cached. This ensures predictions always have the latest H2H data
    while keeping the /fixtures/ingest endpoint fast.
    
    Predictions combine:
    - Historical head-to-head data (70% weight) - fetched on-demand if missing
    - Recent team form and statistics (30% weight)
    
    Predictions include:
    - Match outcome probabilities (Home/Draw/Away)
    - Over/Under 2.5 goals recommendations
    - Both Teams To Score (BTTS) predictions
    - Confidence levels (HIGH/MEDIUM/LOW)
    - Prediction method indicator (H2H + Team Stats or Team Stats Only)
    
    Args:
        force_refresh: If True, regenerates predictions from latest data. 
                      If False (default), returns cached predictions if available.
    
    Returns:
        JSON response with ranked predictions for today's matches
    """
    try:
        if force_refresh:
            # Force fresh calculation (includes lazy H2H fetch)
            top_predictions = predict_today_v2(use_h2h=True, fetch_h2h_on_demand=True)
        else:
            # Try to get cached predictions first
            cached_predictions = get_persisted_predictions_today()
            if cached_predictions:
                top_predictions = cached_predictions
            else:
                # No cached predictions, calculate fresh (includes lazy H2H fetch)
                top_predictions = predict_today_v2(use_h2h=True, fetch_h2h_on_demand=True)
        
        if not top_predictions:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "statusCode": 204,
                    "status": "no_data",
                    "message": "No predictions available for today. No fixtures found for tracked competitions.",
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
        logger.error(f"Failed to generate predictions: {str(e)}", exc_info=True)
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

@app.get("/predictions/top-picks")
def get_predictions_top_picks_endpoint(limit: int = Settings.DEFAULT_LIMIT):
    """
    Get top-ranked predictions using composite scoring.
    
    Top picks are selected based on:
    - Prediction confidence
    - Outcome probability
    - Historical H2H data quality
    
    This endpoint always uses the latest predictions with H2H enhancement.
    
    Args:
        limit: Maximum number of top picks to return (default: 35)
    
    Returns:
        JSON response with top-ranked predictions
    """
    try:
        # Generate fresh predictions with H2H
        all_predictions = predict_today_v2(use_h2h=True)
        
        if not all_predictions:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "statusCode": 204,
                    "status": "no_data",
                    "message": "No predictions available for today. No fixtures found for tracked competitions.",
                    "count": 0,
                    "top_picks": []
                }
            )
        
        # Rank and limit
        top_picks = all_predictions[:limit] if len(all_predictions) > limit else all_predictions
        
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
        logger.error(f"Failed to get top picks: {str(e)}", exc_info=True)
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

@app.post("/database/cleanup", dependencies=[Depends(verify_admin_key)])
def cleanup_database(days: Annotated[int, Body(ge=1, embed=True)] = 7):
    """
    Delete all records older than the specified number of days.
    This helps manage database storage by removing old data.
    
    **Authentication Required**: This endpoint requires admin authentication.
    Include the admin API key in the X-API-Key header.
    
    Request Body:
        {
            "days": 7  // Number of days to retain (default: 7, must be >= 1)
        }
    
    Args:
        days: Number of days to retain. Records older than this will be deleted.
              For example, days=7 keeps only the last 7 days of data.
              Common values: 7, 15, 30, 90 days.
              Must be at least 1.
    
    Returns:
        Summary of deleted records per collection
    
    Examples:
        POST /database/cleanup
        Headers: X-API-Key: your-admin-api-key
        Body: {"days": 7}   # Clean records older than 7 days
        
        POST /database/cleanup
        Headers: X-API-Key: your-admin-api-key
        Body: {"days": 15}  # Clean records older than 15 days
        
        POST /database/cleanup
        Headers: X-API-Key: your-admin-api-key
        Body: {"days": 30}  # Clean records older than 30 days
        
        POST /database/cleanup
        Headers: X-API-Key: your-admin-api-key
        Body: {"days": 90}  # Clean records older than 90 days
    """
    try:
        logger.info(f"Cleanup requested with days={days}")
        
        result = cleanup_old_records(days=days)
        logger.info(f"Cleanup completed successfully: {result.get('total_records_deleted', 0)} records deleted")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": f"Successfully cleaned up records older than {days} days",
                **result
            }
        )
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Cleanup failed: {str(e)}"
            }
        )

@app.get("/database/stats", dependencies=[Depends(verify_admin_key)])
def get_db_statistics():
    """
    Get statistics about the database collections including record counts
    and date ranges. Useful for monitoring database size before cleanup.
    
    **Authentication Required**: This endpoint requires admin authentication.
    Include the admin API key in the X-API-Key header.
    
    Returns:
        Statistics for each collection (fixtures, predictions, team_stats)
    """
    try:
        stats = get_database_stats()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "statusCode": 200,
                "status": "success",
                "message": "Database statistics retrieved successfully",
                "stats": stats
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "statusCode": 500,
                "status": "error",
                "message": f"Failed to retrieve statistics: {str(e)}"
            }
        )

