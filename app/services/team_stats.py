"""
Compute enhanced team statistics from historical fixtures with weighted recent form.
"""
from app.config.settings import Settings
from app.db.mongo import get_collection
from datetime import datetime, timedelta
import math


def compute_team_stats_from_fixtures(team_id: int, league_id: int = None, days_back: int = Settings.MAX_DAYS_BACK, max_fixtures: int = Settings.MAX_FIXTURES):
    """
    Compute enhanced stats for a team from recent fixtures with recency weighting.
    
    More recent matches are weighted more heavily to capture current form.
    
    Args:
        team_id: ID of the team to compute stats for
        league_id: Optional league ID to filter fixtures by a specific league
        days_back: Number of days to look back for fixtures (default: 90)
        max_fixtures: Maximum number of most recent fixtures to include in stats calculation (default: 15)
    
    Returns:
        dict with keys: form, goals_for, goals_against, games_played, home_form, away_form
        Returns None if no fixtures found.
    
    Note:
        Uses exponential decay weighting where most recent match has weight 1.0,
        and older matches decay with factor 0.9 per match.
    """
    fixtures_col = get_collection("fixtures")
    
    # Look back N days
    cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
    
    query = {
        "$or": [
            {"teams.home.id": team_id},
            {"teams.away.id": team_id}
        ],
        "fixture.date": {"$gte": cutoff_date},
        "fixture.status.short": {"$in": ["FT", "AET", "PEN"]}  # Only finished matches
    }
    
    if league_id:
        query["league.id"] = league_id
    
    # Sort by date descending to get most recent first
    fixtures = list(fixtures_col.find(query).sort("fixture.date", -1).limit(max_fixtures))
    
    if not fixtures:
        return None
    
    # Weighted statistics using exponential decay
    decay_factor = 0.9  # Recent matches weighted more heavily
    
    weighted_goals_for = 0.0
    weighted_goals_against = 0.0
    weighted_points = 0.0
    total_weight = 0.0
    
    # Separate tracking for home/away performance
    home_points = 0
    home_games = 0
    away_points = 0
    away_games = 0
    
    games = len(fixtures)
    
    for i, f in enumerate(fixtures):
        # Weight decreases for older matches
        weight = decay_factor ** i
        total_weight += weight
        
        is_home = f["teams"]["home"]["id"] == team_id
        
        goals_for = f["goals"]["home"] if is_home else f["goals"]["away"]
        goals_against = f["goals"]["away"] if is_home else f["goals"]["home"]
        
        # Handle None values
        goals_for = goals_for if goals_for is not None else 0
        goals_against = goals_against if goals_against is not None else 0
        
        weighted_goals_for += (goals_for * weight)
        weighted_goals_against += (goals_against * weight)
        
        # Points: 3 for win, 1 for draw, 0 for loss
        if goals_for > goals_against:
            points = 3
        elif goals_for == goals_against:
            points = 1
        else:
            points = 0
            
        weighted_points += (points * weight)
        
        # Track home/away form separately
        if is_home:
            home_points += points
            home_games += 1
        else:
            away_points += points
            away_games += 1
    
    # Calculate weighted averages
    avg_goals_for = weighted_goals_for / total_weight if total_weight > 0 else 0
    avg_goals_against = weighted_goals_against / total_weight if total_weight > 0 else 0
    form = weighted_points / total_weight if total_weight > 0 else 0
    
    # Calculate home/away form (points per game)
    home_form = home_points / home_games if home_games > 0 else None
    away_form = away_points / away_games if away_games > 0 else None
    
    return {
        "team_id": team_id,
        "form": round(form, 2),
        "goals_for": round(avg_goals_for, 2),
        "goals_against": round(avg_goals_against, 2),
        "games_played": games,
        "home_form": round(home_form, 2) if home_form is not None else None,
        "away_form": round(away_form, 2) if away_form is not None else None,
        "computed_at": datetime.now().isoformat(),
        "league_id": league_id
    }
