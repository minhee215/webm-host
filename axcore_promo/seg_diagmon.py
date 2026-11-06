"""Replacement for 00:00:39:12-00:00:44:03 of seg_axpoint (client re-edit): the M-AI Works page is left out. The AX
diagnosis (the pentagon) holds a moment, then it is the page that becomes the browser window and turns transparent
over the man looking at it, into the ceiling shot - the old monitor passage, unchanged otherwise. 41 frames instead
of 112 (the client wants it short: the diagnosis holds a quarter second, the monitor passage runs ~1.8x): the first frame continues 39:11, the last is the old 44:03 state.
  f  0-5   the diagnosis (film 39.500-39.708)
  f  6-27  the monitor passage, film 41.875-43.60 sped up, the diagnosis on the screen
  f 28-40  the cross-fade into the ceiling at its own pace, film 43.625-44.125 (= the old 44:03)
Usage: python3 seg_diagmon.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import seg_axpoint as A
from engine import R, BLUE, INK, STEEL, STEEL_400, WHITE, paint_fill, paint_stroke, rrect, text

F_TL = 948                       # 00:00:39:12 (the old 39:12-39:13 already blur toward M-AI Works)
HOLD = 6                         # frames of the diagnosis before the monitor passage
MON = 22                         # frames for the monitor passage up to the ceiling (film 41.875-43.60, ~1.8x)
NF = 41
T_END = 44.125                   # the old 44:03 (film time) - the last frame
D0 = F_TL / 24.0                 # diagnosis clock at the first frame


def film(f):
    if f < HOLD:
        return D0 + f / 24.0
    if f < HOLD + MON:
        return 41.875 + (f - HOLD) * (A.T_CEIL - 41.875) / MON
    return T_END - (NF - 1 - f) / 24.0          # the cross-fade into the ceiling at its own pace


def diag_page(c, t):
    """The diagnosis as it stands when the monitor passage begins (its clock runs on from the hold)."""
    A.diag(c, D0 + HOLD / 24.0 + (t - film(HOLD)))


def chrome(c, a, y0):
    """Browser chrome (as seg_axpoint's), for the diagnosis page."""
    if a <= 0.003:
        return
    c.drawRect(R(0, y0, A.W, 80), paint_fill("#F3F4F8", a))
    tab = R(18, y0 + 8, 330, 34)
    rrect(c, tab, 10, WHITE, a)
    A.diamond(c, tab.left() + 22, tab.centerY(), 7, BLUE, a)
    text(c, "AXpoint · AI 컨설턴트", tab.left() + 40, tab.centerY() + 5, 13, "SemiBold", INK, a)
    text(c, "×", tab.right() - 18, tab.centerY() + 5, 15, "Medium", STEEL, a, "center")
    text(c, "+", tab.right() + 22, tab.centerY() + 6, 18, "Medium", STEEL, a, "center")
    for j, s in enumerate(("←", "→", "↻")):
        text(c, s, 36 + j * 34, y0 + 67, 16, "Medium", STEEL, a, "center")
    url = R(150, y0 + 48, 1620, 26)
    rrect(c, url, 13, "#E6E8EF", a)
    c.drawCircle(url.left() + 16, url.centerY(), 5, paint_stroke(STEEL_400, a, 1.4))
    text(c, "axpoint  /  AX 진단 결과", url.left() + 34, url.centerY() + 5, 13, "Medium", STEEL, a)
    c.drawLine(0, y0 + 80, A.W, y0 + 80, paint_stroke("#DADDE6", a, 1.0))


def monitor(c, t):
    """seg_axpoint.monitor with the man fading in (not popping on) behind the page as it turns transparent: the
    diagnosis' own blue is behind him until then."""
    from engine import W, H, lerp, prog, e_io_cubic, e_io_sine, BLUE as _B
    k1 = e_io_cubic(prog(t, A.T_MON, 0.6))
    k2 = e_io_cubic(prog(t, A.T_MON + 0.3, 1.1))
    fi = e_io_sine(prog(t, A.T_MON + 0.25, 1.05))     # the man fades in
    c.drawRect(R(0, 0, W, H), paint_fill(_B))
    img = A.plate("monitor", t)
    if fi > 0 and img is not None:
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(fi)
        sg = lerp(10, 3.0, k2) * A.SCV
        p.setImageFilter(skia.ImageFilters.Blur(sg, sg, skia.TileMode.kClamp))
        c.save()
        c.translate(W / 2, A.BAR)
        c.scale(1.1, 1.1)
        c.translate(-W / 2, -A.BAR)
        c.drawImageRect(img, R(0, 0, W, H), A.E.SAMP, p)
        c.restore()
    ui = A.snap(1, lambda cc: A.cands(cc, t))
    c.save()
    c.translate(W / 2, A.BAR + 80 * k1)
    c.scale(lerp(1.0, 0.93, k1), lerp(1.0, 0.93, k1))
    c.translate(-W / 2, -A.BAR)
    A.draw_img(c, ui, lerp(1.0, 0.45, k2))
    c.restore()
    c.drawRect(R(0, 0, W, H), paint_fill(WHITE, 0.22 * k2 * fi))
    c.save()
    c.translate(0, -80 * (1 - k1))
    A.chrome(c, lerp(1.0, 0.55, k2) * k1, A.BAR)
    c.restore()


A.monitor = monitor
A.cands = diag_page              # the monitor passage (and its cross-fade into the ceiling) shows the diagnosis
A.chrome = chrome


def render(c, f):
    t = film(f)
    if f < HOLD:
        A.diag(c, t)
    else:
        A.part_b(c, t)


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = A.setup(height)
    bar = int(round(A.BAR * A.SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(A.SCV, A.SCV)
        render(c, f)
        c.restore()
        fr = finish.apply(surf, F_TL + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
