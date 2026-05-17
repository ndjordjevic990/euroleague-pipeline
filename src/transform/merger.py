"""Merge PlayByPlay events with Points (shot) data.

PBP has all events but lacks coordinates, UTC timestamps, and shot context flags.
Points has only shot events but with rich spatial and temporal data.
Join key: event_id (NUMBEROFPLAY in PBP = NUM_ANOT in Points).
"""

import logging

logger = logging.getLogger(__name__)


def merge_events_with_shots(events: list, shots: list) -> list:
    """Merge cleaned PBP events with cleaned Points data.
    
    Enriches PBP events with shot coordinates, UTC timestamps,
    zone, and context flags (fastbreak, second chance, off turnover)
    where a matching shot record exists.
    
    Args:
        events: Cleaned PBP events (from clean_playbyplay)
        shots: Cleaned shot events (from clean_points)
        
    Returns:
        Enriched events list. Non-shot events pass through unchanged.
    """
    # Build lookup: event_id -> shot data
    shots_by_id = {}
    for shot in shots:
        shot_id = shot.get("event_id")
        if shot_id is not None:
            shots_by_id[shot_id] = shot

    # Merge
    merged_count = 0
    unmatched_shots = set(shots_by_id.keys())

    for event in events:
        event_id = event.get("event_id")
        shot = shots_by_id.get(event_id)

        if shot:
            # Enrich PBP event with Points data
            event["coord_x"] = shot.get("coord_x")
            event["coord_y"] = shot.get("coord_y")
            event["zone"] = shot.get("zone")
            event["utc"] = shot.get("utc")
            event["is_fastbreak"] = shot.get("is_fastbreak", False)
            event["is_second_chance"] = shot.get("is_second_chance", False)
            event["is_off_turnover"] = shot.get("is_off_turnover", False)

            # Use Points score if PBP score is null
            if event.get("points_a") is None and shot.get("points_a") is not None:
                event["points_a"] = shot["points_a"]
            if event.get("points_b") is None and shot.get("points_b") is not None:
                event["points_b"] = shot["points_b"]

            merged_count += 1
            unmatched_shots.discard(event_id)
        else:
            # Non-shot event — set defaults
            event.setdefault("coord_x", None)
            event.setdefault("coord_y", None)
            event.setdefault("zone", None)
            event.setdefault("utc", None)
            event.setdefault("is_fastbreak", False)
            event.setdefault("is_second_chance", False)
            event.setdefault("is_off_turnover", False)

    # Log merge stats
    logger.info(
        f"Merged {merged_count} shot events. "
        f"PBP events: {len(events)}, Points records: {len(shots)}, "
        f"Unmatched shots: {len(unmatched_shots)}"
    )

    if unmatched_shots:
        logger.warning(
            f"Shot event_ids not found in PBP: {sorted(unmatched_shots)[:10]}"
        )

    return events


def forward_fill_score(events: list) -> list:
    """Forward-fill running score for non-scoring events.
    
    Only scoring events have points_a/points_b populated.
    This fills in the current score for all events based on
    the last known scoring event. Ignores score values that
    would go backward (data quality issue in some games).
    
    Args:
        events: List of events sorted by event_id.
        
    Returns:
        Same list with scores filled in.
    """
    current_a = 0
    current_b = 0

    for event in events:
        pa = event.get("points_a")
        pb = event.get("points_b")

        # Only update if score moves forward (or stays same)
        if pa is not None and pa >= current_a:
            current_a = pa
        if pb is not None and pb >= current_b:
            current_b = pb

        event["score_a"] = current_a
        event["score_b"] = current_b

    return events