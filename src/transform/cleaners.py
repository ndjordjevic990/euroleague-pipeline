"""Clean raw API data: strip whitespace, fix types, normalize values."""

import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


def clean_string(value: str | None) -> str | None:
    """Strip whitespace from string values. Return None for empty strings."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned if cleaned else None


def clean_header(raw_header: dict) -> dict:
    """Clean the Header endpoint data.
    
    Fixes:
    - Strip whitespace from all string fields
    - Cast score fields to int
    - Parse date/time fields
    - Fix 'Foults' typo
    """
    h = deepcopy(raw_header)

    # Strip all string fields
    string_fields = [
        "Round", "Date", "Hour", "Stadium", "Capacity",
        "TeamA", "TeamB", "CodeTeamA", "CodeTeamB",
        "TVCodeA", "TVCodeB", "imA", "imB",
        "CoachA", "CoachB", "GameTime", "Quarter",
        "Phase", "PhaseReducedName", "Competition",
        "CompetitionReducedName", "pcom",
        "Referee1", "Referee2", "Referee3",
    ]
    for field in string_fields:
        if field in h:
            h[field] = clean_string(h[field])

    # Cast scores to int (API returns mix of string and int)
    int_fields = [
        "ScoreA", "ScoreB", "wid",
        "FoultsA", "FoultsB", "TimeoutsA", "TimeoutsB",
        "ScoreQuarter1A", "ScoreQuarter2A", "ScoreQuarter3A", "ScoreQuarter4A",
        "ScoreQuarter1B", "ScoreQuarter2B", "ScoreQuarter3B", "ScoreQuarter4B",
        "ScoreExtraTimeA", "ScoreExtraTimeB", "Capacity",
    ]
    for field in int_fields:
        if field in h and h[field] is not None:
            try:
                h[field] = int(h[field])
            except (ValueError, TypeError):
                logger.warning(f"Header: Could not cast {field}={h[field]!r} to int")

    # Rename typo field
    if "FoultsA" in h:
        h["FoulsA"] = h.pop("FoultsA")
    if "FoultsB" in h:
        h["FoulsB"] = h.pop("FoultsB")

    return h


def clean_players(raw_players: list) -> list:
    """Clean the Players endpoint data.
    
    Fixes:
    - Strip whitespace from string fields
    - Rename cryptic field names to readable ones
    """
    cleaned = []

    for p in raw_players:
        player = {
            "team_code": clean_string(p.get("c")),
            "player_id": clean_string(p.get("ac")),
            "player_name": clean_string(p.get("na")),
            "jersey_number": clean_string(p.get("nu")),
            "is_starter": p.get("st", 0) == 1,
            "is_squad_list": p.get("sl", 0) == 1,
            "is_active": p.get("nn", 0) == 1,
            "position": clean_string(p.get("p")),
            "image_url": clean_string(p.get("im")),
        }
        cleaned.append(player)

    return cleaned


def clean_pbp_event(event: dict) -> dict:
    """Clean a single play-by-play event.
    
    Fixes:
    - Strip whitespace from all string fields
    - Normalize MARKERTIME ('ND' -> None)
    - Strip PLAYTYPE (trailing whitespace issue)
    """
    return {
        "type": event.get("TYPE"),
        "event_id": event.get("NUMBEROFPLAY"),
        "team_code": clean_string(event.get("CODETEAM")),
        "player_id": clean_string(event.get("PLAYER_ID")),
        "play_type": clean_string(event.get("PLAYTYPE")),
        "player_name": clean_string(event.get("PLAYER")),
        "team_name": clean_string(event.get("TEAM")),
        "jersey_number": clean_string(event.get("DORSAL")),
        "minute": event.get("MINUTE"),
        "marker_time": _clean_marker_time(event.get("MARKERTIME")),
        "points_a": event.get("POINTS_A"),
        "points_b": event.get("POINTS_B"),
        "comment": clean_string(event.get("COMMENT")),
        "play_info": clean_string(event.get("PLAYINFO")),
    }


def _clean_marker_time(value: str | None) -> str | None:
    """Clean MARKERTIME field. 'ND' and empty strings become None."""
    if value is None:
        return None
    cleaned = value.strip()
    if cleaned in ("", "ND"):
        return None
    return cleaned


def clean_playbyplay(raw_pbp: dict) -> list:
    """Clean PlaybyPlay data: flatten quarters into single list with quarter labels.
    
    Returns:
        List of cleaned events with 'quarter' field added.
    """
    quarter_map = {
        "FirstQuarter": 1,
        "SecondQuarter": 2,
        "ThirdQuarter": 3,
        "ForthQuarter": 4,      # API typo: "Forth" not "Fourth"
        "FourthQuarter": 4,     # In case they ever fix it
        "ExtraTime": 5,
    }

    all_events = []

    for quarter_key, quarter_num in quarter_map.items():
        quarter_data = raw_pbp.get(quarter_key) or []
        for event in quarter_data:
            cleaned = clean_pbp_event(event)
            cleaned["quarter"] = quarter_num
            all_events.append(cleaned)

    # Sort by event_id (NUMBEROFPLAY) — the true ordering
    all_events.sort(key=lambda e: e.get("event_id", 0))

    return all_events


def clean_points_event(event: dict) -> dict:
    """Clean a single Points (shot) event."""
    coord_x = event.get("COORD_X")
    coord_y = event.get("COORD_Y")

    # Filter free throw sentinel coordinates (-1, -1)
    is_sentinel = (coord_x == -1 and coord_y == -1)

    return {
        "event_id": event.get("NUM_ANOT"),
        "team_code": clean_string(event.get("TEAM")),
        "player_id": clean_string(event.get("ID_PLAYER")),
        "player_name": clean_string(event.get("PLAYER")),
        "action_code": clean_string(event.get("ID_ACTION")),
        "action_label": clean_string(event.get("ACTION")),
        "points": event.get("POINTS"),
        "coord_x": None if is_sentinel else coord_x,
        "coord_y": None if is_sentinel else coord_y,
        "zone": clean_string(event.get("ZONE")),
        "is_fastbreak": event.get("FASTBREAK") == "1",
        "is_second_chance": event.get("SECOND_CHANCE") == "1",
        "is_off_turnover": event.get("POINTS_OFF_TURNOVER") == "1",
        "minute": event.get("MINUTE"),
        "game_clock": clean_string(event.get("CONSOLE")),
        "points_a": event.get("POINTS_A"),
        "points_b": event.get("POINTS_B"),
        "utc": clean_string(event.get("UTC")),
    }


def clean_points(raw_points: dict) -> list:
    """Clean Points endpoint data."""
    rows = raw_points.get("Rows", [])
    return [clean_points_event(event) for event in rows]


def clean_boxscore_player(player: dict) -> dict:
    """Clean a single player's box score stats."""
    minutes_raw = player.get("Minutes", "")

    # Parse minutes: "26:10" -> 1570 seconds, "DNP" -> None
    minutes_seconds = None
    if minutes_raw and minutes_raw != "DNP":
        try:
            parts = minutes_raw.split(":")
            minutes_seconds = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            logger.warning(f"BoxScore: Could not parse minutes={minutes_raw!r}")

    return {
        "player_id": clean_string(player.get("Player_ID")),
        "is_starter": player.get("IsStarter", 0) == 1,
        "is_playing": player.get("IsPlaying", 0) == 1,
        "team_code": clean_string(player.get("Team")),
        "jersey_number": clean_string(player.get("Dorsal")),
        "player_name": clean_string(player.get("Player")),
        "minutes_raw": minutes_raw,
        "minutes_seconds": minutes_seconds,
        "points": player.get("Points", 0),
        "fg2m": player.get("FieldGoalsMade2", 0),
        "fg2a": player.get("FieldGoalsAttempted2", 0),
        "fg3m": player.get("FieldGoalsMade3", 0),
        "fg3a": player.get("FieldGoalsAttempted3", 0),
        "ftm": player.get("FreeThrowsMade", 0),
        "fta": player.get("FreeThrowsAttempted", 0),
        "off_rebounds": player.get("OffensiveRebounds", 0),
        "def_rebounds": player.get("DefensiveRebounds", 0),
        "total_rebounds": player.get("TotalRebounds", 0),
        "assists": player.get("Assistances", 0),
        "steals": player.get("Steals", 0),
        "turnovers": player.get("Turnovers", 0),
        "blocks_made": player.get("BlocksFavour", 0),
        "blocks_against": player.get("BlocksAgainst", 0),
        "fouls_committed": player.get("FoulsCommited", 0),
        "fouls_drawn": player.get("FoulsReceived", 0),
        "pir": player.get("Valuation", 0),
        "plus_minus": player.get("Plusminus", 0),
    }


def clean_boxscore(raw_boxscore: dict) -> dict:
    """Clean BoxScore endpoint data."""
    cleaned = {
        "referees": clean_string(raw_boxscore.get("Referees")),
        "attendance": None,
        "by_quarter": raw_boxscore.get("ByQuarter", []),
        "end_of_quarter": raw_boxscore.get("EndOfQuarter", []),
        "team_stats": [],
    }

    # Parse attendance
    att = raw_boxscore.get("Attendance", "0")
    try:
        cleaned["attendance"] = int(att)
    except (ValueError, TypeError):
        pass

    # Clean player stats per team
    for team_stats in raw_boxscore.get("Stats", []):
        team_entry = {
            "team_name": clean_string(team_stats.get("Team")),
            "coach": clean_string(team_stats.get("Coach")),
            "players": [
                clean_boxscore_player(p)
                for p in team_stats.get("PlayersStats", [])
            ],
        }
        cleaned["team_stats"].append(team_entry)

    return cleaned


def clean_game(raw_game: dict) -> dict:
    """Clean all endpoints for a single game.
    
    Args:
        raw_game: Dict with raw endpoint data as loaded from JSON file.
        
    Returns:
        Dict with cleaned data for all endpoints.
    """
    cleaned = {}

    # Header
    if raw_game.get("Header"):
        cleaned["header"] = clean_header(raw_game["Header"])

    # Players
    if raw_game.get("PlayersTeamA"):
        cleaned["players_team_a"] = clean_players(raw_game["PlayersTeamA"])
    if raw_game.get("PlayersTeamB"):
        cleaned["players_team_b"] = clean_players(raw_game["PlayersTeamB"])

    # PlaybyPlay
    if raw_game.get("PlaybyPlay"):
        cleaned["events"] = clean_playbyplay(raw_game["PlaybyPlay"])

    # Points (shots)
    if raw_game.get("Points"):
        cleaned["shots"] = clean_points(raw_game["Points"])

    # BoxScore
    if raw_game.get("BoxScore"):
        cleaned["boxscore"] = clean_boxscore(raw_game["BoxScore"])

    # Pass through simpler endpoints (clean later if needed)
    if raw_game.get("Evolution"):
        cleaned["evolution"] = raw_game["Evolution"]
    if raw_game.get("Comparison"):
        cleaned["comparison"] = raw_game["Comparison"]
    if raw_game.get("ShootingGraphic"):
        cleaned["shooting"] = raw_game["ShootingGraphic"]

    return cleaned