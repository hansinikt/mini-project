# ─── config.py ───────────────────────────────────────────────────
# All shared constants live here.
# Every other file imports from this — change a value once, it
# updates everywhere.

# ── Frame / layout ───────────────────────────────────────────────
FRAME_W   = 1280
FRAME_H   = 720
TOP_BAR_H = 55
BOT_BAR_H = 50
PANEL_W   = 280

# ── Detection zones ──────────────────────────────────────────────
RESTRICTED_ZONE = (60, TOP_BAR_H + 20, 350, FRAME_H - BOT_BAR_H - 180)
LOCK_ZONE       = (550, TOP_BAR_H + 60, 900, FRAME_H - BOT_BAR_H - 60)

# ── Timing ───────────────────────────────────────────────────────
LOCK_DWELL_TIME  = 1.0   # seconds hand must be in zone before timer starts
LOCK_ALERT_TIME  = 5.0   # seconds of continuous presence to trigger alert

# ── Climbing ─────────────────────────────────────────────────────
CLIMB_HISTORY_LEN      = 15
CLIMB_MOTION_THRESHOLD = 3
CLIMB_MIN_VISIBILITY   = 0.5

# ── Colors (BGR) ─────────────────────────────────────────────────
C_GREEN  = (0, 255, 120)
C_RED    = (0, 60,  255)
C_YELLOW = (0, 220, 255)
C_CYAN   = (255, 220, 0)
C_WHITE  = (230, 230, 230)
C_GRAY   = (130, 130, 130)
C_DARK   = (15,  15,  15)
C_ORANGE = (0,   140, 255)

# ── Suspicion bar ─────────────────────────────────────────────────
# Bar goes from 0.0 to 1.0. Rates are per frame at ~30fps.
# 2+ detectors: 1/(3s × 30fps)  = 0.0111 per frame → full in 3 seconds
# 1 detector:   1/(30s × 30fps) = 0.0011 per frame → full in 30 seconds
# Decay:        1/(10s × 30fps) = 0.0033 per frame → empty in 10 seconds
SUSPICION_FAST_RATE  = 0.0111   # 2+ detectors active
SUSPICION_SLOW_RATE  = 0.0011   # 1 detector active
SUSPICION_DECAY_RATE = 0.0033   # no detectors active
EMAIL_COOLDOWN       = 300      # seconds between alert emails (5 minutes)