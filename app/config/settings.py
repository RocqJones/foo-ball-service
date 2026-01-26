from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "foo_ball_service")

    # Leagues to track - easily configurable
    TRACKED_LEAGUES = [
        {"name": 'Premier League', "country": 'England'},
        {"name": 'La Liga', "country": 'Spain'},
        {"name": 'Bundesliga', "country": 'Germany'},
        {"name": 'UEFA Champions League', "country": 'World'}
    ]

    # Default prediction limit (None = no limit)
    PREDICTION_LIMIT = 30

    # Maximum number of fixtures to consider for team stats
    MAX_FIXTURES = 15

    # Maximum number of days to look back for team stats
    MAX_DAYS_BACK = 90

    DEFAULT_LIMIT = 35

settings = Settings()
