"""
Enhanced prediction analysis using pandas for better insights.
"""
import pandas as pd
from typing import List, Dict

from app.config.settings import Settings


def analyze_predictions(predictions: List[Dict]) -> Dict:
    """
    Analyze predictions using pandas to extract insights.
    
    Returns:
        dict with various analyses including best bets, high confidence picks, etc.
    """
    if not predictions:
        return {
            "total_predictions": 0,
            "best_bets": [],
            "summary": {}
        }
    
    # Convert to DataFrame
    df = pd.DataFrame(predictions)
    
    # Extract goals prediction info into separate columns
    df['goals_bet'] = df['goals_prediction'].apply(lambda x: x['bet'])
    df['goals_probability'] = df['goals_prediction'].apply(lambda x: x['probability'])
    df['goals_confidence'] = df['goals_prediction'].apply(lambda x: x['confidence'])
    
    # Best home win bets (high confidence + high probability)
    best_home_wins = df[
        (df['home_win_confidence'] == 'HIGH') & 
        (df['home_win_probability'] >= 0.80)
    ].nlargest(5, 'home_win_probability')[
        [
            'match',
            'league',
            'league_logo',
            'league_flag',
            'home_team_logo',
            'away_team_logo',
            'home_win_probability',
            'home_win_confidence',
            'draw_probability',
            'away_win_probability',
            'value_score'
        ]
    ].to_dict('records')
    
    # Best over/under bets (high confidence)
    best_goals_bets = df[
        df['goals_confidence'] == 'HIGH'
    ].nlargest(5, 'goals_probability')[
        [
            'match',
            'league_logo',
            'league_flag',
            'home_team_logo',
            'away_team_logo',
            'goals_bet',
            'goals_probability',
            'goals_confidence'
        ]
    ].to_dict('records')
    
    # Best BTTS bets
    best_btts = df[
        (df['btts_confidence'].isin(['HIGH', 'MEDIUM'])) &
        (df['btts_probability'] >= 0.65)
    ].nlargest(5, 'btts_probability')[
        [
            'match',
            'league_logo',
            'league_flag',
            'home_team_logo',
            'away_team_logo',
            'btts_probability',
            'btts_confidence'
        ]
    ].to_dict('records')
    
    # Best value bets (positive value score + decent probability)
    # Filter out None values and convert to numeric
    df_with_value = df[df['value_score'].notna()].copy()
    if len(df_with_value) > 0:
        df_with_value['value_score'] = pd.to_numeric(df_with_value['value_score'], errors='coerce')
        best_value = df_with_value[
            (df_with_value['value_score'] > 0.15) &
            (df_with_value['home_win_probability'] >= 0.65)
        ].nlargest(5, 'value_score')[
            [
                'match',
                'league_logo',
                'league_flag',
                'home_team_logo',
                'away_team_logo',
                'home_win_probability',
                'draw_probability',
                'away_win_probability',
                'value_score',
                'home_win_confidence'
            ]
        ].to_dict('records')
    else:
        best_value = []
    
    # Summary statistics
    summary = {
        "total_matches": len(df),
        "high_confidence_home_wins": len(df[df['home_win_confidence'] == 'HIGH']),
        "over_2_5_count": len(df[df['goals_bet'] == 'Over 2.5']),
        "under_2_5_count": len(df[df['goals_bet'] == 'Under 2.5']),
        "avg_home_win_probability": round(df['home_win_probability'].mean(), 3),
        "avg_btts_probability": round(df['btts_probability'].mean(), 3),
        "high_confidence_goals_bets": len(df[df['goals_confidence'] == 'HIGH']),
    }
    
    # Distribution by league
    if 'league' in df.columns:
        league_dist = df['league'].value_counts().to_dict()
        summary['matches_by_league'] = league_dist
    
    return {
        "total_predictions": len(predictions),
        "best_home_wins": best_home_wins,
        "best_goals_bets": best_goals_bets,
        "best_btts": best_btts,
        "best_value_bets": best_value,
        "summary": summary
    }


def get_top_picks(predictions: List[Dict], limit: int) -> List[Dict]:
    """
    Get top picks using a composite scoring system.
    
    Scoring: (home_win_prob * 0.4) + (goals_prob * 0.3) + (btts_prob * 0.2) + (value_score * 0.1)
    """
    if not predictions:
        return []
    
    df = pd.DataFrame(predictions)
    df['goals_probability'] = df['goals_prediction'].apply(lambda x: x['probability'])
    
    # Handle value_score with None values properly
    df['value_score_numeric'] = pd.to_numeric(df['value_score'], errors='coerce').fillna(0).clip(lower=0)
    
    # Composite score
    df['composite_score'] = (
        df['home_win_probability'] * 0.4 +
        df['goals_probability'] * 0.3 +
        df['btts_probability'] * 0.2 +
        df['value_score_numeric'] * 0.1  # Only positive value scores, treat missing as 0
    )
    
    top_picks = df.nlargest(limit, 'composite_score')[
        [
            'fixture_id',
            'match',
            'league',
            'league_logo',
            'league_flag',
            'home_team_logo',
            'away_team_logo',
            'home_win_probability',
            'draw_probability',
            'away_win_probability',
            'goals_prediction',
            'btts_probability',
            'composite_score',
            'created_at'
        ]
    ].to_dict('records')
    
    # Round composite score for readability
    for pick in top_picks:
        pick['composite_score'] = round(pick['composite_score'], 3)
    
    return top_picks
