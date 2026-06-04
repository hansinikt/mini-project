# ─── alerts/suspicion.py ─────────────────────────────────────────
# Suspicion bar logic:
#
#   2+ detectors active          → bar fills fast (~3 seconds to full)
#   1 detector active            → bar fills slowly (~30 seconds to full)
#   Person detected, 0 detectors → bar HOLDS its current value
#   No person in frame           → bar decays down (~10 seconds to empty)
#   Bar hits 100%                → alert fires (once per session)
#   Press R                      → resets bar and allows alert again
#
# This means if a person triggers trespassing then moves to the lock
# zone, the bar keeps its accumulated value and fills fast once
# lockpicking fires — rather than resetting when they leave the zone.
#
# Bar value is stored as 0.0 to 1.0 (0% to 100%)

from config import (SUSPICION_SLOW_RATE, SUSPICION_FAST_RATE,
                    SUSPICION_DECAY_RATE)


def make_suspicion_state() -> dict:
    """Call once at startup."""
    return {
        "bar":        0.0,    # 0.0 = empty, 1.0 = full
        "email_sent": False,  # only one email per session
    }


def update_suspicion(state: dict, alerts: dict,
                     person_detected: bool) -> tuple:
    """
    Call every frame.

    Parameters
    ----------
    state            : dict from make_suspicion_state()
    alerts           : {"intrusion": bool, "climb": bool, "lock": bool}
    person_detected  : bool — True if any person is visible in frame

    Returns
    -------
    (bar_value, alert_should_fire)
      bar_value         — float 0.0 to 1.0
      alert_should_fire — True once bar hits 1.0 and alert not yet sent
    """
    active_count = sum([
        alerts.get("intrusion", False),
        alerts.get("climb",     False),
        alerts.get("lock",      False),
    ])

    if active_count >= 2:
        # Two or more detectors — fill fast
        state["bar"] += SUSPICION_FAST_RATE
    elif active_count == 1:
        # One detector — fill slowly
        state["bar"] += SUSPICION_SLOW_RATE
    elif person_detected:
        # Person in frame but not in any zone — hold the bar value
        pass
    else:
        # No person at all — decay
        state["bar"] -= SUSPICION_DECAY_RATE

    # Clamp between 0 and 1
    state["bar"] = max(0.0, min(1.0, state["bar"]))

    # Fire alert once when bar hits full
    alert_should_fire = False
    if state["bar"] >= 1.0 and not state["email_sent"]:
        alert_should_fire  = True
        state["email_sent"] = True

    return state["bar"], alert_should_fire


def reset_suspicion(state: dict):
    """Reset bar and allow alert to fire again."""
    state["bar"]        = 0.0
    state["email_sent"] = False