"""Extract multiple seasons overnight."""

import logging

from src.extract.extract_season import extract_season

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SEASONS_TO_EXTRACT = [
    "E2016",
    "E2017",
    "E2018",
    "E2019",
    "E2020",
    "E2021",
    "E2022",
    # "E2023",  # Already done
    # "E2024",  # Already done
    "E2025",
]

if __name__ == "__main__":
    results = {}

    for season in SEASONS_TO_EXTRACT:
        try:
            extracted = extract_season(season)
            results[season] = len(extracted)
        except Exception as e:
            logger.error(f"Season {season} failed: {e}")
            results[season] = "FAILED"

    # Final summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("OVERNIGHT RUN COMPLETE")
    logger.info("=" * 60)
    for season, count in results.items():
        logger.info(f"  {season}: {count} games extracted")
    logger.info("=" * 60)