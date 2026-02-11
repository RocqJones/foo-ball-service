#!/usr/bin/env python3
"""
Quick test script for Football-Data.org API integration.

This script tests:
1. API connectivity
2. Data ingestion
3. H2H fetching
4. Prediction generation

Usage:
    python scripts/test_integration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.data_sources.football_data_api import (
    get_competitions,
    get_scheduled_matches,
    get_head_to_head
)
from app.services.ingestion import (
    ingest_competitions,
    ingest_matches_for_competition,
    fetch_and_cache_h2h
)
from app.services.team_stats_v2 import update_team_stats_for_all_teams
from app.services.prediction_v2 import get_predictions_today
from app.db.mongo import get_collection
from app.utils.logger import logger
from datetime import date


def test_api_connection():
    """Test basic API connectivity."""
    print("\n" + "=" * 60)
    print("TEST 1: API Connection")
    print("=" * 60)
    
    try:
        competitions = get_competitions()
        print(f"✓ Successfully connected to Football-Data.org API")
        print(f"✓ Fetched {len(competitions)} competitions")
        
        # Show first 3 competitions
        print("\nSample competitions:")
        for comp in competitions[:3]:
            print(f"  - {comp['name']} ({comp['code']})")
        
        return True
    except Exception as e:
        print(f"✗ API connection failed: {str(e)}")
        return False


def test_ingestion():
    """Test data ingestion."""
    print("\n" + "=" * 60)
    print("TEST 2: Data Ingestion")
    print("=" * 60)
    
    try:
        # Ingest competitions
        print("\nIngesting competitions...")
        comp_count = ingest_competitions()
        print(f"✓ Ingested {comp_count} competitions")
        
        # Ingest matches for Premier League
        print("\nIngesting Premier League matches...")
        match_count = ingest_matches_for_competition("PL")
        print(f"✓ Ingested {match_count} matches for Premier League")
        
        # Check database
        matches_col = get_collection("matches")
        total_matches = matches_col.count_documents({})
        print(f"✓ Total matches in database: {total_matches}")
        
        return True
    except Exception as e:
        print(f"✗ Ingestion failed: {str(e)}")
        return False


def test_h2h():
    """Test H2H data fetching."""
    print("\n" + "=" * 60)
    print("TEST 3: Head-to-Head Data")
    print("=" * 60)
    
    try:
        # Find a scheduled match
        matches_col = get_collection("matches")
        match = matches_col.find_one({
            "status": {"$in": ["SCHEDULED", "TIMED"]}
        })
        
        if not match:
            print("⚠ No scheduled matches found. Skipping H2H test.")
            return True
        
        match_id = match["id"]
        print(f"\nTesting H2H for match: {match['homeTeam']['name']} vs {match['awayTeam']['name']}")
        print(f"Match ID: {match_id}")
        
        # Fetch and cache H2H
        h2h_data = fetch_and_cache_h2h(match_id, limit=5)
        
        if h2h_data:
            aggregates = h2h_data.get("aggregates", {})
            print(f"✓ Fetched H2H data:")
            print(f"  - Total past meetings: {aggregates.get('numberOfMatches', 0)}")
            print(f"  - Total goals: {aggregates.get('totalGoals', 0)}")
            
            # Verify it's cached in DB
            updated_match = matches_col.find_one({"id": match_id})
            if updated_match.get("h2h"):
                print(f"✓ H2H data cached in database")
            else:
                print(f"⚠ H2H data not found in database cache")
            
            return True
        else:
            print(f"⚠ No H2H data available for this match")
            return True
    except Exception as e:
        print(f"✗ H2H test failed: {str(e)}")
        return False


def test_team_stats():
    """Test team statistics computation."""
    print("\n" + "=" * 60)
    print("TEST 4: Team Statistics")
    print("=" * 60)
    
    try:
        print("\nUpdating team statistics...")
        count = update_team_stats_for_all_teams(
            competition_codes=["PL"],
            days_back=90,
            max_matches=10
        )
        print(f"✓ Updated stats for {count} teams")
        
        # Show sample team stats
        team_stats_col = get_collection("team_stats")
        sample_stats = team_stats_col.find_one()
        
        if sample_stats:
            print(f"\nSample team stats (Team ID {sample_stats['team_id']}):")
            print(f"  - Form: {sample_stats.get('form')}")
            print(f"  - Goals For: {sample_stats.get('goals_for')}")
            print(f"  - Goals Against: {sample_stats.get('goals_against')}")
            print(f"  - Games Played: {sample_stats.get('games_played')}")
        
        return True
    except Exception as e:
        print(f"✗ Team stats test failed: {str(e)}")
        return False


def test_predictions():
    """Test prediction generation."""
    print("\n" + "=" * 60)
    print("TEST 5: Prediction Generation")
    print("=" * 60)
    
    try:
        today = date.today().isoformat()
        print(f"\nGenerating predictions for {today}...")
        
        predictions = get_predictions_today(use_h2h=True)
        print(f"✓ Generated {len(predictions)} predictions")
        
        # Show first prediction
        if predictions:
            pred = predictions[0]
            print(f"\nSample prediction:")
            print(f"  Match: {pred['match']}")
            print(f"  Competition: {pred['competition']}")
            print(f"  Predicted Outcome: {pred['predicted_outcome']} ({pred['predicted_outcome_probability']})")
            print(f"  Goals Prediction: {pred['goals_prediction']['bet']} ({pred['goals_prediction']['probability']})")
            print(f"  BTTS: {pred['btts_probability']}")
            print(f"  Method: {pred['prediction_method']}")
            print(f"  H2H Available: {pred['h2h_available']}")
        
        return True
    except Exception as e:
        print(f"✗ Prediction test failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("FOOTBALL-DATA.ORG INTEGRATION TEST")
    print("=" * 60)
    
    tests = [
        ("API Connection", test_api_connection),
        ("Data Ingestion", test_ingestion),
        ("Head-to-Head", test_h2h),
        ("Team Statistics", test_team_stats),
        ("Predictions", test_predictions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\n✗ Unexpected error in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Integration is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
