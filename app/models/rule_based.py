import math

def sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))

def predict_home_win(home_stats: dict, away_stats: dict) -> float:
    score = 2.0  # home advantage
    score += (home_stats.get("form",0) - away_stats.get("form",0)) * 0.8
    score += ((home_stats.get("goals_for",0) - home_stats.get("goals_against",0)) -
              (away_stats.get("goals_for",0) - away_stats.get("goals_against",0))) * 0.6
    score -= home_stats.get("missing_key_players",0) * 1.2
    return sigmoid(score)

def predict_over_under(home_stats: dict, away_stats: dict, line: float = 2.5) -> float:
    avg_goals = (home_stats.get("goals_for",1) + away_stats.get("goals_for",1)) / 2
    prob_over = sigmoid(avg_goals - line)
    return prob_over

def predict_btts(home_stats: dict, away_stats: dict) -> float:
    home_scoring = home_stats.get("goals_for",1)
    away_scoring = away_stats.get("goals_for",1)
    prob = sigmoid(min(home_scoring, away_scoring) / 3)  # simple scaling
    return prob
