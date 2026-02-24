from fastapi import FastAPI, status, Body, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import Annotated, Optional, Sequence
import html
from app.config.settings import Settings
from app.services.prediction_v2 import get_predictions_today as predict_today_v2, get_persisted_predictions_today
from app.services.ranking import rank_predictions
from app.services.cleanup import cleanup_old_records, get_database_stats
from app.jobs.daily_run import run as daily_run
from app.middleware import APILoggingMiddleware
from app.utils.logger import logger
from app.security.auth import verify_admin_key
from app.legal_content import (
    PRIVACY_POLICY_SECTIONS,
    TERMS_AND_CONDITIONS_SECTIONS,
    LegalSection,
)

app = FastAPI(title="Foo Ball Service")


# ==========================================================================
# Public browser pages (non-API) - Privacy Policy & Terms
# ==========================================================================

_LEGAL_PAGE_CSS = """
    :root { color-scheme: dark; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; background: #0b1220; color: #e6edf3; }
    a { color: #7dd3fc; text-decoration: underline; }
    .wrap { max-width: 980px; margin: 0 auto; padding: 32px 20px 56px; }
    header { margin-bottom: 18px; }
    .brand { font-weight: 700; letter-spacing: 0.2px; color: #cbd5e1; font-size: 14px; text-transform: uppercase; }
    h1 { margin: 10px 0 6px; font-size: 34px; line-height: 1.15; }
    .subtitle { margin: 0; color: #a8b3cf; }
    .card { background: rgba(255,255,255,0.06); border: 1px solid rgba(148,163,184,0.23); border-radius: 14px; padding: 18px 18px; margin: 16px 0; }
    h2 { margin: 0 0 10px; font-size: 18px; color: #e2e8f0; }
    p { margin: 10px 0; color: #d6deea; }
    ul { margin: 10px 0 0; padding-left: 20px; }
    li { margin: 7px 0; color: #d6deea; }
    .meta { display:flex; gap:12px; flex-wrap:wrap; margin-top: 10px; color:#a8b3cf; font-size: 14px; }
    .pill { background: rgba(125,211,252,0.10); border: 1px solid rgba(125,211,252,0.25); padding: 4px 10px; border-radius: 999px; }
    footer { margin-top: 26px; color:#94a3b8; font-size: 13px; }
    .divider { height: 1px; background: rgba(148,163,184,0.18); margin: 14px 0; }
"""


def _render_legal_page(title: str, updated_date: str, sections: Sequence[LegalSection]) -> str:
    """Render a simple, accessible HTML page for legal text."""
    safe_title = html.escape(title, quote=True)
    safe_updated_date = html.escape(updated_date, quote=True)

    sections_html = []
    for s in sections:
        safe_heading = html.escape(s.heading, quote=True)

        bullets = "".join(
            f"<li>{html.escape(str(b), quote=True)}</li>" for b in (s.bullets or [])
        )

        body = s.body
        body_html = f"<p>{html.escape(body, quote=True)}</p>" if body else ""
        ul_html = f"<ul>{bullets}</ul>" if bullets else ""

        sections_html.append(
            """
            <section class="card">
                            <h2>{heading}</h2>
              {body_html}
              {ul_html}
            </section>
            """.format(
                                heading=safe_heading,
                body_html=body_html,
                ul_html=ul_html,
            )
        )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{safe_title} | Foo Ball Service</title>
    <style>{_LEGAL_PAGE_CSS}</style>
  </head>
  <body>
    <div class="wrap">
      <header>
        <div class="brand">Foo Ball Service</div>
                <h1>{safe_title}</h1>
        <p class="subtitle">This page is provided for transparency and compliance. It’s readable in any browser.</p>
        <div class="meta">
                    <span class="pill">Last updated: {safe_updated_date}</span>
          <span class="pill"><a href="/health">Service status</a></span>
        </div>
      </header>
      <div class="divider"></div>
      {"".join(sections_html)}
      <footer>
        <div class="divider"></div>
        <div>Questions? Contact the service owner/administrator for support and privacy inquiries.</div>
      </footer>
    </div>
  </body>
</html>"""


@app.get("/privacy", include_in_schema=False, response_class=HTMLResponse)
def privacy_policy_page():
    updated_date = date.today().isoformat()
    html = _render_legal_page("Privacy Policy", updated_date, PRIVACY_POLICY_SECTIONS)
    return html


@app.get("/terms", include_in_schema=False, response_class=HTMLResponse)
def terms_and_conditions_page():
    updated_date = date.today().isoformat()
    html = _render_legal_page("Terms & Conditions", updated_date, TERMS_AND_CONDITIONS_SECTIONS)
    return html

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

# ============================================================================
# PUBLIC ENDPOINTS - Smart Auto-Fetch from Source
# ============================================================================

@app.get("/competitions")
async def get_competitions():
    """
    Get all available competitions.
    
    Smart auto-fetch logic:
    - First checks if competitions exist in database
    - If empty, automatically fetches from source (transparent to FE)
    - Returns competitions with clean response (no source implementation details)
    
    Frontend Usage:
    - Use this to get competition list for filters/dropdowns
    - Extract 'code' field to use in POST /matches
    
    Returns:
        {
            "status": "success",
            "count": 6,
            "competitions": [
                {
                    "code": "PL",
                    "name": "Premier League",
                    "emblem": "https://...",
                    "area": {"name": "England", "code": "ENG"},
                    "currentSeason": {...}
                }
            ]
        }
    """
    try:
        from app.db.mongo import get_collection
        from app.services.ingestion import ingest_competitions
        
        competitions_col = get_collection("competitions")
        
        # Check if we have competitions in DB
        existing_count = competitions_col.count_documents({})
        
        # Auto-fetch if empty (transparent to FE)
        if existing_count == 0:
            logger.info("No competitions in DB, auto-fetching from source...")
            ingest_result = ingest_competitions()
            if not ingest_result.get("success"):
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "error",
                        "message": "Failed to fetch competitions from source",
                        "details": ingest_result.get("error")
                    }
                )
            logger.info(f"Auto-fetched {ingest_result.get('inserted', 0)} competitions")
        
        # Get competitions from DB (clean response, no source details)
        competitions = list(competitions_col.find(
            {},
            {
                "_id": 0,
                "code": 1,
                "name": 1,
                "type": 1,
                "emblem": 1,
                "area": 1,
                "currentSeason": 1,
                "numberOfAvailableSeasons": 1
            }
        ).sort("name", 1))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "count": len(competitions),
                "competitions": competitions
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get competitions: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Failed to retrieve competitions"
            }
        )


class MatchesRequest(BaseModel):
    """Request model for POST /matches"""
    competition_code: str
    status_filter: Optional[str] = None  # SCHEDULED, TIMED, FINISHED, LIVE
    date_from: Optional[str] = None  # YYYY-MM-DD
    date_to: Optional[str] = None  # YYYY-MM-DD
    limit: Optional[int] = 100


@app.post("/matches")
async def get_matches(request: MatchesRequest):
    """
    Get matches for a specific competition (smart auto-fetch).
    
    Smart auto-fetch logic:
    - Checks if matches exist for the competition code
    - If empty, automatically fetches from source using competition code
    - Avoids duplicates and unnecessary source calls
    - Returns clean response (no source implementation details)
    
    Request Body:
        {
            "competition_code": "PL",          // Required: from /competitions
            "status_filter": "SCHEDULED",      // Optional: SCHEDULED, TIMED, FINISHED, LIVE
            "date_from": "2026-02-11",         // Optional: YYYY-MM-DD
            "date_to": "2026-02-15",           // Optional: YYYY-MM-DD
            "limit": 100                       // Optional: default 100, max 500
        }
    
    Response:
        {
            "status": "success",
            "count": 38,
            "matches": [
                {
                    "id": 538036,
                    "utcDate": "2026-02-14T15:00:00Z",
                    "status": "SCHEDULED",
                    "homeTeam": {"name": "Arsenal FC"},
                    "awayTeam": {"name": "Liverpool FC"},
                    "competition": {"code": "PL", "name": "Premier League"}
                }
            ]
        }
    """
    try:
        from app.db.mongo import get_collection
        from app.services.ingestion import ingest_matches_for_competition
        
        competition_code = request.competition_code.upper()
        matches_col = get_collection("matches")
        competitions_col = get_collection("competitions")
        
        # Validate competition exists
        competition = competitions_col.find_one({"code": competition_code})
        if not competition:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "status": "error",
                    "message": f"Competition '{competition_code}' not found. Use GET /competitions to see available competitions."
                }
            )
        
        # Check if we have matches for this competition
        existing_count = matches_col.count_documents({"competition.code": competition_code})
        
        # Auto-fetch if empty (transparent to FE)
        if existing_count == 0:
            logger.info(f"No matches for {competition_code} in DB, auto-fetching from source...")
            ingest_result = ingest_matches_for_competition(competition_code)
            if not ingest_result.get("success"):
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "status": "error",
                        "message": f"Failed to fetch matches for {competition_code}",
                        "details": ingest_result.get("error")
                    }
                )
            logger.info(f"Auto-fetched {ingest_result.get('inserted', 0)} matches for {competition_code}")
        
        # Build query for filtering
        query = {"competition.code": competition_code}
        
        if request.status_filter:
            statuses = [s.strip().upper() for s in request.status_filter.split(",")]
            query["status"] = {"$in": statuses}
        
        if request.date_from or request.date_to:
            date_query = {}
            if request.date_from:
                date_query["$gte"] = f"{request.date_from}T00:00:00Z"
            if request.date_to:
                date_query["$lte"] = f"{request.date_to}T23:59:59Z"
            query["utcDate"] = date_query
        
        # Limit validation
        limit = min(request.limit or 100, 500)
        
        # Get matches from DB (clean response, no H2H data)
        matches = list(matches_col.find(
            query,
            {
                "_id": 0,
                "id": 1,
                "utcDate": 1,
                "status": 1,
                "matchday": 1,
                "stage": 1,
                "competition": 1,
                "season": 1,
                "homeTeam": 1,
                "awayTeam": 1,
                "score": 1
                # h2h excluded - too large for list view
            }
        ).sort("utcDate", 1).limit(limit))
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "success",
                "count": len(matches),
                "competition": {
                    "code": competition_code,
                    "name": competition.get("name")
                },
                "matches": matches
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get matches: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "message": "Failed to retrieve matches"
            }
        )

# ============================================================================
# ADMIN ENDPOINTS (Authentication Required)
# ============================================================================

@app.post("/database/cleanup", dependencies=[Depends(verify_admin_key)])
def cleanup_database(days: Annotated[int, Body(ge=1, embed=True)] = 7):
    """
    Delete all records older than the specified number of days.
    This helps manage database storage by removing old data.
    
    **PROTECTED COLLECTIONS (never cleaned):**
    - competitions: Master data, cached permanently for performance
    - matches: Scheduled matches, cached with smart ingestion logic
    
    **CLEANED COLLECTIONS:**
    - fixtures: Legacy API-Football data (can be re-fetched)
    - predictions: Daily predictions (can be regenerated)
    - team_stats: Team statistics (can be recomputed)
    
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

