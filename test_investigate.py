"""Investigate the two merge/lineup issues."""

import json
from src.transform.cleaners import clean_game

with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

cleaned = clean_game(raw_game)

# ============================================================
# ISSUE 1: Unmatched shot event_ids
# ============================================================
print("=" * 70)
print("ISSUE 1: Event ID ranges")
print("=" * 70)

# PBP event IDs per quarter
events = cleaned["events"]
for q in [1, 2, 3, 4, 5]:
    q_events = [e for e in events if e["quarter"] == q]
    if q_events:
        ids = [e["event_id"] for e in q_events]
        print(f"  Q{q}: {len(q_events)} events, IDs {min(ids)} - {max(ids)}")

# Points event IDs
shots = cleaned["shots"]
shot_ids = [s["event_id"] for s in shots]
print(f"\n  Points: {len(shots)} shots, IDs {min(shot_ids)} - {max(shot_ids)}")

# Which shot IDs are NOT in PBP?
pbp_ids = {e["event_id"] for e in events}
unmatched = [s for s in shots if s["event_id"] not in pbp_ids]
print(f"\n  Unmatched shots: {len(unmatched)}")
if unmatched:
    print(f"  First 5 unmatched shot IDs: {[s['event_id'] for s in unmatched[:5]]}")
    print(f"  Their quarters (by minute):")
    for s in unmatched[:5]:
        print(f"    ID={s['event_id']}, minute={s['minute']}, "
              f"clock={s['game_clock']}, player={s['player_name']}")

# ============================================================
# ISSUE 2: IN/OUT ordering at substitution points
# ============================================================
print("\n" + "=" * 70)
print("ISSUE 2: IN/OUT ordering")
print("=" * 70)

# Find substitution pairs
subs = [e for e in events if e["play_type"] in ("IN", "OUT")]
print(f"\n  Total sub events: {len(subs)}")

# Show the first few substitution sequences
print(f"\n  Events around first substitution:")
first_sub_idx = next(i for i, e in enumerate(events) if e["play_type"] in ("IN", "OUT"))
for e in events[first_sub_idx-1 : first_sub_idx+6]:
    print(f"    #{e['event_id']:3d} Q{e['quarter']} {e['marker_time'] or 'N/A':>5s} | "
          f"{e['play_type']:5s} | {e['team_code'] or 'N/A':5s} | "
          f"{e['player_name'] or 'N/A'}")