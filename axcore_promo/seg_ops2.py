"""Patch 00:01:25:12-00:01:36:17 (270 frames) over the seg_ask -> seg_ops join and seg_ops (client re-edit):
  - the first shot (영업팀 · 다음 달 수요는?) is a team meeting in a conference room instead of the retail aisle
  - into the production shot the card itself travels from the upper left to where the production card sits
    (lower right) and turns into it - glass white -> navy, the sales content giving way to the production card's,
    which goes on as that card does; the footage cross-fades underneath (no line-particle cut)
  - the link to the robot cell runs from the start of the shot, and its marker opens on the robot arm's shoulder
    joint (tracked) as it arrives; one diamond moves down the steps as they come in, 'AUTO' set tighter
  - 설비팀 · 오래된 설비도 연결돼? holds to 01:36:17 (no exit here: the next scene is being reworked)
Before 01:25:20 the frames are seg_ask's; the grain runs on as both files' (seg_ask's numbering).
Film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_ops2.py <out.mp4> [height=480] [first last]
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_axpoint as A
import seg_ask as K
import seg_ops as O
from engine import (W, H, R, WHITE, NAVY_950, CYAN, BLUE, INK, STEEL, STEEL_200, lerp, prog, clamp, e_io_cubic,
                    e_io_sine, e_out_cubic, e_out_expo, paint_fill, paint_stroke, rrect, text, text_w, icon, poly)

TL0, TL1 = 85 * 24 + 12, 96 * 24 + 17         # timeline 01:25:12 .. 01:36:17
NF = TL1 - TL0 + 1
MEET = os.environ.get("AXP_MEET", "m1_meeting")
O.SHOTS[0] = (MEET, 86.50, 2.80, dict(s=(1.03, 1.10), grade=S.GRADE_DAY))
O.SHOTS[2] = ("17_robot", 92.10, 4.80, dict(s=(1.05, 1.14), x=(-20, 20), grade=S.GRADE_COOL))
LINK0 = O.L_AUTO + 0.40                       # the link to the robot draws as the shot's card comes in
MV0, MV_D = 88.25, 0.80                       # the card travels to the production card's place
R1, R2 = R(96, 186, 760, 430), R(1110, 470, 720, 420)
END = TL1 / 24.0
JOINT = json.load(open(os.path.join(E.HERE, "assets", "tracks", "17_robot_joint.json")))["points"]["joint"]
SCV = 1.0


def grain(tl):
    return K.GRAIN0 + (tl - K.F_TL)


def lerp_rect(a, b, k):
    return R(lerp(a.left(), b.left(), k), lerp(a.top(), b.top(), k), lerp(a.width(), b.width(), k),
             lerp(a.height(), b.height(), k))


def into(c, src, dst):
    """Map rect src onto rect dst (the card content follows its card)."""
    c.translate(dst.left(), dst.top())
    c.scale(dst.width() / src.width(), dst.height() / src.height())
    c.translate(-src.left(), -src.top())


# ---------------------------------------------------------------- 1 sales content (as seg_ops.sales, without its card)
def sales_content(c, t, r):
    O.team_head(c, r.left() + 44, r.top() + 64, "영업팀", "다음 달 수요는?", 1.0, True)
    gx, gy, gw, gh = r.left() + 44, r.top() + 150, r.width() - 88, 210
    c.drawLine(gx, gy + gh, gx + gw, gy + gh, paint_stroke(STEEL_200, 1.0, 1.4))
    hist = [0.18, 0.30, 0.25, 0.38, 0.48, 0.41, 0.56, 0.62]
    fut = [0.62, 0.70, 0.78, 0.74, 0.90]
    n = len(hist) + len(fut) - 2
    pts = [(gx + i * gw / n, gy + gh * (1 - v)) for i, v in enumerate(hist)]
    fp = [(gx + (len(hist) - 1 + i) * gw / n, gy + gh * (1 - v)) for i, v in enumerate(fut)]
    E.line(c, poly(pts), INK, 1.0, 3.0, (0, e_io_sine(prog(t, O.L_SALES + 0.35, 0.8))))
    tk = e_io_sine(prog(t, O.L_SALES + 1.0, 0.3))
    ox = pts[-1][0]
    c.drawLine(ox, gy - 18, ox, gy + gh, paint_stroke(STEEL_200, tk, 1.6))
    text(c, "오늘", ox + 10, gy - 4, 19, "SemiBold", STEEL, tk)
    g2 = e_io_sine(prog(t, O.L_SALES + 1.1, 0.8))
    if g2 > 0:
        band = poly([(x, y - 10 - i * 5) for i, (x, y) in enumerate(fp)] +
                    [(x, y + 10 + i * 5) for i, (x, y) in reversed(list(enumerate(fp)))], True)
        c.save()
        c.clipRect(R(ox, gy - 60, (fp[-1][0] - ox) * g2 + 2, gh + 120))
        c.drawPath(band, paint_fill(CYAN, 0.22))
        c.restore()
        E.line(c, poly(fp), BLUE, 1.0, 3.2, (0, g2), dash=[12, 8])
    dk = e_out_expo(prog(t, O.L_SALES + 1.8, 0.35))
    if dk > 0:
        x, y = fp[-1]
        O.diamond(c, x, y, 14 * dk, BLUE, 1.0)
        text(c, "예측", x, y - 28, 20, "Bold", BLUE, dk, "right")
        cr = R(r.right() - 44 - 128, r.top() + 42, 128, 44)
        rrect(c, cr, 22, BLUE, dk)
        text(c, "+12.4%", cr.centerX(), cr.centerY() + 8, 22, "Bold", WHITE, dk, "center")


# ---------------------------------------------------------------- 2 production (as seg_ops.production, split)
def gate(c, t, cam):
    bad = t >= O.SPIKE_T
    k = e_io_sine(prog(t, O.L_PROD + 0.1, 0.5))
    if k <= 0.003:
        return
    r = cam.rect(*O.GATE)
    E.corner_brackets(c, r, 34, O.ACC if bad else WHITE, k, 3.0)
    sp = ((t - O.L_PROD) * 0.9) % 1.0
    y = lerp(r.top(), r.bottom(), e_io_sine(sp))
    c.drawLine(r.left(), y, r.right(), y, paint_stroke(O.ACC, 0.5 * k, 10, blur=10, blend=skia.BlendMode.kScreen))
    c.drawLine(r.left(), y, r.right(), y, paint_stroke(WHITE, 0.95 * k, 1.6))
    lab = "이상 징후 감지 · 0.91" if bad else "품질 검사 중 · 정상 0.98"
    tw = text_w(lab, 20, "Bold") + 32
    lr = R(r.left(), r.top() - 54, tw, 42)
    c.drawPath(O.shape(lr, 12), paint_fill(O.ACC if bad else "#0A1630", 0.95 * k))
    text(c, lab, lr.left() + 16, lr.centerY() + 7, 20, "Bold", NAVY_950 if bad else WHITE, k)
    if bad:
        ph = ((t - O.SPIKE_T) % 1.1) / 1.1
        c.drawRect(r.makeOutset(14 * ph, 14 * ph), paint_stroke(O.ACC, (1 - ph) * 0.8, 2))


def prod_glow(t):
    return 0.8 * e_io_sine(prog(t, O.SPIKE_T, 0.4)) * (1 - 0.5 * prog(t, O.SPIKE_T + 0.4, 1.0))


def prod_content(c, t, r):
    O.team_head(c, r.left() + 44, r.top() + 64, "생산팀", "지금 이상 징후 있어?", 1.0)
    gx, gy, gw, gh = r.left() + 44, r.top() + 150, r.width() - 88, 200
    n = len(O.SIG)
    pts = [(gx + j * gw / (n - 1), gy + gh * (1 - v)) for j, v in enumerate(O.SIG)]
    E.line(c, poly(pts), WHITE, 1.0, 2.4, (0, prog(t, O.L_PROD + 0.7, 1.4)))
    bk = e_out_expo(prog(t, O.SPIKE_T, 0.35))
    if bk > 0:
        ax = gx + 71.5 / (n - 1) * gw
        br = R(ax - 46, gy - 22, 92, gh + 10)
        c.drawPath(O.shape(br, 10), paint_stroke(O.ACC, bk, 2.6))
        top = min(p[1] for p in pts[68:76])
        O.diamond(c, ax, top - 2, 13 * bk, O.ACC, 1.0)
        lab = "이상 감지 · 14:20"
        tw = text_w(lab, 21, "Bold") + 34
        lr = R(min(br.right() + 18, r.right() - 44 - tw), gy - 30, tw, 44)
        c.drawPath(O.shape(lr, 12), paint_fill(O.ACC, bk))
        text(c, lab, lr.centerX(), lr.centerY() + 8, 21, "Bold", NAVY_950, bk, "center")


def production(c, t, cam):
    gate(c, t, cam)
    O.ncard(c, R2, 1.0, glow=prod_glow(t))
    prod_content(c, t, R2)


def travel(c, t):
    """The sales card travelling to the production card's place and turning into it."""
    m = e_io_cubic(prog(t, MV0, MV_D))
    rc = lerp_rect(R1, R2, m)
    tm = e_io_sine(prog(t, MV0 + 0.15, 0.5))              # white glass -> navy glass
    if tm < 1:
        O.ncard(c, rc, 1 - tm, light=True)
    if tm > 0:
        O.ncard(c, rc, tm)
    ka = 1 - e_io_sine(prog(t, MV0, 0.35))                # the sales content gives way ...
    if ka > 0.003:
        A.blur_layer(c, 6 * (1 - ka), ka)
        c.save()
        into(c, R1, rc)
        sales_content(c, t, R1)
        c.restore()
        c.restore()
    kb = e_io_sine(prog(t, MV0 + 0.20, 0.45))             # ... to the production card's, running as it does
    if kb > 0.003:
        A.blur_layer(c, 6 * (1 - kb), kb)
        c.save()
        into(c, R2, rc)
        prod_content(c, t, R2)
        c.restore()
        c.restore()


# ---------------------------------------------------------------- 3 automation + equipment + robots
def checklist(c, t, r):
    O.team_head(c, r.left() + 44, r.top() + 64, "구매팀", "새 도면, 자재 발주까지 돼?", 1.0)
    for i, s in enumerate(O.STEPS):
        t0 = O.L_AUTO + 0.15 + i * 0.28
        k, dy, bl = A.blur_in(t, t0, 0.6)
        if k <= 0.003:
            continue
        y = r.top() + 160 + i * 74 + dy
        on = e_out_expo(prog(t, t0 + 0.3, 0.3))
        b = R(r.left() + 44, y - 22, 42, 42)
        c.drawPath(O.shape(b, 8), paint_fill(O.ACC if on > 0.5 else O.CARD_BG, k))
        c.drawPath(O.shape(b, 8), paint_stroke(O.ACC, k, 1.8))
        if on > 0:
            icon(c, "check", b.centerX(), b.centerY(), 24, NAVY_950, k * on, 3.2)
        text(c, s, b.right() + 22, y + 11, 30, "SemiBold", WHITE, k)
        x1 = r.right() - 44 - 62
        p = paint_stroke("#3A4E80", k, 1.4)
        p.setPathEffect(skia.DashPathEffect.Make([2, 7], 0))
        x0 = b.right() + 40 + text_w(s, 30, "SemiBold")
        c.drawLine(x0, y, x1 - 16, y, p)
        O.spaced(c, "AUTO", x1, y + 8, 20, O.ACC, k * on, 0.6)       # tighter tracking
    # one diamond marking the step at work: it moves down to each step as that step comes in
    t_0 = O.L_AUTO + 0.15
    if t > t_0:
        j = 0.0
        for i in range(1, len(O.STEPS)):
            j += e_io_cubic(prog(t, t_0 + i * 0.28, 0.22))
        da = e_io_sine(prog(t, t_0, 0.3))
        O.diamond(c, r.left() + 26, r.top() + 160 + j * 74, 9, O.ACC, da)


def joint(cam, t):
    """Screen position of the robot's shoulder joint (tracked in the clip)."""
    plate, s0, d, kw = O.SHOTS[2]
    fi = int(min(max((t - s0) * 24, 0), len(JOINT) - 1))
    return cam.screen(*JOINT[fi])


def robots(c, t, cam):
    k, dy, bl = O.card_in(t, O.L_AUTO + 0.0)
    if k > 0.003:
        r = O.CARD3
        A.blur_layer(c, bl, k)
        c.save()
        c.translate(0, dy)
        O.ncard(c, r, 1.0)
        sl = e_io_cubic(prog(t, O.SLIDE0, 0.55))
        c.save()
        c.clipPath(O.shape(r.makeInset(3, 3), 24), True)
        if sl < 1:
            c.save()
            c.translate(0, -150 * sl)
            A.blur_layer(c, 8 * sl, 1 - sl)
            checklist(c, t, r)
            c.restore()
            c.restore()
        if sl > 0:
            c.save()
            c.translate(0, 150 * (1 - sl))
            A.blur_layer(c, 8 * (1 - sl), sl)
            O.machines(c, t, r)
            c.restore()
            c.restore()
        c.restore()
        c.restore()
        c.restore()
    # the robot cell: the link runs out from the card to the arm's shoulder joint (tracked) from the start of the
    # shot, and the marker opens there as it arrives (as before, only earlier)
    gx, gy = joint(cam, t)
    L0 = LINK0
    g = e_io_cubic(prog(t, L0, 0.8))
    if g > 0:
        p0 = (O.CARD3.right(), O.CARD3.centerY() + 40)
        pth = E.curve(p0, (gx - 74, gy), 0.4)
        E.line(c, pth, O.ACC, 0.95, 2.4, (0, g), glow=0.9)
        if t > L0 + 0.75:
            E.pulse(c, pth, ((t - L0 - 0.75) * 0.8) % 1.0, WHITE, 0.9, 14)
    rk = e_io_sine(prog(t, L0 + 0.55, 0.5))
    if rk > 0.003:
        c.save()
        c.translate(gx, gy)
        c.rotate(t * 30)
        for j in range(4):
            c.drawArc(R(-74, -74, 148, 148), j * 90 + 10, 60, False, paint_stroke(O.ACC, rk, 2.6))
        c.restore()
        c.drawCircle(gx, gy, 50, paint_stroke(WHITE, rk * 0.7, 1.4))
        lab = "로봇 셀 R-02 · 연결됨"
        tw = text_w(lab, 20, "Bold") + 60
        lr = R(min(gx + 90, W - 60 - tw), gy - 108, tw, 44)
        c.drawPath(O.shape(lr, 12), paint_fill("#0A1630", 0.88 * rk))
        c.drawPath(O.shape(lr, 12), paint_stroke("#5C78B8", 0.9 * rk, 1.4))
        icon(c, "robot", lr.left() + 26, lr.centerY(), 20, O.ACC, rk)
        text(c, lab, lr.left() + 46, lr.centerY() + 7, 20, "Bold", WHITE, rk)


def shot(c, i, t, card=True):
    plate, s0, d, kw = O.SHOTS[i]
    cam = E.draw_plate(c, plate, t - s0, d, **kw)
    if not card:
        return cam
    if i == 0:
        O.sales(c, t)
    elif i == 1:
        production(c, t, cam)
    else:
        robots(c, t, cam)
    return cam


O.shot = shot                    # seg_ops' way in (the 실행 완료 light) clears onto this first shot


def render(c, t):
    if t < O.IN0 + O.IN_GROW + O.IN_CLEAR:
        O.light_in(c, t)
        return
    if MV0 <= t < MV0 + MV_D + 0.1:
        fb = e_io_sine(prog(t, MV0, MV_D + 0.1))           # the footage cross-fades under the travelling card
        a_img = A.snap(30, lambda cc: shot(cc, 0, t, card=False))
        A.draw_img(c, a_img, 1.0)

        def line_bg(cc):
            gate(cc, t, shot(cc, 1, t, card=False))
        b_img = A.snap(31, line_bg)
        A.draw_img(c, b_img, fb)
        if t < MV0 + MV_D:
            travel(c, t)
        else:
            O.ncard(c, R2, 1.0, glow=prod_glow(t))
            prod_content(c, t, R2)
        return
    c0, cd, kind, kw = O.CUTS[2]
    if c0 <= t < c0 + cd:
        a_img = A.snap(30, lambda cc: shot(cc, 1, t))
        b_img = A.snap(31, lambda cc: shot(cc, 2, t))
        E.TRANSITIONS[kind](c, a_img, b_img, (t - c0) / cd, **kw)
        return
    shot(c, 0 if t < MV0 else (1 if t < c0 else 2), t)


def setup(height):
    global SCV
    out = O.setup(height)
    SCV = A.SCV
    return out


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    bar = int(round(O.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (O.FPS_NUM, O.FPS_DEN), "-i", "-",
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
        fr = finish.apply(surf, grain(tl))
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
