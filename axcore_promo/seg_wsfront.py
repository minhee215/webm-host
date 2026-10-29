"""Patch 00:00:47:09-00:00:57:23 (255 frames) over the seg_axpoint -> seg_connect2 join and the connect scene: as the
ceiling cards shuffle into the AI workspace, the UI comes down off the ceiling to face the lens (the move of the old
49:06-49:18 turn) and settles above the lower-left title with a margin; the room behind it goes soft. No light
transition: the soft room and the title fade out while the workspace UI blurs and fades back to become the
background of the connect scene, whose graphics (company systems on the left, the AXCORE node, the external SaaS
on the right) are seg_connect2's, at their own times - except the company systems, now one '사내 시스템' panel
after the client's card design (a row per system kind, each joined to the node). The background is a deep navy
field with the soft UI slowly drawing back (shrinking) on it.
Film time = timeline frame / 24 (seg_connect2's one-frame late placement in the client's edit is not kept: the
patch runs on one clock). 23.976 fps, 21:9 letterbox.
Usage: python3 seg_wsfront.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import math

import cv2
import numpy as np
import skia

import engine as E
import media
import seg_axpoint as A
import seg_connect as C
import seg_connect2 as K
from engine import W, H, R, CYAN, WHITE, colint, lerp, prog, clamp, e_io_cubic, e_io_sine, paint_fill, paint_stroke
from seg_axpoint import colint_mix

TL0, TL1 = 47 * 24 + 9, 57 * 24 + 23         # timeline 00:00:47:09 .. 00:00:57:23
NF = TL1 - TL0 + 1
DOWN0, DOWN_D = TL0 / 24.0 + 0.02, 1.10      # the UI comes down to face the lens (from the first frame on)
UI_L, UI_B, UI_W = 96.0, 728.0, 1728.0       # where it settles: aligned with the title, a margin above it
UI_H = UI_W * A.UH / A.UW
X0, X_D = 49.35, 0.85                        # the room and the title fade out, the UI goes soft: the background
BG_BLUR, BG_ALPHA, BG_DIM = 14.0, 0.55, 0.50    # the soft UI as the background: blur, opacity, navy over it
BG_SHRINK = 0.84                                # and it slowly draws back (shrinks) under the graphics
SCV = 1.0


def clock(tl):
    return tl / 24.0


def grain(tl):
    return tl


def front_quad():
    return [(UI_L, UI_B - UI_H), (UI_L + UI_W, UI_B - UI_H), (UI_L + UI_W, UI_B), (UI_L, UI_B)]


def base(c):
    """What is left under the soft UI once the room has gone: a deep navy field."""
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 138), skia.Point(0, 942)],
                                        [E.colint("#16264A", 1.0), E.colint("#0B1530", 1.0)])
    c.drawRect(R(-W, -H, 3 * W, 3 * H), skia.Paint(Shader=sh))


def grade(c, k):
    """The connect scene's look over its background (as seg_connect2.background), faded in with k."""
    if k <= 0.003:
        return
    c.drawRect(R(0, 0, W, H), paint_fill(E.NAVY_950, BG_DIM * k))
    E.radial(c, K.HUB[0], K.HUB[1], 1100, "#3D6FD8", 0.20 * k, blend=skia.BlendMode.kScreen)
    sh = skia.GradientShader.MakeRadial(skia.Point(*K.HUB), 1300,
                                        [E.colint(E.NAVY_950, 0.0), E.colint(E.NAVY_950, 0.45 * k)], [0.40, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


# ---------------------------------------------------------------- the company systems (client's card design)
SYS = [("ERP", "erp", False, "SAP · Oracle · Microsoft Dynamics · 더존 · 영림원", 5),
       ("PLM/PLS", "cube", False, "Siemens Teamcenter · PTC Windchill · 3DEXPERIENCE", 3),
       ("SCM", "truck", True, "엠로 · SAP IBP · Oracle SCM", 3),
       ("QMS", "shield", True, "Siemens Opcenter · SAP QM · ETQ Reliance", 3),
       ("WMS", "store", False, "SAP EWM · 삼성SDS Cello Square · 한화시스템 WMS", 3),
       ("HRM", "user", False, "휴넬 · flex · SAP SuccessFactors · Workday", 4),
       ("그룹웨어", "chat", False, "하이웍스 · 아마란스10 · 네이버웍스", 3)]
SP_X, SP_W, SP_HEAD, SP_PAD, ROW_H, ROW_G = 96, 700, 70, 22, 54, 10
SP_H = SP_HEAD + len(SYS) * ROW_H + (len(SYS) - 1) * ROW_G + SP_PAD
SP = R(SP_X, K.HUB[1] - SP_H / 2, SP_W, SP_H)
ROW_DT = 0.27


def row_rect(i):
    return R(SP.left() + SP_PAD, SP.top() + SP_HEAD + i * (ROW_H + ROW_G), SP.width() - 2 * SP_PAD, ROW_H)


def row_time(i):
    return K.PAN0 + 0.35 + i * ROW_DT


def sys_icon(c, kind, x, y, col, a):
    p = paint_stroke(col, a, 1.6)
    rr = lambda r_, k_: c.drawRRect(skia.RRect.MakeRectXY(r_, k_, k_), p)
    if kind == "erp":
        rr(R(x - 9, y - 8, 18, 16), 3)
        c.drawLine(x - 9, y - 3, x + 9, y - 3, p)
        c.drawLine(x - 3, y - 3, x - 3, y + 8, p)
    elif kind == "truck":
        rr(R(x - 10, y - 6, 12, 10), 2)
        pth = skia.Path()
        pth.moveTo(x + 2, y - 3)
        pth.lineTo(x + 7, y - 3)
        pth.lineTo(x + 10, y + 1)
        pth.lineTo(x + 10, y + 4)
        pth.lineTo(x + 2, y + 4)
        c.drawPath(pth, p)
        c.drawCircle(x - 6, y + 6, 2.2, p)
        c.drawCircle(x + 6, y + 6, 2.2, p)
    elif kind == "shield":
        pth = skia.Path()
        pth.moveTo(x, y - 10)
        pth.lineTo(x + 8, y - 7)
        pth.cubicTo(x + 8, y + 1, x + 5, y + 6, x, y + 9)
        pth.cubicTo(x - 5, y + 6, x - 8, y + 1, x - 8, y - 7)
        pth.close()
        c.drawPath(pth, p)
        c.drawPath(E.poly([(x - 3.5, y - 0.5), (x - 0.5, y + 2.5), (x + 4, y - 3)]), p)
    elif kind == "store":
        pth = skia.Path()
        pth.moveTo(x - 10, y - 2)
        pth.lineTo(x, y - 9)
        pth.lineTo(x + 10, y - 2)
        c.drawPath(pth, p)
        rr(R(x - 8, y - 2, 16, 11), 1.5)
        c.drawLine(x - 8, y + 3, x + 8, y + 3, p)
        c.drawLine(x, y - 2, x, y + 3, p)
    else:
        E.icon(c, kind, x, y, 18, col, a, 1.6)


def systems_panel(c, t):
    """One glass panel '사내 시스템': a row per system kind (icon, name, products, count), each joined to the node
    from a port on its right; the panel comes in as the old left panels did, the rows one by one."""
    a = e_io_sine(prog(t, K.PAN0, 0.9))
    if a <= 0.003:
        return
    dx = -50 * (1 - E.e_out_cubic(prog(t, K.PAN0, 1.1)))
    P = SP.makeOffset(dx, 0)
    for i in range(len(SYS)):                                  # the connectors (behind the panel)
        t0 = row_time(i)
        la = e_io_sine(prog(t, t0, 0.5))
        if la <= 0.003:
            continue
        r = row_rect(i).makeOffset(dx, 0)
        px, py = P.right() + 26, r.centerY()
        pth = E.curve((px, py), (K.HUB[0] - 40, K.HUB[1]), 0.45)
        g = e_io_cubic(prog(t, t0 + 0.1, 0.8))
        E.line(c, pth, CYAN, 0.75 * la * a, 1.5, (0, g), glow=0.7)
        if t > t0 + 1.0:
            E.pulse(c, pth, ((t - t0 - 1.0) * 0.5 + i * 0.13) % 1.0, CYAN, 0.7 * la * a, 10, 0.15)
        c.drawLine(P.right() - 2, py, px, py, paint_stroke(CYAN, 0.6 * la * a, 1.4))
        E.glow_dot(c, px, py, 9, CYAN, la * a)
    blur = 10 * (1 - e_io_sine(prog(t, K.PAN0, 0.9)))
    lp = skia.Paint()
    if blur > 0.2:
        lp.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kDecal))
    c.saveLayer(None, lp)
    E.glass(c, P, 22, a, tint=E.NAVY_950, tint_a=0.55, blur=24, border=0.5, shadow=0.3)
    E.text(c, "사내 시스템", P.left() + SP_PAD + 2, P.top() + 46, 26, "Bold", WHITE, a)
    n_on = sum(SYS[i][4] for i in range(len(SYS)) if t >= row_time(i) + 0.9)
    E.text(c, "%d연결%s" % (n_on, "+" if n_on == 24 else ""), P.right() - SP_PAD, P.top() + 45, 19, "Bold",
           "#5FB4E8", a, "right")
    c.restore()
    for i, (name, ic, own, prods, n) in enumerate(SYS):
        t0 = row_time(i)
        ca = a * e_io_sine(prog(t, t0, 0.5))
        if ca <= 0.003:
            continue
        r = row_rect(i).makeOffset(dx + 16 * (1 - E.e_out_cubic(prog(t, t0, 0.6))), 0)
        on = e_io_sine(prog(t, t0 + 0.8, 0.3))
        flash = math.sin(math.pi * clamp((t - t0 - 0.8) / 0.7))
        E.rrect(c, r, 14, "#0A1530", 0.55 * ca)
        E.rrect_stroke(c, r, 14, "#2E4670", ca, 1.2)
        if flash > 0:
            E.rrect_stroke(c, r, 14, CYAN, 0.45 * ca * flash, 1.4)
        ib = R(r.left() + 12, r.centerY() - 18, 36, 36)
        E.rrect(c, ib, 9, "#162A4D", ca)
        E.rrect_stroke(c, ib, 9, "#3B5D8F", ca, 1.1)
        sys_icon(c, ic, ib.centerX(), ib.centerY(), "#9CC6F2", ca)
        E.text(c, name, r.left() + 62, r.centerY() + 8, 22, "Bold", WHITE, ca)
        xp = r.left() + 184
        if own:
            cw = E.text_w("자체 구축", 13, "SemiBold") + 22
            cr = R(xp, r.centerY() - 14, cw, 28)
            E.rrect(c, cr, 8, "#0E1C38", ca)
            E.rrect_stroke(c, cr, 8, "#4A6690", ca, 1.1)
            E.text(c, "자체 구축", cr.centerX(), cr.centerY() + 5, 13, "SemiBold", WHITE, ca, "center")
            xp += cw + 12
        E.text(c, prods, xp, r.centerY() + 6, 16, "Medium", "#C9D6EA", ca)
        bx, by = r.right() - 30, r.centerY()
        c.drawCircle(bx, by, 14, paint_fill("#1B3559", ca))
        E.text(c, str(n), bx, by + 5, 14, "Bold", colint_mix("#7FB6E0", CYAN, on), ca, "center")
        if flash > 0:
            E.glow_dot(c, bx, by, 8 + 6 * flash, CYAN, 0.6 * ca * flash)


SAAS_H = C.PAN_HEAD + 5 * 54 + 4 * 14 + C.PAN_PAD


def saas_panel():
    """The external SaaS panel mirrors the systems panel (same width and margin), sized to its five rows and centred
    on the node like it."""
    return R(W - SP_X - SP_W, K.HUB[1] - SAAS_H / 2, SP_W, SAAS_H)


K.saas_panel = saas_panel
K.SAAS_RH = 54
K.BEATS[:] = [row_time(i) + 0.9 for i in range(len(SYS))] + [K.saas_time(i) + 0.9 for i in range(len(K.SAAS))]


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
    # the workspace UI: facing the lens, then soft and faded back as the background, slowly drawing back
    zb = lerp(1.0, BG_SHRINK, e_io_sine(prog(t, X0, K.T_END - X0)))
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
        systems_panel(c, t)
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
