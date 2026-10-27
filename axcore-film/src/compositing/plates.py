"""Live-action plates: decode → grade → cache (memmap) → sample per output frame.

Plates are generated at 24fps / 1280x716 by Kling 4.0 and stored here at
960x540 BGRA, graded with the shared pipeline in grade.py.
"""
import json
import subprocess

import cv2
import numpy as np
import skia

from ..utils.config import ASSETS, CACHE, PLATE_W, PLATE_H, DESIGN_W, DESIGN_H
from .grade import plate_stats, grade_frame
from . import gfx

PLATES = {
    "V1": "V1_office_engineer",
    "V2": "V2_factory_floor",
    "V3": "V3_documents_topdown",
    "V4": "V4_meeting_room",
    "V5": "V5_control_panel",
    "V6": "V6_conveyor",
    "V7": "V7_engineer_ots",
}
SRC_FPS = 24.0
PLATE_DIR = CACHE / "plates"

# plate pixel -> design pixel
SX, SY = DESIGN_W / PLATE_W, DESIGN_H / PLATE_H


def _decode(path):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf",
           f"scale={PLATE_W}:{PLATE_H}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, PLATE_H, PLATE_W, 3)


def prepare(key, force=False):
    """Decode + grade one plate into the cache. Returns cache path."""
    PLATE_DIR.mkdir(parents=True, exist_ok=True)
    out = PLATE_DIR / f"{key}.npy"
    if out.exists() and not force:
        return out
    frames = _decode(ASSETS / "generated-video" / f"{PLATES[key]}.mp4")
    mean, std = plate_stats(frames[:: max(1, len(frames) // 12)])
    arr = np.lib.format.open_memmap(out, mode="w+", dtype=np.uint8,
                                    shape=(len(frames), PLATE_H, PLATE_W, 4))
    for i, f in enumerate(frames):
        g = grade_frame(f, mean, std)
        arr[i, ..., :3] = g
        arr[i, ..., 3] = 255
    arr.flush()
    (PLATE_DIR / f"{key}.json").write_text(json.dumps(
        {"frames": len(frames), "mean": mean.tolist(), "std": std.tolist()}))
    return out


class Plate:
    _open = {}

    def __init__(self, key):
        self.key = key
        if key not in Plate._open:
            Plate._open[key] = np.load(prepare(key), mmap_mode="r")
        self.frames = Plate._open[key]
        self.n = len(self.frames)

    def index(self, t):
        """Fractional source-frame index for plate-local time t (seconds)."""
        return float(np.clip(t * SRC_FPS, 0, self.n - 1))

    def array(self, t):
        fi = self.index(t)
        i0 = int(fi)
        i1 = min(i0 + 1, self.n - 1)
        w = fi - i0
        if w < 0.02 or i0 == i1:
            return self.frames[i0]
        a = self.frames[i0].astype(np.float32)
        b = self.frames[i1].astype(np.float32)
        return (a * (1 - w) + b * w).astype(np.uint8)

    def image(self, t):
        return gfx.to_image(self.array(t))

    def draw(self, c, t, x=0, y=0, w=DESIGN_W, h=DESIGN_H, a=1.0):
        gfx.draw_image(c, self.image(t), x, y, w, h, a)

    _blur_cache = {}

    def blurred(self, t, sigma=14):
        """Defocused plate for use behind UI (computed at 1/4 res, cached)."""
        i = int(round(self.index(t)))
        key = (self.key, i, sigma)
        cache = Plate._blur_cache
        if key not in cache:
            if len(cache) > 64:
                cache.clear()
            small = cv2.resize(np.asarray(self.frames[i]), (PLATE_W // 4, PLATE_H // 4),
                               interpolation=cv2.INTER_AREA)
            small = cv2.GaussianBlur(small, (0, 0), sigma / 4)
            cache[key] = gfx.to_image(np.ascontiguousarray(small))
        return cache[key]

    def draw_blurred(self, c, t, sigma=14, a=1.0, veil=None, veil_a=0.0, scale=1.06):
        """Full-frame defocused plate (+ optional veil) as a UI background."""
        w, h = DESIGN_W * scale, DESIGN_H * scale
        gfx.draw_image(c, self.blurred(t, sigma), (DESIGN_W - w) / 2, (DESIGN_H - h) / 2, w, h, a)
        if veil and veil_a > 0:
            c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill(veil, veil_a * a))


def to_design(pt):
    return pt[0] * SX, pt[1] * SY


def quad_to_design(q):
    return [to_design(p) for p in q]
