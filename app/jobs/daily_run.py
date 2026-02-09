from datetime import date
from app.services.ingestion import ingest_fixtures
from app.config.settings import settings

def run() -> int:
    today = date.today().isoformat()
    fixtures_count = ingest_fixtures(today, timezone=settings.TIMEZONE)
    print(f"Daily ingestion complete: {fixtures_count} fixtures ingested for {today}")
    return fixtures_count

if __name__ == "__main__":
    run()
