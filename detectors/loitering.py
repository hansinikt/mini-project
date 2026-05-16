# ─── detectors/loitering.py ──────────────────────────────────────
# Two additional conditions that feed into the suspicion score:
#
# 1. Time in zone — how long the person has been continuously
#    inside the restricted zone. Only counts after 2 seconds
#    to filter out people just walking past.
#
# 2. Loitering — person is barely moving while inside or near
#    the restricted zone. Tracks hip position over 60 frames.

import time
from config import RESTRICTED_ZONE, FRAME_W, FRAME_H

# Tuning constants
LOITER_HISTORY_LEN    = 60     # frames to track
LOITER_MOVEMENT_LIMIT = 0.015  # max hip movement to count as loitering
ZONE_ENTRY_GRACE      = 2.0    # seconds before time-in-zone counts


def make_loiter_state() -> dict:
    """Call once at startup."""
    return {
        "zone_entry_time": None,   # when person first entered zone
        "hip_history":     [],     # recent hip positions for movement check
    }


def check_loitering(lm, state: dict) -> tuple:
    """
    Parameters
    ----------
    lm    : pose landmarks list
    state : dict from make_loiter_state(), mutated in place

    Returns
    -------
    (time_in_zone, is_loitering)
      time_in_zone  — seconds person has been in zone (0 if not in zone)
      is_loitering  — True if barely moving inside/near zone
    """
    # Check if nose is in restricted zone
    nx = int(lm[0].x * FRAME_W)
    ny = int(lm[0].y * FRAME_H)
    x1, y1, x2, y2 = RESTRICTED_ZONE
    in_zone = x1 < nx < x2 and y1 < ny < y2

    # ── Time in zone ─────────────────────────────────────────────
    if in_zone:
        if state["zone_entry_time"] is None:
            state["zone_entry_time"] = time.time()
        time_in_zone = time.time() - state["zone_entry_time"]
    else:
        state["zone_entry_time"] = None
        time_in_zone = 0.0

    # ── Loitering — hip movement check ───────────────────────────
    hip_x = (lm[23].x + lm[24].x) / 2
    hip_y = (lm[23].y + lm[24].y) / 2

    state["hip_history"].append((hip_x, hip_y))
    if len(state["hip_history"]) > LOITER_HISTORY_LEN:
        state["hip_history"].pop(0)

    is_loitering = False
    if in_zone and len(state["hip_history"]) >= 20:
        xs = [p[0] for p in state["hip_history"]]
        ys = [p[1] for p in state["hip_history"]]
        movement = max(
            max(xs) - min(xs),
            max(ys) - min(ys)
        )
        is_loitering = movement < LOITER_MOVEMENT_LIMIT

    return time_in_zone, is_loitering