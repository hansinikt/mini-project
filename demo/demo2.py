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
BaseOptions           = mp.tasks.BaseOptions
PoseLandmarker        = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode

options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE)

# ─── Config ───────────────────────────────────────────────────────
FRAME_W, FRAME_H = 1280, 720
TOP_BAR_H        = 55
BOT_BAR_H        = 50
PANEL_W          = 280

# Zone definitions — Code 1's layout
RESTRICTED_ZONE = (60, TOP_BAR_H + 20, 560, FRAME_H - BOT_BAR_H - 20)
LOCK_ZONE       = (820, TOP_BAR_H + 60, 1020, FRAME_H - BOT_BAR_H - 60)
LOCK_DURATION   = 5

# ─── Climbing Detection Config (from Code 2) ──────────────────────
climb_history        = []
CLIMB_HISTORY_LEN    = 15   # frames to track
CLIMB_MOTION_THRESHOLD = 3  # how many frames must show upward motion

# ─── Colors (BGR) ─────────────────────────────────────────────────
C_GREEN  = (0, 255, 120)
C_RED    = (0, 60,  255)
C_YELLOW = (0, 220, 255)
C_CYAN   = (255, 220, 0)
C_WHITE  = (230, 230, 230)
C_GRAY   = (130, 130, 130)
C_DARK   = (15,  15,  15)
C_ORANGE = (0,   140, 255)

# ─────────────────────────────────────────────────────────────────
# HELPERS  (Code 1's HUD style throughout)
# ─────────────────────────────────────────────────────────────────

def draw_corner_rect(frame, x1, y1, x2, y2, color, thickness=2, corner_len=28):
    for (px, py), (dx, dy) in zip(
            [(x1,y1),(x2,y1),(x1,y2),(x2,y2)],
            [(1,1),(-1,1),(1,-1),(-1,-1)]):
        cv2.line(frame, (px, py), (px+dx*corner_len, py), color, thickness)
        cv2.line(frame, (px, py), (px, py+dy*corner_len), color, thickness)

def draw_hud_text(frame, text, x, y, color=C_WHITE, scale=0.6, thickness=1):
    cv2.putText(frame, text, (x+1, y+1), cv2.FONT_HERSHEY_SIMPLEX, scale, (0,0,0), thickness+2)
    cv2.putText(frame, text, (x,   y  ), cv2.FONT_HERSHEY_SIMPLEX, scale, color,   thickness)

def draw_alert_banner(frame, text, y_pos, color, alpha=0.8):
    overlay = frame.copy()
    h = 58
    cv2.rectangle(overlay, (0, y_pos), (FRAME_W - PANEL_W, y_pos+h), color, -1)
    cv2.addWeighted(overlay, alpha, frame, 1-alpha, 0, frame)
    font = cv2.FONT_HERSHEY_DUPLEX
    (tw, th), _ = cv2.getTextSize(text, font, 1.0, 2)
    tx = ((FRAME_W - PANEL_W) - tw) // 2
    ty = y_pos + h//2 + th//2
    cv2.putText(frame, text, (tx+1, ty+1), font, 1.0, (0,0,0), 3)
    cv2.putText(frame, text, (tx,   ty  ), font, 1.0, C_WHITE,  2)

def draw_landmark_custom(frame, landmarks):
    connections = [
        (11,12),(11,13),(13,15),(12,14),(14,16),
        (11,23),(12,24),(23,24),(23,25),(24,26),
        (25,27),(26,28),(27,29),(28,30),(29,31),(30,32)
    ]
    pts = {i: (int(lm.x*FRAME_W), int(lm.y*FRAME_H))
           for i, lm in enumerate(landmarks)}
    for a, b in connections:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], C_GREEN, 2, cv2.LINE_AA)
    for (x, y) in pts.values():
        cv2.circle(frame, (x, y), 5, C_GREEN,    -1, cv2.LINE_AA)
        cv2.circle(frame, (x, y), 7, (0,180,80),  1, cv2.LINE_AA)

def draw_scanline_overlay(frame):
    for y in range(0, FRAME_H, 5):
        cv2.line(frame, (0, y), (FRAME_W, y), (0,0,0), 1)

def draw_top_bar(frame, alert_active):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0,0), (FRAME_W, TOP_BAR_H), (10,10,10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (0, TOP_BAR_H), (FRAME_W, TOP_BAR_H), C_GRAY, 1)

    now   = datetime.now().strftime("%Y-%m-%d   %H:%M:%S")
    blink = C_RED if int(time.time()) % 2 == 0 else (80,80,80)
    draw_hud_text(frame, f"● REC   {now}", 18, 36, blink, scale=0.65)

    title = "CAM-01   |   AI SECURITY SYSTEM   |   LIVE"
    (tw,_), _ = cv2.getTextSize(title, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
    draw_hud_text(frame, title, (FRAME_W - PANEL_W - tw)//2, 36, C_WHITE, scale=0.6)

    status = "⚠  ALERT ACTIVE" if alert_active else "●  MONITORING"
    color  = C_RED if alert_active else C_GREEN
    draw_hud_text(frame, status, FRAME_W - PANEL_W - 230, 36, color, scale=0.65)

def draw_bottom_bar(frame, person_detected):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, FRAME_H-BOT_BAR_H), (FRAME_W, FRAME_H), (10,10,10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (0, FRAME_H-BOT_BAR_H), (FRAME_W, FRAME_H-BOT_BAR_H), C_GRAY, 1)

    det = "▶  SUBJECT DETECTED" if person_detected else "○  NO SUBJECT IN FRAME"
    draw_hud_text(frame, det, 18, FRAME_H-16,
                  C_YELLOW if person_detected else C_GRAY, scale=0.58)
    draw_hud_text(frame, "PRESS  Q  TO EXIT",
                  FRAME_W - PANEL_W - 240, FRAME_H-16, C_GRAY, scale=0.52)

def draw_side_panel(frame, alerts, lock_elapsed=0):
    px = FRAME_W - PANEL_W
    overlay = frame.copy()
    cv2.rectangle(overlay, (px,0), (FRAME_W, FRAME_H), (8,8,8), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.line(frame, (px, 0), (px, FRAME_H), C_GRAY, 1)

    draw_hud_text(frame, "STATUS", px+20, 38, C_CYAN, scale=0.7)
    cv2.line(frame, (px+15, 50), (FRAME_W-15, 50), C_GRAY, 1)

    items = [
        ("INTRUSION", alerts.get("intrusion", False), C_RED),
        ("CLIMBING",  alerts.get("climb",     False), C_ORANGE),
        ("LOCKPICK",  alerts.get("lock",      False), C_CYAN),
    ]

    for i, (label, active, acolor) in enumerate(items):
        y  = 95 + i * 70
        bx = px + 15
        bg = (30,10,10) if active else (20,20,20)
        cv2.rectangle(frame, (bx, y-22), (FRAME_W-15, y+18), bg, -1)
        cv2.rectangle(frame, (bx, y-22), (FRAME_W-15, y+18),
                      acolor if active else C_GRAY, 1)
        cv2.circle(frame, (bx+18, y), 7, acolor if active else C_GRAY, -1)
        draw_hud_text(frame, label, bx+36, y+6,
                      acolor if active else C_GRAY, scale=0.58)
        status_txt = "ALERT" if active else "CLEAR"
        (sw,_), _ = cv2.getTextSize(status_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        draw_hud_text(frame, status_txt,
                      FRAME_W-15-sw-8, y+6,
                      acolor if active else (60,60,60), scale=0.45)

    # Divider
    dy = 95 + len(items)*70 + 10
    cv2.line(frame, (px+15, dy), (FRAME_W-15, dy), C_GRAY, 1)

    # Config info
    cy = dy + 28
    for txt in [f"ZONE   LEFT PANEL",
                f"LOCK   RIGHT PANEL",
                f"TIMER  {LOCK_DURATION} SEC"]:
        draw_hud_text(frame, txt, px+18, cy, C_GRAY, scale=0.44)
        cy += 28

    # Lock progress bar
    if lock_elapsed > 0:
        bar_y = FRAME_H - BOT_BAR_H - 60
        bar_x = px + 15
        bar_w = PANEL_W - 30
        progress = min(lock_elapsed / LOCK_DURATION, 1.0)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x+bar_w, bar_y+12), (30,30,30), -1)
        cv2.rectangle(frame, (bar_x, bar_y),
                      (bar_x+int(bar_w*progress), bar_y+12), C_CYAN, -1)
        draw_hud_text(frame, f"LOCK  {lock_elapsed:.1f}s / {LOCK_DURATION}s",
                      bar_x, bar_y-8, C_CYAN, scale=0.45)

def draw_climb_indicators(frame, arms_raised, moving_up, leg_spread):
    """
    Code 2's climb sub-condition display, repositioned into Code 1's side panel.
    Drawn below the config block in the right panel.
    """
    px = FRAME_W - PANEL_W
    # find Y below config block  (3 config lines * 28px + divider + margin)
    dy  = 95 + 3*70 + 10           # same divider Y as in draw_side_panel
    cy  = dy + 28 + 3*28 + 18      # after 3 config lines + gap

    cv2.line(frame, (px+15, cy-10), (FRAME_W-15, cy-10), C_GRAY, 1)
    draw_hud_text(frame, "CLIMB CHECK", px+20, cy+14, C_CYAN, scale=0.48)
    cy += 30

    checks = [
        ("ARMS UP",    arms_raised),
        ("MOVING UP",  moving_up),
        ("LEG SPREAD", leg_spread),
    ]
    for label, active in checks:
        color = C_GREEN if active else C_GRAY
        dot   = "●" if active else "○"
        draw_hud_text(frame, f"{dot}  {label}", px+20, cy, color, scale=0.44)
        cy += 26

# ─────────────────────────────────────────────────────────────────
# IMPROVED CLIMBING DETECTION  (Code 2's logic, unchanged)
# ─────────────────────────────────────────────────────────────────

def is_climbing(lm, climb_history):
    """
    3-condition check — needs at least 2/3 to trigger.
      1. Arms raised: at least one wrist above the nose
      2. Upward motion: hip Y decreasing across recent frames
      3. Leg spread:  ankles far apart horizontally
    """
    nose_y    = lm[0].y
    l_wrist_y = lm[15].y
    r_wrist_y = lm[16].y
    l_ankle_x = lm[27].x
    r_ankle_x = lm[28].x
    avg_hip_y = (lm[23].y + lm[24].y) / 2

    # Condition 1
    arms_raised = (l_wrist_y < nose_y) or (r_wrist_y < nose_y)

    # Condition 2
    climb_history.append(avg_hip_y)
    if len(climb_history) > CLIMB_HISTORY_LEN:
        climb_history.pop(0)
    upward_frames = sum(
        1 for i in range(1, len(climb_history))
        if climb_history[i] < climb_history[i-1]
    )
    moving_up = upward_frames >= CLIMB_MOTION_THRESHOLD

    # Condition 3
    leg_spread = abs(l_ankle_x - r_ankle_x) > 0.2

    score = sum([arms_raised, moving_up, leg_spread])
    return score >= 2, arms_raised, moving_up, leg_spread

# ─── Main Loop ────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

lock_start_time = None

with PoseLandmarker.create_from_options(options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # ── Pose detection ──
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results   = landmarker.detect(mp_image)

        alerts          = {"intrusion": False, "climb": False, "lock": False}
        person_detected = bool(results.pose_landmarks)
        alert_banners   = []
        lock_elapsed    = 0

        # Default climb sub-states (shown even without a detected person)
        arms_raised = moving_up = leg_spread = False

        # ── Draw zones ──
        draw_corner_rect(frame, *RESTRICTED_ZONE, C_YELLOW, thickness=2, corner_len=28)
        draw_hud_text(frame, "RESTRICTED ZONE",
                      RESTRICTED_ZONE[0]+8, RESTRICTED_ZONE[1]-10, C_YELLOW, scale=0.52)

        draw_corner_rect(frame, *LOCK_ZONE, C_CYAN, thickness=2, corner_len=28)
        draw_hud_text(frame, "LOCK ZONE",
                      LOCK_ZONE[0]+8, LOCK_ZONE[1]-10, C_CYAN, scale=0.52)

        if results.pose_landmarks:
            lm = results.pose_landmarks[0]
            draw_landmark_custom(frame, lm)

            # ── Intrusion (restricted zone) ──
            nx = int(lm[0].x * FRAME_W)
            ny = int(lm[0].y * FRAME_H)
            if (RESTRICTED_ZONE[0] < nx < RESTRICTED_ZONE[2] and
                    RESTRICTED_ZONE[1] < ny < RESTRICTED_ZONE[3]):
                alerts["intrusion"] = True
                alert_banners.append(("!! INTRUSION — RESTRICTED ZONE !!", (0, 40, 180)))

            # ── Climbing (Code 2's improved 3-condition logic) ──
            climbing_detected, arms_raised, moving_up, leg_spread = \
                is_climbing(lm, climb_history)
            if climbing_detected:
                alerts["climb"] = True
                alert_banners.append(("!! CLIMBING DETECTED !!", (0, 80, 160)))

            # ── Lockpicking ──
            wx = int(lm[16].x * FRAME_W)
            wy = int(lm[16].y * FRAME_H)
            in_zone = (LOCK_ZONE[0] < wx < LOCK_ZONE[2] and
                       LOCK_ZONE[1] < wy < LOCK_ZONE[3])
            if in_zone:
                if lock_start_time is None:
                    lock_start_time = time.time()
                lock_elapsed = time.time() - lock_start_time
                if lock_elapsed > LOCK_DURATION:
                    alerts["lock"] = True
                    alert_banners.append(("!! LOCKPICKING ALERT !!", (0, 40, 140)))
            else:
                lock_start_time = None

        # ── HUD layers ──
        draw_scanline_overlay(frame)
        draw_top_bar(frame,    any(alerts.values()))
        draw_bottom_bar(frame, person_detected)
        draw_side_panel(frame, alerts, lock_elapsed)
        draw_climb_indicators(frame, arms_raised, moving_up, leg_spread)   # Code 2 addition

        # ── Alert banners ──
        for i, (msg, color) in enumerate(alert_banners):
            draw_alert_banner(frame, msg, TOP_BAR_H + i*64, color)

        cv2.imshow("AI Security System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()