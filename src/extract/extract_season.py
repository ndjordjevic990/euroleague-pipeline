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
    """Extract all games for a season, skipping already downloaded games.
    
    Since there's no schedule API, we iterate through game codes
    and stop after consecutive misses.
    
    Args:
        season_code: Season identifier (e.g., "E2024")
        max_game_code: Maximum game code to try
        
    Returns:
        List of successfully extracted game codes.
    """
    from pathlib import Path
    from src.config import RAW_DATA_DIR

    season_dir = Path(RAW_DATA_DIR) / season_code

    logger.info(f"{'='*60}")
    logger.info(f"Starting extraction for season {season_code}")
    logger.info(f"{'='*60}")

    extracted_games = []
    skipped_games = []
    consecutive_misses = 0
    max_consecutive_misses = 20

    for game_code in range(1, max_game_code + 1):
        # Skip if already downloaded
        file_path = season_dir / f"game_{game_code:03d}.json"
        if file_path.exists():
            skipped_games.append(game_code)
            consecutive_misses = 0  # Existing file = game exists
            continue

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

        consecutive_misses = 0
        save_game(game_data, season_code, game_code)
        extracted_games.append(game_code)

        time.sleep(REQUEST_DELAY)

    logger.info(f"{'='*60}")
    logger.info(f"Season {season_code} complete:")
    logger.info(f"  Skipped (already existed): {len(skipped_games)}")
    logger.info(f"  Newly extracted: {len(extracted_games)}")
    logger.info(f"  Total games: {len(skipped_games) + len(extracted_games)}")
    logger.info(f"{'='*60}")

    return extracted_games


if __name__ == "__main__":
    # Allow running with: python -m src.extract.extract_season E2024
    season = sys.argv[1] if len(sys.argv) > 1 else "E2024"
    extract_season(season)