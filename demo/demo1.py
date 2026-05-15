import cv2
import mediapipe as mp
import time
import urllib.request
import os
import numpy as np
from datetime import datetime

# ─── Model Download ───────────────────────────────────────────────
MODEL_PATH = "pose_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading pose model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        MODEL_PATH
    )
    print("Done!")

# ─── MediaPipe Setup ──────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE)

# ─── Config ───────────────────────────────────────────────────────
FRAME_W, FRAME_H = 960, 540
TRESPASS_LINE_X = FRAME_W // 2
CLIMB_THRESHOLD = 0.35
LOCK_ZONE = (650, 120, 850, 380)
LOCK_DURATION = 5

# ─── Climbing Detection Config ────────────────────────────────────
climb_history = []
CLIMB_HISTORY_LEN = 15      # frames to track
CLIMB_MOTION_THRESHOLD = 3  # how many frames must show upward motion

# ─── Colors (BGR) ─────────────────────────────────────────────────
C_GREEN   = (0, 255, 120)
C_RED     = (0, 60, 255)
C_YELLOW  = (0, 220, 255)
C_CYAN    = (255, 220, 0)
C_WHITE   = (230, 230, 230)
C_GRAY    = (120, 120, 120)
C_DARK    = (20, 20, 20)
C_ORANGE  = (0, 140, 255)

# ─── Helpers ──────────────────────────────────────────────────────
def draw_corner_rect(frame, x1, y1, x2, y2, color, thickness=2, corner_len=20):
    """Draw a rectangle with only corners visible (tactical style)."""
    pts = [(x1,y1),(x2,y1),(x1,y2),(x2,y2)]
    dirs = [(1,1),(-1,1),(1,-1),(-1,-1)]
    for (px,py),(dx,dy) in zip(pts,dirs):
        cv2.line(frame,(px,py),(px+dx*corner_len,py),color,thickness)
        cv2.line(frame,(px,py),(px,py+dy*corner_len),color,thickness)

def draw_hud_text(frame, text, x, y, color=C_WHITE, scale=0.55, thickness=1):
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (x+1, y+1), font, scale, (0,0,0), thickness+1)
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)

def draw_alert_banner(frame, text, y_pos, color, alpha=0.75):
    """Draw a semi-transparent alert banner."""
    overlay = frame.copy()
    h = 46
    cv2.rectangle(overlay, (0, y_pos), (FRAME_W, y_pos + h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    font = cv2.FONT_HERSHEY_DUPLEX
    tw, _ = cv2.getTextSize(text, font, 0.85, 2)[0], None
    tx = (FRAME_W - tw[0]) // 2 if isinstance(tw, tuple) else 30
    (tw, th), _ = cv2.getTextSize(text, font, 0.85, 2)
    tx = (FRAME_W - tw) // 2
    ty = y_pos + h // 2 + th // 2
    cv2.putText(frame, text, (tx+1, ty+1), font, 0.85, (0,0,0), 3)
    cv2.putText(frame, text, (tx, ty), font, 0.85, C_WHITE, 2)

def draw_landmark_custom(frame, landmarks):
    """Draw skeleton with custom styled joints and bones."""
    connections = [
        (11,12),(11,13),(13,15),(12,14),(14,16),
        (11,23),(12,24),(23,24),(23,25),(24,26),
        (25,27),(26,28),(27,29),(28,30),(29,31),(30,32)
    ]
    pts = {}
    for i, lm in enumerate(landmarks):
        x, y = int(lm.x * FRAME_W), int(lm.y * FRAME_H)
        pts[i] = (x, y)

    for a, b in connections:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], C_GREEN, 1, cv2.LINE_AA)

    for i, (x, y) in pts.items():
        cv2.circle(frame, (x, y), 4, C_GREEN, -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 5, (0, 180, 80), 1, cv2.LINE_AA)

def draw_scanline_overlay(frame, intensity=18):
    """Subtle scanlines for camera aesthetic."""
    for y in range(0, FRAME_H, 4):
        cv2.line(frame, (0, y), (FRAME_W, y), (0, 0, 0), 1)

def draw_top_bar(frame, alert_active):
    """Top HUD bar with timestamp and status."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (FRAME_W, 38), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    draw_hud_text(frame, f"REC  {now}", 10, 25, C_RED if int(time.time()) % 2 == 0 else C_GRAY, scale=0.55)

    status = "! ALERT ACTIVE" if alert_active else "MONITORING"
    color  = C_RED if alert_active else C_GREEN
    draw_hud_text(frame, status, FRAME_W - 200, 25, color, scale=0.55)

    draw_hud_text(frame, "CAM-01  |  AI SECURITY SYSTEM  |  LIVE", FRAME_W//2 - 180, 25, C_WHITE, scale=0.5)

def draw_bottom_bar(frame, person_detected):
    """Bottom HUD bar."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, FRAME_H - 36), (FRAME_W, FRAME_H), (10,10,10), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    det = "SUBJECT DETECTED" if person_detected else "NO SUBJECT"
    col = C_YELLOW if person_detected else C_GRAY
    draw_hud_text(frame, det, 10, FRAME_H - 12, col, scale=0.5)
    draw_hud_text(frame, "PRESS [Q] TO EXIT", FRAME_W - 190, FRAME_H - 12, C_GRAY, scale=0.45)

def draw_side_panel(frame, alerts):
    """Right side status panel."""
    overlay = frame.copy()
    px, pw = FRAME_W - 200, 200
    cv2.rectangle(overlay, (px, 38), (FRAME_W, FRAME_H - 36), (10,10,10), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    draw_hud_text(frame, "─ STATUS PANEL ─", px + 10, 62, C_CYAN, scale=0.45)

    items = [
        ("TRESPASS",   alerts.get("trespass", False)),
        ("CLIMBING",   alerts.get("climb",    False)),
        ("LOCKPICK",   alerts.get("lock",     False)),
    ]
    for i, (label, active) in enumerate(items):
        y = 95 + i * 38
        color = C_RED if active else C_GRAY
        indicator = "[ ! ]" if active else "[   ]"
        draw_hud_text(frame, f"{indicator} {label}", px + 12, y, color, scale=0.48)
        if active:
            cv2.rectangle(frame, (px + 8, y - 14), (px + pw - 8, y + 6),
                          (0, 30, 100), -1)
            cv2.rectangle(frame, (px + 8, y - 14), (px + pw - 8, y + 6),
                          C_RED, 1)

    draw_hud_text(frame, "─────────────────", px + 10, 215, C_GRAY, scale=0.35)
    draw_hud_text(frame, "BOUNDARY  : MID", px + 12, 235, C_GRAY, scale=0.4)
    draw_hud_text(frame, "LOCK ZONE : RIGHT", px + 12, 255, C_GRAY, scale=0.4)
    draw_hud_text(frame, f"LOCK TIME : {LOCK_DURATION}s", px + 12, 275, C_GRAY, scale=0.4)

def draw_climb_indicators(frame, arms_raised, moving_up, leg_spread):
    """Show which climbing conditions are currently active."""
    px = FRAME_W - 200
    draw_hud_text(frame, "─ CLIMB CHECK ─", px + 10, 300, C_CYAN, scale=0.4)
    checks = [
        ("ARMS UP",   arms_raised),
        ("MOVING UP", moving_up),
        ("LEG SPREAD",leg_spread),
    ]
    for i, (label, active) in enumerate(checks):
        y = 320 + i * 22
        color = C_GREEN if active else C_GRAY
        dot = "●" if active else "○"
        draw_hud_text(frame, f"{dot} {label}", px + 12, y, color, scale=0.38)

# ─── Improved Climbing Detection ──────────────────────────────────
def is_climbing(lm, climb_history):
    """
    Checks 3 things:
    1. Arms raised above head
    2. Upward body movement over time
    3. Legs spread wide (climbing stance)
    Returns: (bool is_climbing, bool arms_raised, bool moving_up, bool leg_spread)
    """
    nose_y      = lm[0].y
    l_wrist_y   = lm[15].y
    r_wrist_y   = lm[16].y
    l_ankle_x   = lm[27].x
    r_ankle_x   = lm[28].x
    avg_hip_y   = (lm[23].y + lm[24].y) / 2

    # Check 1: At least one wrist above the nose
    arms_raised = (l_wrist_y < nose_y) or (r_wrist_y < nose_y)

    # Check 2: Upward movement over recent frames
    climb_history.append(avg_hip_y)
    if len(climb_history) > CLIMB_HISTORY_LEN:
        climb_history.pop(0)

    upward_frames = sum(
        1 for i in range(1, len(climb_history))
        if climb_history[i] < climb_history[i - 1]
    )
    moving_up = upward_frames >= CLIMB_MOTION_THRESHOLD

    # Check 3: Legs spread wide
    leg_spread = abs(l_ankle_x - r_ankle_x) > 0.2

    # Trigger if at least 2 of 3 conditions are true
    score = sum([arms_raised, moving_up, leg_spread])
    return score >= 2, arms_raised, moving_up, leg_spread

# ─── Main Loop ────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

lock_start_time = None
PANEL_W = 200

with PoseLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = landmarker.detect(mp_image)

        alerts = {"trespass": False, "climb": False, "lock": False}
        person_detected = bool(results.pose_landmarks)
        alert_banners = []

        # Climbing indicator defaults (shown even when no person detected)
        arms_raised = moving_up = leg_spread = False

        # ── Trespass line ──
        cv2.line(frame,
                 (TRESPASS_LINE_X, 38),
                 (TRESPASS_LINE_X, FRAME_H - 36),
                 C_YELLOW, 1, cv2.LINE_AA)
        draw_hud_text(frame, "BOUNDARY", TRESPASS_LINE_X + 6, 58, C_YELLOW, scale=0.42)

        # ── Lock zone ──
        draw_corner_rect(frame, *LOCK_ZONE, C_CYAN, thickness=2, corner_len=16)
        draw_hud_text(frame, "LOCK ZONE", LOCK_ZONE[0], LOCK_ZONE[1] - 8, C_CYAN, scale=0.42)

        if results.pose_landmarks:
            lm = results.pose_landmarks[0]
            draw_landmark_custom(frame, lm)

            # TRESPASSING
            nose_x = int(lm[0].x * FRAME_W)
            if nose_x > TRESPASS_LINE_X:
                alerts["trespass"] = True
                alert_banners.append(("!! TRESPASSING DETECTED !!", (0, 40, 180)))

            # CLIMBING (improved)
            climbing_detected, arms_raised, moving_up, leg_spread = is_climbing(lm, climb_history)
            if climbing_detected:
                alerts["climb"] = True
                alert_banners.append(("!! CLIMBING DETECTED !!", (0, 80, 180)))

            # LOCKPICKING
            wx = int(lm[16].x * FRAME_W)
            wy = int(lm[16].y * FRAME_H)
            in_zone = (LOCK_ZONE[0] < wx < LOCK_ZONE[2] and
                       LOCK_ZONE[1] < wy < LOCK_ZONE[3])

            if in_zone:
                if lock_start_time is None:
                    lock_start_time = time.time()
                elapsed = time.time() - lock_start_time
                progress = min(elapsed / LOCK_DURATION, 1.0)
                bar_x, bar_y = LOCK_ZONE[0], LOCK_ZONE[3] + 10
                bar_w = LOCK_ZONE[2] - LOCK_ZONE[0]
                cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 8), C_DARK, -1)
                cv2.rectangle(frame, (bar_x, bar_y),
                              (bar_x + int(bar_w * progress), bar_y + 8), C_CYAN, -1)
                draw_hud_text(frame, f"{elapsed:.1f}s / {LOCK_DURATION}s",
                              bar_x, bar_y + 24, C_CYAN, scale=0.42)
                if elapsed > LOCK_DURATION:
                    alerts["lock"] = True
                    alert_banners.append(("!! LOCKPICKING ALERT !!", (0, 40, 160)))
            else:
                lock_start_time = None

        # ── Overlays ──
        draw_scanline_overlay(frame)
        draw_top_bar(frame, any(alerts.values()))
        draw_bottom_bar(frame, person_detected)
        draw_side_panel(frame, alerts)
        draw_climb_indicators(frame, arms_raised, moving_up, leg_spread)

        # ── Alert banners ──
        for i, (msg, color) in enumerate(alert_banners):
            draw_alert_banner(frame, msg, 44 + i * 52, color)

        cv2.imshow("AI Security System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()