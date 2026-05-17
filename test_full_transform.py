"""Test the complete transformation pipeline on a real game."""

import json
import logging
from src.transform.cleaners import clean_game
from src.transform.parsers import enrich_event_with_parsed_info
from src.transform.merger import merge_events_with_shots, forward_fill_score
from src.transform.lineups import track_lineups

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)

# Test on the problematic game
with open("data/raw/E2016/game_040.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

cleaned = clean_game(raw_game)
header = cleaned["header"]
events = cleaned["events"]
shots = cleaned["shots"]

print(f"Game: {header['TeamA']} vs {header['TeamB']}")
print(f"Score: {header['ScoreA']}-{header['ScoreB']}")
print(f"{'='*70}")

# Step 1: Parse PLAYINFO
for event in events:
    enrich_event_with_parsed_info(event)
print(f"✓ Parsed PLAYINFO for {len(events)} events")

# Step 2: Merge PBP + Points
merge_events_with_shots(events, shots)

# Step 3: Lineup tracking (reorders events for substitutions)
team_a = header["CodeTeamA"]
team_b = header["CodeTeamB"]
events, warnings = track_lineups(
    events, cleaned["players_team_a"], cleaned["players_team_b"],
    team_a, team_b
)
print(f"✓ Lineup tracking complete. Warnings: {len(warnings)}")

bad = [e for e in events if e["lineup_size_a"] != 5 or e["lineup_size_b"] != 5]
print(f"✓ Lineup integrity: {len(bad)} events with non-5v5 lineup")

# Step 4: Forward-fill scores AFTER lineup reordering
forward_fill_score(events)

# Check final score
last_event = events[-1]
print(f"\n✓ Final event score: {last_event['score_a']}-{last_event['score_b']}")
print(f"  Header score:      {header['ScoreA']}-{header['ScoreB']}")
print(f"  Match: {last_event['score_a'] == header['ScoreA'] and last_event['score_b'] == header['ScoreB']}")

print(f"\n{'='*70}")
print(f"TRANSFORMATION COMPLETE")
print(f"  Events: {len(events)}")
print(f"  With coordinates: {len([e for e in events if e.get('coord_x') is not None])}")
print(f"  With UTC: {len([e for e in events if e.get('utc')])}")
print(f"  With lineup: {len([e for e in events if e.get('lineup_a')])}")
print(f"{'='*70}")