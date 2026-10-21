"""Low-res sample of the wind-farm shot with the same light ribbon as the tower sample: one flowing curve
that sweeps in from the left and wraps the turbines in wide tilted loops (reference: client still).

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

# One flowing curve (control polygon, frame uv, Seedance framing) that sweeps in low from the left, wraps the
# middle turbine in a wide tilted loop, flows on and wraps the big turbine, then leaves upper right.
# Third value: 1 on the far side of a loop (dimmed there, never cut).
CTRL = [
    (-0.12, 0.80, 0), (0.05, 0.75, 0), (0.18, 0.70, 0), (0.30, 0.65, 0),
    # middle turbine: tilted loop - in front low-left to right, behind across the top, back down in front
    (0.40, 0.615, 0), (0.50, 0.575, 0), (0.545, 0.505, 1), (0.47, 0.455, 1), (0.385, 0.48, 1), (0.40, 0.545, 0),
    (0.50, 0.535, 0), (0.58, 0.50, 0),
    # big turbine: larger tilted loop, then off to the upper right
    (0.66, 0.465, 0), (0.755, 0.42, 0), (0.78, 0.345, 1), (0.69, 0.295, 1), (0.60, 0.32, 1), (0.61, 0.39, 0),
    (0.72, 0.385, 0), (0.85, 0.33, 0), (0.98, 0.275, 0), (1.14, 0.22, 0),
]


def ribbon(rscale=1.0, n=900):
    """Smooth B-spline of the control polygon; rscale widens the loops slightly for the companion strand."""
    C = np.asarray(CTRL, float)
    if rscale != 1.0:
        c = C[:, :2].mean(0)
        C[:, :2] = c + (C[:, :2] - c) * [1.0, rscale]
    B = E.bspline(C, n)
    return [(x, y) for x, y in B[:, :2]], list(B[:, 2])


STRANDS = [(dict(), 3.0, 1.0, 0.0), (dict(rscale=1.04), 1.5, 0.5, 0.035)]
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
