import cv2
import mediapipe as mp
import urllib.request
import os

from config import (FRAME_W, FRAME_H, TOP_BAR_H,
                    RESTRICTED_ZONE, LOCK_ZONE, C_YELLOW, C_CYAN)
from detectors.trespassing import check_trespassing
from detectors.climbing    import check_climbing
from detectors.lockpicking import check_lockpicking, make_lock_state
from hud.drawing import (draw_corner_rect, draw_hud_text,
                         draw_alert_banner, draw_landmark_custom)
from hud.bars  import draw_top_bar, draw_bottom_bar
from hud.panel import draw_side_panel

MODEL_PATH = "pose_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading pose model...")
    urllib.request.urlretrieve(
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
        MODEL_PATH
    )
    print("Done!")

BaseOptions           = mp.tasks.BaseOptions
PoseLandmarker        = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
VisionRunningMode     = mp.tasks.vision.RunningMode

mp_options = PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE)

climb_history = []
lock_state    = make_lock_state()

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

with PoseLandmarker.create_from_options(mp_options) as landmarker:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img     = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        results = landmarker.detect(img)

        alerts          = {"intrusion": False, "climb": False, "lock": False}
        lock_info       = {"dwell_elapsed": 0.0, "alert_elapsed": 0.0}
        climb_subs      = {"arms_raised": False, "moving_up": False,
                           "leg_spread": False, "active": False}
        alert_banners   = []
        person_detected = bool(results.pose_landmarks)

        draw_corner_rect(frame, *RESTRICTED_ZONE, C_YELLOW, thickness=2, corner_len=28)
        draw_hud_text(frame, "RESTRICTED ZONE",
                      RESTRICTED_ZONE[0] + 8, RESTRICTED_ZONE[1] - 10,
                      C_YELLOW, scale=0.52)
        draw_corner_rect(frame, *LOCK_ZONE, C_CYAN, thickness=2, corner_len=28)
        draw_hud_text(frame, "LOCK ZONE",
                      LOCK_ZONE[0] + 8, LOCK_ZONE[1] - 10,
                      C_CYAN, scale=0.52)

        if results.pose_landmarks:
            lm = results.pose_landmarks[0]
            draw_landmark_custom(frame, lm)

            if check_trespassing(lm):
                alerts["intrusion"] = True
                alert_banners.append(
                    ("!! PERSON IN RESTRICTED ZONE !!", (0, 40, 180)))

            detected, arms_r, mov_up, leg_sp = check_climbing(lm, climb_history)
            climb_subs = {"arms_raised": arms_r, "moving_up": mov_up,
                          "leg_spread": leg_sp, "active": detected}
            if detected:
                alerts["climb"] = True
                alert_banners.append(("!! CLIMBING DETECTED !!", (0, 80, 160)))

            fired, dwell_e, alert_e = check_lockpicking(lm, lock_state)
            lock_info = {"dwell_elapsed": dwell_e, "alert_elapsed": alert_e}
            if fired:
                alerts["lock"] = True
                alert_banners.append(("!! LOCKPICKING ALERT !!", (0, 40, 140)))

        draw_top_bar(frame,    any(alerts.values()))
        draw_bottom_bar(frame, person_detected)
        draw_side_panel(frame, alerts, lock_info, climb_subs)

        for i, (msg, color) in enumerate(alert_banners):
            draw_alert_banner(frame, msg, TOP_BAR_H + i * 64, color)

        cv2.imshow("AI Security System", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()