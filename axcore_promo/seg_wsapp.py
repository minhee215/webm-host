"""Replacement for 00:00:47:09-00:00:57:23 (seg_wsfront), client re-edit: the workspace UI comes down off the ceiling
to face the lens as before, then the room (the man at his desk) fades out and the AXCORE app fades in round the UI,
which settles into the app's main page (주요 정보: briefing bar, then the AI workspace). The workspace's widgets run
slower. For the connect scene the app window draws back a little and goes very slightly soft, the AXCORE node pops
softly in the centre, and the company systems / external SaaS come in as before (their clock 3.1 s later, so the
segment is 58 frames longer: 313 frames, to 00:59:33 = 01:00:09).
  47.38  seg_axpoint's last frame (the ceiling cards turning into the workspace); the UI comes down (as before)
  48.10  no pause: as it lands the room fades out, the app fades in, the UI settles into its main page; the title
         moves from the lower left (white) to the lower right of the page (black)
  48.50  the workspace widgets run (2x slower than before)
  51.30  (client's reference) the app goes up and out of frame onto white with soft blue light; the workspace's
         diamond symbol stays, moves to the centre and grows, and hands over to the AXCORE node as its rings open
  52.50  사내 시스템 ... (seg_wsfront's connect graphics, clock - 2.4 s), each group spreading out of the node as it
         comes in; 외부 SaaS counts "5연결+"
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
SHIFT = 2.40                                   # the connect graphics' clock runs this much later
NF = WF.NF + int(round(SHIFT * 24))
APP0, APP_D = 48.10, 0.85                      # the room fades out, the app fades in, the UI settles into it
WIDG0, WIDG_K = 48.50, 2.0                     # the widgets' animation starts here, this much slower
EXIT0, EXIT_D = 51.30, 0.80                    # the app goes up and out of frame, leaving white
SYM0, SYM_D = 51.30, 0.85                      # its diamond symbol stays, moves to the centre and grows
HUBP = 51.95                                   # the node pops
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


# ---------------------------------------------------------------- the workspace's diamond symbol
_diamond = A.diamond
SYM = {"skip": False}


def diamond_hook(c, x, y, r, col, a, rot=0.0):
    """The workspace header's diamond: remember where it is on screen; leave it out when it is drawn on its own."""
    if r == 24 and col == BLUE:
        m = c.getTotalMatrix()
        p = m.mapXY(x, y)
        q = m.mapXY(x + r, y)
        sc = (SCV or 1.0)
        SYM["xy"] = (p.x() / sc, p.y() / sc)
        SYM["r"] = math.hypot(q.x() - p.x(), q.y() - p.y()) / sc
        if SYM["skip"]:
            return
    _diamond(c, x, y, r, col, a, rot)


A.diamond = diamond_hook


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
    k = 1 - x                                  # the lower-left (white) title gives way ...
    if k > 0:
        lp = skia.Paint()
        lp.setAlphaf(k)
        c.saveLayer(None, lp)
        A.caption(c, t)
        c.restore()
    kr = x   # ... to the same title, black, at the lower right of the page
    if kr > 0.003:
        dy = 10 * (1 - x)
        text(c, "우리 회사에 맞게 구성된", WS_RECT.right(), 828 + dy, 24, "SemiBold", "#1B2333", kr, "right")
        text(c, "AI 워크스페이스", WS_RECT.right(), 884 + dy, 46, "Bold", "#0B0F19", kr, "right")


def hub_light(c, tc, k=1.0):
    """seg_connect2.hub drawn for the white page: the same node (rings, turning arc, a ring per connection, the
    diamond) in deeper blues so it reads on white."""
    hx, hy = K.HUB
    E.radial(c, hx, hy, 210, "#7FB4FF", 0.30 * k, blend=skia.BlendMode.kSrcOver)
    for rr_, aa in ((90, 0.35), (62, 0.55), (36, 0.95)):
        c.drawCircle(hx, hy, rr_, paint_stroke("#2F6BFF", k * aa, 1.6))
    c.save()
    c.translate(hx, hy)
    c.rotate(tc * 40)
    c.drawArc(R(-90, -90, 180, 180), 0, 70, False, paint_stroke("#1E5BFF", k, 2.6))
    c.restore()
    for bt in K.BEATS:
        q_ = prog(tc, bt, 0.9)
        if 0 < q_ < 1:
            c.drawCircle(hx, hy, 40 + 160 * e_out_cubic(q_), paint_stroke("#3D7BFF", (1 - q_) * 0.6 * k, 1.6))
    E.radial(c, hx, hy, 60, "#2FC8FF", 0.55 * k)
    c.save()
    c.translate(hx, hy)
    c.rotate(45)
    c.drawRect(R(-11, -11, 22, 22), paint_fill("#18B4FF", k))
    c.restore()


def node(c, t, tc):
    """The AXCORE node popping softly in the centre (its rings open out of the symbol)."""
    q = prog(t, HUBP, 0.5)
    a = e_io_sine(prog(t, HUBP, 0.35))
    if a <= 0.003:
        return
    s = lerp(0.35, 1.0, e_out_back(q, 1.3))
    hx, hy = K.HUB
    lp = skia.Paint()
    lp.setAlphaf(a)
    c.save()
    c.translate(hx, hy)
    c.scale(s, s)
    c.translate(-hx, -hy)
    c.saveLayer(None, lp)
    hub_light(c, tc)
    c.restore()
    c.restore()


_glass = E.glass


def glass_navy(c, rect, radius=18, alpha=1.0, tint=WHITE, tint_a=0.14, **kw):
    """The panels' dark glass, denser on the white page so they come in navy rather than as grey boxes."""
    if tint == E.NAVY_950:
        tint_a = max(tint_a, 0.86)
    return _glass(c, rect, radius, alpha, tint=tint, tint_a=tint_a, **kw)


def page_bg(c, t):
    """White, with the soft blue light of the reference coming in at the sides."""
    c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF"))
    k = e_io_sine(prog(t, EXIT0 + 0.3, 1.2))
    if k > 0:
        E.radial(c, W + 60, H * 0.45, 900, "#9CC3FF", 0.55 * k, blend=skia.BlendMode.kSrcOver)
        E.radial(c, -120, H * 0.75, 760, "#C9DCFF", 0.45 * k, blend=skia.BlendMode.kSrcOver)


def symbol(c, t):
    """The diamond left behind: from its place in the workspace header to the centre, growing; it hands over to
    the node's own diamond as the rings open."""
    m = e_io_cubic(prog(t, SYM0, SYM_D))
    if t < SYM0 or "xy" not in SYM:
        return
    out = e_io_sine(prog(t, HUBP + 0.10, 0.35))
    if out >= 1:
        return
    (x0, y0), r0 = SYM["xy"], SYM["r"]
    x, y = lerp(x0, K.HUB[0], m), lerp(y0, K.HUB[1], m)
    r = lerp(r0, 34.0, e_io_sine(m)) * (1 + 0.15 * math.sin(math.pi * clamp(prog(t, SYM0 + 0.2, SYM_D))))
    rot = 90 * e_io_cubic(prog(t, SYM0 + 0.25, SYM_D))
    col = A.colint_mix(BLUE, "#2FC8FF", e_io_sine(prog(t, HUBP - 0.2, 0.4)))
    c.drawPath(E.poly([(x, y - r * 1.25), (x + r * 1.25, y), (x, y + r * 1.25), (x - r * 1.25, y)], True),
               paint_fill(col, 0.35 * (1 - out), blur=r * 0.6))
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.translate(-x, -y)
    _diamond(c, x, y, r, col, 1 - out)
    c.restore()


def render(c, t):
    e = e_io_cubic(prog(t, EXIT0, EXIT_D))
    if e <= 0:
        SYM["skip"] = False
        scene(c, t)
    else:                                      # the app goes up and out, its diamond stays behind
        SYM["skip"] = True
        img = A.snap(33, lambda cc: scene(cc, t))
        SYM["skip"] = False
        page_bg(c, t)
        if e < 1:
            A.draw_img(c, img, 1 - e_io_sine(prog(t, EXIT0 + 0.35, 0.45)), 6 * e, 1.0, dy=-1.05 * H * e)
        symbol(c, t)
    tc = t - SHIFT
    if t > HUBP - 0.1:
        c.save()
        zg = 1.0 + 0.03 * prog(tc, K.PAN0 - 0.5, K.T_END - K.PAN0 + 0.5)
        c.translate(*K.HUB)
        c.scale(zg, zg)
        c.translate(-K.HUB[0], -K.HUB[1])
        E.glass = glass_navy
        for t0, fn in ((K.PAN0, WF.systems_panel), (K.SAAS0, WF.right_cards)):
            if tc > t0 - 0.05:                 # each group spreads out of the node as it comes in
                k = e_out_cubic(prog(tc, t0, 1.0))
                s_ = lerp(0.45, 1.0, k)
                c.save()
                c.translate(*K.HUB)
                c.scale(s_, s_)
                c.translate(-K.HUB[0], -K.HUB[1])
                fn(c, tc)
                c.restore()
        E.glass = _glass
        node(c, t, tc)
        c.restore()


K.SAAS_COUNT_PLUS = True                       # 외부 SaaS: "5연결+"
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
