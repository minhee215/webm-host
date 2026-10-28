"""Segment 00:01:02:19-00:01:14:12 (282 frames) - "AI가 설비, 자재, 공정, 제품, 사람과 업무의 관계를 이해하도록
만듭니다. / 이것이 AXCORE 온톨로지입니다."

  62.79  continues the OCR segment's last frame (the data table + OCR card). The transition after the client's
         reference, a zoom-out match cut: the camera pulls back from it, faster and faster, and at full speed cuts
         to the ontology seen very close, which keeps pulling back, decelerating, to its framing
  63.6s  the isometric glass platform ontology (the earlier SC14, rebuilt in the current look): the work from 시작
         to 끝 comes in step by step, the entities rise on their words (설비 자재 공정 제품 사람 업무) with their
         relations; the company's systems stream data onto the platform. On "관계를 이해하도록" a pulse runs the
         work and lights what each step depends on, the AI core links everything. The camera orbits slowly
  70.4s  "이것이 AXCORE 온톨로지입니다": the camera turns quickly to the front and pulls back, so the whole
         structure is seen at once; a light wave runs over the platform, the AXCORE Ontology title lands on top
Frame f is timeline frame 1507 + f; film time = timeline frame / 24 (narration at its original timing).
23.976 fps, 21:9 letterbox.
Usage: python3 seg_onto.py <out.mp4> [height=480] [first last]
"""
import math
import os
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_axpoint as A
import seg_ocr as O
from engine import (W, H, R, BLUE, INK, WHITE, NAVY_950, NAVY_900, NAVY_800, CYAN, CYAN_SOFT, lerp, prog, clamp,
                    e_io_cubic, e_io_sine, e_out_cubic, e_out_expo, e_in_cubic, paint_fill, paint_stroke,
                    rrect, rrect_stroke, text, text_w, icon, poly, colint, line, pulse)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 62 * 24 + 19              # 00:01:02:19 (the OCR segment's last frame)
NF = 74 * 24 + 12 - F_TL + 1     # through 00:01:14:12 (282 frames)
T_END = (F_TL + NF) / 24.0
SCV = 1.0

# narration cues (film time)
CUE = {"EQUIP": 64.40, "MATER": 65.15, "PROC": 65.89, "PROD": 66.58, "PEOPLE": 67.31, "TASK": 67.80,
       "L18": 70.57, "ONTO": 71.25}
PULSE0, PULSE_D = 68.05, 1.85     # "관계를 이해하도록 만듭니다": the work runs from 시작 to 끝
CORE0 = 69.30
BUILD0 = 61.90                    # the platform is there at the cut (built before it)
ORBIT0 = 63.23                    # the camera's slow orbit
FLOW0 = 63.62                     # the work from 시작 to 끝 comes in, step by step
PUNCH0, PUNCH_D = 70.40, 1.30     # "이것이 AXCORE 온톨로지입니다": the reveal move

# transition
SHR0, CUT = 62.84, 63.23          # the previous frame pulls back, accelerating, until the cut
ZIN_D, ZIN_Z = 1.10, 3.2          # after it the ontology, seen very close, pulls back decelerating


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- the transition (the client's reference)
# A zoom-out match cut: the camera pulls back from the previous frame, faster and faster (its graphics shrink
# over the soft background); at full speed it cuts to the ontology seen very close, which keeps pulling back,
# decelerating, to its framing. Both sides of the cut move the same way, so the cut is not felt.


def ocr_pullback(c, t):
    s = min(t, O.T0 + (O.NF - 1) / 24.0) - O.T0
    q = e_in_cubic(prog(t, SHR0, CUT - SHR0))
    O.background(c, s)
    z = lerp(1.0, 0.58, q)
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(z, z)
    c.translate(-W / 2, -H / 2)
    A.blur_layer(c, 7 * q * q, 1.0)
    O.table(c, s)
    O.card(c, s)
    O.send(c, s)
    c.restore()
    c.restore()


# ---------------------------------------------------------------- the ontology
ENT = {
    "설비": ((-5.0, 1.1), "EQUIP", "gear"), "자재": ((-2.7, -1.9), "MATER", "box"),
    "공정": ((-0.1, 0.4), "PROC", "factory"), "제품": ((2.7, -1.7), "PROD", "cube"),
    "사람": ((2.0, 2.0), "PEOPLE", "user"), "업무": ((5.1, 0.5), "TASK", "doc"),
}
REL = S.ON_REL
FLOW = S.ON_FLOW
SRC = S.ON_SRC
SLAB = (7.2, 3.7, 0.32)
FLOW_Z, FLOW_Y = 4.75, -0.55


def punch(t):
    """The reveal move: quick, then a long soft landing."""
    return e_out_expo(prog(t, PUNCH0, PUNCH_D))


def cam(t):
    a = e_io_sine(prog(t, ORBIT0, PUNCH0 - ORBIT0))       # slow orbit in from the left
    b = punch(t)
    d = prog(t, PUNCH0 + PUNCH_D, T_END - PUNCH0 - PUNCH_D)  # then a slow drift
    yaw = lerp(-36, -18, a)
    pitch = lerp(21, 27, a)
    dist = lerp(19.5, 17.2, a)
    yaw = lerp(yaw, 0.0, b) + 1.5 * d                     # to the front, and back a little: the whole of it
    pitch = lerp(pitch, 40, b)
    dist = lerp(dist, 23.0, b) + 0.5 * d
    ty = lerp(0.4, 0.0, b)
    cy = lerp(520, 620, b)
    return S.Proj(math.radians(yaw), math.radians(pitch), dist, (0.0, ty, 0.4), 1200, W / 2, cy)


def stage(c, t, P):
    c.drawRect(R(0, 0, W, H), paint_fill("#081430", 1.0))
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, -120), 1300, [colint("#5E7FD0", 0.55),
                                                                         colint("#22407E", 0.35),
                                                                         colint("#081430", 0.0)], [0.0, 0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))
    E.radial(c, W / 2, H / 2 + 120, 900, "#3A63C8", 0.22)
    # floor grid far below the platform: it moves with the camera
    g = e_io_sine(prog(t, BUILD0, 1.2))
    for i in range(-7, 8):
        for a0, a1 in (((i * 2.0, -2.4, -14), (i * 2.0, -2.4, 14)), ((-14, -2.4, i * 2.0), (14, -2.4, i * 2.0))):
            p0, p1 = P(*a0), P(*a1)
            c.drawLine(p0[0], p0[1], p1[0], p1[1], paint_stroke("#7FA6FF", 0.07 * g, 1.0))


def disc(P, x, z, r, n=48, y=0.0):
    return [P(x + r * math.cos(2 * math.pi * i / n), y, z + r * math.sin(2 * math.pi * i / n))[:2] for i in range(n)]


def platform(c, t, P):
    hw, hd, th = SLAB
    k = e_io_cubic(prog(t, BUILD0, 0.9))
    if k <= 0:
        return
    s = lerp(0.6, 1.0, k)
    corners = [(-hw * s, -hd * s), (hw * s, -hd * s), (hw * s, hd * s), (-hw * s, hd * s)]
    top = [P(x, 0, z)[:2] for x, z in corners]
    bot = [P(x, -th, z)[:2] for x, z in corners]
    front = poly([top[3], top[2], bot[2], bot[3]], True)
    right = poly([top[2], top[1], bot[1], bot[2]], True)
    left = poly([top[0], top[3], bot[3], bot[0]], True)
    c.drawPath(poly(top, True), paint_fill(NAVY_950, 0.35 * k, blur=30))
    for pth, a in ((front, 0.20), (right, 0.12), (left, 0.10)):
        c.drawPath(pth, paint_fill("#9FC0FF", a * k))
    sh = skia.GradientShader.MakeLinear([skia.Point(*top[0]), skia.Point(*top[2])],
                                        [colint("#DCE8FF", 0.20 * k), colint("#9FC0FF", 0.08 * k)])
    c.drawPath(poly(top, True), skia.Paint(AntiAlias=True, Shader=sh))
    for i in range(1, 12):                               # a fine grid on the glass
        x = -hw * s + i * 2 * hw * s / 12
        a0, a1 = P(x, 0.001, -hd * s)[:2], P(x, 0.001, hd * s)[:2]
        c.drawLine(*a0, *a1, paint_stroke("#BFD4FF", 0.07 * k, 1.0))
    for i in range(1, 6):
        z = -hd * s + i * 2 * hd * s / 6
        a0, a1 = P(-hw * s, 0.001, z)[:2], P(hw * s, 0.001, z)[:2]
        c.drawLine(*a0, *a1, paint_stroke("#BFD4FF", 0.07 * k, 1.0))
    c.drawPath(poly(top, True), paint_stroke(CYAN_SOFT, 0.85 * k, 1.8))
    c.drawPath(poly(top, True), paint_stroke(CYAN, 0.25 * k, 6, blur=6))
    for pth in (front, right, left):
        c.drawPath(pth, paint_stroke(CYAN_SOFT, 0.35 * k, 1.0))


def ent_time(n):
    return CUE[ENT[n][1]]


def lit_state(t):
    lit = {n: 0.0 for n in ENT}
    pp = prog(t, PULSE0, PULSE_D)
    for i, (lab, ent) in enumerate(FLOW):
        f = (i + 1) / (len(FLOW) + 1)
        h = clamp((pp - f) * 7) * (1 - clamp((pp - f - 0.3) * 3)) if pp > 0 else 0.0
        lit[ent] = max(lit[ent], h)
        if ent == "공정":
            lit["설비"] = max(lit["설비"], h)
    # the reveal: every entity glows as the structure lands
    w = math.sin(math.pi * clamp(prog(t, PUNCH0 + 0.55, 1.0)))
    for n in lit:
        lit[n] = max(lit[n], 0.8 * w)
    return lit, pp


def flow_lane(c, t, P, lit, pp):
    xs = [lerp(-5.3, 5.3, i / (len(FLOW) - 1)) for i in range(len(FLOW))]
    st, en = P(-6.9, FLOW_Y, FLOW_Z), P(6.9, FLOW_Y, FLOW_Z)
    stops = [P(x, FLOW_Y, FLOW_Z) for x in xs]
    pth = poly([st[:2]] + [p[:2] for p in stops] + [en[:2]])
    fg = e_out_expo(prog(t, FLOW0 - 0.1, 1.4))
    if fg <= 0:
        return
    band = poly([P(-7.4, FLOW_Y, FLOW_Z - 0.45)[:2], P(7.4, FLOW_Y, FLOW_Z - 0.45)[:2],
                 P(7.4, FLOW_Y, FLOW_Z + 0.75)[:2], P(-7.4, FLOW_Y, FLOW_Z + 0.75)[:2]], True)
    c.drawPath(band, paint_fill(NAVY_950, 0.4 * fg, blur=10))
    line(c, pth, WHITE, 0.75, 2.6, (0, fg))
    line(c, pth, CYAN, 1.0, 4.2, (0, pp), glow=1.0, glow_w=12)
    if 0 < pp < 1:
        pulse(c, pth, pp, CYAN, 1.0, 26, 0.08, 4.0)
    for lab, p, t0 in (("시작", st, FLOW0 - 0.15), ("끝", en, FLOW0 + 1.05)):
        k, dy, bl = A.blur_in(t, t0, 0.6)
        if k <= 0.003:
            continue
        on = lab == "시작" or pp >= 1
        tw = text_w(lab, 20, "Bold") + 36
        r = R(p[0] - tw / 2, p[1] + 22 + dy, tw, 40)
        rrect(c, r, 20, CYAN if on else NAVY_800, k)
        rrect_stroke(c, r, 20, CYAN, k, 1.6)
        text(c, lab, p[0], r.top() + 27, 20, "Bold", NAVY_950 if on else WHITE, k, "center")
        E.square(c, p[0], p[1], 16, CYAN if on else WHITE, k)
    for i, (lab, ent) in enumerate(FLOW):
        f = (i + 1) / (len(FLOW) + 1)
        k, dy, bl = A.blur_in(t, FLOW0 + i * 0.16, 0.6)
        if k <= 0.003:
            continue
        sx, sy, _ = stops[i]
        passed = pp > f
        E.square(c, sx, sy, 13, CYAN if passed else WHITE, k)
        tw = text_w(lab, 18, "SemiBold") + 30
        r = R(sx - tw / 2, sy + 20 + dy, tw, 36)
        rrect(c, r, 18, "#1E4FC0" if passed else "#13285C", 0.92 * k)
        rrect_stroke(c, r, 18, CYAN if passed else "#6F9BFF", k, 1.3)
        text(c, lab, sx, r.top() + 24, 18, "SemiBold", WHITE, k, "center")
        # the link to what the step depends on: drawn as the pulse passes, then it stays (bright while lit)
        g = e_out_cubic(clamp((pp - f) * 5)) if pp > f else 0.0
        if g > 0:
            h = clamp((pp - f) * 7) * (1 - clamp((pp - f - 0.3) * 3))
            (ex, ez), _, _ = ENT[ent]
            q = P(ex, 0.05, ez)
            line(c, E.curve((sx, sy - 10), q[:2], 0.3, False), CYAN, 0.45 + 0.5 * h, 1.6 + 0.6 * h, (0, g),
                 glow=0.3 + 0.5 * h)


def relations(c, t, P, lit):
    for s_, d_, lab in REL:
        t0 = max(ent_time(s_), ent_time(d_)) + 0.2
        g = e_out_cubic(prog(t, t0, 0.8))
        if g <= 0:
            continue
        (x0, z0), (x1, z1) = ENT[s_][0], ENT[d_][0]
        a0, a1 = P(x0, 0.02, z0)[:2], P(x1, 0.02, z1)[:2]
        hl = max(lit[s_], lit[d_])
        dash = paint_stroke(CYAN if hl > 0.3 else "#BFD4FF", 0.4 + 0.55 * hl, 1.3 + hl)
        dash.setPathEffect(skia.DashPathEffect.Make([5, 7], -t * 30))
        c.drawPath(E.path_seg(poly([a0, a1]), 0, g), dash)
        k = e_io_sine(prog(t, t0 + 0.3, 0.5))
        if k > 0:
            mx, my = (a0[0] + a1[0]) / 2, (a0[1] + a1[1]) / 2
            tw = text_w(lab, 13, "SemiBold") + 18
            rrect(c, R(mx - tw / 2, my - 12, tw, 24), 12, NAVY_950, 0.72 * k)
            rrect_stroke(c, R(mx - tw / 2, my - 12, tw, 24), 12, CYAN if hl > 0.3 else "#8FB4FF", 0.7 * k, 1.0)
            text(c, lab, mx, my + 5, 13, "SemiBold", WHITE, k, "center")


def sources(c, t, P):
    """The company's systems stream data down onto the platform (everything connected so far)."""
    out = 1 - e_io_sine(prog(t, PUNCH0 - 0.1, 0.4))
    for i, (lab, x) in enumerate(SRC):
        t0 = CUE["MATER"] + i * 0.14
        k, dy, bl = A.blur_in(t, t0, 0.6)
        k *= out
        if k <= 0.003:
            continue
        top = P(x, 3.0, -3.2)
        base = P(x, 0.0, -3.2)
        g = e_io_cubic(prog(t, t0 + 0.2, 0.9))
        pth = poly([top[:2], base[:2]])
        E.line(c, pth, "#9FC0FF", 0.35 * k, 1.2, (0, g))
        if t > t0 + 0.8:
            for j in range(2):
                pulse(c, pth, ((t - t0) * 0.8 + j * 0.5) % 1.0, CYAN, 0.7 * k, 10, 0.18, 2.0)
        tw = text_w(lab, 15, "SemiBold") + 28
        r = R(top[0] - tw / 2, top[1] - 34 + dy, tw, 30)
        rrect(c, r, 15, NAVY_950, 0.6 * k)
        rrect_stroke(c, r, 15, "#8FB4FF", 0.7 * k, 1.0)
        text(c, lab, top[0], r.top() + 20, 15, "SemiBold", WHITE, k, "center")


def core(c, t, P):
    ak = e_out_cubic(prog(t, CORE0, 0.7))
    if ak <= 0:
        return
    cp = P(0.4, 3.1, -0.4)
    for i, (n, ((x, z), key, ic)) in enumerate(ENT.items()):
        q = P(x, 1.0, z)
        g = e_out_expo(prog(t, CORE0 + 0.1 + 0.06 * i, 0.5))
        line(c, poly([cp[:2], q[:2]]), CYAN_SOFT, 0.35 * ak, 1.1, (0, g))
    ph = (t * 0.8) % 1.0
    for k_ in range(3):
        q = (ph + k_ / 3) % 1.0
        c.drawCircle(cp[0], cp[1], 34 + 70 * q, paint_stroke(CYAN, (1 - q) * 0.7 * ak, 1.4))
    E.glow_dot(c, cp[0], cp[1], 70, CYAN, 0.8 * ak)
    c.drawCircle(cp[0], cp[1], 34, paint_fill(NAVY_900, 0.92 * ak))
    c.drawCircle(cp[0], cp[1], 34, paint_stroke(CYAN, ak, 2.2))
    text(c, "AI", cp[0], cp[1] + 9, 26, "Bold", WHITE, ak, "center")


def entities(c, t, P, lit):
    for n in sorted(ENT, key=lambda k_: ENT[k_][0][1]):
        (x, z), key, ic = ENT[n]
        t0 = max(ent_time(n) - 0.1, 64.0)
        k = e_io_sine(prog(t, t0, 0.6))
        if k <= 0.003:
            continue
        rise = 0.7 * (1 - e_out_cubic(prog(t, t0, 0.8)))
        hl = lit[n]
        hero = n == "공정"
        on = hero or hl > 0.3
        d = disc(P, x, z, 0.95)
        c.drawPath(poly(d, True), paint_fill("#BFD4FF", 0.16 * k))
        c.drawPath(poly(d, True), paint_stroke(CYAN if on else CYAN_SOFT, k * (0.7 + 0.3 * hl), 1.6 + hl))
        q = prog(t, t0, 0.9)                              # a ripple as it lands
        if 0 < q < 1:
            c.drawPath(poly(disc(P, x, z, 0.95 + 1.1 * e_out_cubic(q)), True), paint_stroke(CYAN, (1 - q) * 0.7, 1.4))
        if hl > 0:
            c.drawPath(poly(disc(P, x, z, 0.95 + 0.5 * hl), True), paint_stroke(CYAN, k * hl * 0.6, 1.4))
        bx, by, _ = P(x, 0.0, z)
        ix, iy, ik = P(x, 1.0 - rise, z)
        c.drawLine(bx, by, ix, iy, paint_stroke(CYAN_SOFT, 0.5 * k, 1.2))
        sz = ik * 0.66
        A.blur_layer(c, 10 * (1 - k), k)
        r = R(ix - sz, iy - sz, sz * 2, sz * 2)
        E.glass(c, r, sz * 0.48, 1.0, tint=NAVY_800, tint_a=0.75, blur=8, border=0.0, shadow=0.0, highlight=0.1,
                glow=0.8 * max(hl, 0.5 if hero else 0), glow_col=CYAN)
        rrect_stroke(c, r, sz * 0.48, CYAN if on else "#8FB4FF", 1.0, 1.7)
        icon(c, ic, ix, iy, sz * 1.05, WHITE, 1.0)
        tw = text_w(n, 20, "Bold") + 30
        pr = R(ix - tw / 2, iy - sz - 48, tw, 36)
        rrect(c, pr, 18, CYAN if on else WHITE, 1.0)
        text(c, n, ix, pr.top() + 25, 20, "Bold", NAVY_950, 1.0, "center")
        c.restore()


def wave(c, t, P):
    """A light wave over the platform as the structure lands."""
    q = prog(t, PUNCH0 + 0.5, 1.1)
    if not 0 < q < 1:
        return
    r = 0.5 + 9.0 * e_out_cubic(q)
    pts = disc(P, 0.0, 0.0, r, 72, 0.01)
    c.save()
    hw, hd, _ = SLAB
    c.clipPath(poly([P(x, 0, z)[:2] for x, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))], True), True)
    c.drawPath(poly(pts, True), paint_stroke(WHITE, 0.55 * (1 - q), 3.0, blur=2))
    c.drawPath(poly(pts, True), paint_stroke(CYAN, 0.45 * (1 - q), 18, blur=14))
    c.restore()


def title(c, t):
    k = e_io_sine(prog(t, CUE["ONTO"] - 0.15, 0.7))
    if k <= 0.003:
        return
    s = lerp(1.14, 1.0, e_out_cubic(prog(t, CUE["ONTO"] - 0.15, 0.9)))
    L = E.logo()
    lw = 330
    tw = text_w("Ontology", 52, "Light")
    gap = 14
    x0 = W / 2 - (lw + gap + tw) / 2
    y0 = 215
    c.save()
    c.translate(W / 2, y0)
    c.scale(s, s)
    c.translate(-W / 2, -y0)
    A.blur_layer(c, 12 * (1 - k), k)
    L.draw(c, x0 + lw / 2, y0, lw, e_io_cubic(prog(t, CUE["ONTO"] - 0.15, 0.6)), k, (k, k, k), True, 1.0)
    text(c, "Ontology", x0 + lw + gap, y0 + 22, 52, "Light", WHITE, 1.0)
    c.restore()
    c.restore()
    fl = math.sin(math.pi * clamp(prog(t, CUE["ONTO"] - 0.1, 0.8)))
    if fl > 0:
        E.radial(c, W / 2, y0 + 6, 520, "#9FC0FF", 0.22 * fl)


def onto_full(c, t):
    P = cam(t)
    stage(c, t, P)
    lit, pp = lit_state(t)
    sources(c, t, P)
    platform(c, t, P)
    wave(c, t, P)
    flow_lane(c, t, P, lit, pp)
    relations(c, t, P, lit)
    core(c, t, P)
    entities(c, t, P, lit)
    title(c, t)


def render(c, t):
    if t < CUT:
        ocr_pullback(c, t)
        return
    z = lerp(ZIN_Z, 1.0, e_out_expo(prog(t, CUT, ZIN_D)))
    ax, ay, _ = cam(t)(0.0, 0.0, 0.6)                    # pull back from the middle of the platform
    c.save()
    c.translate(ax, ay)
    c.scale(z, z)
    c.translate(-ax, -ay)
    A.blur_layer(c, 8 * (1 - e_out_cubic(prog(t, CUT, 0.35))), 1.0)
    onto_full(c, t)
    c.restore()
    c.restore()


def frame(f, surf, finish):
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    c.save()
    c.scale(SCV, SCV)
    render(c, ft(f))
    c.restore()
    fr = finish.apply(surf, F_TL + f)
    bar = int(round(BAR * SCV))
    fr[:bar] = 0
    fr[-bar:] = 0
    return np.ascontiguousarray(fr)


def setup(height):
    global SCV
    surf, finish, SWD, SHD = A.setup(height)
    SCV = O.SCV = A.SCV
    return surf, finish, SWD, SHD


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        enc.stdin.write(frame(f, surf, finish).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
