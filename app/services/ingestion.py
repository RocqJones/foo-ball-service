from app.data_sources.api_football import get_fixtures
from app.db.mongo import get_collection

def ingest_fixtures(date: str) -> int:
    """
    Ingest fixtures for a given date.
    
    Args:
        date: Date string in ISO format (YYYY-MM-DD)
    
    Returns:
        Number of fixtures ingested
    """
    fixtures_col = get_collection("fixtures")
    fixtures = get_fixtures(date)

    # Remove all existing fixtures for this date to prevent duplicates
    # The delete_many operation won't crash if no records exist (deleted_count will be 0)
    delete_result = fixtures_col.delete_many({"fixture.date": {"$regex": f"^{date}"}})
    print(f"Deleted {delete_result.deleted_count} existing fixtures for {date}")
    
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
