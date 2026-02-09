import math

# Default fallback values for goals statistics when team data is unavailable
# 1.3 goals represents a realistic average for both scoring and conceding in football:
# - Matches typical league averages (most leagues average 2.6-2.8 total goals)
# - Avoids extreme predictions when data is missing
# - More conservative than 1.5, reducing over-prediction of high-scoring games
DEFAULT_GOALS_FOR = 1.3
DEFAULT_GOALS_AGAINST = 1.3

# Home advantage constants based on football statistics research
HOME_ADVANTAGE_GOALS = 0.3  # Home teams score ~0.3 more goals on average
HOME_ADVANTAGE_WIN = 0.15   # Home win probability boost (15%)

def sigmoid(x: float) -> float:
    """Sigmoid activation function for probability conversion."""
    return 1 / (1 + math.exp(-x))


def _compute_win_score(side_stats: dict, opponent_stats: dict, advantage: float) -> float:
    """
    Compute win score for a side given team stats and a home/away advantage modifier.
    
    Enhanced to consider:
    - Form (recent points per game)
    - Goal difference
    - Attack vs defense matchup
    - Consistency (games played - more data = more reliable)
    
    Args:
        side_stats: Statistics for the team we're computing score for
        opponent_stats: Statistics for the opposing team
        advantage: Home advantage modifier (positive for home, negative for away)
    
    Returns:
        Raw score before sigmoid transformation
    """
    score = advantage
    
    # Form difference (weighted heavily - recent performance is key)
    form_diff = side_stats.get("form", 1.5) - opponent_stats.get("form", 1.5)
    score += form_diff * 0.9
    
    # Goal difference (measures overall quality)
    side_gd = side_stats.get("goals_for", DEFAULT_GOALS_FOR) - side_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    opp_gd = opponent_stats.get("goals_for", DEFAULT_GOALS_FOR) - opponent_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    score += (side_gd - opp_gd) * 0.7
    
    # Attack vs defense matchup (specific tactical consideration)
    attack_vs_defense = side_stats.get("goals_for", DEFAULT_GOALS_FOR) - opponent_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    score += attack_vs_defense * 0.5
    
    # Penalize missing key players
    score -= side_stats.get("missing_key_players", 0) * 1.2
    
    # Data reliability bonus (more games = more confidence)
    games_played = side_stats.get("games_played", 0)
    if games_played < 5:
        # Reduce confidence for teams with limited data
        score *= 0.85
    
    return score


def predict_home_win(home_stats: dict, away_stats: dict) -> float:
    """
    Predict probability of home team winning.
    Includes home advantage boost.
    """
    score = _compute_win_score(home_stats, away_stats, advantage=2.2)
    return sigmoid(score)


def predict_away_win(home_stats: dict, away_stats: dict) -> float:
    """
    Predict probability of away team winning.
    Away team faces disadvantage (negative home advantage), requiring stronger stats to win.
    """
    score = _compute_win_score(away_stats, home_stats, advantage=-1.8)
    return sigmoid(score)


def predict_match_outcome(home_stats: dict, away_stats: dict) -> tuple[float, float, float]:
    """
    Predict probabilities for all three possible match outcomes.
    Returns: (home_win_prob, draw_prob, away_win_prob)
    
    The probabilities are normalized to sum to 1.0 (100%).
    
    Enhanced draw prediction based on:
    - Match closeness (similar team quality)
    - Defensive strength (low-scoring games more likely to draw)
    - Form similarity
    """
    # Calculate raw probabilities
    home_win_raw = predict_home_win(home_stats, away_stats)
    away_win_raw = predict_away_win(home_stats, away_stats)
    
    # Enhanced draw probability calculation
    # 1. Match closeness factor
    match_closeness = 1 - abs(home_win_raw - away_win_raw)
    
    # 2. Defensive strength factor (defensive teams draw more)
    home_defensive = 2.0 - home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    away_defensive = 2.0 - away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    defensive_factor = max(0, (home_defensive + away_defensive) / 4.0)
    
    # 3. Form similarity (teams in similar form tend to draw)
    form_similarity = 1 - abs(home_stats.get("form", 1.5) - away_stats.get("form", 1.5)) / 3.0
    
    # Combine factors for draw probability
    draw_raw = (match_closeness * 0.4 + defensive_factor * 0.3 + form_similarity * 0.3) * 0.32
    
    # Normalize to ensure probabilities sum to 1.0
    total = home_win_raw + draw_raw + away_win_raw
    
    home_win_prob = home_win_raw / total
    draw_prob = draw_raw / total
    away_win_prob = away_win_raw / total
    
    return home_win_prob, draw_prob, away_win_prob


def predict_over_under(home_stats: dict, away_stats: dict, line: float = 2.5) -> float:
    """
    Predict probability of over X goals in the match.
    
    Enhanced to consider:
    - Attack vs defense matchups (more realistic than simple averages)
    - Home advantage in scoring
    - Both teams' form (attacking momentum)
    """
    # Home team expected goals (their attack vs away defense + home advantage)
    home_attack = home_stats.get("goals_for", DEFAULT_GOALS_FOR)
    away_defense = away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    home_expected = (home_attack * 0.6 + away_defense * 0.4) + HOME_ADVANTAGE_GOALS
    
    # Away team expected goals (their attack vs home defense)
    away_attack = away_stats.get("goals_for", DEFAULT_GOALS_FOR)
    home_defense = home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    away_expected = (away_attack * 0.6 + home_defense * 0.4)
    
    # Total expected goals in the match
    total_expected_goals = home_expected + away_expected
    
    # Form adjustment (teams in good form score more)
    avg_form = (home_stats.get("form", 1.5) + away_stats.get("form", 1.5)) / 2
    form_multiplier = 0.85 + (avg_form / 3.0) * 0.3  # Range: 0.85 to 1.15
    total_expected_goals *= form_multiplier
    
    # Use sigmoid to convert difference to probability
    # Tuned scaling factor for better calibration
    prob_over = sigmoid((total_expected_goals - line) * 1.2)
    return prob_over


def predict_btts(home_stats: dict, away_stats: dict) -> float:
    """
    Predict Both Teams To Score (BTTS).
    
    Enhanced to consider:
    - Attack vs defense matchups
    - Home advantage in scoring
    - Minimum threshold for both teams
    """
    # Home team's scoring potential (attack vs away defense + home advantage)
    home_attack = home_stats.get("goals_for", DEFAULT_GOALS_FOR)
    away_defense = away_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    home_scoring_potential = (home_attack * 0.6 + away_defense * 0.4) + (HOME_ADVANTAGE_GOALS * 0.5)
    
    # Away team's scoring potential (attack vs home defense)
    away_attack = away_stats.get("goals_for", DEFAULT_GOALS_FOR)
    home_defense = home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)
    away_scoring_potential = (away_attack * 0.6 + home_defense * 0.4)
    
    # Use minimum of both (weakest link determines BTTS)
    min_scoring = min(home_scoring_potential, away_scoring_potential)
    
    # Average scoring potential (context for matchup)
    avg_scoring = (home_scoring_potential + away_scoring_potential) / 2
    
    # Combine both factors: minimum must be decent AND average must be reasonable
    # A high-scoring game with one weak attack might still see BTTS
    combined_score = min_scoring * 0.7 + avg_scoring * 0.3
    
    # Convert to probability - teams need to score at least ~0.8 goals per game
    prob = sigmoid((combined_score - 0.9) * 2.2)
    return prob
