import cv2
from config import FRAME_W, FRAME_H, C_WHITE, C_GREEN, PANEL_W

def draw_corner_rect(frame, x1, y1, x2, y2, color, thickness=2, corner_len=28):
    for (px, py), (dx, dy) in zip(
            [(x1, y1), (x2, y1), (x1, y2), (x2, y2)],
            [(1, 1), (-1, 1), (1, -1), (-1, -1)]):
        cv2.line(frame, (px, py), (px + dx * corner_len, py), color, thickness)
        cv2.line(frame, (px, py), (px, py + dy * corner_len), color, thickness)

def draw_hud_text(frame, text, x, y, color=C_WHITE, scale=0.6, thickness=1):
    cv2.putText(frame, text, (x + 1, y + 1),
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thickness + 2)
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

def draw_alert_banner(frame, text, y_pos, color, alpha=0.8):
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