# ─── hud/drawing.py ──────────────────────────────────────────────
# Low-level drawing helpers shared by all HUD modules.
# No detection logic here — purely visual.

import cv2
from config import FRAME_W, FRAME_H, PANEL_W, C_WHITE, C_GREEN, C_DARK


def draw_corner_rect(frame, x1, y1, x2, y2, color, thickness=2, corner_len=28):
    """Draw a rectangle showing only its four corners (tactical style)."""
    for (px, py), (dx, dy) in zip(
            [(x1, y1), (x2, y1), (x1, y2), (x2, y2)],
            [(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        cv2.line(frame, (px, py), (px + dx * corner_len, py), color, thickness)
        cv2.line(frame, (px, py), (px, py + dy * corner_len), color, thickness)


def draw_hud_text(frame, text, x, y, color=C_WHITE, scale=0.6, thickness=1):
    """Draw text with a dark drop-shadow for readability on any background."""
    cv2.putText(frame, text, (x + 1, y + 1),
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def draw_alert_banner(frame, text, y_pos, color, alpha=0.8):
    """Full-width semi-transparent banner with centred text."""
    overlay = frame.copy()
    h = 58
    cv2.rectangle(overlay, (0, y_pos), (FRAME_W - PANEL_W, y_pos + h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    font = cv2.FONT_HERSHEY_DUPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 1.0, 2)
    tx = ((FRAME_W - PANEL_W) - tw) // 2
    ty = y_pos + h // 2 + th // 2
    cv2.putText(frame, text, (tx + 1, ty + 1), font, 1.0, (0, 0, 0), 3)
    cv2.putText(frame, text, (tx, ty), font, 1.0, C_WHITE, 2)


def draw_landmark_custom(frame, landmarks):
    """Draw pose skeleton with styled joints."""
    connections = [
        (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
        (11, 23), (12, 24), (23, 24), (23, 25), (24, 26),
        (25, 27), (26, 28), (27, 29), (28, 30), (29, 31), (30, 32)
    ]
    pts = {i: (int(lm.x * FRAME_W), int(lm.y * FRAME_H))
           for i, lm in enumerate(landmarks)}
    for a, b in connections:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], C_GREEN, 2, cv2.LINE_AA)
    for (x, y) in pts.values():
        cv2.circle(frame, (x, y), 5, C_GREEN, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 7, (0, 180, 80), 1, cv2.LINE_AA)


def draw_tracking_box(frame, landmarks, color, label):
    """
    Draw a full-body tracking box around the detected person.
    Box is computed from the outermost visible landmarks so it
    wraps the whole body tightly.

    Parameters
    ----------
    landmarks : pose landmarks list
    color     : BGR color for the box (red for intrusion, cyan for lockpick)
    label     : text shown above the box e.g. "TRACKING: INTRUDER"
    """
    PADDING = 18   # pixels of extra space around the body

    # Use all landmarks that are reasonably visible
    xs = [int(lm.x * FRAME_W) for lm in landmarks
          if hasattr(lm, 'visibility') and lm.visibility > 0.3]
    ys = [int(lm.y * FRAME_H) for lm in landmarks
          if hasattr(lm, 'visibility') and lm.visibility > 0.3]

    if not xs or not ys:
        return

    x1 = max(0,        min(xs) - PADDING)
    y1 = max(0,        min(ys) - PADDING)
    x2 = min(FRAME_W,  max(xs) + PADDING)
    y2 = min(FRAME_H,  max(ys) + PADDING)

    # Outer glow effect — slightly thicker darker rectangle behind
    cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2), (0, 0, 0), 3)
    # Main tracking box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    # Corner accents to match zone style
    draw_corner_rect(frame, x1, y1, x2, y2, color, thickness=2, corner_len=20)

    # Label above the box
    draw_hud_text(frame, label, x1, y1 - 10, color, scale=0.5)