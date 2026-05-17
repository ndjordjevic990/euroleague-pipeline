"""Reconstruct on-court lineups from substitution events.

Processes IN/OUT events to track which 5 players are on court
for each team at every moment of the game.
"""

import logging

logger = logging.getLogger(__name__)


class LineupTracker:
    """State machine that tracks on-court players from substitution events.
    
    Initialized with starters (5 per team), then processes IN/OUT events
    to maintain current lineup state. Attaches lineup info to every event.
    """

    def __init__(self, starters_a: set[str], starters_b: set[str],
                 team_a_code: str, team_b_code: str):
        """Initialize with starting lineups.
        
        Args:
            starters_a: Set of player_ids for team A starters
            starters_b: Set of player_ids for team B starters
            team_a_code: Team code for team A (e.g., 'BER')
            team_b_code: Team code for team B (e.g., 'PAN')
        """
        self.on_court_a = set(starters_a)
        self.on_court_b = set(starters_b)
        self.team_a_code = team_a_code
        self.team_b_code = team_b_code

        self.warnings = []

        # Validate starters
        if len(self.on_court_a) != 5:
            self.warnings.append(
                f"Team A ({team_a_code}) has {len(self.on_court_a)} starters, expected 5"
            )
        if len(self.on_court_b) != 5:
            self.warnings.append(
                f"Team B ({team_b_code}) has {len(self.on_court_b)} starters, expected 5"
            )

    def process_event(self, event: dict) -> dict:
        """Process a single event and attach current lineup state.
        
        Handles IN/OUT substitutions with tolerance for bad data:
        - OUT for player not on court: log warning, skip
        - IN for player already on court: log warning, skip
        """
        play_type = event.get("play_type")
        team_code = event.get("team_code")
        player_id = event.get("player_id")

        # Process substitution
        if play_type == "OUT" and player_id and team_code:
            court = self._get_court(team_code)
            if court is not None:
                if player_id in court:
                    court.discard(player_id)
                else:
                    self.warnings.append(
                        f"Event #{event.get('event_id')}: OUT for {player_id} "
                        f"({team_code}) but player not on court"
                    )
                    # Don't discard — player wasn't there

        elif play_type == "IN" and player_id and team_code:
            court = self._get_court(team_code)
            if court is not None:
                if player_id in court:
                    self.warnings.append(
                        f"Event #{event.get('event_id')}: IN for {player_id} "
                        f"({team_code}) but player already on court"
                    )
                    # Don't add — player already there
                else:
                    court.add(player_id)

        # Attach current lineup to event
        event["lineup_a"] = sorted(self.on_court_a)
        event["lineup_b"] = sorted(self.on_court_b)
        event["lineup_size_a"] = len(self.on_court_a)
        event["lineup_size_b"] = len(self.on_court_b)

        return event

    def _get_court(self, team_code: str) -> set | None:
        """Get the on-court set for a team code."""
        if team_code == self.team_a_code:
            return self.on_court_a
        elif team_code == self.team_b_code:
            return self.on_court_b
        else:
            self.warnings.append(f"Unknown team code: {team_code}")
            return None


def get_starters(players: list) -> set[str]:
    """Extract starter player_ids from a cleaned players list.
    
    Args:
        players: Cleaned players list (from clean_players).
        
    Returns:
        Set of player_id strings for starters.
    """
    return {p["player_id"] for p in players if p["is_starter"]}


def track_lineups(events: list, players_a: list, players_b: list,
                  team_a_code: str, team_b_code: str) -> tuple[list, list[str]]:
    """Track lineups through all events in a game."""
    starters_a = get_starters(players_a)
    starters_b = get_starters(players_b)

    # Reorder: within each substitution block, process OUTs before INs per team
    events = _reorder_substitutions(events)

    tracker = LineupTracker(starters_a, starters_b, team_a_code, team_b_code)

    # Process all events but handle substitution blocks atomically
    i = 0
    while i < len(events):
        event = events[i]

        if event.get("play_type") not in ("IN", "OUT"):
            # Normal event — process and attach lineup
            tracker.process_event(event)
            i += 1
            continue

        # Collect the entire substitution block
        block_time = event.get("marker_time")
        block_start = i
        while (i < len(events)
               and events[i].get("play_type") in ("IN", "OUT")
               and events[i].get("marker_time") == block_time):
            # Process the substitution (updates internal state)
            tracker.process_event(events[i])
            i += 1

        # Now attach the FINAL lineup to ALL events in this block
        for j in range(block_start, i):
            events[j]["lineup_a"] = sorted(tracker.on_court_a)
            events[j]["lineup_b"] = sorted(tracker.on_court_b)
            events[j]["lineup_size_a"] = len(tracker.on_court_a)
            events[j]["lineup_size_b"] = len(tracker.on_court_b)

    if tracker.warnings:
        for w in tracker.warnings:
            logger.warning(f"Lineup: {w}")

    # Re-sort by event_id to restore chronological order
    # (substitution reordering may have displaced some events)
    events.sort(key=lambda e: e.get("event_id", 0))

    return events, tracker.warnings


def _reorder_substitutions(events: list) -> list:
    """Reorder IN/OUT events so OUTs come before INs per team within each block.
    
    A substitution block is a consecutive run of IN/OUT events
    at the same marker_time. Within each block, for EACH TEAM separately,
    we place OUT events before IN events.
    """
    result = []
    i = 0

    while i < len(events):
        event = events[i]

        # If not a substitution, just append
        if event.get("play_type") not in ("IN", "OUT"):
            result.append(event)
            i += 1
            continue

        # Collect the entire substitution block
        block_time = event.get("marker_time")
        block = []

        while (i < len(events)
               and events[i].get("play_type") in ("IN", "OUT")
               and events[i].get("marker_time") == block_time):
            block.append(events[i])
            i += 1

        # Group by team
        teams_in_block = {}
        for e in block:
            team = e.get("team_code", "")
            if team not in teams_in_block:
                teams_in_block[team] = []
            teams_in_block[team].append(e)

        # For each team: OUTs first, then INs
        reordered_block = []
        for team in teams_in_block:
            team_events = teams_in_block[team]
            outs = [e for e in team_events if e["play_type"] == "OUT"]
            ins = [e for e in team_events if e["play_type"] == "IN"]
            reordered_block.extend(outs)
            reordered_block.extend(ins)

        result.extend(reordered_block)

    return result