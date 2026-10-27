"""Frame renderer: scene dispatch, sub-frame motion blur, downsample, grain."""
import importlib

import cv2
import numpy as np
import skia

from .utils.config import (FPS, OUT_W, OUT_H, RENDER_W, RENDER_H, DESIGN_W, SCENES)

_modules = {}


def scene_module(name):
    if name not in _modules:
        _modules[name] = importlib.import_module(f"src.scenes.{name}")
    return _modules[name]


def scene_at(t):
    for name, a, b in SCENES:
        if a <= t < b:
            return name, a
    name, a, _ = SCENES[-1]
    return name, a


def _raster(mod, t_local):
    surf = skia.Surface(RENDER_W, RENDER_H)
    c = surf.getCanvas()
    s = RENDER_W / DESIGN_W
    c.scale(s, s)
    mod.render(c, t_local)
    return surf.makeImageSnapshot().toarray()  # BGRA


def render_frame(frame_idx, grain=True):
    t = frame_idx / FPS
    name, start = scene_at(t)
    mod = scene_module(name)
    tl = t - start
    samples = int(getattr(mod, "motion_blur", lambda _t: 1)(tl))
    if samples <= 1:
        img = _raster(mod, tl)[..., :3]
    else:
        shutter = 0.5 / FPS  # 180-degree shutter
        acc = np.zeros((RENDER_H, RENDER_W, 3), np.float32)
        for k in range(samples):
            acc += _raster(mod, tl + (k / (samples - 1) - 0.5) * shutter)[..., :3]
        img = (acc / samples).astype(np.uint8)
    out = cv2.resize(img, (OUT_W, OUT_H), interpolation=cv2.INTER_AREA)
    if grain:
        rng = np.random.default_rng(frame_idx)
        n = rng.normal(0, 1.6, (OUT_H, OUT_W, 1)).astype(np.float32)
        out = np.clip(out.astype(np.float32) + n, 0, 255).astype(np.uint8)
    return out  # BGR uint8
