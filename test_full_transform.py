"""Test the complete transformation pipeline on a real game."""

import json
from src.transform.cleaners import clean_game
from src.transform.parsers import enrich_event_with_parsed_info
from src.transform.merger import merge_events_with_shots, forward_fill_score
from src.transform.lineups import track_lineups

# Load and clean
with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
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
print(f"\n✓ Parsed PLAYINFO for {len(events)} events")

# Step 2: Merge PBP + Points
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")
merge_events_with_shots(events, shots)

# Step 3: Forward-fill scores
forward_fill_score(events)

# Verify: every event should have a score now
events_without_score = [e for e in events if e.get("score_a") is None]
print(f"✓ Forward-filled scores. Events missing score: {len(events_without_score)}")

# Show score progression around a scoring event
scoring_events = [e for e in events if e["play_type"] in ("2FGM", "3FGM", "FTM")]
if scoring_events:
    idx = events.index(scoring_events[5])  # 6th scoring event
    print(f"\n--- Score context around event #{events[idx]['event_id']} ---")
    for e in events[max(0,idx-2):idx+3]:
        print(f"  #{e['event_id']:3d} {e['play_type']:6s} | "
              f"Score: {e['score_a']}-{e['score_b']} | "
              f"{e['player_name'] or 'N/A':25s} | "
              f"coords: ({e.get('coord_x')}, {e.get('coord_y')})")

# Step 4: Track lineups
team_a_code = header["CodeTeamA"]
team_b_code = header["CodeTeamB"]
events, warnings = track_lineups(
    events, cleaned["players_team_a"], cleaned["players_team_b"],
    team_a_code, team_b_code
)

print(f"\n✓ Lineup tracking complete. Warnings: {len(warnings)}")

# Show lineup at a specific point
mid_event = events[len(events)//2]
print(f"\n--- Lineup at event #{mid_event['event_id']} (Q{mid_event['quarter']}, {mid_event['marker_time']}) ---")
print(f"  {team_a_code} on court ({mid_event['lineup_size_a']}): {mid_event['lineup_a']}")
print(f"  {team_b_code} on court ({mid_event['lineup_size_b']}): {mid_event['lineup_b']}")

# Verify lineup integrity: should always be 5v5
bad_lineups = [e for e in events 
               if e["lineup_size_a"] != 5 or e["lineup_size_b"] != 5]
print(f"\n✓ Lineup integrity: {len(bad_lineups)} events with non-5v5 lineup")

if bad_lineups:
    print(f"  First bad event:")
    e = bad_lineups[0]
    print(f"    #{e['event_id']} {e['play_type']} | "
          f"{team_a_code}={e['lineup_size_a']}, {team_b_code}={e['lineup_size_b']}")

# Final summary
print(f"\n{'='*70}")
print(f"TRANSFORMATION COMPLETE")
print(f"  Events: {len(events)}")
print(f"  With coordinates: {len([e for e in events if e.get('coord_x') is not None])}")
print(f"  With UTC: {len([e for e in events if e.get('utc')])}")
print(f"  With lineup: {len([e for e in events if e.get('lineup_a')])}")
print(f"  Lineup warnings: {len(warnings)}")
print(f"{'='*70}")