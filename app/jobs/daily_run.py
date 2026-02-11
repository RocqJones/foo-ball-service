"""
Daily ingestion job for Football-Data.org API.

This job:
1. Ingests competitions (smart caching - only if DB empty)
2. Ingests scheduled matches for tracked competitions (smart caching - only if needed)
3. Updates team statistics
4. H2H data is fetched on-demand when /predictions/today is called (lazy loading)

Run this via cron or scheduler once per day.
"""
from datetime import date
from app.services.ingestion import (
    ingest_competitions,
    ingest_all_tracked_matches
)
from app.services.team_stats_v2 import update_team_stats_for_all_teams
from app.config.settings import settings
from app.utils.logger import logger


def run() -> dict:
    """
    Execute the daily data ingestion pipeline (WITHOUT H2H - that's lazy loaded).
    
    Returns:
        Dictionary with ingestion results
    """
    today = date.today().isoformat()
    results = {
        "date": today,
        "competitions_ingested": 0,
        "matches_ingested": {},
        "teams_updated": 0,
        "errors": [],
        "note": "H2H data is fetched on-demand when /predictions/today is called"
    }
    
    logger.info(f"Starting daily ingestion run for {today}")
    logger.info("Note: H2H data will be fetched on-demand when predictions are requested")
    
    # Step 1: Ingest competitions (smart - only if DB empty)
    try:
        logger.info("Step 1: Ingesting competitions (smart caching)...")
        comp_count = ingest_competitions()
        results["competitions_ingested"] = comp_count
        if comp_count > 0:
            logger.info(f"✓ Ingested {comp_count} new competitions")
        else:
            logger.info(f"✓ Competitions already exist (skipped API call)")
    except Exception as e:
        error_msg = f"Failed to ingest competitions: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    # Step 2: Ingest matches for all tracked competitions (smart - only if needed)
    try:
        logger.info("Step 2: Ingesting matches for tracked competitions (smart caching)...")
        matches_by_comp = ingest_all_tracked_matches()
        results["matches_ingested"] = matches_by_comp
        total_matches = sum(matches_by_comp.values())
        logger.info(f"✓ Ingested {total_matches} total matches across {len(matches_by_comp)} competitions")
    except Exception as e:
        error_msg = f"Failed to ingest matches: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    # Step 3: Update team statistics
    try:
        logger.info("Step 3: Updating team statistics...")
        teams_count = update_team_stats_for_all_teams(
            competition_codes=settings.TRACKED_COMPETITIONS,
            days_back=90,
            max_matches=15
        )
        results["teams_updated"] = teams_count
        logger.info(f"✓ Updated stats for {teams_count} teams")
    except Exception as e:
        error_msg = f"Failed to update team stats: {str(e)}"
        logger.error(error_msg)
        results["errors"].append(error_msg)
    
    # Summary
    logger.info("=" * 60)
    logger.info("DAILY INGESTION SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Date: {today}")
    logger.info(f"Competitions ingested: {results['competitions_ingested']}")
    logger.info(f"Matches ingested: {sum(results['matches_ingested'].values())}")
    logger.info(f"Team stats updated: {results['teams_updated']}")
    logger.info(f"")
    logger.info(f"NOTE: H2H data will be fetched on-demand when /predictions/today is called")
    logger.info(f"      This keeps ingestion fast and only fetches H2H when needed")
    
    if results["errors"]:
        logger.warning(f"Errors encountered: {len(results['errors'])}")
        for error in results["errors"]:
            logger.warning(f"  - {error}")
    else:
        logger.info("✓ Daily ingestion completed successfully!")
    
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    results = run()
    total_matches = sum(results['matches_ingested'].values())
    print(f"\nDaily ingestion completed. {total_matches} matches ingested.")
    print(f"H2H data will be fetched when /predictions/today is called.")

