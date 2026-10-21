"""Low-res sample of the wind-farm shot with the same light ribbon as the tower sample: one long, smooth
sweep from lower left to upper right between the turbines (no loops around them).

The curve is a cubic B-spline of a control polygon, so it is C2-smooth - it cannot kink. Far sides of the
loops are dimmed (never cut). Lines follow the tracked footage.
Usage: python3 sample_wind.py <clip> <out.mp4> [seconds=2.0] [height=480]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E

clip, out = sys.argv[1], sys.argv[2]
dur = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
height = int(sys.argv[4]) if len(sys.argv) > 4 else 480
width = int(round(height * 16 / 9 / 2)) * 2
W, H = E.W, E.H

# One long, smooth sweep (control polygon, frame uv, Seedance framing): in low from the left past the engineer,
# a gentle dip between the turbines, then rising away to the upper right. No loops around anything.
CTRL = [
    (-0.12, 0.85, 0), (0.06, 0.78, 0), (0.22, 0.69, 0), (0.36, 0.62, 0), (0.50, 0.60, 0), (0.62, 0.57, 0),
    (0.73, 0.50, 0), (0.83, 0.40, 0), (0.93, 0.31, 0), (1.14, 0.22, 0),
]


def ribbon(rscale=1.0, n=900):
    """Smooth B-spline of the control polygon; rscale widens the loops slightly for the companion strand."""
    C = np.asarray(CTRL, float)
    if rscale != 1.0:
        c = C[:, :2].mean(0)
        C[:, :2] = c + (C[:, :2] - c) * [1.0, rscale]
    B = E.bspline(C, n)
    return [(x, y) for x, y in B[:, :2]], list(B[:, 2])


STRANDS = [(dict(), 3.0, 1.0, 0.0), (dict(rscale=1.06), 1.5, 0.5, 0.035)]
TAIL, T0, TRAVEL = 0.9, -0.15, 2.15

E.configure(E.SEED, E.CHAOS)
surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.ColorType.kRGBA_8888_ColorType,
                                                   skia.AlphaType.kPremul_AlphaType))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", "%dx%d" % (W, H), "-r", str(E.FPS), "-i", "-",
                        "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", out], stdin=subprocess.PIPE)


def head_at(t, delay):
    return 1.35 * E.e_out_cubic(E.prog(t, T0 + delay, TRAVEL)) - 0.02      # fast in, glides out; still on at the end


paths = [ribbon(**kw) for kw, _, _, _ in STRANDS]
for f in range(int(round(dur * E.FPS))):
    t = f / E.FPS
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    cam = E.draw_plate(c, clip, t, dur, s=(1.0, 1.0))
    for (kw, wd, al, delay), (uv, back) in zip(STRANDS, paths):
        pts = E.flow_pts(cam, uv)
        hd = head_at(t, delay)
        mb = abs(head_at(t + 1 / 96, delay) - head_at(t - 1 / 96, delay)) * 2
        E.light_ribbon(c, pts, hd, TAIL, behind=back, width=wd, alpha=al, mb=mb, back_dim=0.4)
    enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
enc.stdin.close()
enc.wait()
print(out)
