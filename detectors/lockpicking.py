# ─── detectors/lockpicking.py ────────────────────────────────────
# Watches whether EITHER wrist stays inside LOCK_ZONE.
# Two-stage timer:
#   Stage 1 — DWELL: hand must be in zone for LOCK_DWELL_TIME
#             seconds before the main countdown begins.
#   Stage 2 — ALERT: after dwell, counts up to LOCK_ALERT_TIME.
#             When it reaches the limit the alert fires.
#
# State is kept in a small dict so main.py stays clean.

import time
from config import LOCK_ZONE, LOCK_DWELL_TIME, LOCK_ALERT_TIME, FRAME_W, FRAME_H


def make_lock_state() -> dict:
    """Call once at startup to get a fresh state object."""
    return {
        "dwell_start": None,   # when hand first entered zone
        "alert_start": None,   # when dwell completed
    }


def check_lockpicking(lm, state: dict) -> tuple:
    """
    Parameters
    ----------
    lm    : pose landmarks list
    state : dict from make_lock_state(), mutated in place

    Returns
    -------
    (alert_fired, dwell_elapsed, alert_elapsed)
      alert_fired   — True once LOCK_ALERT_TIME is reached
      dwell_elapsed — seconds into the dwell phase (0 if not dwelling)
      alert_elapsed — seconds into the alert countdown (0 if not started)
    """
    # Check both wrists — landmark 15 = left wrist, 16 = right wrist
    lx = int(lm[15].x * FRAME_W)
    ly = int(lm[15].y * FRAME_H)
    rx = int(lm[16].x * FRAME_W)
    ry = int(lm[16].y * FRAME_H)
    x1, y1, x2, y2 = LOCK_ZONE

    in_zone = (x1 < lx < x2 and y1 < ly < y2) or \
              (x1 < rx < x2 and y1 < ry < y2)

    if not in_zone:
        # Hand left — reset everything
        state["dwell_start"] = None
        state["alert_start"] = None
        return False, 0.0, 0.0

    now = time.time()

    # Stage 1 — dwell
    if state["dwell_start"] is None:
        state["dwell_start"] = now

    dwell_elapsed = now - state["dwell_start"]

    if dwell_elapsed < LOCK_DWELL_TIME:
        # Still in dwell phase
        return False, dwell_elapsed, 0.0

    # Stage 2 — alert countdown
    if state["alert_start"] is None:
        state["alert_start"] = now

    alert_elapsed = now - state["alert_start"]
    alert_fired   = alert_elapsed >= LOCK_ALERT_TIME

    return alert_fired, dwell_elapsed, alert_elapsed