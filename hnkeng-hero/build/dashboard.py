#!/usr/bin/env python3
"""Scene 4 — plant monitoring dashboard, rendered from the still.

Generative video garbles small digits, so this shot is built from the crisp
still (stills/04.jpg) instead:
  * the four KPI percentages are erased and re-typeset every frame in
    Inter SemiBold, sheared to the monitor's angle, with a soft glow, and
    tick naturally (one or two small changes each) — always legible;
  * the camera is a mathematically smooth push-in (no jitter possible).

render(n_frames, out_w, out_h) -> list of uint8 RGB frames (ungraded).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
STILL = ROOT / "stills" / "04.jpg"
FONT = "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf"
FPS = 24

# KPI numbers in still pixels: bounding box (x0, y0, x1, y1) of the original
# digits, baseline slope (screen perspective), and value changes over time.
KPIS = [
    dict(box=(1095, 308, 1218, 355), ticks=[(0, 98.7), (22, 98.8), (58, 98.7)]),
    dict(box=(1378, 280, 1510, 330), ticks=[(0, 92.4), (14, 92.6), (50, 92.7)]),
    dict(box=(1695, 250, 1833, 300), ticks=[(0, 99.1), (36, 99.2)]),
    dict(box=(2038, 215, 2200, 268), ticks=[(0, 76.3), (28, 76.5), (64, 76.8)]),
]
SLOPE = -0.055          # baseline rises to the right
PAD = 7


def _erase(img: np.ndarray, box):
    """Fill the digit box with the tile background, interpolated row by row
    between clean columns just left and right of the box."""
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD
    left = np.median(img[y0:y1, x0 - 6:x0 - 1].astype(np.float32), axis=1)
    right = np.median(img[y0:y1, x1 + 1:x1 + 6].astype(np.float32), axis=1)
    t = np.linspace(0, 1, x1 - x0)[None, :, None]
    fill = left[:, None, :] * (1 - t) + right[:, None, :] * t
    # soft edge so the patch never shows a seam
    m = np.ones((y1 - y0, x1 - x0), np.float32)
    m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1)),
                   np.float32)[..., None] / 255.0
    region = img[y0:y1, x0:x1].astype(np.float32)
    img[y0:y1, x0:x1] = np.clip(region * (1 - m) + fill * m, 0, 255).astype(np.uint8)


def _text_layer(text):
    """White text + soft glow on an RGBA canvas at a fixed render size.
    Returns layer, ink width, digit height, origin x, baseline y (layer px)."""
    size = 200
    font = ImageFont.truetype(FONT, size)
    l, t, r, b = font.getbbox(text)
    w, h = r - l + 40, b - t + 40
    canvas = Image.new("L", (w, h), 0)
    ImageDraw.Draw(canvas).text((20 - l, 20 - t), text, font=font, fill=255)
    digit_h = font.getbbox("8")[3] - font.getbbox("8")[1]
    glow = canvas.filter(ImageFilter.GaussianBlur(9))
    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_rgba = Image.new("RGBA", (w, h), (170, 225, 255, 0))
    glow_rgba.putalpha(glow.point(lambda v: int(v * 0.45)))
    txt_rgba = Image.new("RGBA", (w, h), (244, 250, 255, 0))
    txt_rgba.putalpha(canvas)
    rgba = Image.alpha_composite(Image.alpha_composite(rgba, glow_rgba), txt_rgba)
    return rgba, r - l, digit_h, 20, 20 + (b - t)


def _scales(kpi):
    """Per-KPI scale: height from the original digit height, width fitted so the
    original string spans the original box (matches the screen's condensed type)."""
    x0, y0, x1, y1 = kpi["box"]
    rise = abs(SLOPE) * (x1 - x0)
    _, ink_w, digit_h, _, _ = _text_layer(f"{kpi['ticks'][0][1]:.1f}%")
    return (x1 - x0) / ink_w, ((y1 - y0) - rise) / digit_h


def _paste_number(base: Image.Image, text, box, sx, sy):
    x0, y0, x1, y1 = box
    layer, _, _, ox, by = _text_layer(text)
    # still (X, Y) -> layer (u, v), baseline-left anchored at (x0, y1):
    # X = x0 + sx*(u-ox),  Y = y1 + sy*(v-by) + SLOPE*(X-x0)
    coeffs = (1 / sx, 0.0, ox - x0 / sx,
              -SLOPE / sy, 1 / sy, by - y1 / sy + SLOPE * x0 / sy)
    full = layer.transform(base.size, Image.Transform.AFFINE, coeffs,
                           resample=Image.Resampling.BICUBIC)
    base.alpha_composite(full)


def _value_at(ticks, i):
    v = ticks[0][1]
    for f, val in ticks:
        if i >= f:
            v = val
    return v


def render(n_frames, out_w=1280, out_h=720):
    src = np.asarray(Image.open(STILL).convert("RGB")).copy()
    for k in KPIS:
        _erase(src, k["box"])
    scales = [_scales(k) for k in KPIS]
    clean = Image.fromarray(src).convert("RGBA")
    H, W = src.shape[:2]
    frames, cache = [], {}
    for i in range(n_frames):
        key = tuple(_value_at(k["ticks"], i) for k in KPIS)
        if key not in cache:
            im = clean.copy()
            for k, v, (sx, sy) in zip(KPIS, key, scales):
                _paste_number(im, f"{v:.1f}%", k["box"], sx, sy)
            cache[key] = im.convert("RGB")
        im = cache[key]
        # smooth push-in toward the monitor (ease-in-out, sub-pixel)
        u = i / max(n_frames - 1, 1)
        u = u * u * (3 - 2 * u) * 0.5 + u * 0.5
        z = 1.0 + 0.08 * u
        cx = W * (0.50 + 0.06 * u)
        cy = H * 0.50
        cw, ch = W / z, H / z
        x0 = min(max(cx - cw / 2, 0), W - cw)
        y0 = min(max(cy - ch / 2, 0), H - ch)
        big = im.transform((out_w * 2, out_h * 2), Image.Transform.AFFINE,
                           (cw / (out_w * 2), 0, x0, 0, ch / (out_h * 2), y0),
                           resample=Image.Resampling.BICUBIC)
        frames.append(np.asarray(big.resize((out_w, out_h), Image.Resampling.LANCZOS)))
    return frames


if __name__ == "__main__":
    import sys
    fr = render(79)
    Image.fromarray(fr[0]).save(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dash0.png")
    Image.fromarray(fr[-1]).save(sys.argv[2] if len(sys.argv) > 2 else "/tmp/dash1.png")
