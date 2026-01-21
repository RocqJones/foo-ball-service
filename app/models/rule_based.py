import math

def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def predict_home_win(home_stats: dict, away_stats: dict) -> float:
    score = 2.0  # home advantage
    score += (home_stats.get("form", 0) - away_stats.get("form", 0)) * 0.8
    score += ((home_stats.get("goals_for", 0) - home_stats.get("goals_against", 0)) -
              (away_stats.get("goals_for", 0) - away_stats.get("goals_against", 0))) * 0.6
    score -= home_stats.get("missing_key_players", 0) * 1.2
    return sigmoid(score)

def predict_over_under(home_stats: dict, away_stats: dict, line: float = 2.5) -> float:
    """
    Predict probability of over X goals in the match.
    Considers both teams' attacking (goals_for) and defensive (goals_against) stats.
    """
    # Expected goals for home team (their attack vs away defense)
    home_expected = (home_stats.get("goals_for", 1.5) + away_stats.get("goals_against", 1.5)) / 2
    
    # Expected goals for away team (their attack vs home defense)
    away_expected = (away_stats.get("goals_for", 1.5) + home_stats.get("goals_against", 1.5)) / 2
    
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
    home_scoring_potential = (home_stats.get("goals_for", 1.5) + away_stats.get("goals_against", 1.5)) / 2
    
    # Away team's scoring ability vs home defense
    away_scoring_potential = (away_stats.get("goals_for", 1.5) + home_stats.get("goals_against", 1.5)) / 2
    
    # Use minimum of both (weakest link determines BTTS)
    min_scoring = min(home_scoring_potential, away_scoring_potential)
    
    # Convert to probability - teams need to score at least 1 goal each
    # Using a threshold around 1.0 goals per game as baseline
    prob = sigmoid((min_scoring - 0.8) * 2.0)
    return prob
