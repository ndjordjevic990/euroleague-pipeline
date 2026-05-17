"""Query the loaded DuckDB database."""

import duckdb

conn = duckdb.connect("data/euroleague.duckdb", read_only=True)

print("=" * 70)
print("EUROLEAGUE DATABASE OVERVIEW")
print("=" * 70)

print("\n📊 Table sizes:")
for table in ["dim_games", "dim_teams", "dim_players", "fact_events", 
              "fact_boxscore", "fact_score_evolution", "fact_shooting", "fact_comparison"]:
    count = conn.sql(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    print(f"  {table:25s}: {count:>10,} rows")

print("\n📅 Games by season:")
conn.sql("""
    SELECT season_code, COUNT(*) as games, 
           MIN(date) as first_game, MAX(date) as last_game
    FROM dim_games 
    GROUP BY season_code 
    ORDER BY season_code
""").show()

print("\n🏆 All-time top scorers (single game):")
conn.sql("""
    SELECT b.player_name, g.season_code, g.team_a_name || ' vs ' || g.team_b_name as matchup,
           b.points, b.fg3m, b.assists, b.total_rebounds
    FROM fact_boxscore b
    JOIN dim_games g ON b.game_key = g.game_key
    ORDER BY b.points DESC
    LIMIT 15
""").show()

print("\n🎯 Season shooting trends (3PT%):")
conn.sql("""
    SELECT g.season_code,
           COUNT(*) FILTER (WHERE e.play_type = '3FGM') as threes_made,
           COUNT(*) FILTER (WHERE e.play_type IN ('3FGM','3FGA')) as threes_attempted,
           ROUND(COUNT(*) FILTER (WHERE e.play_type = '3FGM') * 100.0 / 
                 NULLIF(COUNT(*) FILTER (WHERE e.play_type IN ('3FGM','3FGA')), 0), 1) as three_pct
    FROM fact_events e
    JOIN dim_games g ON e.game_key = g.game_key
    GROUP BY g.season_code
    ORDER BY g.season_code
""").show()

print("\n🏟️ Top 10 highest-scoring games:")
conn.sql("""
    SELECT season_code, date, team_a_name, score_a, score_b, team_b_name,
           score_a + score_b as total
    FROM dim_games
    ORDER BY total DESC
    LIMIT 10
""").show()

print("\n👥 Most games played (career across all seasons):")
conn.sql("""
    SELECT player_name, COUNT(DISTINCT game_key) as games,
           ROUND(AVG(points), 1) as avg_pts,
           ROUND(AVG(assists), 1) as avg_ast,
           ROUND(AVG(total_rebounds), 1) as avg_reb
    FROM fact_boxscore
    WHERE minutes_seconds > 0
    GROUP BY player_name
    HAVING COUNT(DISTINCT game_key) >= 100
    ORDER BY games DESC
    LIMIT 15
""").show()

# Find the 5 failed games
print("\n⚠️ Games in raw data but NOT in database:")
import json
from pathlib import Path

raw_dir = Path("data/raw")
db_game_keys = set()
for row in conn.sql("SELECT game_key FROM dim_games").fetchall():
    db_game_keys.add(row[0])

missing = []
for season_dir in sorted(raw_dir.iterdir()):
    if not season_dir.is_dir():
        continue
    for game_file in sorted(season_dir.glob("game_*.json")):
        season = season_dir.name
        game_code = int(game_file.stem.split("_")[1])
        game_key = f"{season}_{game_code:03d}"
        if game_key not in db_game_keys:
            missing.append(game_key)

for gk in missing:
    print(f"  {gk}")

conn.close()