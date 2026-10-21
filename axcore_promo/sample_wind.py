"""Low-res sample of the wind-farm shot with one smooth light ribbon that sweeps in from the left and wraps
each turbine in a wide, flat perspective loop (reference: client still with looping lines).

The curve is analytic and densely sampled: a gentle baseline from lower left to upper right, plus loops whose
radius swells from zero and back around each turbine while the angle turns one full revolution - no kinks.
Far sides of the loops are dimmed (never cut). Lines follow the tracked footage.
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

BASE = [(-0.08, 0.80), (0.15, 0.72), (0.30, 0.65), (0.435, 0.60), (0.55, 0.555), (0.655, 0.51), (0.80, 0.45),
        (1.10, 0.36)]                                         # frame uv (Seedance framing), lower left -> upper right
LOOPS = [  # (turbine u, half-width rx as fraction of W, flatness ry/rx); the loop hangs on the baseline
    (0.435, 0.062, 0.26),
    (0.655, 0.088, 0.26),
]


def ribbon(n=700, m=320, rscale=1.0):
    """Baseline with one full perspective ellipse spliced in at each turbine. Each ellipse starts and ends at
    its lowest (front) point, where its tangent points right like the baseline's, so the splice is seamless:
    no corners anywhere. Far side of each loop flagged for dimming."""
    Q, _, _, _ = E.spline([(u * W, v * H) for (u, v) in BASE], n=1200)
    xs = np.linspace(-0.08, 1.10, n) * W
    ys = np.interp(xs, Q[:, 0], Q[:, 1])
    pts, back = [], []
    loops = sorted(LOOPS)
    k = 0
    for i in range(n):
        pts.append((xs[i] / W, ys[i] / H))
        back.append(False)
        while k < len(loops) and i + 1 < n and xs[i] <= loops[k][0] * W < xs[i + 1]:
            cu, rx, flat = loops[k]
            rx, ry = rx * W * rscale, rx * W * rscale * flat
            by = np.interp(cu * W, xs, ys)
            cx, cy = cu * W, by - ry                                  # lowest point sits on the baseline
            for j in range(1, m):
                th = math.pi / 2 - 2 * math.pi * j / m               # front (moving right) -> right -> back -> left
                pts.append(((cx + rx * math.cos(th)) / W, (cy + ry * math.sin(th)) / H))
                back.append(math.sin(th) < 0)
            k += 1
    return pts, back


STRANDS = [(dict(), 3.2, 1.0, 0.0), (dict(rscale=1.08), 1.6, 0.5, 0.035)]
TAIL, T0, TRAVEL = 0.75, -0.25, 2.3

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
