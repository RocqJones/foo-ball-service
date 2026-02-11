#!/usr/bin/env python3
"""
Setup helper for Football-Data.org migration.

This script helps you:
1. Validate environment variables
2. Initialize database
3. Run initial data ingestion
4. Generate test predictions

Usage:
    python scripts/setup_migration.py
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def check_env_file():
    """Check if .env file exists and has required variables."""
    print("Checking environment configuration...")
    
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("✗ .env file not found!")
        print("\nPlease create a .env file with:")
        print("  FOOTBALL_DATA_API_KEY=your_api_key_here")
        print("  MONGO_URI=your_mongo_connection_string")
        return False
    
    print("✓ .env file found")
    
    # Check for required variables
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "FOOTBALL_DATA_API_KEY",
        "MONGO_URI"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing.append(var)
        else:
            # Show masked value
            if "KEY" in var or "TOKEN" in var:
                display = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display = value[:30] + "..." if len(value) > 30 else value
            print(f"  ✓ {var}={display}")
    
    if missing:
        print(f"\n✗ Missing required variables: {', '.join(missing)}")
        return False
    
    print("✓ All required environment variables are set")
    return True


def check_database():
    """Check database connection."""
    print("\nChecking database connection...")
    
    try:
        from app.db.mongo import client, db
        
        # Ping the database
        client.admin.command('ping')
        print(f"✓ Connected to MongoDB")
        print(f"  Database: {db.name}")
        
        # List collections
        collections = db.list_collection_names()
        if collections:
            print(f"  Existing collections: {', '.join(collections)}")
        else:
            print(f"  No collections yet (empty database)")
        
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {str(e)}")
        return False


def initialize_database():
    """Initialize database with indexes."""
    print("\nInitializing database...")
    
    try:
        from app.db.schemas import create_indexes
        
        create_indexes()
        print("✓ Database indexes created")
        return True
    except Exception as e:
        print(f"✗ Failed to create indexes: {str(e)}")
        return False


def run_initial_ingestion():
    """Run initial data ingestion."""
    print("\nRunning initial data ingestion...")
    print("This may take a few minutes depending on API rate limits...")
    
    try:
        from app.services.ingestion import (
            ingest_competitions,
            ingest_all_tracked_matches
        )
        
        # Ingest competitions
        print("\n  [1/2] Ingesting competitions...")
        comp_count = ingest_competitions()
        print(f"      ✓ Ingested {comp_count} competitions")
        
        # Ingest matches
        print("\n  [2/2] Ingesting matches for tracked competitions...")
        results = ingest_all_tracked_matches()
        total_matches = sum(results.values())
        print(f"      ✓ Ingested {total_matches} matches")
        
        for comp_code, count in results.items():
            if count > 0:
                print(f"        - {comp_code}: {count} matches")
        
        return True
    except Exception as e:
        print(f"✗ Ingestion failed: {str(e)}")
        return False


def generate_sample_predictions():
    """Generate sample predictions."""
    print("\nGenerating sample predictions...")
    
    try:
        from app.services.prediction_v2 import get_predictions_today
        from datetime import date
        
        predictions = get_predictions_today(use_h2h=True)
        today = date.today().isoformat()
        
        print(f"✓ Generated {len(predictions)} predictions for {today}")
        
        if predictions:
            print("\nSample prediction:")
            pred = predictions[0]
            print(f"  Match: {pred['match']}")
            print(f"  Competition: {pred['competition']}")
            print(f"  Outcome: {pred['predicted_outcome']} ({pred['predicted_outcome_probability']})")
            print(f"  Method: {pred['prediction_method']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to generate predictions: {str(e)}")
        return False


def main():
    """Run setup wizard."""
    print("=" * 70)
    print("FOOTBALL-DATA.ORG MIGRATION SETUP")
    print("=" * 70)
    print()
    
    # Step 1: Check environment
    if not check_env_file():
        print("\n❌ Setup failed at environment check.")
        print("\nPlease fix the issues above and run this script again.")
        sys.exit(1)
    
    # Step 2: Check database
    if not check_database():
        print("\n❌ Setup failed at database check.")
        print("\nPlease verify your MONGO_URI and database connection.")
        sys.exit(1)
    
    # Step 3: Initialize database
    if not initialize_database():
        print("\n❌ Setup failed at database initialization.")
        sys.exit(1)
    
    # Step 4: Ask if user wants to run ingestion
    print("\n" + "-" * 70)
    print("Initial data ingestion")
    print("-" * 70)
    print("\nThis will fetch competitions and matches from Football-Data.org API.")
    print("Note: This will consume API rate limits (10 requests/minute on free tier).")
    
    response = input("\nDo you want to run initial ingestion now? (y/n): ").strip().lower()
    
    if response == 'y':
        if not run_initial_ingestion():
            print("\n⚠ Ingestion encountered errors, but you can retry later.")
        
        # Step 5: Generate predictions if ingestion succeeded
        response = input("\nDo you want to generate sample predictions? (y/n): ").strip().lower()
        if response == 'y':
            generate_sample_predictions()
    else:
        print("\nSkipping ingestion. You can run it later with:")
        print("  python app/jobs/daily_run.py")
    
    # Summary
    print("\n" + "=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Run daily ingestion: python app/jobs/daily_run.py")
    print("  2. Test integration: python scripts/test_integration.py")
    print("  3. Start API server: python app/main.py")
    print("\nFor more information, see MIGRATION_GUIDE.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
