"""Explore raw data: check completeness, find anomalies across all games."""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def explore_all_seasons():
    raw_dir = Path("data/raw")
    
    # Counters
    total_games = 0
    endpoints_missing = Counter()       # How often each endpoint is None
    endpoints_present = Counter()       # How often each endpoint has data
    pbp_play_types = Counter()          # All PLAYTYPE codes across all games
    points_action_types = Counter()     # All ID_ACTION codes
    player_id_formats = Counter()       # Track ID formats (P###### vs legacy)
    season_game_counts = {}
    games_with_issues = []

    for season_dir in sorted(raw_dir.iterdir()):
        if not season_dir.is_dir():
            continue

        season_code = season_dir.name
        game_count = 0

        for game_file in sorted(season_dir.glob("game_*.json")):
            total_games += 1
            game_count += 1

            with open(game_file, "r", encoding="utf-8") as f:
                game_data = json.load(f)

            # Check endpoint completeness
            expected_endpoints = [
                "Header", "PlayersTeamA", "PlayersTeamB", "Points",
                "PlaybyPlay", "BoxScore", "Evolution", "Comparison",
                "ShootingGraphic",
            ]

            missing = []
            for ep in expected_endpoints:
                if game_data.get(ep) is None:
                    endpoints_missing[ep] += 1
                    missing.append(ep)
                else:
                    endpoints_present[ep] += 1

            if missing:
                games_with_issues.append({
                    "file": str(game_file),
                    "missing": missing,
                })

            # Collect all PBP play types
            pbp = game_data.get("PlaybyPlay")
            if pbp:
                for quarter_key in ["FirstQuarter", "SecondQuarter", "ThirdQuarter",
                                     "FourthQuarter", "ExtraTime"]:
                    quarter_data = pbp.get(quarter_key) or []
                    for event in quarter_data:
                        play_type = event.get("PLAYTYPE", "UNKNOWN")
                        pbp_play_types[play_type] += 1

                        # Check player ID format
                        player_id = event.get("PLAYER_ID", "").strip()
                        if player_id:
                            if player_id.startswith("P") and player_id[1:].isdigit():
                                player_id_formats["P######"] += 1
                            else:
                                player_id_formats[f"legacy:{player_id}"] += 1

            # Collect all Points action types
            points = game_data.get("Points")
            if points:
                rows = points.get("Rows", [])
                for row in rows:
                    action = row.get("ID_ACTION", "UNKNOWN")
                    points_action_types[action] += 1

        season_game_counts[season_code] = game_count
        logger.info(f"{season_code}: {game_count} games scanned")

    # Print results
    print("\n" + "=" * 70)
    print("DATA EXPLORATION REPORT")
    print("=" * 70)

    print(f"\n📊 TOTAL: {total_games} games across {len(season_game_counts)} seasons")
    for season, count in sorted(season_game_counts.items()):
        print(f"   {season}: {count} games")

    print(f"\n📦 ENDPOINT COMPLETENESS:")
    for ep in expected_endpoints:
        present = endpoints_present.get(ep, 0)
        missing = endpoints_missing.get(ep, 0)
        pct = (present / total_games * 100) if total_games > 0 else 0
        status = "✅" if missing == 0 else "⚠️"
        print(f"   {status} {ep:20s}: {present:>5} present, {missing:>5} missing ({pct:.1f}%)")

    print(f"\n🏀 PLAY-BY-PLAY EVENT TYPES ({len(pbp_play_types)} unique):")
    for play_type, count in pbp_play_types.most_common():
        print(f"   {play_type:10s}: {count:>8,}")

    print(f"\n🎯 POINTS ACTION TYPES ({len(points_action_types)} unique):")
    for action, count in points_action_types.most_common():
        print(f"   {action:10s}: {count:>8,}")

    print(f"\n🆔 PLAYER ID FORMATS:")
    for fmt, count in player_id_formats.most_common(20):
        print(f"   {fmt:30s}: {count:>8,}")

    if games_with_issues:
        print(f"\n⚠️  GAMES WITH MISSING ENDPOINTS: {len(games_with_issues)}")
        for issue in games_with_issues[:20]:  # Show first 20
            print(f"   {issue['file']}: missing {issue['missing']}")
        if len(games_with_issues) > 20:
            print(f"   ... and {len(games_with_issues) - 20} more")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    explore_all_seasons()