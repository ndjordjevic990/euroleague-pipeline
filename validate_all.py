"""Run transformation on all games and report issues."""

import json
import logging
from pathlib import Path
from src.transform.cleaners import clean_game
from src.transform.parsers import enrich_event_with_parsed_info
from src.transform.merger import merge_events_with_shots, forward_fill_score
from src.transform.lineups import track_lineups

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)

raw_dir = Path("data/raw")
total = 0
success = 0
issues = []
lineup_issues = []

for season_dir in sorted(raw_dir.iterdir()):
    if not season_dir.is_dir():
        continue

    season = season_dir.name
    season_count = 0
    season_ok = 0

    for game_file in sorted(season_dir.glob("game_*.json")):
        total += 1
        season_count += 1
        game_id = f"{season}/{game_file.stem}"

        try:
            with open(game_file, "r", encoding="utf-8") as f:
                raw_game = json.load(f)

            cleaned = clean_game(raw_game)

            # Skip if missing critical endpoints
            if "events" not in cleaned or "shots" not in cleaned:
                issues.append(f"{game_id}: Missing events or shots endpoint")
                continue

            header = cleaned["header"]

            # Parse PLAYINFO
            for event in cleaned["events"]:
                enrich_event_with_parsed_info(event)

            # Merge PBP + Points
            merge_events_with_shots(cleaned["events"], cleaned["shots"])

            # Lineup tracking
            if "players_team_a" in cleaned and "players_team_b" in cleaned:
                team_a = header["CodeTeamA"]
                team_b = header["CodeTeamB"]
                events, warnings = track_lineups(
                    cleaned["events"],
                    cleaned["players_team_a"],
                    cleaned["players_team_b"],
                    team_a, team_b
                )

                bad = [e for e in events if e["lineup_size_a"] != 5 or e["lineup_size_b"] != 5]
                if bad or warnings:
                    lineup_issues.append(
                        f"{game_id}: {len(bad)} non-5v5 events, {len(warnings)} warnings"
                    )
            else:
                events = cleaned["events"]

            # Forward-fill scores
            forward_fill_score(events)

            # Check final score matches header
            last_scoring = None
            for e in reversed(events):
                if e.get("score_a") is not None:
                    last_scoring = e
                    break

            if last_scoring:
                if (last_scoring["score_a"] != header["ScoreA"] or
                    last_scoring["score_b"] != header["ScoreB"]):
                    issues.append(
                        f"{game_id}: Score mismatch - events={last_scoring['score_a']}-{last_scoring['score_b']}, "
                        f"header={header['ScoreA']}-{header['ScoreB']}"
                    )
                    continue

            success += 1
            season_ok += 1

        except Exception as e:
            issues.append(f"{game_id}: EXCEPTION - {type(e).__name__}: {e}")

    print(f"{season}: {season_ok}/{season_count} games OK")

print(f"\n{'='*60}")
print(f"VALIDATION COMPLETE")
print(f"  Total games:      {total}")
print(f"  Fully passing:    {success}")
print(f"  Hard failures:    {len(issues)}")
print(f"  Lineup warnings:  {len(lineup_issues)} games with imperfect lineups")
print(f"  Pass rate:        {success/total*100:.1f}%")
print(f"{'='*60}")

if issues:
    print(f"\nHARD FAILURES ({len(issues)}):")
    for issue in issues[:30]:
        print(f"  {issue}")
    if len(issues) > 30:
        print(f"  ... and {len(issues) - 30} more")

# Summarize lineup issues by season
if lineup_issues:
    print(f"\nLINEUP ISSUES BY SEASON:")
    from collections import Counter
    season_counts = Counter(i.split("/")[0] for i in lineup_issues)
    for season, count in sorted(season_counts.items()):
        print(f"  {season}: {count} games with lineup issues")