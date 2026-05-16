"""Investigate duplicate play type codes and unknown codes."""

import json
from pathlib import Path
from collections import defaultdict

raw_dir = Path("data/raw")

# Track play types by their TYPE field value
type_field_by_playtype = defaultdict(lambda: defaultdict(int))

# Collect examples of unknown codes
unknown_examples = defaultdict(list)
unknown_codes = {"C", "B", "F", "CCH", "CMTI", "CMD"}

# Check for casing issues
playtype_raw_forms = defaultdict(lambda: defaultdict(int))

game_count = 0

for season_dir in sorted(raw_dir.iterdir()):
    if not season_dir.is_dir():
        continue

    for game_file in sorted(season_dir.glob("game_*.json")):
        game_count += 1

        with open(game_file, "r", encoding="utf-8") as f:
            game_data = json.load(f)

        pbp = game_data.get("PlaybyPlay")
        if not pbp:
            continue

        for quarter_key in ["FirstQuarter", "SecondQuarter", "ThirdQuarter",
                             "FourthQuarter", "ExtraTime"]:
            quarter_data = pbp.get(quarter_key) or []
            for event in quarter_data:
                pt = event.get("PLAYTYPE", "")
                type_val = event.get("TYPE", "?")

                # Track TYPE field values per PLAYTYPE
                type_field_by_playtype[pt][type_val] += 1

                # Track exact raw string (detect casing/whitespace)
                playtype_raw_forms[pt][repr(pt)] += 1

                # Collect examples of unknown codes
                if pt in unknown_codes and len(unknown_examples[pt]) < 3:
                    unknown_examples[pt].append({
                        "file": game_file.name,
                        "season": season_dir.name,
                        "NUMBEROFPLAY": event.get("NUMBEROFPLAY"),
                        "PLAYTYPE": pt,
                        "TYPE": type_val,
                        "PLAYINFO": event.get("PLAYINFO"),
                        "PLAYER": event.get("PLAYER"),
                        "TEAM": event.get("TEAM"),
                        "CODETEAM": event.get("CODETEAM"),
                        "MARKERTIME": event.get("MARKERTIME"),
                    })

print(f"Scanned {game_count} games\n")

print("=" * 60)
print("TYPE FIELD VALUES PER PLAYTYPE")
print("=" * 60)
for pt in sorted(type_field_by_playtype.keys()):
    type_counts = type_field_by_playtype[pt]
    if len(type_counts) > 1 or 0 not in type_counts:
        # Only show interesting cases (multiple TYPE values, or TYPE != 0)
        print(f"\n  {pt}:")
        for type_val, count in sorted(type_counts.items()):
            print(f"    TYPE={type_val}: {count:>8,}")

print("\n" + "=" * 60)
print("EXAMPLES OF UNKNOWN CODES")
print("=" * 60)
for code, examples in sorted(unknown_examples.items()):
    print(f"\n  {code}:")
    for ex in examples:
        print(f"    {ex}")