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

# League average base rates (typical across major European leagues)
# Home teams win ~45%, draws ~27%, away wins ~28%
LEAGUE_AVG_HOME_WIN = 0.45
LEAGUE_AVG_DRAW = 0.27
LEAGUE_AVG_AWAY_WIN = 0.28


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

    # Prefer the actual match list count, falling back to aggregates.
    # Relying purely on aggregates for wins/draws/losses has proven unreliable
    # across different H2H orientations and can skew heavily toward draws.
    num_matches = len(matches) if matches else aggregates.get("numberOfMatches", 0)

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

    # Compute outcome counts from the match list to ensure correctness.
    # We transform each historical match result into the perspective of
    # (home_team_id vs away_team_id) for the *current* fixture.
    home_wins = 0
    away_wins = 0
    draws = 0

    # Also compute total goals from the match list (more reliable than aggregates)
    total_goals = 0

    finished_matches = 0
    for m in matches:
        if m.get("status") != "FINISHED":
            continue

        score = m.get("score", {})
        full_time = score.get("fullTime", {})

        home_goals_m = full_time.get("home")
        away_goals_m = full_time.get("away")
        if home_goals_m is None or away_goals_m is None:
            continue
        try:
            home_goals_m = int(float(home_goals_m))
            away_goals_m = int(float(away_goals_m))
        except (ValueError, TypeError):
            continue

        m_home_id = m.get("homeTeam", {}).get("id")
        m_away_id = m.get("awayTeam", {}).get("id")
        if m_home_id is None or m_away_id is None:
            continue

        # Only count matches that are actually between the two teams
        # (defensive programming; the API should do this already).
        teams = {m_home_id, m_away_id}
        if home_team_id not in teams or away_team_id not in teams:
            continue

        finished_matches += 1
        total_goals += home_goals_m + away_goals_m

        # Map the result to the current fixture perspective
        if m_home_id == home_team_id:
            # Same orientation as current fixture
            if home_goals_m > away_goals_m:
                home_wins += 1
            elif home_goals_m < away_goals_m:
                away_wins += 1
            else:
                draws += 1
        else:
            # Reversed orientation
            if home_goals_m > away_goals_m:
                away_wins += 1
            elif home_goals_m < away_goals_m:
                home_wins += 1
            else:
                draws += 1

    # If none were FINISHED, fall back to aggregates for goals and neutral ratios
    if finished_matches == 0:
        total_goals = aggregates.get("totalGoals", 0)
        return {
            "home_win_ratio": 0.33,
            "away_win_ratio": 0.33,
            "draw_ratio": 0.34,
            "avg_goals_per_match": (total_goals / num_matches) if num_matches else 2.5,
            "home_avg_goals": 1.25,
            "away_avg_goals": 1.25,
            "h2h_matches_count": num_matches
        }

    denom = finished_matches
    home_win_ratio = home_wins / denom
    away_win_ratio = away_wins / denom
    draw_ratio = draws / denom
    avg_goals_per_match = total_goals / denom
    
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
            
            try:
                home_goals = int(float(full_time.get("home")))
                away_goals = int(float(full_time.get("away")))
            except (ValueError, TypeError):
                continue
            
            # Accumulate goals from the perspective of the current match's teams
            if match_home_id == home_team_id:
                home_total_goals += home_goals
                away_total_goals += away_goals
            elif match_home_id == away_team_id:
                away_total_goals += home_goals
                home_total_goals += away_goals
    
    home_avg_goals = home_total_goals / finished_matches if finished_matches > 0 else 1.25
    away_avg_goals = away_total_goals / finished_matches if finished_matches > 0 else 1.25
    
    return {
        "home_win_ratio": home_win_ratio,
        "away_win_ratio": away_win_ratio,
        "draw_ratio": draw_ratio,
        "avg_goals_per_match": avg_goals_per_match,
        "home_avg_goals": home_avg_goals,
        "away_avg_goals": away_avg_goals,
        "h2h_matches_count": finished_matches
    }


def predict_match_outcome_from_h2h(h2h_features: Dict[str, float], home_stats: Optional[Dict] = None, away_stats: Optional[Dict] = None) -> Tuple[float, float, float]:
    """
    Predict match outcome using H2H features and optional team stats.
    
    Uses a Bayesian-inspired approach: with few H2H matches, we blend heavily
    with league average base rates. As H2H sample size grows, we trust H2H more.
    
    Args:
        h2h_features: H2H features dictionary
        home_stats: Optional home team statistics
        away_stats: Optional away team statistics
    
    Returns:
        Tuple of (home_win_prob, draw_prob, away_win_prob)
    """
    # H2H probabilities from historical data
    h2h_home_win = h2h_features["home_win_ratio"]
    h2h_draw = h2h_features["draw_ratio"]
    h2h_away_win = h2h_features["away_win_ratio"]
    
    # Determine how much to trust H2H based on sample size
    # With 1 match: ~20% H2H, 80% league average
    # With 5 matches: ~60% H2H, 40% league average
    # With 10+ matches: ~90% H2H, 10% league average
    h2h_count = h2h_features.get("h2h_matches_count", 0)
    h2h_weight = min(0.9, 0.2 + (h2h_count * 0.1))  # Caps at 90% starting at 7 matches
    league_weight = 1.0 - h2h_weight
    
    # Blend H2H with league averages
    home_win_base = (h2h_home_win * h2h_weight) + (LEAGUE_AVG_HOME_WIN * league_weight)
    draw_base = (h2h_draw * h2h_weight) + (LEAGUE_AVG_DRAW * league_weight)
    away_win_base = (h2h_away_win * h2h_weight) + (LEAGUE_AVG_AWAY_WIN * league_weight)
    
    # If we have recent team form, adjust probabilities
    if home_stats and away_stats:
        form_diff = home_stats.get("form", 1.5) - away_stats.get("form", 1.5)
        goal_diff = (home_stats.get("goals_for", DEFAULT_GOALS_FOR) - home_stats.get("goals_against", DEFAULT_GOALS_AGAINST)) - \
                    (away_stats.get("goals_for", DEFAULT_GOALS_FOR) - away_stats.get("goals_against", DEFAULT_GOALS_AGAINST))
        
        # Adjust based on current form (outputs range -0.5 to 0.5)
        form_adjustment = sigmoid(form_diff * 0.5) - 0.5  # -0.5 to 0.5
        goal_adjustment = sigmoid(goal_diff * 0.3) - 0.5  # -0.5 to 0.5
        
        # Apply form adjustments (15% weight to recent form, 85% to base probabilities)
        combined_adjustment = form_adjustment + goal_adjustment
        home_win_base = home_win_base * 0.85 + combined_adjustment * 0.15
        away_win_base = away_win_base * 0.85 - combined_adjustment * 0.15
        # Reduce draw probability proportionally to the magnitude of form difference
        draw_base = draw_base * max(0.0, 1.0 - abs(combined_adjustment) * 0.15)
    
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
