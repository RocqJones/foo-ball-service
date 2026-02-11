"""
Compute team statistics from Football-Data.org matches.

This service computes:
- Team form (average points per game)
- Goals scored per game
- Goals conceded per game
- Recent match performance
"""
from typing import Optional, Dict, Any
from app.db.mongo import get_collection
from datetime import datetime, timedelta, timezone
from app.config.settings import Settings
from app.utils.logger import logger


def compute_team_stats_from_matches(
    team_id: int,
    competition_code: Optional[str] = None,
    days_back: int = Settings.MAX_DAYS_BACK,
    max_matches: int = Settings.MAX_FIXTURES
) -> Optional[Dict[str, Any]]:
    """
    Compute team statistics from recent matches in the new matches collection.
    
    Args:
        team_id: ID of the team
        competition_code: Optional competition code filter (e.g., 'PL', 'CL')
        days_back: Number of days to look back (default: 90)
        max_matches: Maximum number of matches to analyze (default: 15)
    
    Returns:
        Dictionary with keys:
        - team_id: int
        - form: float (0-3 scale, average points per game)
        - goals_for: float (average goals scored per game)
        - goals_against: float (average goals conceded per game)
        - games_played: int
        - competition_code: str (if filtered)
        - computed_at: str (ISO timestamp)
        
        Returns None if no finished matches found.
    """
    matches_col = get_collection("matches")
    
    # Calculate cutoff date
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    
    # Build query
    query = {
        "$or": [
            {"homeTeam.id": team_id},
            {"awayTeam.id": team_id}
        ],
        "utcDate": {"$gte": cutoff_date},
        "status": "FINISHED"
    }
    
    if competition_code:
        query["competition.code"] = competition_code
    
    # Fetch and sort matches
    matches = list(
        matches_col.find(query)
        .sort("utcDate", -1)
        .limit(max_matches)
    )
    
    if not matches:
        logger.warning(f"No finished matches found for team {team_id}")
        return None
    
    total_goals_for = 0
    total_goals_against = 0
    points = 0
    games = len(matches)
    
    for match in matches:
        is_home = match["homeTeam"]["id"] == team_id
        
        # Extract score
        score = match.get("score", {})
        full_time = score.get("fullTime", {})
        
        goals_for = full_time.get("home", 0) if is_home else full_time.get("away", 0)
        goals_against = full_time.get("away", 0) if is_home else full_time.get("home", 0)
        
        # Handle None values
        if goals_for is None:
            goals_for = 0
        if goals_against is None:
            goals_against = 0
        
        total_goals_for += goals_for
        total_goals_against += goals_against
        
        # Calculate points
        if goals_for > goals_against:
            points += 3
        elif goals_for == goals_against:
            points += 1
    
    # Compute averages
    form = points / games if games > 0 else 0
    avg_goals_for = total_goals_for / games if games > 0 else 0
    avg_goals_against = total_goals_against / games if games > 0 else 0
    
    stats = {
        "team_id": team_id,
        "form": round(form, 2),
        "goals_for": round(avg_goals_for, 2),
        "goals_against": round(avg_goals_against, 2),
        "games_played": games,
        "computed_at": datetime.now(timezone.utc).isoformat()
    }
    
    if competition_code:
        stats["competition_code"] = competition_code
    
    logger.info(f"Computed stats for team {team_id}: {games} games, form={stats['form']}")
    
    return stats


def update_team_stats_for_all_teams(
    competition_codes: Optional[list] = None,
    days_back: int = Settings.MAX_DAYS_BACK,
    max_matches: int = Settings.MAX_FIXTURES
) -> int:
    """
    Update team statistics for all teams that have recent matches.
    
    Args:
        competition_codes: Optional list of competition codes to filter by
        days_back: Number of days to look back
        max_matches: Maximum number of matches per team
    
    Returns:
        Number of teams updated
    """
    matches_col = get_collection("matches")
    team_stats_col = get_collection("team_stats")
    
    # Calculate cutoff date
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    
    # Build query for finished matches
    query = {
        "utcDate": {"$gte": cutoff_date},
        "status": "FINISHED"
    }
    
    if competition_codes:
        query["competition.code"] = {"$in": competition_codes}
    
    # Get all unique team IDs
    matches = list(matches_col.find(query))
    
    team_ids = set()
    for match in matches:
        team_ids.add(match["homeTeam"]["id"])
        team_ids.add(match["awayTeam"]["id"])
    
    if not team_ids:
        logger.info("No teams found with recent matches")
        return 0
    
    logger.info(f"Updating stats for {len(team_ids)} teams...")
    
    updated_count = 0
    
    for team_id in team_ids:
        try:
            stats = compute_team_stats_from_matches(
                team_id,
                competition_code=None,
                days_back=days_back,
                max_matches=max_matches
            )
            
            if stats:
                # Upsert team stats
                team_stats_col.update_one(
                    {"team_id": team_id},
                    {"$set": stats},
                    upsert=True
                )
                updated_count += 1
        
        except Exception as e:
            logger.error(f"Error updating stats for team {team_id}: {str(e)}")
            continue
    
    logger.info(f"Updated stats for {updated_count} teams")
    
    return updated_count


# Legacy function for backwards compatibility
def compute_team_stats_from_fixtures(
    team_id: int,
    league_id: Optional[int] = None,
    days_back: int = Settings.MAX_DAYS_BACK,
    max_fixtures: int = Settings.MAX_FIXTURES
) -> Optional[Dict[str, Any]]:
    """
    Legacy function for computing team stats from old fixtures collection.
    
    Args:
        team_id: ID of the team
        league_id: Optional league ID filter
        days_back: Number of days to look back
        max_fixtures: Maximum number of fixtures to analyze
    
    Returns:
        Team statistics dictionary or None
    """
    fixtures_col = get_collection("fixtures")
    
    cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
    
    query = {
        "$or": [
            {"teams.home.id": team_id},
            {"teams.away.id": team_id}
        ],
        "fixture.date": {"$gte": cutoff_date},
        "fixture.status.short": {"$in": ["FT", "AET", "PEN"]}
    }
    
    if league_id:
        query["league.id"] = league_id
    
    fixtures = list(fixtures_col.find(query).sort("fixture.date", -1).limit(max_fixtures))
    
    if not fixtures:
        return None
    
    total_goals_for = 0
    total_goals_against = 0
    points = 0
    games = len(fixtures)
    
    for f in fixtures:
        is_home = f["teams"]["home"]["id"] == team_id
        
        goals_for = f["goals"]["home"] if is_home else f["goals"]["away"]
        goals_against = f["goals"]["away"] if is_home else f["goals"]["home"]
        
        total_goals_for += goals_for or 0
        total_goals_against += goals_against or 0
        
        if goals_for > goals_against:
            points += 3
        elif goals_for == goals_against:
            points += 1
    
    form = points / games if games > 0 else 0
    
    return {
        "team_id": team_id,
        "form": round(form, 2),
        "goals_for": round(total_goals_for / games, 2) if games > 0 else 0,
        "goals_against": round(total_goals_against / games, 2) if games > 0 else 0,
        "games_played": games,
        "computed_at": datetime.now().isoformat()
    }
