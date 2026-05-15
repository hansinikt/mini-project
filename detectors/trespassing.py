from config import RESTRICTED_ZONE, FRAME_W, FRAME_H

def check_trespassing(lm) -> bool:
    nx = int(lm[0].x * FRAME_W)
    ny = int(lm[0].y * FRAME_H)
    x1, y1, x2, y2 = RESTRICTED_ZONE
    return x1 < nx < x2 and y1 < ny < y2