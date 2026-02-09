import requests
from app.config.settings import settings

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": settings.API_FOOTBALL_KEY
}

def get_fixtures(date: str, timezone: str = "Europe/London"):
    """
    Fetches fixtures for a given date and timezone.
    
    Args:
        date: Date in YYYY-MM-DD format.
        timezone: Timezone string, e.g., "Europe/London".
    
    Returns:
        List of fixtures.
    """
    url = f"{BASE_URL}/fixtures"
    params = {"date": date, "timezone": timezone}

    response = requests.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()["response"]

def get_team_statistics(team_id: int, league_id: int, season: int):
    url = f"{BASE_URL}/teams/statistics"
    params = {
        "team": team_id,
        "league": league_id,
        "season": season
    }

    response = requests.get(url, headers=HEADERS, params=params, timeout=15)
    response.raise_for_status()
    return response.json()["response"]
