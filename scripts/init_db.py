#!/usr/bin/env python3
"""
Database initialization script.

This script:
1. Creates all necessary MongoDB indexes
2. Optionally seeds initial data
3. Validates database connection

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --drop-indexes  # Drop and recreate indexes
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.schemas import create_indexes, drop_all_indexes
from app.db.mongo import db, client
from app.utils.logger import logger
import argparse


def check_connection():
    """Check MongoDB connection."""
    try:
        # Ping the database
        client.admin.command('ping')
        logger.info(f"✓ Connected to MongoDB: {db.name}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        return False


def init_database(drop_existing: bool = False):
    """
    Initialize the database with indexes.
    
    Args:
        drop_existing: Whether to drop existing indexes first
    """
    logger.info("Starting database initialization...")
    
    # Check connection
    if not check_connection():
        logger.error("Cannot proceed without database connection")
        sys.exit(1)
    
    # Drop indexes if requested
    if drop_existing:
        logger.warning("Dropping existing indexes...")
        drop_all_indexes()
    
    # Create indexes
    logger.info("Creating indexes...")
    create_indexes()
    
    logger.info("✓ Database initialization complete!")


def list_collections():
    """List all collections in the database."""
    logger.info(f"\nCollections in '{db.name}':")
    collections = db.list_collection_names()
    
    if not collections:
        logger.info("  (No collections yet)")
    else:
        for col_name in collections:
            col = db[col_name]
            count = col.count_documents({})
            logger.info(f"  - {col_name}: {count} documents")


def list_indexes():
    """List all indexes in the database."""
    logger.info("\nIndexes:")
    
    collections = ["competitions", "matches", "team_stats", "predictions", "fixtures"]
    
    for col_name in collections:
        col = db[col_name]
        
        # Check if collection exists
        if col_name not in db.list_collection_names():
            logger.info(f"  {col_name}: (collection does not exist)")
            continue
        
        indexes = list(col.list_indexes())
        
        if len(indexes) <= 1:  # Only _id index
            logger.info(f"  {col_name}: (no custom indexes)")
        else:
            logger.info(f"  {col_name}:")
            for idx in indexes:
                if idx["name"] != "_id_":
                    keys = ", ".join([f"{k}:{v}" for k, v in idx["key"].items()])
                    unique = " [UNIQUE]" if idx.get("unique") else ""
                    logger.info(f"    - {idx['name']}: {keys}{unique}")


def main():
    parser = argparse.ArgumentParser(description="Initialize Football-Data database")
    parser.add_argument(
        "--drop-indexes",
        action="store_true",
        help="Drop existing indexes before creating new ones"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List collections and indexes without making changes"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # Just list current state
        check_connection()
        list_collections()
        list_indexes()
    else:
        # Initialize database
        init_database(drop_existing=args.drop_indexes)
        list_collections()
        list_indexes()


if __name__ == "__main__":
    main()
