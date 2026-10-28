"""Segment 00:01:25:20-00:01:35:19 (240 frames) - "영업에서는 수요를 예측하고, / 생산과 품질에서는 이상 징후를
감지합니다. / 반복 업무를 자동화하고 설비와 로봇까지 연결하며,"

The original film's three shots (stock footage and its moves unchanged: 16_retail, 06_line, 17_robot) with their
graphics in the film's own glass cards (white on the aisle, navy on the factory), more opaque and with larger
type than before; their content after the client's cards (team chip + the question they would ask), kept simple.
  85.83  straight in on the retail aisle (no transition; nothing moves before the narration, 86:10)
  86.45  영업팀 · 다음 달 수요는? - sales so far, the 오늘 marker, the forecast running on (dashed, +12.4%)
  88.25  line-particle cut to the production line: the inspection gate over the conveyor (kept), and
         생산팀 · 지금 이상 징후 있어? - the vibration signal, its spike boxed (이상 감지 · 14:20)
  91.9   match cut to the robot cell: 구매팀 · 새 도면, 자재 발주까지 돼? - the steps check themselves (AUTO);
  93.45  "설비와 로봇까지 연결하며": the card slides up to 설비팀 · 오래된 설비도 연결돼? (the machines, 연결됨)
         and a link runs to the robot gripper (로봇 셀 R-02 · 연결됨)
Frame f is timeline frame 2060 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_ops.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_axpoint as A
import seg_ask as K
from engine import (W, H, R, WHITE, NAVY_950, CYAN, BLUE, INK, STEEL, STEEL_200, lerp, prog, clamp, e_io_cubic, e_io_sine, e_out_cubic,
                    e_out_expo, paint_fill, paint_stroke, rrect, text, text_w, icon, poly, colint)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 85 * 24 + 20              # 00:01:25:20: seg_ask's last frame
NF = 95 * 24 + 19 - F_TL + 1     # through 00:01:35:19 (240 frames)
GRAIN0 = K.GRAIN0 + K.NF        # film-grain index of frame 0 (after seg_ask's last frame)
T0 = F_TL / 24.0
SCV = 1.0

ACC = "#58B8FF"                  # the cards' blue (the client's)
SUB = "#9FB0CC"
CARD_BG = "#0B1426"

# shots: (plate, scene start in the original film (its clock), length, draw_plate kwargs)
SHOTS = [("16_retail", 86.50, 2.20, dict(s=(1.04, 1.14), grade=S.GRADE_DAY, beats=[(0.5, 0.03)])),
         ("06_line", 88.70, 3.40, dict(s=(1.02, 1.08), x=(20, -20), grade=S.GRADE_COOL)),
         ("17_robot", 92.10, 3.75, dict(s=(1.05, 1.13), x=(-20, 20), grade=S.GRADE_COOL))]
CUTS = [(T0, 0.0, "cut", {}),                                     # (start, length, kind, kwargs): straight in
        (88.25, 0.90, "lines", {"angle": 10, "key": "t18"}),
        (91.90, 0.40, "match", {})]

# narration (film time)
L_SALES, L_PROD, L_AUTO, L_LINK = 86.58, 88.61, 91.87, 93.50


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- the card look
def chamfer(r, k):
    return poly([(r.left() + k, r.top()), (r.right() - k, r.top()), (r.right(), r.top() + k),
                 (r.right(), r.bottom() - k), (r.right() - k, r.bottom()), (r.left() + k, r.bottom()),
                 (r.left(), r.bottom() - k), (r.left(), r.top() + k)], True)


def shape(r, k):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(r, k, k))
    return p


def ncard(c, r, a, cut=22, glow=0.0, light=False):
    """The film's glass card, a little more opaque than before so it reads on the footage."""
    if a <= 0.003:
        return
    if light:
        E.glass(c, r, cut, a, tint=WHITE, tint_a=0.93, blur=26, border=0.9, shadow=0.34)
    else:
        E.glass(c, r, cut, a, tint="#0A1630", tint_a=0.78, blur=24, border=0.55, shadow=0.36, glow=glow, glow_col=CYAN)


def team_head(c, x, y, team, q, a, light=False):
    """The team chip and the question."""
    tw = text_w(team, 21, "Bold") + 32
    r = R(x, y - 22, tw, 42)
    rrect(c, r, 21, BLUE if light else ACC, a)
    text(c, team, r.centerX(), y + 7, 21, "Bold", WHITE if light else NAVY_950, a, "center")
    text(c, q, r.right() + 16, y + 9, 28, "SemiBold", INK if light else WHITE, a)


def diamond(c, x, y, r, col, a):
    A.diamond(c, x, y, r, col, a)


def card_in(t, t0):
    """(alpha, rise, blur) of a card's entrance."""
    k = e_io_sine(prog(t, t0, 0.6))
    return k, 30 * (1 - e_out_cubic(prog(t, t0, 0.8))), 10 * (1 - k)


# ---------------------------------------------------------------- 1 sales: demand forecast
def sales(c, t):
    k, dy, bl = card_in(t, 86.45)                      # after the silence (85:20-86:10): nothing moves before
    if k <= 0.003:
        return
    r = R(96, 186, 760, 430)
    A.blur_layer(c, bl, k)
    c.save()
    c.translate(0, dy)
    ncard(c, r, 1.0, light=True)
    team_head(c, r.left() + 44, r.top() + 64, "영업팀", "다음 달 수요는?", 1.0, True)
    gx, gy, gw, gh = r.left() + 44, r.top() + 150, r.width() - 88, 210
    c.drawLine(gx, gy + gh, gx + gw, gy + gh, paint_stroke(STEEL_200, 1.0, 1.4))
    hist = [0.18, 0.30, 0.25, 0.38, 0.48, 0.41, 0.56, 0.62]
    fut = [0.62, 0.70, 0.78, 0.74, 0.90]
    n = len(hist) + len(fut) - 2
    pts = [(gx + i * gw / n, gy + gh * (1 - v)) for i, v in enumerate(hist)]
    fp = [(gx + (len(hist) - 1 + i) * gw / n, gy + gh * (1 - v)) for i, v in enumerate(fut)]
    g1 = e_io_sine(prog(t, L_SALES + 0.35, 0.8))
    E.line(c, poly(pts), INK, 1.0, 3.0, (0, g1))
    # 오늘
    tk = e_io_sine(prog(t, L_SALES + 1.0, 0.3))
    ox = pts[-1][0]
    c.drawLine(ox, gy - 18, ox, gy + gh, paint_stroke(STEEL_200, tk, 1.6))
    text(c, "오늘", ox + 10, gy - 4, 19, "SemiBold", STEEL, tk)
    # the forecast: band + dashed line + diamond
    g2 = e_io_sine(prog(t, L_SALES + 1.1, 0.8))
    if g2 > 0:
        band = poly([(x, y - 10 - i * 5) for i, (x, y) in enumerate(fp)] +
                    [(x, y + 10 + i * 5) for i, (x, y) in reversed(list(enumerate(fp)))], True)
        c.save()
        c.clipRect(R(ox, gy - 60, (fp[-1][0] - ox) * g2 + 2, gh + 120))
        c.drawPath(band, paint_fill(CYAN, 0.22))
        c.restore()
        E.line(c, poly(fp), BLUE, 1.0, 3.2, (0, g2), dash=[12, 8])
    dk = e_out_expo(prog(t, L_SALES + 1.8, 0.35))
    if dk > 0:
        x, y = fp[-1]
        diamond(c, x, y, 14 * dk, BLUE, 1.0)
        text(c, "예측", x, y - 28, 20, "Bold", BLUE, dk, "right")
        cr = R(r.right() - 44 - 128, r.top() + 42, 128, 44)
        rrect(c, cr, 22, BLUE, dk)
        text(c, "+12.4%", cr.centerX(), cr.centerY() + 8, 22, "Bold", WHITE, dk, "center")
    c.restore()
    c.restore()


# ---------------------------------------------------------------- 2 production & quality: anomaly
GATE = S.SC18_GATE
SPIKE_T = L_PROD + 1.75


def signal(seed=18, n=96):
    rr = np.random.default_rng(seed)
    v = []
    for j in range(n):
        x = 0.42 + 0.10 * math.sin(j * 0.55) + 0.07 * math.sin(j * 1.7) + rr.uniform(-0.05, 0.05)
        if 68 <= j <= 75:
            x += 0.40 * math.sin((j - 68) / 7 * math.pi)
        v.append(x)
    return v


SIG = signal()


def production(c, t, cam):
    bad = t >= SPIKE_T
    # the inspection gate over the conveyor (the original graphic, stronger)
    k = e_io_sine(prog(t, L_PROD + 0.1, 0.5))
    if k > 0.003:
        r = cam.rect(*GATE)
        col = ACC if bad else WHITE
        E.corner_brackets(c, r, 34, col, k, 3.0)
        sp = ((t - L_PROD) * 0.9) % 1.0
        y = lerp(r.top(), r.bottom(), e_io_sine(sp))
        c.drawLine(r.left(), y, r.right(), y, paint_stroke(ACC, 0.5 * k, 10, blur=10, blend=skia.BlendMode.kScreen))
        c.drawLine(r.left(), y, r.right(), y, paint_stroke(WHITE, 0.95 * k, 1.6))
        lab = "이상 징후 감지 · 0.91" if bad else "품질 검사 중 · 정상 0.98"
        tw = text_w(lab, 20, "Bold") + 32
        lr = R(r.left(), r.top() - 54, tw, 42)
        c.drawPath(shape(lr, 12), paint_fill(ACC if bad else "#0A1630", 0.95 * k))
        text(c, lab, lr.left() + 16, lr.centerY() + 7, 20, "Bold", NAVY_950 if bad else WHITE, k)
        if bad:
            ph = ((t - SPIKE_T) % 1.1) / 1.1
            c.drawRect(r.makeOutset(14 * ph, 14 * ph), paint_stroke(ACC, (1 - ph) * 0.8, 2))
    # the signal card
    k, dy, bl = card_in(t, L_PROD + 0.45)
    if k <= 0.003:
        return
    r = R(1110, 470, 720, 420)
    A.blur_layer(c, bl, k)
    c.save()
    c.translate(0, dy)
    ncard(c, r, 1.0, glow=0.8 * e_io_sine(prog(t, SPIKE_T, 0.4)) * (1 - 0.5 * prog(t, SPIKE_T + 0.4, 1.0)))
    team_head(c, r.left() + 44, r.top() + 64, "생산팀", "지금 이상 징후 있어?", 1.0)
    gx, gy, gw, gh = r.left() + 44, r.top() + 150, r.width() - 88, 200
    n = len(SIG)
    pts = [(gx + j * gw / (n - 1), gy + gh * (1 - v)) for j, v in enumerate(SIG)]
    g = prog(t, L_PROD + 0.7, 1.4)
    E.line(c, poly(pts), WHITE, 1.0, 2.4, (0, g))
    bk = e_out_expo(prog(t, SPIKE_T, 0.35))
    if bk > 0:
        j = 71.5
        ax = gx + j / (n - 1) * gw
        br = R(ax - 46, gy - 22, 92, gh + 10)
        c.drawPath(shape(br, 10), paint_stroke(ACC, bk, 2.6))
        top = min(p[1] for p in pts[68:76])
        diamond(c, ax, top - 2, 13 * bk, ACC, 1.0)
        lab = "이상 감지 · 14:20"
        tw = text_w(lab, 21, "Bold") + 34
        lr = R(min(br.right() + 18, r.right() - 44 - tw), gy - 30, tw, 44)
        c.drawPath(shape(lr, 12), paint_fill(ACC, bk))
        text(c, lab, lr.centerX(), lr.centerY() + 8, 21, "Bold", NAVY_950, bk, "center")
    c.restore()
    c.restore()


# ---------------------------------------------------------------- 3 automation + equipment + robots
STEPS = ["도면 업로드", "BOM 자동 추출", "부족 자재 확인", "발주서 메일 발송"]
MACH = [("FANUC", "머시닝센터"), ("SG-PRM", "프레스 설비"), ("OCR 판독", "아날로그 계기"), ("실시간 통합", "PLC 라인")]
SLIDE0 = L_LINK - 0.05
CARD3 = R(96, 196, 720, 470)


def spaced(c, s, x, y, size, col, a, gap=2.0):
    for ch in s:
        w = text_w(ch, size, "SemiBold")
        text(c, ch, x, y, size, "SemiBold", col, a)
        x += w + gap
    return x


def checklist(c, t, r):
    team_head(c, r.left() + 44, r.top() + 64, "구매팀", "새 도면, 자재 발주까지 돼?", 1.0)
    for i, s in enumerate(STEPS):
        t0 = L_AUTO + 0.15 + i * 0.28
        k, dy, bl = A.blur_in(t, t0, 0.6)
        if k <= 0.003:
            continue
        y = r.top() + 160 + i * 74 + dy
        on = e_out_expo(prog(t, t0 + 0.3, 0.3))
        b = R(r.left() + 44, y - 22, 42, 42)
        c.drawPath(shape(b, 8), paint_fill(ACC if on > 0.5 else CARD_BG, k))
        c.drawPath(shape(b, 8), paint_stroke(ACC, k, 1.8))
        if on > 0:
            icon(c, "check", b.centerX(), b.centerY(), 24, NAVY_950, k * on, 3.2)
        text(c, s, b.right() + 22, y + 11, 30, "SemiBold", WHITE, k)
        x1 = r.right() - 44 - 74
        p = paint_stroke("#3A4E80", k, 1.4)
        p.setPathEffect(skia.DashPathEffect.Make([2, 7], 0))
        x0 = b.right() + 40 + text_w(s, 30, "SemiBold")
        c.drawLine(x0, y, x1 - 16, y, p)
        spaced(c, "AUTO", x1, y + 8, 20, ACC, k * on, 4)
    if t > L_AUTO + 1.2:
        j = clamp((t - L_AUTO - 0.45) / 0.28, 0, len(STEPS) - 1)
        diamond(c, r.left() + 26, r.top() + 160 + int(j) * 74, 9, ACC, 1.0)


def machines(c, t, r):
    team_head(c, r.left() + 44, r.top() + 64, "설비팀", "오래된 설비도 연결돼?", 1.0)
    tw, th, gap = (r.width() - 88 - 20) / 2, 126, 20
    for i, (tag, name) in enumerate(MACH):
        t0 = SLIDE0 + 0.25 + i * 0.16
        k, dy, bl = A.blur_in(t, t0, 0.6)
        if k <= 0.003:
            continue
        x = r.left() + 44 + (i % 2) * (tw + gap)
        y = r.top() + 124 + (i // 2) * (th + gap) + dy
        tr = R(x, y, tw, th)
        c.drawPath(shape(tr, 16), paint_fill("#0E1D3C", 0.9 * k))
        c.drawPath(shape(tr, 16), paint_stroke("#5C78B8", 0.9 * k, 1.4))
        spaced(c, tag, tr.left() + 22, tr.top() + 36, 16, SUB, k, 2.5)
        text(c, name, tr.left() + 22, tr.top() + 76, 28, "Bold", WHITE, k)
        on = e_out_expo(prog(t, t0 + 0.35, 0.3))
        cr = R(tr.right() - 22 - 96, tr.bottom() - 22 - 36, 96, 36)
        c.drawPath(shape(cr, 18), paint_fill(ACC, k * on))
        text(c, "연결됨", cr.centerX(), cr.centerY() + 7, 18, "Bold", NAVY_950, k * on, "center")
        if i == 3:
            diamond(c, tr.right() - 26, tr.top() + 30, 10, ACC, k * on)


def robots(c, t, cam):
    k, dy, bl = card_in(t, L_AUTO + 0.0)
    if k > 0.003:
        r = CARD3
        A.blur_layer(c, bl, k)
        c.save()
        c.translate(0, dy)
        ncard(c, r, 1.0)
        sl = e_io_cubic(prog(t, SLIDE0, 0.55))                  # vertical slide to the equipment
        c.save()
        c.clipPath(shape(r.makeInset(3, 3), 24), True)
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
            machines(c, t, r)
            c.restore()
            c.restore()
        c.restore()
        c.restore()
        c.restore()
    # ... and the robot cell
    gp = cam.point("grip")
    gx, gy = gp if gp else cam.map(*S.SC19_GRIP)
    g = e_io_cubic(prog(t, L_LINK + 0.55, 0.8))
    if g > 0:
        p0 = (CARD3.right(), CARD3.centerY() + 40)
        pth = E.curve(p0, (gx - 74, gy), 0.4)
        E.line(c, pth, ACC, 0.95, 2.4, (0, g), glow=0.9)
        if t > L_LINK + 1.3:
            E.pulse(c, pth, ((t - L_LINK - 1.3) * 0.8) % 1.0, WHITE, 0.9, 14)
        rk = e_io_sine(prog(t, L_LINK + 1.1, 0.5))
        c.save()
        c.translate(gx, gy)
        c.rotate(t * 30)
        for j in range(4):
            c.drawArc(R(-74, -74, 148, 148), j * 90 + 10, 60, False, paint_stroke(ACC, rk, 2.6))
        c.restore()
        c.drawCircle(gx, gy, 50, paint_stroke(WHITE, rk * 0.7, 1.4))
        lab = "로봇 셀 R-02 · 연결됨"
        tw = text_w(lab, 20, "Bold") + 60
        lr = R(min(gx + 90, W - 60 - tw), gy - 108, tw, 44)
        c.drawPath(shape(lr, 12), paint_fill("#0A1630", 0.88 * rk))
        c.drawPath(shape(lr, 12), paint_stroke("#5C78B8", 0.9 * rk, 1.4))
        icon(c, "robot", lr.left() + 26, lr.centerY(), 20, ACC, rk)
        text(c, lab, lr.left() + 46, lr.centerY() + 7, 20, "Bold", WHITE, rk)


# ---------------------------------------------------------------- shots and cuts
def shot(c, i, t):
    plate, s0, d, kw = SHOTS[i]
    cam = E.draw_plate(c, plate, t - s0, d, **kw)
    if i == 0:
        sales(c, t)
    elif i == 1:
        production(c, t, cam)
    else:
        robots(c, t, cam)


def render(c, t):
    for i, (c0, cd, kind, kw) in enumerate(CUTS):
        if c0 <= t < c0 + cd:
            p = (t - c0) / cd
            a_img = A.snap(30, lambda cc: shot(cc, i - 1, t))
            b_img = A.snap(31, lambda cc: shot(cc, i, t))
            E.TRANSITIONS[kind](c, a_img, b_img, p, **kw)
            return
    i = max(j for j, cut in enumerate(CUTS) if t >= cut[0])
    shot(c, i, t)


def frame(f, surf, finish):
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    c.save()
    c.scale(SCV, SCV)
    render(c, ft(f))
    c.restore()
    fr = finish.apply(surf, GRAIN0 + f)
    bar = int(round(BAR * SCV))
    fr[:bar] = 0
    fr[-bar:] = 0
    return np.ascontiguousarray(fr)


def setup(height):
    global SCV
    import media
    media.MAX_READERS = 14 if height > 1080 else 6
    out = K.setup(height)
    SCV = A.SCV
    return out


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
