# ─── main.py ─────────────────────────────────────────────────────
# Entry point for SmartSurveil.
# This file only handles:
#   - Camera setup
#   - MediaPipe pose model setup
#   - The frame loop
#   - Calling each detector and passing results to the HUD
#
# All logic lives in detectors/, hud/, and alerts/

import cv2
import mediapipe as mp
import urllib.request
import os
import threading

from config import (FRAME_W, FRAME_H, TOP_BAR_H,
                    RESTRICTED_ZONE, LOCK_ZONE, C_YELLOW, C_CYAN,
                    C_WHITE, C_RED, C_GREEN, C_GRAY, C_ORANGE)

from detectors.trespassing import check_trespassing
from detectors.climbing    import check_climbing
from detectors.lockpicking import check_lockpicking, make_lock_state

from hud.drawing import (draw_corner_rect, draw_hud_text,
                         draw_alert_banner, draw_landmark_custom,
                         draw_tracking_box)
from hud.bars    import draw_top_bar, draw_bottom_bar
from hud.panel   import draw_side_panel

from alerts.suspicion  import make_suspicion_state, update_score, reset_score
from alerts.email_alert import send_alert_email

# ─── Model download ───────────────────────────────────────────────
MODEL_PATH = "pose_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading pose model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        MODEL_PATH
    )
    print("Done!")

# ─── MediaPipe setup ──────────────────────────────────────────────
BaseOptions           = mp.tasks.BaseOptions
PoseLandmarker        = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode

mp_options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE)

# ─── Per-session state ────────────────────────────────────────────
climb_history    = []
lock_state       = make_lock_state()
suspicion_state  = make_suspicion_state()

# ─── Camera ───────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

def _draw_score_bar(frame, score, threshold=100):
    """Draw suspicion score bar in bottom-left of frame."""
    bar_x  = 18
    bar_y  = FRAME_H - 90
    bar_w  = 200
    bar_h  = 12
    progress = min(score / threshold, 1.0)

    # Color shifts red as score rises
    if progress > 0.7:
        bar_color = C_RED
    elif progress > 0.4:
        bar_color = C_ORANGE
    else:
        bar_color = C_GREEN

    draw_hud_text(frame, "SUSPICION", bar_x, bar_y - 6, C_GRAY, scale=0.42)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40,40,40), -1)
    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + int(bar_w * progress), bar_y + bar_h), bar_color, -1)
    draw_hud_text(frame, f"{score:.0f} / {threshold}",
                  bar_x, bar_y + bar_h + 16, bar_color, scale=0.42)
    draw_hud_text(frame, "R = RESET SCORE",
                  bar_x, bar_y + bar_h + 34, C_GRAY, scale=0.38)

# ─── Main loop ────────────────────────────────────────────────────
with PoseLandmarker.create_from_options(mp_options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        # Pose detection
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = landmarker.detect(img)

        # ── Default state ─────────────────────────────────────────
        alerts = {"intrusion": False, "climb": False, "lock": False}
        lock_info  = {"dwell_elapsed": 0.0, "alert_elapsed": 0.0,
                      "near_door": False, "crouching": False, "stationary": False}
        climb_subs = {"arms_raised": False, "moving_up": False,
                      "leg_spread": False, "active": False}
        alert_banners   = []
        person_detected = bool(results.pose_landmarks)

        # ── Draw static zones ─────────────────────────────────────
        draw_corner_rect(frame, *RESTRICTED_ZONE, C_YELLOW, thickness=2, corner_len=28)
        draw_hud_text(frame, "RESTRICTED ZONE",
                      RESTRICTED_ZONE[0] + 8, RESTRICTED_ZONE[1] - 10,
                      C_YELLOW, scale=0.52)

        draw_corner_rect(frame, *LOCK_ZONE, C_CYAN, thickness=2, corner_len=28)
        draw_hud_text(frame, "LOCK ZONE",
                      LOCK_ZONE[0] + 8, LOCK_ZONE[1] - 10,
                      C_CYAN, scale=0.52)

        # ── Run detectors ─────────────────────────────────────────
        if results.pose_landmarks:
            lm = results.pose_landmarks[0]
            draw_landmark_custom(frame, lm)

            # 1. Trespassing
            if check_trespassing(lm):
                alerts["intrusion"] = True
                alert_banners.append(
                    ("!! PERSON IN RESTRICTED ZONE !!", (0, 40, 180)))

            # 2. Climbing
            detected, arms_r, mov_up, leg_sp = check_climbing(lm, climb_history)
            climb_subs = {"arms_raised": arms_r, "moving_up": mov_up,
                          "leg_spread": leg_sp, "active": detected}
            if detected:
                alerts["climb"] = True
                alert_banners.append(("!! CLIMBING DETECTED !!", (0, 80, 160)))

            # 3. Lockpicking
            fired, dwell_e, alert_e, near_door, crouching, stationary = \
                check_lockpicking(lm, lock_state)
            lock_info = {
                "dwell_elapsed": dwell_e,
                "alert_elapsed": alert_e,
                "near_door":     near_door,
                "crouching":     crouching,
                "stationary":    stationary,
            }
            if fired:
                alerts["lock"] = True
                alert_banners.append(("!! LOCKPICKING ALERT !!", (0, 40, 140)))

            # ── Tracking ─────────────────────────────────────────
            if alerts["intrusion"]:
                draw_tracking_box(frame, lm,
                                  color=(0, 60, 255),
                                  label="TRACKING: INTRUDER")
            if alerts["lock"]:
                draw_tracking_box(frame, lm,
                                  color=(255, 220, 0),
                                  label="TRACKING: SUSPECT")

        # ── Suspicion score ───────────────────────────────────────
        score, threshold_crossed = update_score(suspicion_state, alerts)

        if threshold_crossed:
            # Build trigger list for email
            triggers = []
            if alerts["intrusion"]: triggers.append("Person in restricted zone")
            if alerts["lock"]:      triggers.append("Lockpicking behavior detected")
            if alerts["climb"]:     triggers.append("Climbing detected")

            # Send email in background so it doesn't freeze the camera
            threading.Thread(
                target=send_alert_email,
                args=(triggers, score),
                daemon=True
            ).start()

            alert_banners.append(("!! SUSPICION THRESHOLD REACHED — ALERT SENT !!",
                                   (0, 0, 140)))

        # ── Draw HUD ──────────────────────────────────────────────
        draw_top_bar(frame,    any(alerts.values()))
        draw_bottom_bar(frame, person_detected)
        draw_side_panel(frame, alerts, lock_info, climb_subs)
        _draw_score_bar(frame, score)

        for i, (msg, color) in enumerate(alert_banners):
            draw_alert_banner(frame, msg, TOP_BAR_H + i * 64, color)

        cv2.imshow("AI Security System", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('r'):
            reset_score(suspicion_state)
            print("[SCORE] Suspicion score reset.")

cap.release()
cv2.destroyAllWindows()