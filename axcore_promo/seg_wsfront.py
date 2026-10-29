"""Patch 00:00:47:09-00:00:50:04 (68 frames) across the seg_axpoint -> seg_connect2 join: as the ceiling cards
shuffle into the AI workspace, the UI comes down off the ceiling to face the lens (the move of the old 49:06-49:18
turn) and settles above the lower-left title with a margin; the room behind it goes soft. The later turn is
dropped - the UI already faces the lens - and only the light swells out of it, fills the frame and draws back into
the datacenter node (seg_connect2's own light, so from the peak on the frames are seg_connect2's).
In the client's edit seg_connect2 starts one frame late (its 48:23 frame, the same picture as seg_axpoint's last one,
sits at 48:24), so at 50:04 the picture is seg_connect2's frame for 50:03: the clock here runs from 47:09 to that
50:03 evenly (one frame of slack spread over the patch), the grain follows each file's own numbering.
23.976 fps, 21:9 letterbox.
Usage: python3 seg_wsfront.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import cv2
import numpy as np
import skia

import engine as E
import media
import seg_axpoint as A
import seg_connect as C
import seg_connect2 as K
from engine import W, H, R, lerp, prog, e_io_cubic, e_io_sine, paint_fill

TL0, TL1 = 47 * 24 + 9, 50 * 24 + 4          # timeline 00:00:47:09 .. 00:00:50:04
NF = TL1 - TL0 + 1
DOWN0, DOWN_D = TL0 / 24.0 + 0.02, 1.10      # the UI comes down to face the lens (from the first frame on)
UI_L, UI_B, UI_W = 96.0, 728.0, 1728.0       # where it settles: aligned with the title, a margin above it
UI_H = UI_W * A.UH / A.UW
SCV = 1.0
JOIN = 48 * 24 + 23                          # seg_axpoint's last frame; seg_connect2 follows from the next one


def clock(tl):
    """Film time shown at timeline frame tl (47:09 -> 47:09, 50:04 -> 50:03)."""
    return (TL0 + (tl - TL0) * (TL1 - 1 - TL0) / (TL1 - TL0)) / 24.0


def grain(tl):
    return tl if tl <= JOIN else tl - 1


def front_quad():
    return [(UI_L, UI_B - UI_H), (UI_L + UI_W, UI_B - UI_H), (UI_L + UI_W, UI_B), (UI_L, UI_B)]


def ui_down(c, t):
    u = e_io_cubic(prog(t, DOWN0, DOWN_D))
    q0 = K.ui_quad_ceiling()
    q = [(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(q0, front_quad())]
    # the room: a touch closer, out of focus behind the UI
    img = A.plate("ceiling", t)
    if img is not None:
        fx, fy = sum(p[0] for p in q0) / 4, sum(p[1] for p in q0) / 4
        z = 1.0 + 0.10 * u
        p = skia.Paint(AntiAlias=True)
        bl = 14 * u
        if bl > 0.05:
            p.setImageFilter(skia.ImageFilters.Blur(bl, bl, skia.TileMode.kClamp))
        c.save()
        c.translate(fx, fy)
        c.scale(z, z)
        c.translate(-fx, -fy)
        c.drawImageRect(img, R(0, 0, W, H), E.SAMP, p)
        c.restore()
        c.drawRect(R(0, 0, W, H), paint_fill("#EAF2FF", 0.22 * u))
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [A.UW, 0], [A.UW, A.UH], [0, A.UH]]), np.float32(q))
    c.save()
    c.concat(skia.Matrix.MakeAll(*(M / M[2, 2]).flatten().tolist()))
    lp = skia.Paint()
    lp.setAlphaf(0.92)
    c.saveLayer(None, lp)
    A.ceiling_ui(c, t)
    c.restore()
    c.restore()
    k = 1 - e_io_sine(prog(t, K.GLOW0, K.GLOW_PEAK - K.GLOW0))    # the title stays until the light takes over
    if k > 0:
        lp = skia.Paint()
        lp.setAlphaf(k)
        c.saveLayer(None, lp)
        A.caption(c, t)
        c.restore()


def render(c, t):
    if t < K.GLOW_PEAK:
        ui_down(c, t)
    else:
        K.datacenter(c, t)
    K.light(c, t)


def setup(height):
    global SCV
    surf, finish, SWD, SHD = A.setup(height)
    SCV = A.SCV
    C.HD = height > 1080
    media.MAX_READERS = 14 if C.HD else 4
    return surf, finish, SWD, SHD


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    bar = int(round(A.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        tl = TL0 + f
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        render(c, clock(tl))
        c.restore()
        fr = finish.apply(surf, grain(tl))
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
