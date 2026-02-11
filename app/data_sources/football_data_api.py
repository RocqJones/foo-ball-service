"""
Football-Data.org v4 API client
https://www.football-data.org/documentation/api
"""
import requests
from typing import Optional, List, Dict, Any
from app.config.settings import settings
from app.utils.logger import logger
import time


BASE_URL = settings.FOOTBALL_DATA_BASE_URL

HEADERS = {
    "X-Auth-Token": settings.FOOTBALL_DATA_API_KEY
}

# Rate limiting and retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
TIMEOUT = 15  # seconds


def _make_request(url: str, params: Optional[Dict[str, Any]] = None, retries: int = 0) -> Dict[str, Any]:
    """
    Make HTTP request with retry logic and exponential backoff.
    
    Args:
        url: Full URL to request
        params: Optional query parameters
        retries: Current retry attempt (internal use)
    
    Returns:
        JSON response as dictionary
    
    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        
        # Log rate limit info if available
        if "X-Requests-Available-Minute" in response.headers:
            logger.info(f"API rate limit - Remaining: {response.headers['X-Requests-Available-Minute']}")
        
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:  # Rate limit exceeded
            if retries < MAX_RETRIES:
                wait_time = RETRY_DELAY * (2 ** retries)  # Exponential backoff
                logger.warning(f"Rate limit hit. Retrying in {wait_time}s... (attempt {retries + 1}/{MAX_RETRIES})")
                time.sleep(wait_time)
                return _make_request(url, params, retries + 1)
            else:
                logger.error(f"Max retries exceeded for {url}")
                raise
        
        elif e.response.status_code == 403:
            logger.error(f"Forbidden: Check API key permissions or competition access - {url}")
            raise
        
        elif e.response.status_code == 404:
            logger.error(f"Resource not found: {url}")
            raise
        
        else:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            raise
    
    except requests.exceptions.Timeout:
        if retries < MAX_RETRIES:
            wait_time = RETRY_DELAY * (2 ** retries)
            logger.warning(f"Request timeout. Retrying in {wait_time}s... (attempt {retries + 1}/{MAX_RETRIES})")
            time.sleep(wait_time)
            return _make_request(url, params, retries + 1)
        else:
            logger.error(f"Max retries exceeded due to timeout for {url}")
            raise
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {url}: {str(e)}")
        raise


def get_competitions() -> List[Dict[str, Any]]:
    """
    Fetch all available competitions for the current plan.
    
    Returns:
        List of competition dictionaries with structure:
        {
            "id": int,
            "name": str,
            "code": str,
            "type": str,
            "emblem": str,
            "currentSeason": {...},
            "area": {...}
        }
    
    Example:
        competitions = get_competitions()
    """
    url = f"{BASE_URL}/competitions"
    
    logger.info(f"Fetching competitions from {url}")
    data = _make_request(url)
    
    competitions = data.get("competitions", [])
    logger.info(f"Fetched {len(competitions)} competitions")
    
    return competitions


def get_scheduled_matches(competition_code: str, season: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch scheduled (upcoming) matches for a specific competition.
    
    Args:
        competition_code: Competition code (e.g., 'PL', 'PD', 'BL1', 'CL')
        season: Optional season year (e.g., '2025'). If None, uses current season.
    
    Returns:
        Dictionary with structure:
        {
            "competition": {...},
            "matches": [
                {
                    "id": int,
                    "utcDate": str,
                    "status": str,
                    "homeTeam": {...},
                    "awayTeam": {...},
                    "score": {...}
                },
                ...
            ]
        }
    
    Example:
        matches = get_scheduled_matches('PL')
    """
    url = f"{BASE_URL}/competitions/{competition_code}/matches"
    params = {"status": "SCHEDULED"}
    
    if season:
        params["season"] = season
    
    logger.info(f"Fetching scheduled matches for {competition_code}")
    data = _make_request(url, params)
    
    matches = data.get("matches", [])
    logger.info(f"Fetched {len(matches)} scheduled matches for {competition_code}")
    
    return {
        "competition": data.get("competition", {}),
        "matches": matches,
        "filters": data.get("filters", {}),
        "resultSet": data.get("resultSet", {})
    }


def get_head_to_head(match_id: int, limit: int = 10) -> Dict[str, Any]:
    """
    Fetch head-to-head statistics for a specific match.
    
    Args:
        match_id: Match ID
        limit: Number of past meetings to retrieve (default: 10)
    
    Returns:
        Dictionary with structure:
        {
            "aggregates": {
                "numberOfMatches": int,
                "totalGoals": int,
                "homeTeam": {"wins": int, "draws": int, "losses": int},
                "awayTeam": {"wins": int, "draws": int, "losses": int}
            },
            "matches": [
                {
                    "id": int,
                    "utcDate": str,
                    "homeTeam": {...},
                    "awayTeam": {...},
                    "score": {...}
                },
                ...
            ]
        }
    
    Example:
        h2h = get_head_to_head(538036, limit=10)
    """
    url = f"{BASE_URL}/matches/{match_id}/head2head"
    params = {"limit": limit}
    
    logger.info(f"Fetching head-to-head data for match {match_id}")
    data = _make_request(url, params)
    
    matches = data.get("matches", [])
    logger.info(f"Fetched {len(matches)} head-to-head matches for match {match_id}")
    
    return {
        "aggregates": data.get("aggregates", {}),
        "matches": matches,
        "filters": data.get("filters", {}),
        "resultSet": data.get("resultSet", {})
    }


def get_team_matches(team_id: int, limit: int = 10, status: str = "FINISHED") -> List[Dict[str, Any]]:
    """
    Fetch recent matches for a specific team.
    
    Args:
        team_id: Team ID
        limit: Number of matches to retrieve (default: 10)
        status: Match status filter (default: "FINISHED")
    
    Returns:
        List of match dictionaries
    
    Example:
        matches = get_team_matches(58, limit=5)
    """
    url = f"{BASE_URL}/teams/{team_id}/matches"
    params = {
        "limit": limit,
        "status": status
    }
    
    logger.info(f"Fetching matches for team {team_id}")
    data = _make_request(url, params)
    
    matches = data.get("matches", [])
    logger.info(f"Fetched {len(matches)} matches for team {team_id}")
    
    return matches
