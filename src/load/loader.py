"""Load transformed game data into DuckDB."""

import json
import logging
from pathlib import Path

import duckdb

from src.load.schema import SCHEMA_SQL
from src.transform.cleaners import clean_game
from src.transform.parsers import enrich_event_with_parsed_info
from src.transform.merger import merge_events_with_shots, forward_fill_score
from src.transform.lineups import track_lineups

logger = logging.getLogger(__name__)

DB_PATH = "data/euroleague.duckdb"


def get_connection(db_path: str = DB_PATH) -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection, creating the database if needed."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    conn.execute(SCHEMA_SQL)
    return conn


def make_game_key(season_code: str, game_code: int) -> str:
    """Create a unique game key like 'E2024_001'."""
    return f"{season_code}_{game_code:03d}"


def parse_date(date_str: str | None) -> str | None:
    """Parse 'DD/MM/YYYY' to 'YYYY-MM-DD'."""
    if not date_str:
        return None
    try:
        parts = date_str.split("/")
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except (IndexError, ValueError):
        return None


def load_game(conn: duckdb.DuckDBPyConnection, raw_game: dict,
              season_code: str, game_code: int) -> bool:
    """Transform and load a single game into the database.
    
    Returns True if successful, False otherwise.
    """
    game_key = make_game_key(season_code, game_code)

    try:
        # Transform
        cleaned = clean_game(raw_game)
        header = cleaned.get("header")
        if not header:
            return False

        # ── dim_teams ──
        for code, name in [(header["CodeTeamA"], header["TeamA"]),
                           (header["CodeTeamB"], header["TeamB"])]:
            if code:
                conn.execute("""
                    INSERT INTO dim_teams (team_code, team_name)
                    VALUES (?, ?)
                    ON CONFLICT (team_code) DO UPDATE SET team_name = excluded.team_name
                """, [code, name])

        # ── dim_games ──
        # ── dim_games ──
        conn.execute("""
            INSERT INTO dim_games (
                game_key, season_code, game_code, date, hour, stadium, capacity,
                team_a_code, team_b_code, team_a_name, team_b_name,
                score_a, score_b,
                score_q1_a, score_q1_b, score_q2_a, score_q2_b,
                score_q3_a, score_q3_b, score_q4_a, score_q4_b,
                score_ot_a, score_ot_b,
                coach_a, coach_b, referee_1, referee_2, referee_3,
                phase, round, fouls_a, fouls_b, timeouts_a, timeouts_b,
                attendance
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
                ?
            ) ON CONFLICT (game_key) DO NOTHING
        """, [
            game_key, season_code, game_code,
            parse_date(header.get("Date")), header.get("Hour"),
            header.get("Stadium"), header.get("Capacity"),
            header.get("CodeTeamA"), header.get("CodeTeamB"),
            header.get("TeamA"), header.get("TeamB"),
            header.get("ScoreA"), header.get("ScoreB"),
            header.get("ScoreQuarter1A"), header.get("ScoreQuarter1B"),
            header.get("ScoreQuarter2A"), header.get("ScoreQuarter2B"),
            header.get("ScoreQuarter3A"), header.get("ScoreQuarter3B"),
            header.get("ScoreQuarter4A"), header.get("ScoreQuarter4B"),
            header.get("ScoreExtraTimeA"), header.get("ScoreExtraTimeB"),
            header.get("CoachA"), header.get("CoachB"),
            header.get("Referee1"), header.get("Referee2"), header.get("Referee3"),
            header.get("Phase"), header.get("Round"),
            header.get("FoulsA"), header.get("FoulsB"),
            header.get("TimeoutsA"), header.get("TimeoutsB"),
            cleaned.get("boxscore", {}).get("attendance"),
        ])

        # ── dim_players + fact_boxscore ──
        boxscore = cleaned.get("boxscore")
        if boxscore:
            for team_stats in boxscore.get("team_stats", []):
                for p in team_stats.get("players", []):
                    pid = p.get("player_id")
                    if not pid:
                        continue

                    conn.execute("""
                        INSERT INTO dim_players (player_id, player_name, position)
                        VALUES (?, ?, NULL)
                        ON CONFLICT (player_id) DO UPDATE 
                        SET player_name = excluded.player_name
                    """, [pid, p.get("player_name")])

                    conn.execute("""
                        INSERT INTO fact_boxscore (
                            game_key, player_id, team_code, player_name,
                            is_starter, minutes_seconds,
                            points, fg2m, fg2a, fg3m, fg3a, ftm, fta,
                            off_rebounds, def_rebounds, total_rebounds,
                            assists, steals, turnovers,
                            blocks_made, blocks_against,
                            fouls_committed, fouls_drawn, pir, plus_minus
                        ) VALUES (
                            ?, ?, ?, ?,
                            ?, ?,
                            ?, ?, ?, ?, ?, ?, ?,
                            ?, ?, ?,
                            ?, ?, ?,
                            ?, ?,
                            ?, ?, ?, ?
                        ) ON CONFLICT (game_key, player_id) DO NOTHING
                    """, [
                        game_key, pid, p.get("team_code"), p.get("player_name"),
                        p.get("is_starter"), p.get("minutes_seconds"),
                        p.get("points"), p.get("fg2m"), p.get("fg2a"),
                        p.get("fg3m"), p.get("fg3a"), p.get("ftm"), p.get("fta"),
                        p.get("off_rebounds"), p.get("def_rebounds"), p.get("total_rebounds"),
                        p.get("assists"), p.get("steals"), p.get("turnovers"),
                        p.get("blocks_made"), p.get("blocks_against"),
                        p.get("fouls_committed"), p.get("fouls_drawn"),
                        p.get("pir"), p.get("plus_minus"),
                    ])

        # ── dim_players from Players API (for position data) ──
        for players_key in ["players_team_a", "players_team_b"]:
            for p in cleaned.get(players_key, []):
                pid = p.get("player_id")
                if pid:
                    conn.execute("""
                        INSERT INTO dim_players (player_id, player_name, position)
                        VALUES (?, ?, ?)
                        ON CONFLICT (player_id) DO UPDATE 
                        SET position = COALESCE(excluded.position, dim_players.position),
                            player_name = excluded.player_name
                    """, [pid, p.get("player_name"), p.get("position")])

        # ── fact_events ──
        events = cleaned.get("events", [])
        shots = cleaned.get("shots", [])

        if events:
            for event in events:
                enrich_event_with_parsed_info(event)

            if shots:
                merge_events_with_shots(events, shots)

            # Lineup tracking
            if cleaned.get("players_team_a") and cleaned.get("players_team_b"):
                events, _ = track_lineups(
                    events,
                    cleaned["players_team_a"],
                    cleaned["players_team_b"],
                    header["CodeTeamA"],
                    header["CodeTeamB"],
                )

            forward_fill_score(events)

            # Insert events
            for e in events:
                conn.execute("""
                    INSERT INTO fact_events (
                        game_key, event_id, quarter, game_clock, utc,
                        team_code, player_id, player_name, jersey_number,
                        play_type, play_info,
                        made, attempted, player_total_points, cumulative_count,
                        score_a, score_b,
                        coord_x, coord_y, zone,
                        is_fastbreak, is_second_chance, is_off_turnover,
                        lineup_a, lineup_b
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?, ?,
                        ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?
                    ) ON CONFLICT (game_key, event_id) DO NOTHING
                """, [
                    game_key, e.get("event_id"), e.get("quarter"),
                    e.get("marker_time"), e.get("utc"),
                    e.get("team_code"), e.get("player_id"),
                    e.get("player_name"), e.get("jersey_number"),
                    e.get("play_type"), e.get("play_info"),
                    e.get("made"), e.get("attempted"),
                    e.get("player_total_points"), e.get("cumulative_count"),
                    e.get("score_a"), e.get("score_b"),
                    e.get("coord_x"), e.get("coord_y"), e.get("zone"),
                    e.get("is_fastbreak", False),
                    e.get("is_second_chance", False),
                    e.get("is_off_turnover", False),
                    e.get("lineup_a"), e.get("lineup_b"),
                ])

        # ── fact_score_evolution ──
        evolution = cleaned.get("evolution")
        if evolution:
            points_list = evolution.get("PointsList")
            minutes_list = evolution.get("MinutesList")
            if points_list and len(points_list) == 2 and minutes_list:
                for i, minute in enumerate(minutes_list):
                    score_a = points_list[0][i] if i < len(points_list[0]) else None
                    score_b = points_list[1][i] if i < len(points_list[1]) else None
                    conn.execute("""
                        INSERT INTO fact_score_evolution VALUES (?, ?, ?, ?)
                        ON CONFLICT (game_key, minute) DO NOTHING
                    """, [game_key, minute, score_a, score_b])

        # ── fact_shooting ──
        shooting = cleaned.get("shooting")
        if shooting:
            conn.execute("""
                INSERT INTO fact_shooting VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (game_key) DO NOTHING
            """, [
                game_key,
                shooting.get("FastbreakPointsA", 0),
                shooting.get("FastbreakPointsB", 0),
                shooting.get("TurnoversPointsA", 0),
                shooting.get("TurnoversPointsB", 0),
                shooting.get("SecondChancePointsA", 0),
                shooting.get("SecondChancePointsB", 0),
            ])

        # ── fact_comparison ──
        comparison = cleaned.get("comparison")
        if comparison:
            conn.execute("""
                INSERT INTO fact_comparison (
                    game_key,
                    off_rebounds_a, off_rebounds_b, def_rebounds_a, def_rebounds_b,
                    points_starters_a, points_bench_a, points_starters_b, points_bench_b,
                    assists_starters_a, assists_bench_a, assists_starters_b, assists_bench_b,
                    steals_starters_a, steals_bench_a, steals_starters_b, steals_bench_b,
                    turnovers_starters_a, turnovers_bench_a, turnovers_starters_b, turnovers_bench_b,
                    max_lead_a, max_lead_b, max_run_a, max_run_b
                ) VALUES (
                    ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                ) ON CONFLICT (game_key) DO NOTHING
            """, [
                game_key,
                comparison.get("OffensiveReboundsA"),
                comparison.get("OffensiveReboundsB"),
                comparison.get("DefensiveReboundsA"),
                comparison.get("DefensiveReboundsB"),
                comparison.get("PointsStartersA"),
                comparison.get("PointsBenchA"),
                comparison.get("PointsStartersB"),
                comparison.get("PointsBenchB"),
                comparison.get("AssistsStartersA"),
                comparison.get("AssistsBenchA"),
                comparison.get("AssistsStartersB"),
                comparison.get("AssistsBenchB"),
                comparison.get("StealsStartersA"),
                comparison.get("StealsBenchA"),
                comparison.get("StealsStartersB"),
                comparison.get("StealsBenchB"),
                comparison.get("TurnoversStartersA"),
                comparison.get("TurnoversBenchA"),
                comparison.get("TurnoversStartersB"),
                comparison.get("TurnoversBenchB"),
                comparison.get("maxLeadA"),
                comparison.get("maxLeadB"),
                comparison.get("maxA"),
                comparison.get("maxB"),
            ])

        return True

    except Exception as e:
        logger.error(f"Failed to load {game_key}: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_all_seasons(raw_dir: str = "data/raw", db_path: str = DB_PATH):
    """Load all seasons from raw JSON files into DuckDB."""
    raw_path = Path(raw_dir)
    conn = get_connection(db_path)

    total = 0
    loaded = 0
    failed = 0

    for season_dir in sorted(raw_path.iterdir()):
        if not season_dir.is_dir():
            continue

        season_code = season_dir.name
        season_loaded = 0

        for game_file in sorted(season_dir.glob("game_*.json")):
            total += 1
            game_code = int(game_file.stem.split("_")[1])

            # Skip if already loaded
            game_key = make_game_key(season_code, game_code)
            existing = conn.execute(
                "SELECT 1 FROM dim_games WHERE game_key = ?", [game_key]
            ).fetchone()
            if existing:
                season_loaded += 1
                loaded += 1
                continue

            with open(game_file, "r", encoding="utf-8") as f:
                raw_game = json.load(f)

            if load_game(conn, raw_game, season_code, game_code):
                loaded += 1
                season_loaded += 1
            else:
                failed += 1

        logger.info(f"{season_code}: {season_loaded} games loaded")

    conn.close()
    logger.info(f"Complete: {loaded} loaded, {failed} failed, {total} total")
    return loaded, failed