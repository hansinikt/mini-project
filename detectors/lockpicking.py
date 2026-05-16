# ─── detectors/lockpicking.py ────────────────────────────────────
# Detects suspicious lockpicking behavior using body pose instead
# of hand position. More realistic than hand-zone detection since
# a real intruder would not visibly reach toward a lock.
#
# 3 conditions — ALL 3 must be true for the full LOCK_ALERT_TIME:
#   1. Near door  — hip midpoint is within or close to the lock zone
#   2. Crouching  — hips are in the lower portion of the frame
#   3. Stationary — very little body movement over recent frames
#
# Two stage timer:
#   Stage 1 — DWELL: all 3 conditions must hold for LOCK_DWELL_TIME
#   Stage 2 — ALERT: countdown runs for LOCK_ALERT_TIME, then fires

import time
from config import (LOCK_ZONE, LOCK_DWELL_TIME, LOCK_ALERT_TIME,
                    FRAME_W, FRAME_H)

# ── Tuning constants ──────────────────────────────────────────────
CROUCH_THRESHOLD  = 0.35   # hips must be below this fraction of frame height
STATIONARY_FRAMES = 30     # how many frames to track for movement
STATIONARY_LIMIT  = 0.025  # max hip movement allowed (fraction of frame height)
ZONE_MARGIN       = 80     # pixels outside zone that still count as "near door"


def make_lock_state() -> dict:
    """Call once at startup to get a fresh state object."""
    return {
        "dwell_start": None,
        "alert_start": None,
        "hip_history": [],
    }


def check_lockpicking(lm, state: dict) -> tuple:
    """
    Parameters
    ----------
    lm    : pose landmarks list
    state : dict from make_lock_state(), mutated in place

    Returns
    -------
    (alert_fired, dwell_elapsed, alert_elapsed, near_door, crouching, stationary)
    """
    # ── Hip midpoint ─────────────────────────────────────────────
    hip_x = (lm[23].x + lm[24].x) / 2
    hip_y = (lm[23].y + lm[24].y) / 2
    hip_px = int(hip_x * FRAME_W)
    hip_py = int(hip_y * FRAME_H)

    # ── Condition 1: near door zone ──────────────────────────────
    x1, y1, x2, y2 = LOCK_ZONE
    near_door = (x1 - ZONE_MARGIN < hip_px < x2 + ZONE_MARGIN and
                 y1 - ZONE_MARGIN < hip_py < y2 + ZONE_MARGIN)

    # ── Condition 2: crouching ───────────────────────────────────
    crouching = hip_y > CROUCH_THRESHOLD

    # ── Condition 3: stationary ──────────────────────────────────
    state["hip_history"].append(hip_y)
    if len(state["hip_history"]) > STATIONARY_FRAMES:
        state["hip_history"].pop(0)

    if len(state["hip_history"]) >= 10:
        movement  = max(state["hip_history"]) - min(state["hip_history"])
        stationary = movement < STATIONARY_LIMIT
    else:
        stationary = False

    # ── 2 out of 3 must be true ───────────────────────────────────
    score = sum([near_door, crouching, stationary])
    all_conditions = score >= 2

    if not all_conditions:
        state["dwell_start"] = None
        state["alert_start"] = None
        return False, 0.0, 0.0, near_door, crouching, stationary

    now = time.time()

    # Stage 1 — dwell
    if state["dwell_start"] is None:
        state["dwell_start"] = now
    dwell_elapsed = now - state["dwell_start"]

    if dwell_elapsed < LOCK_DWELL_TIME:
        return False, dwell_elapsed, 0.0, near_door, crouching, stationary

    # Stage 2 — alert countdown
    if state["alert_start"] is None:
        state["alert_start"] = now
    alert_elapsed = now - state["alert_start"]
    alert_fired   = alert_elapsed >= LOCK_ALERT_TIME

    return alert_fired, dwell_elapsed, alert_elapsed, near_door, crouching, stationary