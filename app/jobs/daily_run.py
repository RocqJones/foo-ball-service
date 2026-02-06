from datetime import date
from app.services.ingestion import ingest_fixtures

def run() -> int:
    today = date.today().isoformat()
    fixtures_count = ingest_fixtures(today)
    print(f"Daily ingestion complete: {fixtures_count} fixtures ingested")
    return fixtures_count

if __name__ == "__main__":
    run()
