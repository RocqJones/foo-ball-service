from datetime import datetime, timedelta, timezone
from app.db.mongo import get_collection
from app.utils.logger import logger


def cleanup_old_records(days: int = 7):
    """
    Delete all records older than the specified number of days.
    
    PROTECTED COLLECTIONS (never cleaned):
    - competitions: Master data, cached permanently for performance
    - matches: Scheduled matches, cached with smart ingestion logic
    
    CLEANED COLLECTIONS:
    - fixtures: Legacy API-Football data (can be re-fetched)
    - predictions: Daily predictions (can be regenerated)
    - team_stats: Team statistics (can be recomputed)
    
    Args:
        days: Number of days to retain. Records older than this will be deleted.
              Default is 7 days.
    
    Returns:
        dict: Summary of deleted records per collection
    """
    # Calculate the cutoff datetime (7 days ago)
    cutoff_datetime = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_datetime_str = cutoff_datetime.isoformat()
    cutoff_date_str = cutoff_datetime.date().isoformat()
    
    logger.info(f"Starting cleanup of records older than {days} days (before {cutoff_datetime_str})")
    logger.info("Protected collections: competitions, matches (will NOT be cleaned)")
    
    results = {
        "cutoff_datetime": cutoff_datetime_str,
        "cutoff_date": cutoff_date_str,
        "days_retained": days,
        "collections_cleaned": {}
    }
    
    # Clean up fixtures collection
    # fixture.date format is typically "2025-01-29T19:00:00+00:00" (ISO datetime string)
    # Use cutoff_datetime_str for accurate comparison with datetime strings
    try:
        fixtures_col = get_collection("fixtures")
        # Delete fixtures where the date is before the cutoff datetime
        delete_result = fixtures_col.delete_many({
            "fixture.date": {"$lt": cutoff_datetime_str}
        })
        results["collections_cleaned"]["fixtures"] = delete_result.deleted_count
        logger.info(f"Deleted {delete_result.deleted_count} fixtures older than {cutoff_datetime_str}")
    except Exception as e:
        logger.error(f"Error cleaning fixtures collection: {str(e)}")
        results["collections_cleaned"]["fixtures"] = {
            "error": str(e)
        }
    
    # Clean up predictions collection
    # created_at format is "2025-01-29" (ISO date string)
    try:
        predictions_col = get_collection("predictions")
        delete_result = predictions_col.delete_many({
            "created_at": {"$lt": cutoff_date_str}
        })
        results["collections_cleaned"]["predictions"] = delete_result.deleted_count
        logger.info(f"Deleted {delete_result.deleted_count} predictions older than {cutoff_date_str}")
    except Exception as e:
        logger.error(f"Error cleaning predictions collection: {str(e)}")
        results["collections_cleaned"]["predictions"] = {
            "error": str(e)
        }
    
    # Clean up team_stats collection
    # If team_stats has a date field, use cutoff_datetime_str for accurate comparison.
    # Expected format: ISO datetime string (e.g., "2025-01-29T19:00:00+00:00")
    try:
        team_stats_col = get_collection("team_stats")
        # Check if team_stats has a date or timestamp field
        sample_doc = team_stats_col.find_one({}, {"created_at": 1, "updated_at": 1, "computed_at": 1})
        date_field = None
        if sample_doc:
            for field_name in ("created_at", "updated_at", "computed_at"):
                if field_name in sample_doc:
                    date_field = field_name
                    break
        if date_field:
            delete_result = team_stats_col.delete_many({
                date_field: {"$lt": cutoff_datetime_str}
            })
            results["collections_cleaned"]["team_stats"] = delete_result.deleted_count
            logger.info(f"Deleted {delete_result.deleted_count} team_stats older than {cutoff_datetime_str} using field '{date_field}'")
        else:
            results["collections_cleaned"]["team_stats"] = "skipped - no date field found"
            logger.info("Skipped team_stats collection - no created_at/updated_at/computed_at timestamp field found")
    except Exception as e:
        logger.error(f"Error cleaning team_stats collection: {str(e)}")
        results["collections_cleaned"]["team_stats"] = {
            "error": str(e)
        }
    
    total_deleted = sum(
        v for v in results["collections_cleaned"].values() 
        if isinstance(v, int)
    )
    results["total_records_deleted"] = total_deleted
    
    logger.info(f"Cleanup complete. Total records deleted: {total_deleted}")
    
    return results


def get_database_stats():
    """
    Get statistics about the database collections including record counts
    and date ranges.
    
    Returns:
        dict: Statistics for each collection including:
        - competitions: Football-Data.org competitions (protected, permanent cache)
        - matches: Football-Data.org matches (protected, smart cached)
        - fixtures: Legacy API-Football fixtures (cleanable)
        - predictions: Daily predictions (cleanable)
        - team_stats: Team statistics (cleanable)
    """
    stats = {}
    
    # NEW: Competitions collection (Football-Data.org)
    try:
        competitions_col = get_collection("competitions")
        competitions_count = competitions_col.count_documents({})
        oldest_comp = competitions_col.find_one(
            sort=[("ingested_at", 1)]
        )
        newest_comp = competitions_col.find_one(
            sort=[("ingested_at", -1)]
        )
        
        stats["competitions"] = {
            "total_count": competitions_count,
            "oldest_ingested": oldest_comp.get("ingested_at") if oldest_comp else None,
            "newest_ingested": newest_comp.get("ingested_at") if newest_comp else None,
            "status": "PROTECTED - permanent cache, never cleaned"
        }
    except Exception as e:
        stats["competitions"] = {"error": str(e)}
    
    # NEW: Matches collection (Football-Data.org)
    try:
        matches_col = get_collection("matches")
        matches_count = matches_col.count_documents({})
        scheduled_count = matches_col.count_documents({"status": {"$in": ["SCHEDULED", "TIMED"]}})
        matches_with_h2h = matches_col.count_documents({"h2h": {"$exists": True}})
        oldest_match = matches_col.find_one(
            sort=[("utcDate", 1)]
        )
        newest_match = matches_col.find_one(
            sort=[("utcDate", -1)]
        )
        
        stats["matches"] = {
            "total_count": matches_count,
            "scheduled_count": scheduled_count,
            "with_h2h_count": matches_with_h2h,
            "oldest_date": oldest_match.get("utcDate") if oldest_match else None,
            "newest_date": newest_match.get("utcDate") if newest_match else None,
            "status": "PROTECTED - smart cached, never cleaned"
        }
    except Exception as e:
        stats["matches"] = {"error": str(e)}
    
    # Legacy: Fixtures collection (API-Football)
    try:
        fixtures_col = get_collection("fixtures")
        fixtures_count = fixtures_col.count_documents({})
        oldest_fixture = fixtures_col.find_one(
            sort=[("fixture.date", 1)]
        )
        newest_fixture = fixtures_col.find_one(
            sort=[("fixture.date", -1)]
        )
        
        stats["fixtures"] = {
            "total_count": fixtures_count,
            "oldest_date": oldest_fixture.get("fixture", {}).get("date") if oldest_fixture else None,
            "newest_date": newest_fixture.get("fixture", {}).get("date") if newest_fixture else None,
            "status": "cleanable - legacy data"
        }
    except Exception as e:
        stats["fixtures"] = {"error": str(e)}
    
    # Predictions collection
    try:
        predictions_col = get_collection("predictions")
        predictions_count = predictions_col.count_documents({})
        oldest_prediction = predictions_col.find_one(
            sort=[("created_at", 1)]
        )
        newest_prediction = predictions_col.find_one(
            sort=[("created_at", -1)]
        )
        
        stats["predictions"] = {
            "total_count": predictions_count,
            "oldest_date": oldest_prediction.get("created_at") if oldest_prediction else None,
            "newest_date": newest_prediction.get("created_at") if newest_prediction else None,
            "status": "cleanable - regenerated daily"
        }
    except Exception as e:
        stats["predictions"] = {"error": str(e)}
    
    # Team stats collection
    try:
        team_stats_col = get_collection("team_stats")
        team_stats_count = team_stats_col.count_documents({})
        
        stats["team_stats"] = {
            "total_count": team_stats_count,
            "status": "cleanable - recomputed from matches"
        }
    except Exception as e:
        stats["team_stats"] = {"error": str(e)}
    
    return stats
