"""
Ingestion service for Football-Data.org API v4.

This module handles:
- Daily competition ingestion
- Scheduled match ingestion
- Head-to-head data caching
- Deduplication logic to prevent unnecessary API calls
"""
from datetime import datetime, date, timezone
from typing import List, Dict, Any, Optional
from app.data_sources.football_data_api import (
    get_competitions,
    get_scheduled_matches,
    get_head_to_head
)
from app.db.mongo import get_collection
from app.config.settings import settings
from app.utils.logger import logger


def _get_today_iso() -> str:
    """Get today's date in ISO format."""
    return date.today().isoformat()


def _already_ingested_today(collection_name: str) -> bool:
    """
    Check if data has already been ingested today for a collection.
    
    Args:
        collection_name: Name of the collection to check
    
    Returns:
        True if data exists with today's date, False otherwise
    """
    col = get_collection(collection_name)
    today = _get_today_iso()
    
    # Check if any document exists with today's ingestion date
    exists = col.find_one({
        "$or": [
            {"ingested_at": today},
            {"last_ingested_date": today}
        ]
    })
    
    return exists is not None


def ingest_competitions() -> int:
    """
    Ingest all available competitions from Football-Data.org.
    Only runs once per day to prevent unnecessary API calls.
    
    Returns:
        Number of competitions ingested/updated
    """
    today = _get_today_iso()
    competitions_col = get_collection("competitions")
    
    # Check if competitions already exist in DB
    existing_count = competitions_col.count_documents({})
    if existing_count > 0:
        logger.info(f"Found {existing_count} competitions already in database. Skipping API call.")
        # Update last_ingested_date for existing competitions
        competitions_col.update_many(
            {},
            {"$set": {"last_ingested_date": today}}
        )
        return 0
    
    logger.info("Fetching competitions from Football-Data.org...")
    
    try:
        competitions = get_competitions()
        
        if not competitions:
            logger.warning("No competitions returned from API")
            return 0
        
        ingested_count = 0
        
        for comp in competitions:
            # Prepare competition document
            comp_doc = {
                "id": comp.get("id"),
                "code": comp.get("code"),
                "name": comp.get("name"),
                "type": comp.get("type"),
                "emblem": comp.get("emblem"),
                "area": comp.get("area"),
                "currentSeason": comp.get("currentSeason"),
                "numberOfAvailableSeasons": comp.get("numberOfAvailableSeasons"),
                "plan": comp.get("plan"),
                "lastUpdated": comp.get("lastUpdated"),
                "ingested_at": today,
                "last_ingested_date": today
            }
            
            # Upsert by competition code
            result = competitions_col.update_one(
                {"code": comp.get("code")},
                {"$set": comp_doc},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                ingested_count += 1
        
        logger.info(f"Successfully ingested {ingested_count} competitions")
        return ingested_count
    
    except Exception as e:
        logger.error(f"Failed to ingest competitions: {str(e)}")
        raise


def ingest_matches_for_competition(competition_code: str) -> int:
    """
    Ingest scheduled matches for a specific competition.
    Only runs once per day per competition.
    
    Args:
        competition_code: Competition code (e.g., 'PL', 'CL')
    
    Returns:
        Number of matches ingested/updated
    """
    today = _get_today_iso()
    matches_col = get_collection("matches")
    
    # Check if we have upcoming matches for this competition already
    upcoming_query = {
        "competition.code": competition_code,
        "status": {"$in": ["SCHEDULED", "TIMED"]},
        "utcDate": {"$gte": datetime.now(timezone.utc).isoformat()}
    }
    existing_upcoming = matches_col.count_documents(upcoming_query)
    
    # Check if we've already ingested this competition's matches today
    ingested_today = matches_col.find_one({
        "competition.code": competition_code,
        "ingested_at": today
    })
    
    if existing_upcoming > 0 and ingested_today:
        logger.info(f"Found {existing_upcoming} upcoming matches for {competition_code} already ingested today. Skipping.")
        return 0
    
    logger.info(f"Fetching scheduled matches for {competition_code}...")
    
    try:
        data = get_scheduled_matches(competition_code)
        matches = data.get("matches", [])
        
        if not matches:
            logger.info(f"No scheduled matches found for {competition_code}")
            return 0
        
        ingested_count = 0
        
        for match in matches:
            # Prepare match document
            match_doc = {
                "id": match.get("id"),
                "utcDate": match.get("utcDate"),
                "status": match.get("status"),
                "matchday": match.get("matchday"),
                "stage": match.get("stage"),
                "group": match.get("group"),
                "lastUpdated": match.get("lastUpdated"),
                "competition": match.get("competition"),
                "season": match.get("season"),
                "area": match.get("area"),
                "homeTeam": match.get("homeTeam"),
                "awayTeam": match.get("awayTeam"),
                "score": match.get("score"),
                "referees": match.get("referees", []),
                "ingested_at": today,
                "last_ingested_date": today
            }
            
            # Upsert by match ID
            result = matches_col.update_one(
                {"id": match.get("id")},
                {"$set": match_doc},
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                ingested_count += 1
        
        logger.info(f"Successfully ingested {ingested_count} matches for {competition_code}")
        return ingested_count
    
    except Exception as e:
        logger.error(f"Failed to ingest matches for {competition_code}: {str(e)}")
        # Don't raise - continue with other competitions
        return 0


def ingest_all_tracked_matches() -> Dict[str, int]:
    """
    Ingest scheduled matches for all tracked competitions.
    
    Returns:
        Dictionary mapping competition codes to number of matches ingested
    """
    results = {}
    
    for comp_code in settings.TRACKED_COMPETITIONS:
        try:
            count = ingest_matches_for_competition(comp_code)
            results[comp_code] = count
        except Exception as e:
            logger.error(f"Error ingesting {comp_code}: {str(e)}")
            results[comp_code] = 0
    
    total = sum(results.values())
    logger.info(f"Total matches ingested across all competitions: {total}")
    
    return results


def fetch_and_cache_h2h(match_id: int, limit: int = 10) -> Optional[Dict[str, Any]]:
    """
    Fetch head-to-head data for a match and cache it in the match document.
    Only fetches if:
    - h2h field is missing, OR
    - h2h_last_updated is not today
    
    Args:
        match_id: Match ID
        limit: Number of past H2H matches to fetch (default: 10)
    
    Returns:
        H2H data dictionary or None if fetch fails
    """
    today = _get_today_iso()
    matches_col = get_collection("matches")
    
    # Check if match exists
    match = matches_col.find_one({"id": match_id})
    
    if not match:
        logger.warning(f"Match {match_id} not found in database")
        return None
    
    # Check if H2H is already cached for today
    h2h_data = match.get("h2h")
    if h2h_data and h2h_data.get("last_updated") == today:
        logger.info(f"H2H for match {match_id} already cached today. Skipping.")
        return h2h_data
    
    logger.info(f"Fetching H2H data for match {match_id}...")
    
    try:
        h2h_response = get_head_to_head(match_id, limit)
        
        # Prepare H2H data structure
        h2h_doc = {
            "last_updated": today,
            "aggregates": h2h_response.get("aggregates", {}),
            "matches": h2h_response.get("matches", []),
            "resultSet": h2h_response.get("resultSet", {})
        }
        
        # Update match document with H2H data
        matches_col.update_one(
            {"id": match_id},
            {"$set": {"h2h": h2h_doc}}
        )
        
        logger.info(f"Successfully cached H2H data for match {match_id}")
        return h2h_doc
    
    except Exception as e:
        logger.error(f"Failed to fetch H2H for match {match_id}: {str(e)}")
        return None


def fetch_h2h_for_upcoming_matches(days_ahead: int = 7, max_per_day: int = 10) -> int:
    """
    Fetch and cache H2H data for upcoming matches within N days.
    Only fetches H2H if not already cached today.
    LIMITS to max_per_day to stay within API rate limits.
    
    Args:
        days_ahead: Number of days to look ahead (default: 7)
        max_per_day: Maximum H2H requests per day (default: 10)
    
    Returns:
        Number of H2H datasets fetched
    """
    matches_col = get_collection("matches")
    today = _get_today_iso()
    
    # Count how many H2H requests we've made today
    h2h_today_count = matches_col.count_documents({
        "h2h.last_updated": today
    })
    
    if h2h_today_count >= max_per_day:
        logger.info(f"Already fetched {h2h_today_count} H2H today. Limit is {max_per_day}. Skipping.")
        return 0
    
    remaining_quota = max_per_day - h2h_today_count
    logger.info(f"H2H quota: {h2h_today_count}/{max_per_day} used. Remaining: {remaining_quota}")
    
    # Calculate cutoff date
    from datetime import timedelta
    cutoff_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
    
    # Find upcoming matches without today's H2H data
    # Prioritize matches happening sooner
    query = {
        "status": {"$in": ["SCHEDULED", "TIMED"]},
        "utcDate": {
            "$gte": datetime.now(timezone.utc).isoformat(),
            "$lte": cutoff_date
        },
        "$or": [
            {"h2h": {"$exists": False}},
            {"h2h.last_updated": {"$ne": today}}
        ]
    }
    
    # Sort by date (soonest first) and limit to remaining quota
    matches = list(matches_col.find(query).sort("utcDate", 1).limit(remaining_quota))
    
    if not matches:
        logger.info("No upcoming matches need H2H data")
        return 0
    
    logger.info(f"Found {len(matches)} matches needing H2H data (fetching up to {remaining_quota})")
    
    fetched_count = 0
    
    # CRITICAL: Only fetch up to remaining_quota
    for i, match in enumerate(matches):
        # Double-check we haven't exceeded limit (in case of concurrent requests)
        current_count = h2h_today_count + fetched_count
        if current_count >= max_per_day:
            logger.warning(f"Reached daily H2H limit ({max_per_day}). Stopping.")
            break
            
        try:
            h2h = fetch_and_cache_h2h(match["id"])
            if h2h:
                fetched_count += 1
                logger.info(f"H2H progress: {current_count + 1}/{max_per_day} | Match {i+1}/{len(matches)}")
        except Exception as e:
            logger.error(f"Error fetching H2H for match {match['id']}: {str(e)}")
            continue
    
    total_today = h2h_today_count + fetched_count
    logger.info(f"Successfully fetched H2H for {fetched_count} matches (Total today: {total_today}/{max_per_day})")
    return fetched_count


def fetch_h2h_for_todays_matches(max_per_day: int = 10) -> int:
    """
    Fetch H2H data ONLY for today's matches (lazy loading for predictions).
    This is called on-demand when /predictions/today endpoint is hit.
    
    Args:
        max_per_day: Maximum H2H requests per day (default: 10)
    
    Returns:
        Number of H2H datasets fetched
    """
    matches_col = get_collection("matches")
    today = _get_today_iso()
    
    # Count how many H2H requests we've made today (global limit)
    h2h_today_count = matches_col.count_documents({
        "h2h.last_updated": today
    })
    
    if h2h_today_count >= max_per_day:
        logger.info(f"Already fetched {h2h_today_count} H2H today. Limit is {max_per_day}. Skipping.")
        return 0
    
    remaining_quota = max_per_day - h2h_today_count
    logger.info(f"H2H quota for today's matches: {h2h_today_count}/{max_per_day} used. Remaining: {remaining_quota}")
    
    # Find TODAY's matches without H2H data
    query = {
        "utcDate": {
            "$gte": f"{today}T00:00:00Z",
            "$lt": f"{today}T23:59:59Z"
        },
        "status": {"$in": ["SCHEDULED", "TIMED"]},
        "$or": [
            {"h2h": {"$exists": False}},
            {"h2h.last_updated": {"$ne": today}}
        ]
    }
    
    # Get today's matches needing H2H (limit to remaining quota)
    matches = list(matches_col.find(query).limit(remaining_quota))
    
    if not matches:
        logger.info("All of today's matches already have H2H data")
        return 0
    
    logger.info(f"Found {len(matches)} of today's matches needing H2H data (fetching up to {remaining_quota})")
    
    fetched_count = 0
    
    # Fetch H2H for today's matches (respecting daily limit)
    for i, match in enumerate(matches):
        # Double-check we haven't exceeded limit
        current_count = h2h_today_count + fetched_count
        if current_count >= max_per_day:
            logger.warning(f"Reached daily H2H limit ({max_per_day}). Stopping.")
            break
            
        try:
            h2h = fetch_and_cache_h2h(match["id"])
            if h2h:
                fetched_count += 1
                logger.info(f"H2H for today's match: {current_count + 1}/{max_per_day} | {i+1}/{len(matches)}")
        except Exception as e:
            logger.error(f"Error fetching H2H for match {match['id']}: {str(e)}")
            continue
    
    total_today = h2h_today_count + fetched_count
    logger.info(f"Fetched H2H for {fetched_count} of today's matches (Total H2H today: {total_today}/{max_per_day})")
    return fetched_count


# Legacy function for backwards compatibility
def ingest_fixtures(date: str) -> int:
    """
    Legacy function for API-Football fixtures ingestion.
    Kept for backwards compatibility.
    
    Args:
        date: Date string in ISO format (YYYY-MM-DD)
    
    Returns:
        Number of fixtures ingested
    """
    from app.data_sources.api_football import get_fixtures
    
    fixtures_col = get_collection("fixtures")
    fixtures = get_fixtures(date)

    # Remove all existing fixtures for this date to prevent duplicates
    delete_result = fixtures_col.delete_many({"fixture.date": {"$regex": f"^{date}"}})
    logger.info(f"Deleted {delete_result.deleted_count} existing fixtures for {date}")
    
    # Insert all new fixtures
    ingested_count = 0
    for fixture in fixtures:
        result = fixtures_col.update_one(
            {"fixture_id": fixture["fixture"]["id"]},
            {"$set": fixture},
            upsert=True
        )
        if result.upserted_id or result.modified_count > 0:
            ingested_count += 1
    
    return ingested_count
