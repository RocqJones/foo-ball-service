from app.data_sources.api_football import get_fixtures
from app.db.mongo import get_collection

def ingest_fixtures(date: str):
    fixtures_col = get_collection("fixtures")
    fixtures = get_fixtures(date)

    # Remove all existing fixtures for this date to prevent duplicates
    # The delete_many operation won't crash if no records exist (deleted_count will be 0)
    delete_result = fixtures_col.delete_many({"fixture.date": {"$regex": f"^{date}"}})
    print(f"Deleted {delete_result.deleted_count} existing fixtures for {date}")
    
    # Insert all new fixtures
    for fixture in fixtures:
        fixtures_col.update_one(
            {"fixture_id": fixture["fixture"]["id"]},
            {"$set": fixture},
            upsert=True
        )
