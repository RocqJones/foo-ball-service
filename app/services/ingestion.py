from app.data_sources.api_football import get_fixtures
from app.db.mongo import get_collection
from app.config.settings import settings
from app.utils.logger import logger

def ingest_fixtures(date: str, timezone: str = None) -> int:
    """
    Ingest fixtures for a given date.
    
    Args:
        date: Date string in ISO format (YYYY-MM-DD)
        timezone: Timezone string (defaults to settings.TIMEZONE)
    
    Returns:
        Number of fixtures ingested
    """
    if timezone is None:
        timezone = settings.TIMEZONE
        
    fixtures_col = get_collection("fixtures")
    
    # Fetch fixtures with timezone
    logger.info(f"Fetching fixtures for {date} with timezone {timezone}")
    fixtures = get_fixtures(date, timezone=timezone)
    
    logger.info(f"API returned {len(fixtures)} total fixtures for {date}")

    # Remove all existing fixtures for this date to prevent duplicates
    # The delete_many operation won't crash if no records exist (deleted_count will be 0)
    delete_result = fixtures_col.delete_many({"fixture.date": {"$regex": f"^{date}"}})
    logger.info(f"Deleted {delete_result.deleted_count} existing fixtures for {date}")
    
    # Insert all new fixtures (we'll filter by league during prediction, not ingestion)
    # This allows us to have all data available and adjust league filters without re-ingesting
    ingested_count = 0
    for fixture in fixtures:
        # Add metadata for easier debugging
        fixture["ingested_at"] = date
        
        result = fixtures_col.update_one(
            {"fixture.id": fixture["fixture"]["id"]},
            {"$set": fixture},
            upsert=True
        )
        if result.upserted_id or result.modified_count > 0:
            ingested_count += 1
    
    logger.info(f"Successfully ingested {ingested_count} fixtures for {date}")
    return ingested_count
