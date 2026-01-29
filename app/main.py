from fastapi import FastAPI, status, Body, Depends
from fastapi.responses import JSONResponse
from datetime import date
from typing import Annotated
from app.config.settings import Settings
from app.services.prediction import predict_today, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.analysis import analyze_predictions, get_top_picks
from app.services.cleanup import cleanup_old_records, get_database_stats
from app.jobs.daily_run import run as daily_run
from app.middleware import APILoggingMiddleware
from app.utils.logger import logger
from app.auth import verify_admin_key

app = FastAPI(title="Foo Ball Service")

# Add API logging middleware for security and monitoring
app.add_middleware(APILoggingMiddleware)

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

