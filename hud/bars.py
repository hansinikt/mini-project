# ─── hud/bars.py ─────────────────────────────────────────────────
# Top bar (timestamp, title, alert status) and
# bottom bar (subject detected, exit hint).

import cv2
import time
from datetime import datetime
from config import FRAME_W, FRAME_H, TOP_BAR_H, BOT_BAR_H, PANEL_W, C_RED, C_GREEN, C_YELLOW, C_GRAY, C_WHITE
from hud.drawing import draw_hud_text


def draw_top_bar(frame, alert_active: bool):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, TOP_BAR_H), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (0, TOP_BAR_H), (FRAME_W, TOP_BAR_H), C_GRAY, 1)

    # Left — blinking REC + timestamp
    now   = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    blink = C_RED if int(time.time()) % 2 == 0 else (80, 80, 80)
    rec_text = f"[REC]  {now}"
    draw_hud_text(frame, rec_text, 18, 36, blink, scale=0.6)

    # Centre — title (computed from available space between REC and status)
    title = "AI SECURITY SYSTEM  |  LIVE"
    (tw, _), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    title_x = (FRAME_W - PANEL_W - tw) // 2
    draw_hud_text(frame, title, title_x, 36, C_WHITE, scale=0.6)

    # Right — alert / monitoring status
    status = "[!] ALERT ACTIVE" if alert_active else "[*] MONITORING"
    color  = C_RED if alert_active else C_GREEN
    (sw, _), _ = cv2.getTextSize(status, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    draw_hud_text(frame, status, FRAME_W - PANEL_W - sw - 18, 36, color, scale=0.6)


def draw_bottom_bar(frame, person_detected: bool):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, FRAME_H - BOT_BAR_H), (FRAME_W, FRAME_H), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (0, FRAME_H - BOT_BAR_H), (FRAME_W, FRAME_H - BOT_BAR_H), C_GRAY, 1)

    det   = "[>] SUBJECT DETECTED" if person_detected else "[ ] NO SUBJECT IN FRAME"
    color = C_YELLOW if person_detected else C_GRAY
    draw_hud_text(frame, det, 18, FRAME_H - 16, color, scale=0.58)
    draw_hud_text(frame, "PRESS  Q  TO EXIT",
                  FRAME_W - PANEL_W - 240, FRAME_H - 16, C_GRAY, scale=0.52)