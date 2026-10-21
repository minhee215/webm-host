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

out = sys.argv[1]
dur = float(sys.argv[2]) if len(sys.argv) > 2 else 3.4
height = int(sys.argv[3]) if len(sys.argv) > 3 else 480
width = int(round(height * 16 / 9 / 2)) * 2
W, H = E.W, E.H


def helix(n=480, turns=1.5, lag=0.0, rscale=1.0):
    """Frame-0 uv points of a smooth vortex around the tower: enters wide from off-screen left, tightens into
    wide flat perspective loops around the tower (front = lower half of each ellipse, far side passes behind
    the tower) and opens out again to leave the frame upper right. Radius and centre are smooth functions of
    the angle, so the curve has no corners. The far side is dimmed rather than cut, so the line never breaks."""
    uv, back = [], []
    for i in range(n):
        s = i / (n - 1)
        th = math.pi - 2 * math.pi * turns * (s - lag)
        k = s * s * (3 - 2 * s)
        cx = (0.47 + 0.03 * k) * W
        cy = (0.88 - 0.66 * k) * H
        rx = (0.26 + 0.62 * (2 * s - 1) ** 2) * W * rscale          # wide -> tight -> wide
        ry = rx * (0.24 - 0.06 * k)
        x, y = cx + rx * math.cos(th), cy + ry * math.sin(th)
        uv.append((x / W, y / H))
        back.append(math.sin(th) < 0)
    return uv, back


TOWER = [(0.085, 1.03), (0.43, 0.12), (0.465, 0.12), (1.03, 0.62), (1.03, 1.03)]   # frame-0 silhouette


STRANDS = [  # (helix kwargs, width, alpha, head delay)
    (dict(), 3.0, 1.0, 0.0),
    (dict(rscale=1.05, lag=0.02), 1.5, 0.5, 0.05),
]
TAIL, T0, TRAVEL = 0.5, -0.3, 3.4

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
    for (kw, wd, al, delay), (uv, back) in zip(STRANDS, paths):
        pts = E.flow_pts(cam, uv, "tower")
        hd = head_at(t, delay)
        mb = abs(head_at(t + 1 / 96, delay) - head_at(t - 1 / 96, delay)) * 2     # full-frame shutter
        E.light_ribbon(c, pts, hd, TAIL, behind=back, width=wd, alpha=al, mb=mb, back_dim=0.35)
    enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
enc.stdin.close()
enc.wait()
print(out)
