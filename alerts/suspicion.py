# ─── alerts/suspicion.py ─────────────────────────────────────────
# Tracks a suspicion score across frames.
#
# Each detector contributes points when active:
#   Trespassing  = 40 pts  (highest — being in restricted zone is serious)
#   Lockpicking  = 40 pts  (high — stationary near door is very suspicious)
#   Climbing     = 25 pts  (medium — could be accidental)
#
# Score decays slowly every frame so it doesn't stay permanently high.
# When score crosses SUSPICION_THRESHOLD → alert fires.
# Score resets manually via reset().

import time
from config import (SUSPICION_THRESHOLD, SCORE_TRESPASSING,
                    SCORE_LOCKPICKING, SCORE_CLIMBING,
                    SCORE_DECAY_PER_FRAME)


def make_suspicion_state() -> dict:
    """Call once at startup."""
    return {
        "score":          0.0,
        "alert_fired":    False,   # True once threshold crossed
        "last_alert_time": 0.0,    # timestamp of last alert
    }


def update_score(state: dict, alerts: dict) -> tuple:
    """
    Call every frame with the current alert flags.

    Parameters
    ----------
    state  : dict from make_suspicion_state(), mutated in place
    alerts : {"intrusion": bool, "climb": bool, "lock": bool}

    Returns
    -------
    (score, threshold_crossed)
      score             — current score (0 to SUSPICION_THRESHOLD+)
      threshold_crossed — True if score just crossed the threshold
                          AND cooldown has passed
    """
    # Add points for active detections
    if alerts.get("intrusion", False):
        state["score"] += SCORE_TRESPASSING
    if alerts.get("lock", False):
        state["score"] += SCORE_LOCKPICKING
    if alerts.get("climb", False):
        state["score"] += SCORE_CLIMBING

    # Decay score slowly each frame
    state["score"] = max(0.0, state["score"] - SCORE_DECAY_PER_FRAME)

    # Cap at 2x threshold so it doesn't balloon
    state["score"] = min(state["score"], SUSPICION_THRESHOLD * 2)

    # Check if threshold crossed and cooldown passed
    threshold_crossed = False
    if state["score"] >= SUSPICION_THRESHOLD:
        now = time.time()
        if not state["alert_fired"] or (now - state["last_alert_time"]) > 300:
            threshold_crossed    = True
            state["alert_fired"] = True
            state["last_alert_time"] = now

    return state["score"], threshold_crossed


def reset_score(state: dict):
    """Reset score and alert flag — call when user resets via email reply."""
    state["score"]       = 0.0
    state["alert_fired"] = False