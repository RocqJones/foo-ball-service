from datetime import datetime, timedelta, timezone
from app.db.mongo import get_collection
from app.utils.logger import logger


def cleanup_old_records(days: int = 7):
    """
    Delete all records older than the specified number of days.
    
    Args:
        days: Number of days to retain. Records older than this will be deleted.
              Default is 7 days.
    
    Returns:
        dict: Summary of deleted records per collection
    """
    # Calculate the cutoff datetime (7 days ago)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_datetime_str = cutoff_date.isoformat()
    cutoff_date_str = cutoff_date.date().isoformat()
    
    logger.info(f"Starting cleanup of records older than {days} days (before {cutoff_datetime_str})")
    
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
    # If team_stats has a date field, use cutoff_datetime_str for accurate comparison
    try:
        team_stats_col = get_collection("team_stats")
        # Check if team_stats has a date or timestamp field
        sample_doc = team_stats_col.find_one({}, {"created_at": 1, "updated_at": 1})
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
        dict: Statistics for each collection
    """
    stats = {}
    
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
            "newest_date": newest_fixture.get("fixture", {}).get("date") if newest_fixture else None
        }
    except Exception as e:
        stats["fixtures"] = {"error": str(e)}
    
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
            "newest_date": newest_prediction.get("created_at") if newest_prediction else None
        }
    except Exception as e:
        stats["predictions"] = {"error": str(e)}
    
    try:
        team_stats_col = get_collection("team_stats")
        team_stats_count = team_stats_col.count_documents({})
        
        stats["team_stats"] = {
            "total_count": team_stats_count
        }
    except Exception as e:
        stats["team_stats"] = {"error": str(e)}
    
    return stats
