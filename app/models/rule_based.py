import math

# Default fallback values for goals statistics when team data is unavailable
# 1.5 goals represents a reasonable average for both scoring and conceding in football:
# - It's slightly above 1.0 (which would be very defensive)
# - It's slightly below 2.0 (which would be very attacking)
# - This neutral value avoids biasing predictions toward high or low scoring outcomes
DEFAULT_GOALS_FOR = 1.5
DEFAULT_GOALS_AGAINST = 1.5

def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


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
