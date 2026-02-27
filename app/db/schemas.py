"""
MongoDB schema definitions and index creation for foo-ball-service.

Collections:
- competitions: Football competitions/leagues
- matches: Match fixtures and results
- team_stats: Computed team statistics
- predictions: Match predictions
- fixtures: Legacy fixtures (API-Football)
"""
from pymongo import ASCENDING, DESCENDING
from app.db.mongo import db
from app.utils.logger import logger


def create_indexes():
    """
    Create all necessary indexes for optimal query performance.
    Indexes are created with `background=True` to avoid blocking operations.
    """
    logger.info("Creating database indexes...")
    
    # Competitions collection indexes
    competitions_col = db["competitions"]
    competitions_col.create_index([("code", ASCENDING)], unique=True, background=True)
    competitions_col.create_index([("id", ASCENDING)], background=True)
    logger.info("✓ Created indexes for 'competitions' collection")
    
    # Matches collection indexes
    matches_col = db["matches"]
    matches_col.create_index([("id", ASCENDING)], unique=True, background=True)
    matches_col.create_index([("competition.code", ASCENDING)], background=True)
    matches_col.create_index([("utcDate", ASCENDING)], background=True)
    matches_col.create_index([("status", ASCENDING)], background=True)
    matches_col.create_index([("homeTeam.id", ASCENDING)], background=True)
    matches_col.create_index([("awayTeam.id", ASCENDING)], background=True)
    matches_col.create_index([("h2h.last_updated", ASCENDING)], background=True)
    # Compound index for common queries
    matches_col.create_index([
        ("competition.code", ASCENDING),
        ("utcDate", ASCENDING),
        ("status", ASCENDING)
    ], background=True)
    logger.info("✓ Created indexes for 'matches' collection")
    
    # Team stats collection indexes
    team_stats_col = db["team_stats"]
    team_stats_col.create_index([("team_id", ASCENDING)], unique=True, background=True)
    team_stats_col.create_index([("computed_at", DESCENDING)], background=True)
    logger.info("✓ Created indexes for 'team_stats' collection")
    
    # Predictions collection indexes
    predictions_col = db["predictions"]
    predictions_col.create_index([("match_id", ASCENDING)], background=True)
    predictions_col.create_index([("created_at", DESCENDING)], background=True)
    predictions_col.create_index([
        ("created_at", DESCENDING),
        ("competition", ASCENDING)
    ], background=True)
    logger.info("✓ Created indexes for 'predictions' collection")
    
    # Legacy fixtures collection indexes (for backwards compatibility)
    fixtures_col = db["fixtures"]
    fixtures_col.create_index([("fixture_id", ASCENDING)], background=True)
    fixtures_col.create_index([("fixture.date", ASCENDING)], background=True)
    logger.info("✓ Created indexes for 'fixtures' collection (legacy)")

    # ── Install tracking: users collection ──────────────────────────────────
    users_col = db["users"]
    users_col.create_index(
        [("installation_id", ASCENDING)], unique=True, background=True
    )
    users_col.create_index(
        [("google_id", ASCENDING)],
        unique=True,
        sparse=True,   # allows multiple null google_ids
        background=True,
    )
    logger.info("✓ Created indexes for 'users' collection")

    # ── Install tracking: api_usage_logs collection ─────────────────────────
    logs_col = db["api_usage_logs"]
    logs_col.create_index([("installation_id", ASCENDING)], background=True)
    logs_col.create_index([("endpoint", ASCENDING)], background=True)
    logs_col.create_index([("created_at", DESCENDING)], background=True)
    logger.info("✓ Created indexes for 'api_usage_logs' collection")

    logger.info("All indexes created successfully!")


def drop_all_indexes():
    """
    Drop all indexes except _id (for testing/debugging).
    WARNING: Use with caution in production.
    """
    logger.warning("Dropping all custom indexes...")
    
    collections = ["competitions", "matches", "team_stats", "predictions", "fixtures"]
    
    for col_name in collections:
        col = db[col_name]
        # Get all indexes
        indexes = col.list_indexes()
        
        for index in indexes:
            if index["name"] != "_id_":  # Never drop the _id index
                col.drop_index(index["name"])
                logger.info(f"Dropped index {index['name']} from {col_name}")
    
    logger.warning("All custom indexes dropped!")


if __name__ == "__main__":
    create_indexes()
