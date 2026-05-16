# ─── alerts/suspicion.py ─────────────────────────────────────────
# Suspicion bar logic:
#
#   0 detectors active  → bar decays down
#   1 detector active   → bar fills slowly (~30 seconds to full)
#   2+ detectors active → bar fills fast (~3 seconds to full)
#   Bar hits 100%       → email fires (once per session)
#   Press R             → resets bar and allows email again
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


def update_suspicion(state: dict, alerts: dict) -> tuple:
    """
    Call every frame.

    Parameters
    ----------
    state  : dict from make_suspicion_state()
    alerts : {"intrusion": bool, "climb": bool, "lock": bool}

    Returns
    -------
    (bar_value, email_should_fire)
      bar_value         — float 0.0 to 1.0
      email_should_fire — True once bar hits 1.0 and email not yet sent
    """
    active_count = sum([
        alerts.get("intrusion", False),
        alerts.get("climb",     False),
        alerts.get("lock",      False),
    ])

    if active_count >= 2:
        state["bar"] += SUSPICION_FAST_RATE
    elif active_count == 1:
        state["bar"] += SUSPICION_SLOW_RATE
    else:
        state["bar"] -= SUSPICION_DECAY_RATE

    # Clamp between 0 and 1
    state["bar"] = max(0.0, min(1.0, state["bar"]))

    # Fire email once when bar hits full
    email_should_fire = False
    if state["bar"] >= 1.0 and not state["email_sent"]:
        email_should_fire  = True
        state["email_sent"] = True

    return state["bar"], email_should_fire


def reset_suspicion(state: dict):
    """Reset bar and allow email to fire again."""
    state["bar"]        = 0.0
    state["email_sent"] = False