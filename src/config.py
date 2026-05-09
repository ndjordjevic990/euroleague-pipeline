"""Configuration for the Euroleague ETL pipeline."""

BASE_URL = "https://live.euroleague.net/api"

ENDPOINTS = [
    "Header",
    "Players",
    "Points",
    "PlaybyPlay",
    "BoxScore",
    "Evolution",
    "Comparison",
    "ShootingGraphic",
]

# Seasons available (Euroleague uses format E + start year)
# E2021 = 2021-2022 season, E2022 = 2022-2023, etc.
SEASONS = [
    "E2016",
    "E2017",
    "E2018",
    "E2019",
    "E2020",
    "E2021",
    "E2022",
    "E2023",
    "E2024",
    "E2025",
]

# API request settings
REQUEST_TIMEOUT = 15        # seconds
REQUEST_DELAY = 0.5         # seconds between requests (be respectful)
MAX_RETRIES = 3

# Data storage
RAW_DATA_DIR = "data/raw"