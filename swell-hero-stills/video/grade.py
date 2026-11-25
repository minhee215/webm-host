"""Blue-hour grade: darker mids, cool deep blues, highlights (neon/lights) kept bright, soft vignette."""
import numpy as np
W, H = 1920, 1080
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.22 * np.clip(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H * 0.45) / (H * 0.75)) ** 2, 0, 1))[..., None].astype(np.float32)
TINT = np.array([0.84, 0.92, 1.06], np.float32)


def grade(rgb, k=1.0):
    """rgb uint8 HxWx3, k = strength 0..1"""
    x = rgb.astype(np.float32) / 255
    d = np.power(x, 1.9) * 0.95 * TINT * VIG                     # darker, cooler
    r, g, b = x[..., 0:1], x[..., 1:2], x[..., 2:3]
    neon = np.clip((b - r - 0.50) / 0.15, 0, 1) * np.clip((g - 0.66) / 0.15, 0, 1)   # saturated cyan light only
    lamp = np.clip((x.min(axis=2, keepdims=True) - 0.85) / 0.1, 0, 1)               # white light cores
    hi = np.clip(neon + lamp, 0, 1)
    d = d * (1 - hi * 0.85) + x * hi * 0.85
    out = x * (1 - k) + d * k
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
