"""API client for extracting data from the Euroleague Live API."""

import json
import logging
import time
from pathlib import Path

import requests

from src.config import (
    BASE_URL,
    ENDPOINTS,
    MAX_RETRIES,
    RAW_DATA_DIR,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)


def fetch_endpoint(endpoint: str, season_code: str, game_code: int) -> dict | None:
    """Fetch a single API endpoint for a given game.
    
    Args:
        endpoint: API endpoint name (e.g., "Header", "PlaybyPlay")
        season_code: Season identifier (e.g., "E2024")
        game_code: Game number within the season
        
    Returns:
        Parsed JSON response as dict/list, or None if request failed.
    """
    url = f"{BASE_URL}/{endpoint}"
    params = {"gamecode": game_code, "seasoncode": season_code}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()

            # Check if the response is empty/meaningless
            # Header returns empty TeamA if game doesn't exist
            if endpoint == "Header" and not data.get("TeamA"):
                logger.debug(f"No game found: {season_code} game {game_code}")
                return None

            logger.info(f"✓ {endpoint} | {season_code} game {game_code}")
            return data

        except requests.exceptions.HTTPError as e:
            logger.warning(
                f"✗ {endpoint} | {season_code} game {game_code} | "
                f"HTTP {e.response.status_code} (attempt {attempt}/{MAX_RETRIES})"
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"✗ {endpoint} | {season_code} game {game_code} | "
                f"Connection error (attempt {attempt}/{MAX_RETRIES})"
            )
        except requests.exceptions.Timeout:
            logger.warning(
                f"✗ {endpoint} | {season_code} game {game_code} | "
                f"Timeout (attempt {attempt}/{MAX_RETRIES})"
            )
        except requests.exceptions.JSONDecodeError:
            logger.warning(
                f"✗ {endpoint} | {season_code} game {game_code} | "
                f"Invalid JSON response (attempt {attempt}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES:
            wait_time = attempt * 2  # Exponential backoff: 2s, 4s
            time.sleep(wait_time)

    logger.error(f"✗ {endpoint} | {season_code} game {game_code} | Failed after {MAX_RETRIES} attempts")
    return None


def fetch_players(season_code: str, game_code: int, team_code: str) -> list | None:
    """Fetch players for a specific team in a game.
    
    The Players endpoint requires additional team parameters
    that differ from other endpoints.
    
    Args:
        season_code: Season identifier (e.g., "E2024")
        game_code: Game number within the season
        team_code: Three-letter team code (e.g., "MCO", "BAR")
        
    Returns:
        List of player dicts, or None if request failed.
    """
    url = f"{BASE_URL}/Players"
    params = {
        "gamecode": game_code,
        "seasoncode": season_code,
        "equipo": team_code,
        "temp": season_code,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()

            data = response.json()
            logger.info(f"✓ Players ({team_code}) | {season_code} game {game_code}")
            return data

        except requests.exceptions.HTTPError as e:
            logger.warning(
                f"✗ Players ({team_code}) | {season_code} game {game_code} | "
                f"HTTP {e.response.status_code} (attempt {attempt}/{MAX_RETRIES})"
            )
        except requests.exceptions.ConnectionError:
            logger.warning(
                f"✗ Players ({team_code}) | {season_code} game {game_code} | "
                f"Connection error (attempt {attempt}/{MAX_RETRIES})"
            )
        except requests.exceptions.Timeout:
            logger.warning(
                f"✗ Players ({team_code}) | {season_code} game {game_code} | "
                f"Timeout (attempt {attempt}/{MAX_RETRIES})"
            )
        except (requests.exceptions.JSONDecodeError, ValueError):
            logger.warning(
                f"✗ Players ({team_code}) | {season_code} game {game_code} | "
                f"Invalid JSON (attempt {attempt}/{MAX_RETRIES})"
            )

        if attempt < MAX_RETRIES:
            wait_time = attempt * 2
            time.sleep(wait_time)

    logger.error(
        f"✗ Players ({team_code}) | {season_code} game {game_code} | "
        f"Failed after {MAX_RETRIES} attempts"
    )
    return None


def fetch_game(season_code: str, game_code: int) -> dict | None:
    """Fetch all endpoints for a single game.
    
    First fetches Header to verify the game exists and get team codes,
    then fetches Players for each team, then all remaining endpoints.
    
    Args:
        season_code: Season identifier (e.g., "E2024")
        game_code: Game number within the season
        
    Returns:
        Dict with endpoint names as keys and response data as values,
        or None if the game doesn't exist.
    """
    # First check if game exists via Header
    header = fetch_endpoint("Header", season_code, game_code)
    if header is None:
        return None

    game_data = {"Header": header}
    time.sleep(REQUEST_DELAY)

    # Extract team codes from Header (strip whitespace!)
    team_a_code = header.get("CodeTeamA", "").strip()
    team_b_code = header.get("CodeTeamB", "").strip()

    # Fetch Players for each team
    if team_a_code:
        players_a = fetch_players(season_code, game_code, team_a_code)
        game_data["PlayersTeamA"] = players_a
        time.sleep(REQUEST_DELAY)

    if team_b_code:
        players_b = fetch_players(season_code, game_code, team_b_code)
        game_data["PlayersTeamB"] = players_b
        time.sleep(REQUEST_DELAY)

    # Fetch remaining endpoints (skip Header and Players)
    for endpoint in ENDPOINTS:
        if endpoint in ("Header", "Players"):
            continue

        data = fetch_endpoint(endpoint, season_code, game_code)
        game_data[endpoint] = data
        time.sleep(REQUEST_DELAY)

    return game_data


def save_game(game_data: dict, season_code: str, game_code: int) -> Path:
    """Save raw game data to a JSON file.
    
    Args:
        game_data: Dict containing all endpoint responses for a game
        season_code: Season identifier
        game_code: Game number
        
    Returns:
        Path to the saved file.
    """
    # Create directory: data/raw/E2024/
    season_dir = Path(RAW_DATA_DIR) / season_code
    season_dir.mkdir(parents=True, exist_ok=True)

    # Save as: data/raw/E2024/game_001.json
    file_path = season_dir / f"game_{game_code:03d}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(game_data, f, indent=2, ensure_ascii=False)

    logger.info(f"💾 Saved {file_path} ({file_path.stat().st_size:,} bytes)")
    return file_path