"""Test the cleaners on a real game file."""

import json
from src.transform.cleaners import clean_game

# Load a raw game
with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

# Clean it
cleaned = clean_game(raw_game)

# Check header
h = cleaned["header"]
print("=== HEADER ===")
print(f"  Teams: {h['TeamA']} vs {h['TeamB']}")
print(f"  Score: {h['ScoreA']}-{h['ScoreB']} (type: {type(h['ScoreA']).__name__})")
print(f"  Fouls key fixed: {'FoulsA' in h and 'FoultsA' not in h}")
print(f"  Team codes: '{h['CodeTeamA']}' '{h['CodeTeamB']}' (no whitespace: {' ' not in h['CodeTeamA']})")

# Check players
print(f"\n=== PLAYERS ===")
for p in cleaned["players_team_a"][:3]:
    print(f"  {p['player_name']:25s} | ID: {p['player_id']:10s} | {p['position']:8s} | Starter: {p['is_starter']}")

# Check events
print(f"\n=== EVENTS ===")
print(f"  Total events: {len(cleaned['events'])}")
events = cleaned["events"]
play_types = set(e["play_type"] for e in events)
print(f"  Unique play types: {sorted(play_types)}")
print(f"  First 5 events:")
for e in events[:5]:
    print(f"    #{e['event_id']:3d} Q{e['quarter']} {e['marker_time'] or 'N/A':>5s} | "
          f"{e['play_type']:6s} | {e['player_name'] or 'N/A':25s} | {e['play_info'] or ''}")

# Check whitespace is gone
bad_events = [e for e in events if e["play_type"] and " " in e["play_type"]]
print(f"  Events with whitespace in play_type: {len(bad_events)}")

# Check shots
print(f"\n=== SHOTS ===")
print(f"  Total shots: {len(cleaned['shots'])}")
fts = [s for s in cleaned["shots"] if s["action_code"] == "FTM" or s["action_code"] == "FTA"]
ft_with_coords = [s for s in fts if s["coord_x"] is not None]
print(f"  Free throws: {len(fts)} (with coords after sentinel filter: {len(ft_with_coords)})")

# Check boxscore
print(f"\n=== BOXSCORE ===")
for team in cleaned["boxscore"]["team_stats"]:
    print(f"  {team['team_name']} ({team['coach']}):")
    for p in team["players"][:3]:
        mins = f"{p['minutes_seconds']//60}:{p['minutes_seconds']%60:02d}" if p["minutes_seconds"] else "DNP"
        print(f"    {p['player_name']:25s} | {mins:>5s} | {p['points']:2d}pts | +/-: {p['plus_minus']:+d}")