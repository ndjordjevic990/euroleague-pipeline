"""Check if duplicate play types are caused by whitespace differences."""

import json
from pathlib import Path
from collections import Counter

raw_dir = Path("data/raw")
playtype_repr = Counter()

for season_dir in sorted(raw_dir.iterdir()):
    if not season_dir.is_dir():
        continue
    for game_file in season_dir.glob("game_*.json"):
        with open(game_file, "r", encoding="utf-8") as f:
            game_data = json.load(f)

        pbp = game_data.get("PlaybyPlay")
        if not pbp:
            continue

        for quarter_key in ["FirstQuarter", "SecondQuarter", "ThirdQuarter",
                             "FourthQuarter", "ExtraTime"]:
            for event in (pbp.get(quarter_key) or []):
                pt = event.get("PLAYTYPE", "")
                # Use repr() to expose hidden whitespace/casing
                playtype_repr[repr(pt)] += 1

# Show all forms, sorted by the stripped value
print("PLAYTYPE raw representations:")
print("-" * 50)
for raw_form, count in sorted(playtype_repr.items()):
    print(f"  {raw_form:20s}: {count:>8,}")