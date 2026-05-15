from config import (CLIMB_HISTORY_LEN, CLIMB_MOTION_THRESHOLD,
                    CLIMB_MIN_VISIBILITY)

def check_climbing(lm, climb_history: list) -> tuple:
    def vis(idx) -> bool:
        return (hasattr(lm[idx], 'visibility') and
                lm[idx].visibility >= CLIMB_MIN_VISIBILITY)

    # Condition 1: arms raised
    if vis(0) and (vis(15) or vis(16)):
        nose_y    = lm[0].y
        l_wrist_y = lm[15].y if vis(15) else 1.0
        r_wrist_y = lm[16].y if vis(16) else 1.0
        arms_raised = (l_wrist_y < nose_y) or (r_wrist_y < nose_y)
    else:
        arms_raised = False

    # Condition 2: upward motion
    if vis(23) and vis(24):
        avg_hip_y = (lm[23].y + lm[24].y) / 2
        climb_history.append(avg_hip_y)
        if len(climb_history) > CLIMB_HISTORY_LEN:
            climb_history.pop(0)
        upward_frames = sum(
            1 for i in range(1, len(climb_history))
            if climb_history[i] < climb_history[i - 1]
        )
        moving_up = upward_frames >= CLIMB_MOTION_THRESHOLD
    else:
        climb_history.clear()
        moving_up = False

    # Condition 3: leg spread
    if vis(27) and vis(28):
        leg_spread = abs(lm[27].x - lm[28].x) > 0.2
    else:
        leg_spread = False

    score = sum([arms_raised, moving_up, leg_spread])
    return score >= 2, arms_raised, moving_up, leg_spread