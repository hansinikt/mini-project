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
LOCK_ZONE       = (620, TOP_BAR_H + 60, 820, FRAME_H - BOT_BAR_H - 60)

# ── Timing ───────────────────────────────────────────────────────
LOCK_DWELL_TIME  = 1.5   # seconds hand must be in zone before timer starts
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