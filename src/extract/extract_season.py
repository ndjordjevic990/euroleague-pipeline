"""Extract all games for a Euroleague season."""

import logging
import sys
import time

from src.config import REQUEST_DELAY
from src.extract.api_client import fetch_game, save_game

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def extract_season(season_code: str, max_game_code: int = 400) -> list[int]:
    """Extract all games for a season.
    
    Since there's no schedule API, we iterate through game codes
    and stop after consecutive misses.
    
    Args:
        season_code: Season identifier (e.g., "E2024")
        max_game_code: Maximum game code to try
        
    Returns:
        List of successfully extracted game codes.
    """
    logger.info(f"{'='*60}")
    logger.info(f"Starting extraction for season {season_code}")
    logger.info(f"{'='*60}")

    extracted_games = []
    consecutive_misses = 0
    max_consecutive_misses = 20  # Stop after 20 misses in a row

    for game_code in range(1, max_game_code + 1):
        logger.info(f"--- Game {game_code} ---")

        game_data = fetch_game(season_code, game_code)

        if game_data is None:
            consecutive_misses += 1
            logger.info(f"Game {game_code} not found (miss streak: {consecutive_misses})")

            if consecutive_misses >= max_consecutive_misses:
                logger.info(
                    f"Stopping: {max_consecutive_misses} consecutive misses. "
                    f"Likely reached end of season."
                )
                break
            continue

        # Game exists — save it
        consecutive_misses = 0
        save_game(game_data, season_code, game_code)
        extracted_games.append(game_code)

        # Small delay between games
        time.sleep(REQUEST_DELAY)

    logger.info(f"{'='*60}")
    logger.info(f"Season {season_code} complete: {len(extracted_games)} games extracted")
    logger.info(f"Game codes: {extracted_games[:10]}{'...' if len(extracted_games) > 10 else ''}")
    logger.info(f"{'='*60}")

    return extracted_games


if __name__ == "__main__":
    # Allow running with: python -m src.extract.extract_season E2024
    season = sys.argv[1] if len(sys.argv) > 1 else "E2024"
    extract_season(season)