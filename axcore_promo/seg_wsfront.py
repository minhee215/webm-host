"""Patch 00:00:47:09-00:00:57:23 (255 frames) over the seg_axpoint -> seg_connect2 join and the connect scene: as the
ceiling cards shuffle into the AI workspace, the UI comes down off the ceiling to face the lens (the move of the old
49:06-49:18 turn) and settles above the lower-left title with a margin; the room behind it goes soft. No light
transition: the soft room and the title fade out while the workspace UI blurs and fades back to become the
background of the connect scene, whose graphics (company systems on the left, the AXCORE node, the external SaaS
on the right) are seg_connect2's own, at their own times.
Film time = timeline frame / 24 (seg_connect2's one-frame late placement in the client's edit is not kept: the
patch runs on one clock). 23.976 fps, 21:9 letterbox.
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

TL0, TL1 = 47 * 24 + 9, 57 * 24 + 23         # timeline 00:00:47:09 .. 00:00:57:23
NF = TL1 - TL0 + 1
DOWN0, DOWN_D = TL0 / 24.0 + 0.02, 1.10      # the UI comes down to face the lens (from the first frame on)
UI_L, UI_B, UI_W = 96.0, 728.0, 1728.0       # where it settles: aligned with the title, a margin above it
UI_H = UI_W * A.UH / A.UW
X0, X_D = 49.35, 0.85                        # the room and the title fade out, the UI goes soft: the background
BG_BLUR, BG_ALPHA = 14.0, 0.55
SCV = 1.0


def clock(tl):
    return tl / 24.0


def grain(tl):
    return tl


def front_quad():
    return [(UI_L, UI_B - UI_H), (UI_L + UI_W, UI_B - UI_H), (UI_L + UI_W, UI_B), (UI_L, UI_B)]


def base(c):
    """What is left under the soft UI once the room has gone: a light, cool field."""
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 138), skia.Point(0, 942)],
                                        [E.colint("#EEF2FA", 1.0), E.colint("#DCE4F3", 1.0)])
    c.drawRect(R(-W, -H, 3 * W, 3 * H), skia.Paint(Shader=sh))


def grade(c, k):
    """The connect scene's look over its background (as seg_connect2.background), faded in with k."""
    if k <= 0.003:
        return
    c.drawRect(R(0, 0, W, H), paint_fill(E.NAVY_950, 0.06 * k))
    E.radial(c, K.HUB[0], K.HUB[1], 1200, "#CFE2FF", 0.26 * k, blend=skia.BlendMode.kScreen)
    sh = skia.GradientShader.MakeRadial(skia.Point(*K.HUB), 1300,
                                        [E.colint(E.NAVY_950, 0.0), E.colint(E.NAVY_950, 0.24 * k)], [0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


def render(c, t):
    u = e_io_cubic(prog(t, DOWN0, DOWN_D))
    x = e_io_sine(prog(t, X0, X_D))
    q0 = K.ui_quad_ceiling()
    q = [(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(q0, front_quad())]
    if x > 0:
        base(c)
    # the room: a touch closer, out of focus behind the UI, then gone
    if x < 1:
        img = A.plate("ceiling", t)
        if img is not None:
            fx, fy = sum(p[0] for p in q0) / 4, sum(p[1] for p in q0) / 4
            z = 1.0 + 0.10 * u
            p = skia.Paint(AntiAlias=True)
            p.setAlphaf(1 - x)
            bl = 14 * u
            if bl > 0.05:
                p.setImageFilter(skia.ImageFilters.Blur(bl, bl, skia.TileMode.kClamp))
            c.save()
            c.translate(fx, fy)
            c.scale(z, z)
            c.translate(-fx, -fy)
            c.drawImageRect(img, R(0, 0, W, H), E.SAMP, p)
            c.restore()
            c.drawRect(R(0, 0, W, H), paint_fill("#EAF2FF", 0.22 * u * (1 - x)))
    # the workspace UI: facing the lens, then soft and faded back as the background (slow push from there on)
    zb = 1.0 + 0.05 * x + 0.05 * prog(t, X0 + X_D, K.T_END - X0 - X_D)
    M = cv2.getPerspectiveTransform(np.float32([[0, 0], [A.UW, 0], [A.UW, A.UH], [0, A.UH]]), np.float32(q))
    c.save()
    c.translate(*K.HUB)
    c.scale(zb, zb)
    c.translate(-K.HUB[0], -K.HUB[1])
    c.concat(skia.Matrix.MakeAll(*(M / M[2, 2]).flatten().tolist()))
    lp = skia.Paint()
    lp.setAlphaf(0.92 * lerp(1.0, BG_ALPHA, x))
    if x > 0.002:
        sg = BG_BLUR * x / (UI_W / A.UW)          # in plane units (the plane is scaled down onto the screen)
        lp.setImageFilter(skia.ImageFilters.Blur(sg, sg, skia.TileMode.kDecal))
    c.saveLayer(None, lp)
    A.ceiling_ui(c, t)
    c.restore()
    c.restore()
    k = 1 - x                                    # the lower-left title fades out with the room
    if k > 0:
        lp = skia.Paint()
        lp.setAlphaf(k)
        c.saveLayer(None, lp)
        A.caption(c, t)
        c.restore()
    grade(c, x)
    # the connect scene's graphics (seg_connect2.datacenter without its corridor)
    if t > K.PAN0 - 0.2:
        c.save()
        zg = 1.0 + 0.03 * prog(t, K.PAN0 - 0.5, K.T_END - K.PAN0 + 0.5)
        c.translate(*K.HUB)
        c.scale(zg, zg)
        c.translate(-K.HUB[0], -K.HUB[1])
        K.left_panels(c, t)
        K.right_cards(c, t)
        K.hub(c, t)
        c.restore()


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
