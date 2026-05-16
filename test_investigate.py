"""Investigate substitution ordering."""

import json
from src.transform.cleaners import clean_game

with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

cleaned = clean_game(raw_game)
events = cleaned["events"]

# Show ALL substitution events and their neighbors
subs = [(i, e) for i, e in enumerate(events) if e["play_type"] in ("IN", "OUT")]

print("First 20 substitution events:")
print(f"  {'ID':>4s} {'Q':>2s} {'Time':>5s} {'Type':>4s} {'Team':>5s} {'Player'}")
print(f"  {'-'*50}")

for idx, e in subs[:20]:
    print(f"  {e['event_id']:>4d} Q{e['quarter']} {e['marker_time'] or 'N/A':>5s} "
          f"{e['play_type']:>4s} {e['team_code'] or '':>5s} {e['player_name'] or 'N/A'}")