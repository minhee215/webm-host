"""Unified color pipeline for every live-action plate.

1. Partial statistical match (Lab) toward a shared reference so shots from
   different generations stop drifting in white balance / contrast.
2. One house look on top: cool-neutral WB, gentle S-curve, reduced chroma,
   navy-tinted shadows, lifted black level, soft highlight roll-off.
The same function runs on every plate, so the look cannot diverge per scene.
"""
import cv2
import numpy as np

# Reference statistics (Lab, OpenCV 8-bit scale) — chosen as the average of the
# seven V-plates and then nudged cooler. Means: L, a, b. Std: L, a, b.
REF_MEAN = np.array([128.0, 127.0, 123.0])
REF_STD = np.array([52.0, 4.0, 7.0])
MATCH_STRENGTH = np.array([0.35, 0.8, 0.8])   # keep each shot's own exposure intent

NAVY = np.array([48.0, 20.0, 10.0])          # BGR shadow tint (#0A1430)
BLACK_LIFT = 7.0


def plate_stats(frames_bgr):
    tiled = np.ascontiguousarray(frames_bgr).reshape(-1, frames_bgr.shape[-2], 3)
    lab = cv2.cvtColor(tiled, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    return lab.mean(0), lab.std(0) + 1e-3


def grade_frame(bgr, mean, std):
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_mean = mean + (REF_MEAN - mean) * MATCH_STRENGTH
    tgt_std = std + (REF_STD - std) * MATCH_STRENGTH
    lab = (lab - mean) / std * tgt_std + tgt_mean

    # chroma reduction around neutral (128)
    lab[..., 1:] = 128 + (lab[..., 1:] - 128) * 0.82
    # gentle S-curve on L (contrast 1.06 around mid, soft shoulder)
    L = lab[..., 0] / 255.0
    L = 0.5 + (L - 0.5) * 1.06
    L = np.where(L > 0.86, 0.86 + (L - 0.86) * 0.55, L)
    lab[..., 0] = np.clip(L, 0, 1) * 255
    out = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)

    # navy shadow tint + black level lift
    lum = out.mean(axis=2, keepdims=True) / 255.0
    w = np.clip(1 - lum / 0.45, 0, 1) ** 2 * 0.28
    out = out * (1 - w) + NAVY * w
    out = BLACK_LIFT + out * (1 - BLACK_LIFT / 255.0)
    return np.clip(out, 0, 255).astype(np.uint8)
