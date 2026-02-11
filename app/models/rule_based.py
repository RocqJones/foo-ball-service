"""
Rule-based prediction model using head-to-head statistics.

This model uses historical head-to-head data and team statistics to predict:
- Match outcome (home win, draw, away win)
- Over/Under goals
- Both teams to score (BTTS)
"""
import math
from typing import Dict, Any, Optional, Tuple

# Default fallback values for goals statistics when team data is unavailable
# 1.5 goals represents a reasonable average for both scoring and conceding in football:
# - It's slightly above 1.0 (which would be very defensive)
# - It's slightly below 2.0 (which would be very attacking)
# - This neutral value avoids biasing predictions toward high or low scoring outcomes
DEFAULT_GOALS_FOR = 1.5
DEFAULT_GOALS_AGAINST = 1.5


def sigmoid(x: float) -> float:
    """Sigmoid activation function for probability conversion."""
    return 1 / (1 + math.exp(-x))


def extract_h2h_features(h2h_data: Optional[Dict[str, Any]], home_team_id: int, away_team_id: int) -> Dict[str, float]:
    """
    Extract features from head-to-head data.
    
    Args:
        h2h_data: H2H data dictionary from match document
        home_team_id: ID of the home team
        away_team_id: ID of the away team
    
    Returns:
        Dictionary with H2H features:
        - home_win_ratio: Proportion of wins for home team in H2H
        - away_win_ratio: Proportion of wins for away team in H2H
        - draw_ratio: Proportion of draws in H2H
        - avg_goals_per_match: Average total goals in H2H matches
        - home_avg_goals: Average goals scored by home team in H2H
        - away_avg_goals: Average goals scored by away team in H2H
    """
    # Default neutral features if no H2H data
    if not h2h_data:
        return {
            "home_win_ratio": 0.33,
            "away_win_ratio": 0.33,
            "draw_ratio": 0.34,
            "avg_goals_per_match": 2.5,
            "home_avg_goals": 1.25,
            "away_avg_goals": 1.25,
            "h2h_matches_count": 0
        }
    
    aggregates = h2h_data.get("aggregates", {})
    matches = h2h_data.get("matches", [])
    
    num_matches = aggregates.get("numberOfMatches", 0)
    
    if num_matches == 0:
        return {
            "home_win_ratio": 0.33,
            "away_win_ratio": 0.33,
            "draw_ratio": 0.34,
            "avg_goals_per_match": 2.5,
            "home_avg_goals": 1.25,
            "away_avg_goals": 1.25,
            "h2h_matches_count": 0
        }
    
    # Extract aggregate stats
    # Note: The aggregates show wins/draws/losses from each team's perspective
    home_team_data = aggregates.get("homeTeam", {})
    away_team_data = aggregates.get("awayTeam", {})
    
    # Get wins, draws, losses (these are already counted correctly in the API response)
    home_wins = home_team_data.get("wins", 0)
    home_draws = home_team_data.get("draws", 0)
    away_wins = away_team_data.get("wins", 0)
    
    total_goals = aggregates.get("totalGoals", 0)
    
    # Calculate ratios
    home_win_ratio = home_wins / num_matches if num_matches > 0 else 0.33
    away_win_ratio = away_wins / num_matches if num_matches > 0 else 0.33
    draw_ratio = home_draws / num_matches if num_matches > 0 else 0.34
    avg_goals_per_match = total_goals / num_matches if num_matches > 0 else 2.5
    
    # Calculate average goals per team from actual match data
    home_total_goals = 0
    away_total_goals = 0
    
    for match in matches:
        if match.get("status") == "FINISHED":
            score = match.get("score", {})
            full_time = score.get("fullTime", {})
            
            # Identify which team was home/away in this H2H match
            match_home_id = match.get("homeTeam", {}).get("id")
            match_away_id = match.get("awayTeam", {}).get("id")
            
            home_goals = full_time.get("home", 0) or 0
            away_goals = full_time.get("away", 0) or 0
            
            # Accumulate goals from the perspective of the current match's teams
            if match_home_id == home_team_id:
                home_total_goals += home_goals
                away_total_goals += away_goals
            elif match_home_id == away_team_id:
                away_total_goals += home_goals
                home_total_goals += away_goals
    
    home_avg_goals = home_total_goals / num_matches if num_matches > 0 else 1.25
    away_avg_goals = away_total_goals / num_matches if num_matches > 0 else 1.25
    
    return {
        "home_win_ratio": home_win_ratio,
        "away_win_ratio": away_win_ratio,
        "draw_ratio": draw_ratio,
        "avg_goals_per_match": avg_goals_per_match,
        "home_avg_goals": home_avg_goals,
        "away_avg_goals": away_avg_goals,
        "h2h_matches_count": num_matches
    }


def predict_match_outcome_from_h2h(h2h_features: Dict[str, float], home_stats: Optional[Dict] = None, away_stats: Optional[Dict] = None) -> Tuple[float, float, float]:
    """
    Predict match outcome using H2H features and optional team stats.
    
    Args:
        h2h_features: H2H features dictionary
        home_stats: Optional home team statistics
        away_stats: Optional away team statistics
    
    Returns:
        Tuple of (home_win_prob, draw_prob, away_win_prob)
    """
    # Base probabilities from H2H history
    home_win_base = h2h_features["home_win_ratio"]
    draw_base = h2h_features["draw_ratio"]
    away_win_base = h2h_features["away_win_ratio"]
    
    # If we have recent team form, adjust probabilities
    if home_stats and away_stats:
        form_diff = home_stats.get("form", 1.5) - away_stats.get("form", 1.5)
        goal_diff = (home_stats.get("goals_for", DEFAULT_GOALS_FOR) - home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) - \
                    (away_stats.get("goals_for", DEFAULT_GOALS_FOR) - away_stats.get("goals_against", DEFAULT_GOALS_AGAINST))
        
        # Adjust based on current form (scale: 0.1 means form has 10% weight)
        form_adjustment = sigmoid(form_diff * 0.5) - 0.5  # -0.5 to 0.5
        goal_adjustment = sigmoid(goal_diff * 0.3) - 0.5  # -0.5 to 0.5
        
        # Blend H2H with recent form (70% H2H, 30% recent form)
        home_win_base = home_win_base * 0.7 + (home_win_base + form_adjustment * 0.3 + goal_adjustment * 0.3) * 0.3
        away_win_base = away_win_base * 0.7 + (away_win_base - form_adjustment * 0.3 - goal_adjustment * 0.3) * 0.3
    
    # Ensure probabilities are positive and normalized
    home_win_base = max(0.05, home_win_base)
    away_win_base = max(0.05, away_win_base)
    draw_base = max(0.05, draw_base)
    
    total = home_win_base + draw_base + away_win_base
    
    home_win_prob = home_win_base / total
    draw_prob = draw_base / total
    away_win_prob = away_win_base / total
    
    return home_win_prob, draw_prob, away_win_prob


def predict_over_under_from_h2h(h2h_features: Dict[str, float], line: float = 2.5, home_stats: Optional[Dict] = None, away_stats: Optional[Dict] = None) -> float:
    """
    Predict Over/Under based on H2H average goals.
    
    Args:
        h2h_features: H2H features dictionary
        line: Goal line (default: 2.5)
        home_stats: Optional home team statistics
        away_stats: Optional away team statistics
    
    Returns:
        Probability of over the line
    """
    # Base expectation from H2H
    expected_goals = h2h_features["avg_goals_per_match"]
    
    # Adjust with recent team stats if available
    if home_stats and away_stats:
        recent_expected = (
            home_stats.get("goals_for", DEFAULT_GOALS_FOR) +
            home_stats.get("goals_against", DEFAULT_GOALS_AGAINST) +
            away_stats.get("goals_for", DEFAULT_GOALS_FOR) +
            away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
        ) / 2
        
        # Blend: 60% H2H, 40% recent
        expected_goals = expected_goals * 0.6 + recent_expected * 0.4
    
    # Convert to probability using sigmoid
    prob_over = sigmoid((expected_goals - line) * 1.0)
    return prob_over


def predict_btts_from_h2h(h2h_features: Dict[str, float], home_stats: Optional[Dict] = None, away_stats: Optional[Dict] = None) -> float:
    """
    Predict Both Teams To Score using H2H data.
    
    Args:
        h2h_features: H2H features dictionary
        home_stats: Optional home team statistics
        away_stats: Optional away team statistics
    
    Returns:
        Probability of BTTS
    """
    # H2H average goals per team
    home_scoring = h2h_features["home_avg_goals"]
    away_scoring = h2h_features["away_avg_goals"]
    
    # Adjust with recent stats if available
    if home_stats and away_stats:
        home_recent = (home_stats.get("goals_for", DEFAULT_GOALS_FOR) + away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
        away_recent = (away_stats.get("goals_for", DEFAULT_GOALS_FOR) + home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
        
        # Blend: 60% H2H, 40% recent
        home_scoring = home_scoring * 0.6 + home_recent * 0.4
        away_scoring = away_scoring * 0.6 + away_recent * 0.4
    
    # Both teams need to score at least 1
    # Using minimum scoring potential
    min_scoring = min(home_scoring, away_scoring)
    
    # Convert to probability
    prob = sigmoid((min_scoring - 0.8) * 2.0)
    return prob


# ===== Legacy functions for backwards compatibility =====

def _compute_win_score(side_stats: dict, opponent_stats: dict, advantage: float) -> float:
    """
    Compute win score for a side given team stats and a home/away advantage modifier.
    
    Args:
        side_stats: Statistics for the team we're computing score for
        opponent_stats: Statistics for the opposing team
        advantage: Home advantage modifier (positive for home, negative for away)
    
    Returns:
        Raw score before sigmoid transformation
    """
    score = advantage
    score += (side_stats.get("form", 0) - opponent_stats.get("form", 0)) * 0.8
    score += ((side_stats.get("goals_for", 0) - side_stats.get("goals_against", 0)) -
              (opponent_stats.get("goals_for", 0) - opponent_stats.get("goals_against", 0))) * 0.6
    score -= side_stats.get("missing_key_players", 0) * 1.2
    return score


def predict_home_win(home_stats: dict, away_stats: dict) -> float:
    score = _compute_win_score(home_stats, away_stats, advantage=2.0)
    return sigmoid(score)


def predict_away_win(home_stats: dict, away_stats: dict) -> float:
    """
    Predict probability of away team winning.
    Away team is modeled with an away disadvantage (negative home-advantage modifier), so they need stronger stats to win.
    """
    score = _compute_win_score(away_stats, home_stats, advantage=-2.0)
    return sigmoid(score)


def predict_match_outcome(home_stats: dict, away_stats: dict) -> tuple[float, float, float]:
    """
    Predict probabilities for all three possible match outcomes.
    Returns: (home_win_prob, draw_prob, away_win_prob)
    
    The probabilities are normalized to sum to 1.0 (100%).
    """
    # Calculate raw probabilities
    home_win_raw = predict_home_win(home_stats, away_stats)
    away_win_raw = predict_away_win(home_stats, away_stats)
    
    # Draw probability is higher when teams are evenly matched
    # Calculate as the inverse of the absolute difference in raw probabilities
    match_closeness = 1 - abs(home_win_raw - away_win_raw)
    draw_raw = match_closeness * 0.35  # Scale factor for typical draw rates (~25-30% in football)
    
    # Normalize to ensure probabilities sum to 1.0
    total = home_win_raw + draw_raw + away_win_raw
    
    home_win_prob = home_win_raw / total
    draw_prob = draw_raw / total
    away_win_prob = away_win_raw / total
    
    return home_win_prob, draw_prob, away_win_prob


def predict_over_under(home_stats: dict, away_stats: dict, line: float = 2.5) -> float:
    """
    Predict probability of over X goals in the match.
    Considers both teams' attacking (goals_for) and defensive (goals_against) stats.
    """
    # Expected goals for home team (their attack vs away defense)
    home_expected = (home_stats.get("goals_for", DEFAULT_GOALS_FOR) + away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
    
    # Expected goals for away team (their attack vs home defense)
    away_expected = (away_stats.get("goals_for", DEFAULT_GOALS_FOR) + home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
    
    # Total expected goals in the match
    total_expected_goals = home_expected + away_expected
    
    # Use sigmoid to convert difference to probability
    # Balanced scaling: 1.0 makes it more sensitive to the difference
    prob_over = sigmoid((total_expected_goals - line) * 1.0)
    return prob_over


def predict_btts(home_stats: dict, away_stats: dict) -> float:
    """
    Predict Both Teams To Score (BTTS).
    Higher probability if both teams have good attacking records.
    """
    # Home team's scoring ability vs away defense
    home_scoring_potential = (home_stats.get("goals_for", DEFAULT_GOALS_FOR) + away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
    
    # Away team's scoring ability vs home defense
    away_scoring_potential = (away_stats.get("goals_for", DEFAULT_GOALS_FOR) + home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) / 2
    
    # Use minimum of both (weakest link determines BTTS)
    min_scoring = min(home_scoring_potential, away_scoring_potential)
    
    # Convert to probability - teams need to score at least 1 goal each
    # Using a threshold around 1.0 goals per game as baseline
    prob = sigmoid((min_scoring - 0.8) * 2.0)
    return prob
