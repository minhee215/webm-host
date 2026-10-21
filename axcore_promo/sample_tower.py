"""Low-res sample of the tower shot (02_tower) with smooth light ribbons spiralling up around the tower.

The spiral is generated analytically (perspective ellipses around the tower axis, densely sampled), so the
curve never kinks; the far side of each loop passes behind the tower. Lines follow the tracked footage.
Usage: python3 sample_tower.py <out.mp4> [seconds=3.4] [height=480]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 3.4
height = int(sys.argv[3]) if len(sys.argv) > 3 else 480
width = int(round(height * 16 / 9 / 2)) * 2
W, H = E.W, E.H


def helix(n=420, turns=1.7, r0=0.56, r1=0.05, theta0=math.pi * 0.92, flat=0.20, lag=0.0, rscale=1.0):
    """Frame-0 uv points of a spiral climbing the tower, plus per-point 'behind' flags (far side)."""
    bx, by, tx, ty = 0.50 * W, 1.10 * H, 0.505 * W, 0.08 * H
    uv, back = [], []
    for i in range(n):
        s = i / (n - 1)
        k = s ** 0.85
        cx, cy = bx + (tx - bx) * k, by + (ty - by) * k
        r = (r0 + (r1 - r0) * s) * W * rscale
        th = theta0 + 2 * math.pi * turns * (s - lag)
        x, y = cx + r * math.cos(th), cy + r * flat * math.sin(th)
        uv.append((x / W, y / H))
        back.append(math.sin(th) < 0)            # upper half of the ellipse = far side of the tower
    return uv, back


STRANDS = [  # (helix kwargs, width, alpha, head delay)
    (dict(), 3.0, 1.0, 0.0),
    (dict(rscale=1.06, lag=0.025, theta0=math.pi * 0.95), 1.6, 0.55, 0.06),
]
TAIL, T0, TRAVEL = 0.55, 0.1, 3.1

E.configure(E.SEED, E.CHAOS)
surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.ColorType.kRGBA_8888_ColorType,
                                                   skia.AlphaType.kPremul_AlphaType))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", "%dx%d" % (W, H), "-r", str(E.FPS), "-i", "-",
                        "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", out], stdin=subprocess.PIPE)


def head_at(t, delay):
    return (1 + TAIL) * E.e_io_sine(E.prog(t, T0 + delay, TRAVEL)) - 0.02


paths = [helix(**kw) for kw, _, _, _ in STRANDS]
for f in range(int(round(dur * E.FPS))):
    t = f / E.FPS
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    cam = E.draw_plate(c, "02_tower", t, dur, s=(1.0, 1.0))
    occ = E.poly(E.flow_pts(cam, S.SC02_TOWER, "tower"), True)
    for (kw, wd, al, delay), (uv, back) in zip(STRANDS, paths):
        pts = E.flow_pts(cam, uv, "tower")
        hd = head_at(t, delay)
        mb = abs(head_at(t + 1 / 96, delay) - head_at(t - 1 / 96, delay)) * 2     # full-frame shutter
        E.light_ribbon(c, pts, hd, TAIL, behind=back, occluder=occ, width=wd, alpha=al, mb=mb)
    enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
enc.stdin.close()
enc.wait()
print(out)
