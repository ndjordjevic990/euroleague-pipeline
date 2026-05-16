"""Parse unstructured text fields into structured data."""

import re
import logging

logger = logging.getLogger(__name__)

# Pattern: "Two Pointer (2/3 -  8 pt)" or "Missed Three Pointer (0/1 -  0 pt)"
SHOT_PATTERN = re.compile(
    r"\((\d+)/(\d+)\s*-\s*(\d+)\s*pt\)"
)

# Pattern: "Def Rebound (3)" or "Assist (1)" or "Foul (2)"
COUNT_PATTERN = re.compile(
    r"\((\d+)\)"
)

# Play types that have shot stats (made/attempted - cumulative points)
SHOT_PLAY_TYPES = {"2FGM", "2FGA", "2FGAB", "3FGM", "3FGA", "3FGAB", "FTM", "FTA"}

# Play types that have cumulative count
COUNT_PLAY_TYPES = {"D", "O", "AS", "ST", "TO", "FV", "AG", "CM", "RV", "OF",
                    "CMU", "CMT", "CMD", "CMTI", "B", "C", "F", "CCH"}


def parse_playinfo(play_type: str | None, play_info: str | None) -> dict:
    """Parse PLAYINFO text into structured fields.
    
    Args:
        play_type: The PLAYTYPE code (e.g., '2FGM', 'D', 'AS')
        play_info: The PLAYINFO text (e.g., 'Two Pointer (2/3 - 8 pt)')
        
    Returns:
        Dict with parsed fields. Empty dict if nothing to parse.
        
    Examples:
        >>> parse_playinfo('2FGM', 'Two Pointer (2/3 -  8 pt)')
        {'made': 2, 'attempted': 3, 'player_total_points': 8}
        
        >>> parse_playinfo('D', 'Def Rebound (3)')
        {'cumulative_count': 3}
        
        >>> parse_playinfo('BP', 'Begin Period')
        {}
    """
    if not play_type or not play_info:
        return {}

    # Shot stats
    if play_type in SHOT_PLAY_TYPES:
        match = SHOT_PATTERN.search(play_info)
        if match:
            return {
                "made": int(match.group(1)),
                "attempted": int(match.group(2)),
                "player_total_points": int(match.group(3)),
            }
        else:
            logger.debug(f"Could not parse shot info: play_type={play_type}, play_info={play_info!r}")
            return {}

    # Cumulative count stats
    if play_type in COUNT_PLAY_TYPES:
        match = COUNT_PATTERN.search(play_info)
        if match:
            return {
                "cumulative_count": int(match.group(1)),
            }
        else:
            logger.debug(f"Could not parse count info: play_type={play_type}, play_info={play_info!r}")
            return {}

    return {}


def enrich_event_with_parsed_info(event: dict) -> dict:
    """Add parsed PLAYINFO fields to a cleaned event dict.
    
    Modifies the event in place and returns it.
    """
    parsed = parse_playinfo(event.get("play_type"), event.get("play_info"))
    event.update(parsed)
    return event