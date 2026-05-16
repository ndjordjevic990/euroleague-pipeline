"""Test the PLAYINFO parser on real game data."""

import json
from src.transform.cleaners import clean_game
from src.transform.parsers import enrich_event_with_parsed_info

# Load and clean a game
with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

cleaned = clean_game(raw_game)

# Enrich all events with parsed PLAYINFO
for event in cleaned["events"]:
    enrich_event_with_parsed_info(event)

# Show examples of each type of parsing
print("=== SHOT EVENTS (parsed made/attempted/points) ===")
shot_types = ["2FGM", "2FGA", "3FGM", "3FGA", "FTM", "FTA"]
for st in shot_types:
    examples = [e for e in cleaned["events"] if e["play_type"] == st]
    if examples:
        e = examples[0]
        print(f"  {st:6s} | {e['player_name']:25s} | {e['play_info']}")
        print(f"         → made={e.get('made')}, attempted={e.get('attempted')}, "
              f"total_pts={e.get('player_total_points')}")

print(f"\n=== COUNT EVENTS (parsed cumulative count) ===")
count_types = ["D", "O", "AS", "ST", "TO", "FV", "CM", "RV"]
for ct in count_types:
    examples = [e for e in cleaned["events"] if e["play_type"] == ct]
    if examples:
        e = examples[0]
        print(f"  {ct:6s} | {e['player_name']:25s} | {e['play_info']}")
        print(f"         → cumulative_count={e.get('cumulative_count')}")

# Verify parsing coverage
print(f"\n=== PARSING COVERAGE ===")
total = len(cleaned["events"])
has_parsed = len([e for e in cleaned["events"]
                  if "made" in e or "cumulative_count" in e])
no_info = len([e for e in cleaned["events"]
               if e["play_type"] in ("BP", "EP", "IN", "OUT", "JB",
                                      "TPOFF", "TOUT", "TOUT_TV", "EG", "CCH")])
unparsed = total - has_parsed - no_info
print(f"  Total events:           {total}")
print(f"  Successfully parsed:    {has_parsed}")
print(f"  No info expected:       {no_info} (BP, EP, IN, OUT, JB, TOUT, etc.)")
print(f"  Unparsed (unexpected):  {unparsed}")

if unparsed > 0:
    print(f"\n  Unparsed events:")
    for e in cleaned["events"]:
        if ("made" not in e and "cumulative_count" not in e
            and e["play_type"] not in ("BP", "EP", "IN", "OUT", "JB",
                                        "TPOFF", "TOUT", "TOUT_TV", "EG", "CCH")):
            print(f"    {e['play_type']:6s} | {e['play_info']}")