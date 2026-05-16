"""Debug lineup tracking step by step."""

import json
from src.transform.cleaners import clean_game
from src.transform.lineups import get_starters, LineupTracker, _reorder_substitutions

with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

cleaned = clean_game(raw_game)
events = cleaned["events"]
header = cleaned["header"]

team_a = header["CodeTeamA"]
team_b = header["CodeTeamB"]

starters_a = get_starters(cleaned["players_team_a"])
starters_b = get_starters(cleaned["players_team_b"])

print(f"Starters {team_a} ({len(starters_a)}): {sorted(starters_a)}")
print(f"Starters {team_b} ({len(starters_b)}): {sorted(starters_b)}")

# Reorder subs
events = _reorder_substitutions(events)

# Track and print every event where lineup changes or is wrong
tracker = LineupTracker(starters_a, starters_b, team_a, team_b)

for event in events:
    prev_a = len(tracker.on_court_a)
    prev_b = len(tracker.on_court_b)
    
    tracker.process_event(event)
    
    size_a = event["lineup_size_a"]
    size_b = event["lineup_size_b"]
    
    # Print if: substitution, or lineup size is wrong, or lineup size changed
    is_sub = event["play_type"] in ("IN", "OUT")
    is_bad = size_a != 5 or size_b != 5
    changed = size_a != prev_a or size_b != prev_b
    
    if is_sub or is_bad or changed:
        marker = " ⚠️" if is_bad else ""
        print(f"  #{event['event_id']:>3d} Q{event['quarter']} {event['marker_time'] or 'N/A':>5s} | "
              f"{event['play_type']:5s} | {event['team_code'] or 'N/A':>5s} | "
              f"{event['player_name'] or 'N/A':25s} | "
              f"{team_a}={size_a} {team_b}={size_b}{marker}")