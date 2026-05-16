import json

with open("data/raw/E2024/game_001.json", "r", encoding="utf-8") as f:
    raw_game = json.load(f)

pbp = raw_game["PlaybyPlay"]
for key, value in pbp.items():
    if isinstance(value, list):
        print(f"  {key:20s}: {len(value)} events")
    else:
        print(f"  {key:20s}: {value}")