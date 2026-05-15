import cv2
from config import (FRAME_W, FRAME_H, PANEL_W, BOT_BAR_H,
                    LOCK_DWELL_TIME, LOCK_ALERT_TIME,
                    C_RED, C_ORANGE, C_CYAN, C_GREEN, C_GRAY, C_WHITE, C_YELLOW)
from hud.drawing import draw_hud_text

_FIXED_BOTTOM_Y = 95 + 3 * 70 + 10

def draw_side_panel(frame, alerts: dict, lock_state_info: dict, climb_subs: dict):
    px = FRAME_W - PANEL_W
    overlay = frame.copy()
    cv2.rectangle(overlay, (px, 0), (FRAME_W, FRAME_H), (8, 8, 8), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (px, 0), (px, FRAME_H), C_GRAY, 1)

    draw_hud_text(frame, "STATUS", px + 20, 38, C_CYAN, scale=0.7)
    cv2.line(frame, (px + 15, 50), (FRAME_W - 15, 50), C_GRAY, 1)

    items = [
        ("PERSON DETECTED", alerts.get("intrusion", False), C_RED),
        ("CLIMBING",        alerts.get("climb",     False), C_ORANGE),
        ("LOCKPICK",        alerts.get("lock",      False), C_CYAN),
    ]
    for i, (label, active, acolor) in enumerate(items):
        y  = 95 + i * 70
        bx = px + 15
        bg = (30, 10, 10) if active else (20, 20, 20)
        cv2.rectangle(frame, (bx, y - 22), (FRAME_W - 15, y + 18), bg, -1)
        cv2.rectangle(frame, (bx, y - 22), (FRAME_W - 15, y + 18),
                      acolor if active else C_GRAY, 1)
        cv2.circle(frame, (bx + 18, y), 7, acolor if active else C_GRAY, -1)
        draw_hud_text(frame, label, bx + 36, y + 6,
                      acolor if active else C_GRAY, scale=0.52)
        status_txt = "ALERT" if active else "CLEAR"
        (sw, _), _ = cv2.getTextSize(status_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        draw_hud_text(frame, status_txt, FRAME_W - 15 - sw - 8, y + 6,
                      acolor if active else (60, 60, 60), scale=0.45)

    cv2.line(frame, (px + 15, _FIXED_BOTTOM_Y), (FRAME_W - 15, _FIXED_BOTTOM_Y), C_GRAY, 1)
    _draw_dynamic_section(frame, px, alerts, lock_state_info, climb_subs)


def _draw_dynamic_section(frame, px, alerts, lock_state_info, climb_subs):
    cy = _FIXED_BOTTOM_Y + 18
    bx = px + 15
    card_w = FRAME_W - 15

    if alerts.get("intrusion", False):
        cy = _draw_card(frame, bx, cy, card_w,
                        title="PERSON IN ZONE",
                        body_lines=["Subject entered", "restricted area"],
                        title_color=C_RED, border_color=C_RED)
        cy += 8

    dwell   = lock_state_info.get("dwell_elapsed", 0.0)
    elapsed = lock_state_info.get("alert_elapsed", 0.0)
    if dwell > 0 or elapsed > 0:
        cy = _draw_lockpick_card(frame, bx, cy, card_w, dwell, elapsed)
        cy += 8

    if climb_subs.get("active", False):
        cy = _draw_climb_card(frame, bx, cy, card_w, climb_subs)


def _draw_card(frame, bx, cy, card_w, title, body_lines,
               title_color, border_color, card_h=None):
    line_h  = 22
    padding = 10
    if card_h is None:
        card_h = padding + 20 + len(body_lines) * line_h + padding
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), (25, 20, 20), -1)
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), border_color, 1)
    cv2.rectangle(frame, (bx, cy), (bx + 3, cy + card_h), title_color, -1)
    draw_hud_text(frame, title, bx + 10, cy + 18, title_color, scale=0.48)
    for i, line in enumerate(body_lines):
        draw_hud_text(frame, line, bx + 10,
                      cy + padding + 20 + i * line_h, C_GRAY, scale=0.4)
    return cy + card_h


def _draw_lockpick_card(frame, bx, cy, card_w, dwell_elapsed, alert_elapsed):
    card_h = 75
    bar_h  = 10
    bar_x  = bx + 10
    bar_w  = card_w - bx - 20
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), (20, 20, 30), -1)
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), C_CYAN, 1)
    cv2.rectangle(frame, (bx, cy), (bx + 3, cy + card_h), C_CYAN, -1)
    draw_hud_text(frame, "LOCKPICK TIMER", bx + 10, cy + 18, C_CYAN, scale=0.48)
    bar_y = cy + 28
    if alert_elapsed > 0:
        progress  = min(alert_elapsed / LOCK_ALERT_TIME, 1.0)
        pct_color = C_RED if progress > 0.7 else C_ORANGE if progress > 0.4 else C_CYAN
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + int(bar_w * progress), bar_y + bar_h), pct_color, -1)
        draw_hud_text(frame, f"{alert_elapsed:.1f}s / {LOCK_ALERT_TIME:.0f}s",
                      bar_x, bar_y + bar_h + 16, pct_color, scale=0.42)
    else:
        progress = min(dwell_elapsed / LOCK_DWELL_TIME, 1.0)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x + int(bar_w * progress), bar_y + bar_h), C_GRAY, -1)
        draw_hud_text(frame, "Confirming...",
                      bar_x, bar_y + bar_h + 16, C_GRAY, scale=0.42)
    return cy + card_h


def _draw_climb_card(frame, bx, cy, card_w, climb_subs):
    card_h = 95
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), (20, 25, 20), -1)
    cv2.rectangle(frame, (bx, cy), (card_w, cy + card_h), C_ORANGE, 1)
    cv2.rectangle(frame, (bx, cy), (bx + 3, cy + card_h), C_ORANGE, -1)
    draw_hud_text(frame, "CLIMB CHECK", bx + 10, cy + 18, C_ORANGE, scale=0.48)
    checks = [
        ("ARMS UP",    climb_subs.get("arms_raised", False)),
        ("MOVING UP",  climb_subs.get("moving_up",   False)),
        ("LEG SPREAD", climb_subs.get("leg_spread",  False)),
    ]
    for i, (label, active) in enumerate(checks):
        color = C_GREEN if active else C_GRAY
        tag   = "[+]" if active else "[ ]"
        draw_hud_text(frame, f"{tag} {label}",
                      bx + 10, cy + 36 + i * 20, color, scale=0.42)
    return cy + card_h