# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Shared utilities for session management across CLI and MCP.
"""

import datetime
from typing import Any, Dict


def get_session_sort_key(session: Dict[str, Any]) -> tuple:
    """
    Generate sort key for session selection.

    Prioritizes ongoing sessions over completed ones, then sorts by most recent time.

    Args:
        session: Session dictionary from list_sessions API response

    Returns:
        Tuple for sorting: (is_completed, -time_value)
        - is_completed: False for ongoing, True for completed (False sorts first)
        - time_value: Negative timestamp for descending order (most recent first)
    """
    is_completed = "endedAt" in session
    default_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)

    if is_completed:
        time_value = session.get("endedAt", default_time).timestamp()
    else:
        time_value = session.get("startedAt", default_time).timestamp()

    # Sort: ongoing first (False < True), then by time descending (negative)
    return (is_completed, -time_value)
