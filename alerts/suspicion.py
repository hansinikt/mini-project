# ─── alerts/suspicion.py ─────────────────────────────────────────
# Tracks a suspicion score across frames.
#
# Score sources per frame:
#   Trespassing              = 2 pts
#   + Time in zone bonus     = 1 pt  (after 2s grace period)
#   + Loitering bonus        = 2 pts (barely moving in zone)
#   Lockpicking              = 2 pts
#   Climbing                 = 1 pt
#   Decay per frame          = -1 pt (when nothing active)
#
# At ~30fps, trespassing + loitering hits 100 in ~10 seconds.
# Only ONE email is sent per session — resets when user presses R.

from config import (SUSPICION_THRESHOLD, SCORE_TRESPASSING,
                    SCORE_TIME_IN_ZONE, SCORE_LOITERING,
                    SCORE_LOCKPICKING, SCORE_CLIMBING,
                    SCORE_DECAY_PER_FRAME, ZONE_ENTRY_GRACE)


def make_suspicion_state() -> dict:
    """Call once at startup."""
    return {
        "score":       0.0,
        "email_sent":  False,   # only send one email per session
    }


def update_score(state: dict, alerts: dict,
                 time_in_zone: float, is_loitering: bool) -> tuple:
    """
    Call every frame.

    Parameters
    ----------
    state        : dict from make_suspicion_state()
    alerts       : {"intrusion": bool, "climb": bool, "lock": bool}
    time_in_zone : seconds person has been in restricted zone
    is_loitering : bool from loitering detector

    Returns
    -------
    (score, threshold_crossed)
    """
    # Add points for active detections
    if alerts.get("intrusion", False):
        state["score"] += SCORE_TRESPASSING
        if time_in_zone > ZONE_ENTRY_GRACE:
            state["score"] += SCORE_TIME_IN_ZONE
        if is_loitering:
            state["score"] += SCORE_LOITERING

    if alerts.get("lock", False):
        state["score"] += SCORE_LOCKPICKING

    if alerts.get("climb", False):
        state["score"] += SCORE_CLIMBING

    # Decay when nothing is active
    if not any(alerts.values()):
        state["score"] = max(0.0, state["score"] - SCORE_DECAY_PER_FRAME)

    # Cap at 2x threshold
    state["score"] = min(state["score"], SUSPICION_THRESHOLD * 2)

    # Only fire once per session
    threshold_crossed = False
    if state["score"] >= SUSPICION_THRESHOLD and not state["email_sent"]:
        threshold_crossed  = True
        state["email_sent"] = True

    return state["score"], threshold_crossed


def reset_score(state: dict):
    """Reset score and allow email to be sent again."""
    state["score"]      = 0.0
    state["email_sent"] = False