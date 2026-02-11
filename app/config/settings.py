from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    # Legacy API (being phased out)
    API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")
    
    # Football-Data.org API v4 (primary data source)
    FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
    FOOTBALL_DATA_BASE_URL = os.getenv("FOOTBALL_DATA_BASE_URL", "http://api.football-data.org/v4")
    
    # Admin API key for protected endpoints (database cleanup, stats, etc.)
    # MUST be set in production to secure admin endpoints
    ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "foo_ball_service")

    # Competitions to track (Football-Data.org competition codes)
    # PL = Premier League, PD = La Liga, BL1 = Bundesliga, CL = Champions League
    # SA = Serie A, ELC = Championship, BSA = Campeonato Brasileiro Série A
    TRACKED_COMPETITIONS = ["PL", "PD", "BL1", "CL", "SA", "ELC"]
    
    # Legacy leagues configuration (for backwards compatibility)
    TRACKED_LEAGUES = [
        {"name": 'Premier League', "country": 'England'},
        {"name": 'La Liga', "country": 'Spain'},
        {"name": 'Bundesliga', "country": 'Germany'},
        {"name": 'UEFA Champions League', "country": 'World'},
        {"name": 'Serie A', "country": 'Italy'},
        {"name": 'Championship', "country": 'England'}
    ]

    # Default prediction limit (None = no limit)
    PREDICTION_LIMIT = 30

    # Maximum number of fixtures to consider for team stats
    MAX_FIXTURES = 15

    # Maximum number of days to look back for team stats
    MAX_DAYS_BACK = 90
    
    # H2H API rate limiting (to stay within free tier limits)
    # Maximum H2H requests per day (free tier is 10 requests/minute)
    MAX_H2H_PER_DAY = 10

    DEFAULT_LIMIT = 35

settings = Settings()
