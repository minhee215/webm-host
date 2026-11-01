"""Replacement for 00:00:47:09-00:00:57:23 (seg_wsfront), client re-edit: the workspace UI comes down off the ceiling
to face the lens as before, then the room (the man at his desk) fades out and the AXCORE app fades in round the UI,
which settles into the app's main page (주요 정보: briefing bar, then the AI workspace). The workspace's widgets run
slower. For the connect scene the app window draws back a little and goes very slightly soft, the AXCORE node pops
softly in the centre, and the company systems / external SaaS come in as before (their clock 3.1 s later, so the
segment is 74 frames longer: 329 frames, to 01:00:21).
  47.38  seg_axpoint's last frame (the ceiling cards turning into the workspace); the UI comes down (as before)
  49.35  the room and the title fade out, the app fades in, the UI settles into its main page
  49.75  the workspace widgets run (2x slower than before)
  52.50  the app window draws back (0.92) and softens slightly; 52.80 the node pops
  53.20  사내 시스템 ... (seg_wsfront's connect graphics, clock - 3.1 s)
Film time = timeline frame / 24; grain = timeline frame. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_wsapp.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import cv2
import numpy as np
import skia

import engine as E
import seg_axpoint as A
import seg_wsfront as WF

_cands, _chrome = A.cands, A.chrome
import seg_maiworks as M                       # (its sidebar look) - it re-points seg_axpoint's page; undo that
A.cands, A.chrome = _cands, _chrome

from engine import (W, H, R, WHITE, INK, STEEL, STEEL_400, BLUE, lerp, prog, clamp, e_io_cubic, e_io_sine,
                    e_out_cubic, paint_fill, paint_stroke, rrect, rrect_stroke, text, icon)

K = WF.K
TL0 = WF.TL0
SHIFT = 3.1                                    # the connect graphics' clock runs this much later
NF = WF.NF + int(round(SHIFT * 24))
APP0, APP_D = 49.35, 0.85                      # the room fades out, the app fades in, the UI settles into it
WIDG0, WIDG_K = 49.75, 2.0                     # the widgets' animation starts here, this much slower
SHR0, SHR_D, SHR_K, SHR_BLUR = 52.50, 0.70, 0.92, 2.5
HUBP = 52.80                                   # the node pops
WS_RECT = R(330, 304, 1550, 1550 * A.UH / A.UW)   # the workspace inside the app's main page
SCV = 1.0


def e_out_back(x, k=1.70158):
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


# ---------------------------------------------------------------- the workspace widgets, slower
_widget = A.widget


def widget_slow(c, key, r, t, a):
    _widget(c, key, r, A.WS0 + 0.8 + (t - WIDG0) / WIDG_K, a)


A.widget = widget_slow


# ---------------------------------------------------------------- the AXCORE app (주요 정보)
NAV = [("주요 정보", "grid"), ("AI대화", "chat"), ("자료실", "folder"), ("알림", "bell")]


def sidebar(c):
    sw = M.SIDE_W
    c.drawRect(R(0, 0, sw, H), paint_fill("#F6F7FA"))
    c.drawLine(sw, 0, sw, H, paint_stroke("#E6E8EE", 1.0, 1.2))
    E.logo().draw(c, 104, 186, 128, 1.0, 1.0, (1.0, 1.0, 1.0), False, 1.0)
    text(c, "‹", sw - 34, 192, 22, "Medium", STEEL_400, 1.0, "center")
    y = 236
    for j, (lab, ic) in enumerate(NAV):
        on = j == 0
        if on:
            r = R(18, y - 21, sw - 36, 42)
            rrect(c, r.makeOffset(0, 2), 10, "#3A55B8", 0.06, blur=6)
            rrect(c, r, 10, WHITE, 1.0)
            rrect_stroke(c, r, 10, M.LINE, 1.0, 1.0)
        M.nav_icon(c, ic, 46, y, INK if on else STEEL, 1.0)
        text(c, lab, 70, y + 6, 16, "Bold" if on else "SemiBold", INK if on else "#2B3342", 1.0)
        y += 44
    text(c, "핵심 기능", 34, y + 22, 12, "SemiBold", STEEL_400, 1.0)
    y += 56
    for lab, _, ic in M.FEATS:
        icon(c, ic, 46, y, 16, STEEL, 1.0, 1.5)
        text(c, lab, 70, y + 5, 15, "Medium", "#2B3342", 1.0)
        y += 40
    c.drawLine(0, 852, sw, 852, paint_stroke("#E6E8EE", 1.0, 1.0))
    rrect(c, R(30, 870, 40, 40), 10, WHITE, 1.0)
    rrect_stroke(c, R(30, 870, 40, 40), 10, M.LINE, 1.0, 1.0)
    c.drawCircle(44, 904, 8, paint_fill("#1B2333", 1.0))
    text(c, A.COMPANY, 84, 886, 15, "Bold", INK, 1.0)
    text(c, "홍길동 · 소유자", 84, 906, 12, "Medium", STEEL, 1.0)
    text(c, "⌃", sw - 34, 896, 14, "Medium", STEEL_400, 1.0, "center")


def app(c):
    c.drawRect(R(0, 0, W, H), paint_fill("#F7F9FC"))
    sidebar(c)
    x0 = 340
    text(c, "주요 정보", x0, 214, 28, "Bold", INK, 1.0)
    text(c, "10월 29일 목요일", x0 + E.text_w("주요 정보", 28, "Bold") + 14, 213, 16, "Medium", STEEL_400, 1.0)
    br = R(330, 232, 1550, 54)
    rrect(c, br, 14, "#EAF0FD", 1.0)
    rrect_stroke(c, br, 14, "#DCE5FB", 1.0, 1.0)
    icon(c, "db", br.left() + 28, br.centerY(), 18, BLUE, 1.0, 1.6)
    t1 = "홍길동 님, 좋은 오후예요"
    text(c, t1, br.left() + 54, br.centerY() + 6, 17, "Bold", INK, 1.0)
    text(c, "10:29 브리핑 · 2가지", br.left() + 70 + E.text_w(t1, 17, "Bold"), br.centerY() + 6, 15, "Medium",
         STEEL, 1.0)
    text(c, "펼치기  ⌄", br.right() - 24, br.centerY() + 6, 15, "Medium", "#2B3342", 1.0, "right")
    icon(c, "gear", br.right() - 118, br.centerY(), 16, STEEL, 1.0, 1.5)


# ---------------------------------------------------------------- the scene
def rect_quad(r):
    return [(r.left(), r.top()), (r.right(), r.top()), (r.right(), r.bottom()), (r.left(), r.bottom())]


def workspace(c, t, q, alpha):
    Mx = cv2.getPerspectiveTransform(np.float32([[0, 0], [A.UW, 0], [A.UW, A.UH], [0, A.UH]]), np.float32(q))
    c.save()
    c.concat(skia.Matrix.MakeAll(*(Mx / Mx[2, 2]).flatten().tolist()))
    lp = skia.Paint()
    lp.setAlphaf(alpha)
    c.saveLayer(None, lp)
    A.ceiling_ui(c, t)
    c.restore()
    c.restore()


def scene(c, t):
    """The UI coming down over the room, then settling into the app."""
    u = e_io_cubic(prog(t, WF.DOWN0, WF.DOWN_D))
    x = e_io_sine(prog(t, APP0, APP_D))
    q0 = K.ui_quad_ceiling()
    qf = [(lerp(a[0], b[0], u), lerp(a[1], b[1], u)) for a, b in zip(q0, WF.front_quad())]
    q = [(lerp(a[0], b[0], x), lerp(a[1], b[1], x)) for a, b in zip(qf, rect_quad(WS_RECT))]
    if x < 1:                                  # the room, soft behind the UI, fading out
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
    if x > 0:                                  # the app fades in over it
        lp = skia.Paint()
        lp.setAlphaf(x)
        c.saveLayer(None, lp)
        app(c)
        c.restore()
    workspace(c, t, q, lerp(0.92, 1.0, x))
    k = 1 - x                                  # the lower-left title fades out with the room
    if k > 0:
        lp = skia.Paint()
        lp.setAlphaf(k)
        c.saveLayer(None, lp)
        A.caption(c, t)
        c.restore()


def node(c, t, tc):
    """The AXCORE node (seg_connect2.hub) popping softly in the centre."""
    q = prog(t, HUBP, 0.5)
    a = e_io_sine(prog(t, HUBP, 0.35))
    if a <= 0.003:
        return
    s = lerp(0.55, 1.0, e_out_back(q, 1.4))
    hx, hy = K.HUB
    lp = skia.Paint()
    lp.setAlphaf(a)
    c.save()
    c.translate(hx, hy)
    c.scale(s, s)
    c.translate(-hx, -hy)
    c.saveLayer(None, lp)
    E.radial(c, hx, hy, 230, "#0A1A3C", 0.42, blend=skia.BlendMode.kSrcOver)   # a little depth for it on the page
    K.hub(c, tc)
    c.restore()
    c.restore()


def render(c, t):
    k = e_io_cubic(prog(t, SHR0, SHR_D))
    if k <= 0:
        scene(c, t)
    else:                                      # the app window draws back and softens a touch
        img = A.snap(33, lambda cc: scene(cc, t))
        c.drawRect(R(0, 0, W, H), paint_fill("#E9EDF4"))
        A.draw_img(c, img, 1.0, SHR_BLUR * k, lerp(1.0, SHR_K, k))
    tc = t - SHIFT
    if tc > K.PAN0 - 0.2 or t > HUBP:
        c.save()
        zg = 1.0 + 0.03 * prog(tc, K.PAN0 - 0.5, K.T_END - K.PAN0 + 0.5)
        c.translate(*K.HUB)
        c.scale(zg, zg)
        c.translate(-K.HUB[0], -K.HUB[1])
        if tc > K.PAN0 - 0.2:
            WF.systems_panel(c, tc)
            WF.right_cards(c, tc)
        node(c, t, tc)
        c.restore()


K.GLOW_PEAK = -100.0                          # the node's own fade-in is replaced by its pop (node())


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = WF.setup(height)
    SCV = WF.SCV
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
        render(c, tl / 24.0)
        c.restore()
        fr = finish.apply(surf, tl)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
