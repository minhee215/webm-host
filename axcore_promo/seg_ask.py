"""Segment 00:01:14:10-00:01:25:20 (275 frames) - "이제 여러 시스템과 문서를 오갈 필요가 없습니다. / 질문 하나면 AI가
관련 데이터를 찾아 / 현재 상황과 원인, 업무의 맥락까지 제시합니다."

Frontal composition after the client's reference video (a prompt bar in the dark, the question flies to the top,
the answer comes in under sweeping light bars); the look is the film's navy glass.
  74.42  continues the ontology segment's last frame; the ontology falls back out of focus while the company's
         scattered systems float up around (ERP, MES, 메일, 엑셀, 드라이브 ...); a highlight hops from window to
         window ("오갈 필요가")
  76.42  "없습니다": the windows rush into the middle and become one AXCORE AI search card (무엇이든 물어보세요)
  78.05  "질문 하나면": the question is typed (gradient text) and sent; the input flies to the top as the question
  79.25  "AI가 관련 데이터를 찾아": 추론 과정 on the left, its steps run one by one with their times; the answer card
         on the right is preparing
  80.97  "현재 상황과 원인": the answer sweeps in under a light bar (원자재 로트 / 1.2% -> 3.4%), the defect rate chart
         draws with the lot change on 9/14
  82.43  "업무의 맥락까지": the sources come in (MES, 작업일지 3건, 입고 검사); the left card slides up to 다음 액션,
         the actions are checked and run (실행 완료)
Frame f is timeline frame 1786 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_ask.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import seg_axpoint as A
import seg_onto as G
from engine import (W, H, R, WHITE, NAVY_950, NAVY_900, NAVY_800, CYAN, lerp, prog, clamp, e_io_cubic, e_io_sine,
                    e_out_cubic, e_out_expo, e_in_cubic, paint_fill, paint_stroke, rrect, rrect_stroke, text, text_w,
                    icon, poly, colint)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 74 * 24 + 10              # 00:01:14:10: the ontology segment's last frame
NF = 85 * 24 + 20 - F_TL + 1     # through 00:01:25:20 (275 frames)
GRAIN0 = G.GRAIN0 + G.NF - 1     # film-grain index of frame 0, as the ontology file's last frame
T0 = F_TL / 24.0
SCV = 1.0

BG = "#050B1C"
HL = "#58B8FF"                   # highlighted words / numbers
LINE_W = "#E9F0FF"
SUB = "#8FA6C8"
BORDER = "#3E6BFF"
GRAD = ["#4FC3FF", "#5B7CFF", "#9B6BFF"]      # the light bars and the gradient text (cyan -> blue -> violet)

# beats (film time)
OUT0 = 74.45                      # the ontology falls back
WIN0 = 74.70                      # the systems float up
HOP0, HOP_DT = 75.45, 0.22        # a highlight hops between them
MERGE0 = 76.42                    # they rush into the middle
CARD0 = 76.92                     # the AXCORE AI search card
TYPE0, TYPE_D = 78.05, 0.75       # "질문 하나면": the question is typed
ENTER = 78.92
FLY0, FLY_D = 79.02, 0.55         # the input flies to the top
PANES0 = 79.22                    # 추론 과정 / AXCORE AI cards
STEP0 = 79.40                     # the reasoning steps (their own times scaled down)
STEP_K = 0.45
ANS0 = 80.97                      # "현재 상황과 원인": the answer
CHART0 = 81.55
LOT_T = 82.05
SRC0 = 82.45                      # "업무의 맥락까지": the sources
ACT0 = 83.30                      # the left card slides up to 다음 액션
RUN_T = 84.85                     # 실행 click

Q = "지난달 3라인 불량, 왜 늘었지?"
STEPS = [("질문 해석", "기간 9월 · 대상 3라인 불량률", 0.4), ("MES 공정 데이터 조회", "3라인 · 9월 1일 – 30일", 1.2),
         ("작업일지 3건 대조", "OCR 문서 · 9/14 · 9/16 · 9/21", 0.8), ("입고 검사 기록 확인", "LOT A-2207 · 9월 14일 입고", 0.6)]
ANS = [[("9월 14일 ", None), ("원자재 로트", HL), ("가 바뀐 뒤부터", None)],
       [("3라인 불량률이 ", None), ("1.2% → 3.4%", HL), ("로 늘었습니다.", None)]]
SOURCES = ["MES · 3라인 공정", "작업일지 3건", "입고 검사 · A-2207"]
ACTIONS = [("LOT A-2207 입고 검사 강화", "품질팀"), ("건조 온도 기준 재설정 ±2°C", "생산팀")]
APPS = [("ERP", "db", 330, 300, 1.10), ("MES", "factory", 780, 280, 0.85), ("메일", "mail", 1260, 300, 1.0),
        ("엑셀", "bars", 1620, 410, 0.9), ("드라이브", "drive", 250, 640, 0.9), ("메신저", "chat", 660, 760, 1.15),
        ("PDF", "doc", 1090, 700, 0.95), ("보고서", "report", 1540, 760, 1.05), ("CRM", "user", 1010, 480, 0.8),
        ("일정", "calendar", 520, 500, 0.8)]
HOPS = [0, 2, 6, 3, 5, 1]

# (client re-edit, seg_ask2.py) one hop fewer and slower; the systems are not swept away into the search card:
# they shrink a little, go soft and stay behind it as its background until the answer cards come in
V2 = False
V2_HOP0, V2_HOP_DT, V2_HOPS = 75.25, 0.28, [0, 2, 6, 3, 5]
V2_SHRINK, V2_BLUR, V2_DIM = 0.86, 4.5, 0.55      # the systems behind the search card
V2_OUT0, V2_OUT_D = 79.10, 0.70                   # and their fade as the answer cards come in

SEARCH = R(530, 370, 860, 300)
PILL0 = R(574, 470, 772, 92)
QPILL = R(560, 168, 800, 72)
LEFT = R(150, 288, 720, 610)
RIGHT = R(900, 288, 870, 610)


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- helpers
def grad_shader(x0, x1, a=1.0, cols=GRAD):
    return skia.GradientShader.MakeLinear([skia.Point(x0, 0), skia.Point(x1, 0)], [colint(k, a) for k in cols])


def gtext(c, s, x, y, size, w, a, cols=GRAD):
    """Gradient text (the reference's thinking / typing look)."""
    if a <= 0.003 or not s:
        return 0
    f = E.font(size, w)
    tw = f.measureText(s)
    p = skia.Paint(AntiAlias=True, Shader=grad_shader(x, x + max(tw, 1), a, cols))
    c.drawString(s, x, y, f, p)
    return tw


def parts_w(parts, size, w):
    return sum(text_w(s, size, w) for s, _ in parts)


def parts_text(c, parts, x, y, size, w, a):
    for s, col in parts:
        x += text(c, s, x, y, size, w, col or LINE_W, a)


def sweep(c, x0, y, h, rx, a, length=300):
    """The reference's light bar: a gradient streak whose head is at rx."""
    if a <= 0.003:
        return
    x1 = rx
    xs = max(x0, x1 - length)
    if x1 - xs < 2:
        return
    r = R(xs, y - h / 2, x1 - xs, h)
    sh = skia.GradientShader.MakeLinear([skia.Point(xs, 0), skia.Point(x1, 0)],
                                        [colint(GRAD[0], 0.0), colint(GRAD[0], 0.55 * a), colint(GRAD[1], 0.8 * a),
                                         colint(GRAD[2], 0.95 * a)], [0.0, 0.35, 0.7, 1.0])
    p = skia.Paint(AntiAlias=True, Shader=sh, BlendMode=skia.BlendMode.kScreen)
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 6))
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOutset(0, 4), h / 2, h / 2), p)
    p2 = skia.Paint(AntiAlias=True, Shader=sh, BlendMode=skia.BlendMode.kScreen)
    c.drawRRect(skia.RRect.MakeRectXY(r, h / 2, h / 2), p2)
    c.drawCircle(x1, y, h * 0.55, paint_fill(WHITE, 0.6 * a, blur=4, blend=skia.BlendMode.kScreen))


def reveal_line(c, parts, x, y, size, w, t, t0, d):
    """A line revealed left to right under the light bar."""
    tw = parts_w(parts, size, w)
    q = e_io_sine(prog(t, t0, d))
    if q <= 0:
        return
    rx = x + (tw + 40) * q
    c.save()
    c.clipRect(R(x - 4, y - size * 1.2, rx - x + 4, size * 1.7))
    parts_text(c, parts, x, y, size, w, 1.0)
    c.restore()
    sweep(c, x, y - size * 0.32, size * 0.42, rx, 1 - e_in_cubic(prog(t, t0 + d * 0.75, d * 0.4)))


def card(c, r, a, glow=0.5, grad_border=False, radius=26):
    if a <= 0.003:
        return
    E.glass(c, r, radius, a, tint=NAVY_900, tint_a=0.74, blur=26, border=0.0, shadow=0.4, highlight=0.05)
    rr = skia.RRect.MakeRectXY(r, radius, radius)
    if grad_border:
        sh = skia.GradientShader.MakeLinear([skia.Point(r.left(), r.top()), skia.Point(r.right(), r.bottom())],
                                            [colint(GRAD[0], a), colint(GRAD[1], a), colint(GRAD[2], a)])
        p = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=1.8)
        c.drawRRect(rr, p)
        p.setStrokeWidth(8)
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        p.setAlphaf(0.5 * glow)
        c.drawRRect(rr, p)
    else:
        c.drawRRect(rr, paint_stroke(BORDER, a * 0.55, 1.4))
        c.drawRRect(rr, paint_stroke(BORDER, a * 0.5 * glow, 8, blur=12, blend=skia.BlendMode.kScreen))


def diamond(c, x, y, r, col, a):
    A.diamond(c, x, y, r, col, a)


def layer(c, a, blur=0.0, dy=0.0, s=1.0, cx=W / 2, cy=H / 2):
    c.save()
    c.translate(cx, cy + dy)
    c.scale(s, s)
    c.translate(-cx, -cy)
    A.blur_layer(c, blur, a)


def unlayer(c):
    c.restore()
    c.restore()


# ---------------------------------------------------------------- background
def background(c, t):
    c.drawRect(R(0, 0, W, H), paint_fill(BG, 1.0))
    E.radial(c, W * 0.78, H * 0.92, 900, "#0E6E86", 0.30)
    E.radial(c, W * 0.18, H * 0.30, 900, "#1B3A8F", 0.30)
    E.radial(c, W / 2, H / 2, 700, "#1A2E6E", 0.20 + 0.10 * e_io_sine(prog(t, CARD0, 0.8)))


# ---------------------------------------------------------------- 1 systems -> one search card
def app_window(c, i, x, y, s, a, hi, blur):
    name, ic, _, _, z = APPS[i]
    w, h = 300, 190
    layer(c, a, blur, 0, s, x, y)
    r = R(x - w / 2, y - h / 2, w, h)
    E.glass(c, r, 16, 1.0, tint=NAVY_800, tint_a=0.72, blur=16, border=0.35, shadow=0.3, highlight=0.06,
            glow=hi, glow_col=CYAN)
    c.drawLine(r.left(), r.top() + 40, r.right(), r.top() + 40, paint_stroke("#2B3F7A", 1.0, 1.0))
    for k in range(3):
        c.drawCircle(r.left() + 20 + k * 14, r.top() + 20, 4, paint_fill("#5C6E9A", 1.0))
    icon(c, ic, r.left() + 82, r.top() + 20, 18, "#8FB4FF", 1.0)
    text(c, name, r.left() + 100, r.top() + 27, 17, "SemiBold", WHITE, 1.0)
    rr = np.random.default_rng(40 + i)
    yy = r.top() + 62
    while yy < r.bottom() - 18:
        ww = rr.uniform(0.35, 0.9) * (w - 40)
        rrect(c, R(r.left() + 20, yy, ww, 7), 3.5, "#3A4E80", 0.9)
        yy += 20
    unlayer(c)


def app_state(i, t):
    name, ic, x0, y0, z = APPS[i]
    t0 = WIN0 + 0.07 * i
    k = e_io_sine(prog(t, t0, 0.6))
    drift = (t - WIN0) * 14 * (1.2 - z)
    x = x0 + drift * (1 if x0 < W / 2 else -1)
    y = y0 - 22 * (1 - e_out_cubic(prog(t, t0, 0.9)))
    s = z * lerp(1.12, 1.0, e_out_cubic(prog(t, t0, 0.9)))
    blur = 12 * (1 - k) + 5 * max(0.0, 1.0 - z)
    if V2:
        m2 = e_io_cubic(prog(t, MERGE0, 0.75))
        sc = lerp(1.0, V2_SHRINK, m2)
        x, y, s = W / 2 + (x - W / 2) * sc, H / 2 + (y - H / 2) * sc, s * sc
        blur += V2_BLUR * m2
        return x, y, s, k * lerp(1.0, V2_DIM, m2) * (1 - e_io_sine(prog(t, V2_OUT0, V2_OUT_D))), blur
    m = e_in_cubic(prog(t, MERGE0 + 0.015 * ((i * 3) % len(APPS)), 0.40))
    if m > 0:
        x, y = lerp(x, W / 2, m), lerp(y, H / 2, m)
        s *= lerp(1.0, 0.12, m)
        blur += 10 * m
    a = k * (1 - e_in_cubic(clamp((m - 0.55) / 0.45)))
    return x, y, s, a, blur


def systems(c, t):
    if t > (V2_OUT0 + V2_OUT_D if V2 else MERGE0 + 0.75):
        return
    HOP0, HOP_DT, HOPS = (V2_HOP0, V2_HOP_DT, V2_HOPS) if V2 else (globals()["HOP0"], globals()["HOP_DT"],
                                                                     globals()["HOPS"])
    st = [app_state(i, t) for i in range(len(APPS))]
    # the hops: a dashed trail between the windows the highlight visits
    hi = [0.0] * len(APPS)
    m = e_io_sine(prog(t, MERGE0, 0.2))
    for j in range(len(HOPS) - 1):
        ta = HOP0 + j * HOP_DT
        g = e_io_cubic(prog(t, ta, HOP_DT * 0.8))
        if g <= 0:
            continue
        a_, b_ = st[HOPS[j]], st[HOPS[j + 1]]
        p = paint_stroke(CYAN, 0.55 * (1 - m), 1.6)
        p.setPathEffect(skia.DashPathEffect.Make([6, 8], 0))
        pth = poly([(a_[0], a_[1]), (lerp(a_[0], b_[0], g), lerp(a_[1], b_[1], g))])
        c.drawPath(pth, p)
    for j, i in enumerate(HOPS):
        ta = HOP0 + (j - 1) * HOP_DT + HOP_DT * 0.8 if j else HOP0
        hi[i] = max(hi[i], math.sin(math.pi * clamp(prog(t, ta, 0.45))))
    for i in sorted(range(len(APPS)), key=lambda k_: APPS[k_][4]):
        x, y, s, a, blur = st[i]
        if a > 0.003:
            app_window(c, i, x, y, s, a, 0.9 * hi[i] * (1 - m), blur)
    # the cursor hopping with the highlight
    if HOP0 - 0.1 < t < MERGE0 + 0.1:
        j = clamp((t - HOP0) / HOP_DT, 0, len(HOPS) - 1)
        j0 = int(j)
        j1 = min(j0 + 1, len(HOPS) - 1)
        q = e_io_cubic(j - j0)
        p0, p1 = st[HOPS[j0]], st[HOPS[j1]]
        A.cursor(c, lerp(p0[0], p1[0], q) + 40, lerp(p0[1], p1[1], q) + 20,
                 clamp(prog(t, HOP0 - 0.1, 0.12)) * (1 - m))
    # the rush: a flash where they meet
    fl = 0.0 if V2 else math.sin(math.pi * clamp(prog(t, MERGE0 + 0.25, 0.5)))
    if fl > 0:
        E.radial(c, W / 2, H / 2, 420, "#7FB2FF", 0.5 * fl)


def search_card(c, t):
    k = e_out_cubic(prog(t, CARD0, 0.6))
    if k <= 0.003:
        return
    fly = e_io_cubic(prog(t, FLY0, FLY_D))
    body = 1 - e_io_sine(prog(t, FLY0, 0.3))
    s = lerp(0.82, 1.0, k) * lerp(1.0, 0.94, fly)
    if body > 0.003:
        layer(c, clamp(k * 1.4) * body, 10 * (1 - k), 0, s)
        card(c, SEARCH, 1.0, 0.6 + 0.4 * math.sin(math.pi * clamp(prog(t, CARD0, 1.0))))
        icon(c, "spark", SEARCH.left() + 58, SEARCH.top() + 58, 26, "#5BA8FF", 1.0)
        text(c, "AXCORE AI", SEARCH.left() + 84, SEARCH.top() + 67, 24, "Bold", WHITE, 1.0)
        unlayer(c)
    # the input: types, then flies to the top as the question
    pr = R(lerp(PILL0.left(), QPILL.left(), fly), lerp(PILL0.top(), QPILL.top(), fly),
           lerp(PILL0.width(), QPILL.width(), fly), lerp(PILL0.height(), QPILL.height(), fly))
    if fly <= 0:
        pr = R(W / 2 + (pr.left() - W / 2) * s, H / 2 + (pr.top() - H / 2) * s, pr.width() * s, pr.height() * s)
    a = clamp(k * 1.4)
    rad = pr.height() / 2
    E.glass(c, pr, rad, a, tint=NAVY_950, tint_a=0.8, blur=12, border=0.0, shadow=0.3 * fly, highlight=0.04)
    hot = math.sin(math.pi * clamp(prog(t, ENTER - 0.05, 0.5)))
    c.drawRRect(skia.RRect.MakeRectXY(pr, rad, rad), paint_stroke(BORDER, a * (0.8 + 0.2 * hot), 1.6))
    c.drawRRect(skia.RRect.MakeRectXY(pr, rad, rad), paint_stroke(BORDER, a * (0.25 + 0.6 * hot), 8, blur=10,
                                                                   blend=skia.BlendMode.kScreen))
    size = lerp(26, 24, fly)
    ix = pr.left() + lerp(44, 34, fly)
    if fly < 0.5:
        icon(c, "search", ix, pr.centerY(), 24, "#B9CCFF", a * (1 - 2 * fly))
    else:
        c.drawCircle(ix, pr.centerY(), 17, paint_fill("#2A55E8", a * (2 * fly - 1)))
        icon(c, "user", ix, pr.centerY(), 18, WHITE, a * (2 * fly - 1))
    tx = pr.left() + lerp(82, 66, fly)
    ty = pr.centerY() + size * 0.36
    n = int(round(len(Q) * clamp(prog(t, TYPE0, TYPE_D))))
    if n == 0:
        text(c, "무엇이든 물어보세요", tx, ty, size, "Medium", "#8EA0C8", a)
    elif fly < 1:
        gtext(c, Q[:n], tx, ty, size, "Medium", a)                    # typed in the gradient
    if fly > 0:
        text(c, Q, tx, ty, size, "Medium", WHITE, a * fly)
    if n < len(Q) and int(t * 2.2) % 2 == 0 and t > CARD0 + 0.4:
        cx_ = tx + text_w(Q[:n], size, "Medium") + 3
        c.drawLine(cx_, pr.centerY() - 15, cx_, pr.centerY() + 15, paint_stroke(WHITE, a, 2))
    if fly < 0.5:                                                    # ENTER key
        ea = a * (1 - 2 * fly) * clamp(prog(t, TYPE0 + 0.2, 0.3))
        er = R(pr.right() - 128, pr.centerY() - 20, 100, 40)
        rrect(c, er, 12, "#2A55E8" if hot > 0.2 else NAVY_800, ea)
        rrect_stroke(c, er, 12, "#5B7CFF", ea, 1.2)
        text(c, "ENTER ↵", er.centerX(), er.centerY() + 6, 15, "SemiBold", WHITE, ea, "center")
        A.ripple(c, er.centerX(), er.centerY(), t, ENTER, "#7FB2FF", 70)


# ---------------------------------------------------------------- 2 the reasoning (left)
def step_time(i):
    return STEP0 + STEP_K * sum(d for _, _, d in STEPS[:i])


STEPS_END = step_time(len(STEPS))


def reasoning(c, t, r):
    text(c, "추론 과정", r.left() + 52, r.top() + 72, 27, "Bold", WHITE, 1.0)
    tot = clamp((t - STEP0) / (STEPS_END - STEP0)) * sum(d for _, _, d in STEPS)
    if t > STEP0:
        text(c, "%.1fs" % tot, r.right() - 52, r.top() + 70, 21, "Medium", "#B9CCFF", 1.0, "right")
    ys = [r.top() + 160 + i * 112 for i in range(len(STEPS))]
    x = r.left() + 68
    # the connector grows as the steps run
    g = clamp((t - STEP0) / (STEPS_END - STEP0))
    if g > 0:
        c.drawLine(x, ys[0], x, lerp(ys[0], ys[-1], g), paint_stroke("#3A5596", 1.0, 2))
    for i, (title, sub, d) in enumerate(STEPS):
        t0 = step_time(i)
        t1 = step_time(i + 1)
        k, dy, bl = A.blur_in(t, t0 - 0.05, 0.6)
        if k <= 0.003:
            continue
        y = ys[i] + dy
        done = t >= t1
        act = t0 <= t < t1
        diamond(c, x, y, 13, HL if done else "#5B7CFF", k)
        if act:
            ph = (t * 1.6) % 1.0
            c.drawCircle(x, y, 16 + 14 * ph, paint_stroke("#7FB2FF", k * (1 - ph), 1.6))
            gtext(c, title, x + 40, y + 10, 29, "SemiBold", k)
        else:
            text(c, title, x + 40, y + 10, 29, "SemiBold", WHITE, k)
        text(c, sub, x + 40, y + 48, 19, "Regular", SUB, k)
        if done:
            text(c, "%.1fs" % d, r.right() - 52, y + 8, 21, "Medium", "#B9CCFF", k * e_io_sine(prog(t, t1, 0.3)),
                 "right")


def actions(c, t, r):
    text(c, "다음 액션", r.left() + 52, r.top() + 72, 27, "Bold", WHITE, 1.0)
    for i, (lab, team) in enumerate(ACTIONS):
        t0 = ACT0 + 0.3 + i * 0.22
        k, dy, bl = A.blur_in(t, t0, 0.6)
        if k <= 0.003:
            continue
        y = r.top() + 160 + i * 96 + dy
        on = e_out_expo(prog(t, t0 + 0.25, 0.3))
        b = R(r.left() + 52, y - 21, 38, 38)
        rrect(c, b, 9, HL if on > 0.5 else NAVY_800, k)
        rrect_stroke(c, b, 9, HL, k, 1.6)
        if on > 0:
            icon(c, "check", b.centerX(), b.centerY(), 22, NAVY_950, k * on, 3.0)
        text(c, lab, b.right() + 22, y + 10, 27, "Medium", WHITE, k)
        text(c, team, r.right() - 52, y + 8, 19, "Medium", SUB, k, "right")
    k = e_io_sine(prog(t, ACT0 + 0.7, 0.4))
    c.drawLine(r.left() + 52, r.top() + 340, r.right() - 52, r.top() + 340, paint_stroke("#2B3F7A", k, 1.4))
    k, dy, bl = A.blur_in(t, ACT0 + 0.8, 0.6)
    if k > 0.003:
        diamond(c, r.left() + 62, r.top() + 400 + dy, 11, HL, k)
        text(c, "바로 실행할까요?", r.left() + 86, r.top() + 411 + dy, 29, "Bold", WHITE, k)
    k, dy, bl = A.blur_in(t, ACT0 + 1.0, 0.6)
    if k > 0.003:
        done = e_out_expo(prog(t, RUN_T + 0.08, 0.3))
        press = math.sin(math.pi * clamp(prog(t, RUN_T, 0.18)))
        b = R(r.left() + 52, r.top() + 450 + dy, 250, 72).makeInset(6 * press, 3 * press)
        rrect(c, b, 16, HL if done > 0.5 else "#2A55E8", k)
        rrect_stroke(c, b, 16, "#7FC8FF", k * 0.8, 1.4)
        lab = "실행 완료" if done > 0.5 else "실행"
        text(c, lab, b.centerX() - (14 if done > 0.5 else 0), b.centerY() + 10, 28, "Bold",
             NAVY_950 if done > 0.5 else WHITE, k, "center")
        if done > 0.5:
            icon(c, "check", b.centerX() + 62, b.centerY(), 22, NAVY_950, k * done, 3.0)
        A.ripple(c, b.centerX(), b.centerY(), t, RUN_T, "#9FD8FF", 90)
        text(c, "품질팀 · 생산팀에 작업 지시를 보냈습니다.", r.left() + 52, r.bottom() - 52, 20, "Medium", SUB,
             k * e_io_sine(prog(t, RUN_T + 0.25, 0.4)))
        # the cursor comes in and clicks
        ca = clamp(prog(t, RUN_T - 0.5, 0.15)) * (1 - clamp(prog(t, RUN_T + 0.6, 0.25)))
        m = e_io_cubic(prog(t, RUN_T - 0.5, 0.45))
        A.cursor(c, lerp(b.right() + 160, b.centerX() + 30, m), lerp(b.bottom() + 120, b.centerY() + 6, m), ca,
                 press)


def left_card(c, t):
    k, dy, bl = A.blur_in(t, PANES0, 0.6)
    if k <= 0.003:
        return
    r = LEFT.makeOffset(0, 24 * (1 - e_out_cubic(prog(t, PANES0, 0.8))))
    layer(c, k, bl, 0)
    card(c, r, 1.0, 0.5)
    sl = e_io_cubic(prog(t, ACT0, 0.6))              # vertical slide: 추론 과정 up and out, 다음 액션 in
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(r, 26, 26), True)
    if sl < 1:
        c.save()
        c.translate(0, -160 * sl)
        A.blur_layer(c, 8 * sl, 1 - sl)
        reasoning(c, t, r)
        c.restore()
        c.restore()
    if sl > 0:
        c.save()
        c.translate(0, 160 * (1 - sl))
        A.blur_layer(c, 8 * (1 - sl), sl)
        actions(c, t, r)
        c.restore()
        c.restore()
    c.restore()
    unlayer(c)


# ---------------------------------------------------------------- 3 the answer (right)
def chart(c, t, r):
    days = np.arange(1, 31)
    rr = np.random.default_rng(9)
    v = np.where(days < 14, 1.2 + rr.normal(0, 0.06, 30), 3.4 + rr.normal(0, 0.07, 30))
    v[12] = 1.15
    x0, x1 = r.left(), r.right()
    yb, yt = r.bottom() - 40, r.top() + 30

    def px(d):
        return x0 + (d - 1) / 29 * (x1 - x0)

    def py(val):
        return lerp(yb, yt, (val - 0.6) / 3.2)
    k = e_io_sine(prog(t, CHART0 - 0.2, 0.4))
    c.drawLine(x0, yb, x1, yb, paint_stroke("#2B3F7A", k, 1.4))
    for gv in (1.2, 3.4):
        p = paint_stroke("#2B3F7A", 0.8 * k, 1.0)
        p.setPathEffect(skia.DashPathEffect.Make([3, 6], 0))
        c.drawLine(x0, py(gv), x1, py(gv), p)
    for d, lab, al in ((1, "9/1", "left"), (14, "9/14", "center"), (30, "9/30", "right")):
        text(c, lab, px(d), yb + 30, 17, "Medium", SUB, k, al)
    g = e_io_sine(prog(t, CHART0, 1.0))
    if g <= 0:
        return
    pts = [(px(d), py(val)) for d, val in zip(days, v)]
    upto = 1 + g * 29
    pre = [p for d, p in zip(days, pts) if d <= min(upto, 13)]
    post = [p for d, p in zip(days, pts) if 13 <= d <= upto]
    if len(pre) > 1:
        line_p = paint_stroke(WHITE, 1.0, 2.6)
        c.drawPath(poly(pre), line_p)
    if len(post) > 1:
        c.drawPath(poly(post), paint_stroke(HL, 0.5, 8, blur=8, blend=skia.BlendMode.kScreen))
        c.drawPath(poly(post), paint_stroke(HL, 1.0, 2.8))
    text(c, "1.2%", x0, py(1.2) - 16, 19, "SemiBold", "#C9D6EA", e_io_sine(prog(t, CHART0 + 0.1, 0.3)))
    text(c, "3.4%", x1, py(3.4) - 20, 19, "SemiBold", HL, e_io_sine(prog(t, CHART0 + 0.9, 0.3)), "right")
    # the lot change on 9/14
    lk = e_io_sine(prog(t, LOT_T, 0.35))
    if lk > 0:
        lx = px(14)
        p = paint_stroke(HL, lk, 1.6)
        p.setPathEffect(skia.DashPathEffect.Make([5, 5], 0))
        c.drawLine(lx, yt - 10, lx, yb, p)
        diamond(c, lx, py(v[13]), 13 * lk, HL, lk)
        ph = prog(t, LOT_T, 0.9)
        if 0 < ph < 1:
            c.drawCircle(lx, py(v[13]), 14 + 36 * e_out_cubic(ph), paint_stroke(HL, 0.7 * (1 - ph), 1.8))
        text(c, "LOT 변경 · 9/14", lx + 14, yt + 2, 19, "SemiBold", HL, lk)


def answer(c, t):
    k, dy, bl = A.blur_in(t, PANES0 + 0.12, 0.6)
    if k <= 0.003:
        return
    r = RIGHT.makeOffset(0, 24 * (1 - e_out_cubic(prog(t, PANES0 + 0.12, 0.8))))
    layer(c, k, bl, 0)
    card(c, r, 1.0, 0.4 + 0.6 * e_io_sine(prog(t, ANS0, 0.6)), True)
    x = r.left() + 56
    diamond(c, x + 8, r.top() + 64, 11, HL, 1.0)
    text(c, "AXCORE AI", x + 32, r.top() + 73, 23, "Bold", WHITE, 1.0)
    # preparing: the reference's gradient "thinking" line
    if t < ANS0 + 0.1:
        pa = 1 - e_io_sine(prog(t, ANS0 - 0.15, 0.25))
        dots = "." * (1 + int(t * 3) % 3)
        ph = (t * 0.8) % 1.0
        sh_cols = [GRAD[0], GRAD[2], GRAD[0]]
        f = E.font(30, "SemiBold")
        s = "관련 데이터를 찾는 중" + dots
        tw = f.measureText(s)
        sh = skia.GradientShader.MakeLinear([skia.Point(x - tw + 2 * tw * ph, 0), skia.Point(x + 2 * tw * ph, 0)],
                                            [colint(k_, pa) for k_ in sh_cols])
        c.drawString(s, x, r.top() + 160, f, skia.Paint(AntiAlias=True, Shader=sh))
    for i, ln in enumerate(ANS):
        reveal_line(c, ln, x, r.top() + 158 + i * 60, 38, "Bold", t, ANS0 + i * 0.58, 0.72)
    chart(c, t, R(x, r.top() + 250, r.width() - 112, 210))
    # sources
    sk = e_io_sine(prog(t, SRC0 - 0.1, 0.3))
    yy = r.bottom() - 70
    text(c, "출처", x, yy + 8, 18, "Medium", SUB, sk)
    cx = x + 58
    for i, s in enumerate(SOURCES):
        k2, dy2, bl2 = A.blur_in(t, SRC0 + i * 0.25, 0.6)
        w = text_w(s, 19, "SemiBold") + 36
        if k2 > 0.003:
            cr = R(cx, yy - 22 + dy2, w, 42)
            rrect(c, cr, 12, NAVY_800, k2)
            rrect_stroke(c, cr, 12, "#3A5596", k2, 1.3)
            text(c, s, cr.centerX(), cr.centerY() + 7, 19, "SemiBold", WHITE, k2, "center")
        cx += w + 12
    unlayer(c)


# ---------------------------------------------------------------- frame
def render(c, t):
    background(c, t)
    out = e_io_sine(prog(t, OUT0, 0.95))
    if out < 1:                                          # the ontology falls back out of focus
        img = A.snap(20, lambda cc: G.render(cc, min(t, G.T_END - 1 / 24)))
        A.draw_img(c, img, 1 - out, 22 * out, lerp(1.0, 0.86, out))
    push = 1.0 + 0.035 * e_io_sine(prog(t, PANES0, T0 + NF / 24.0 - PANES0))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(push, push)
    c.translate(-W / 2, -H / 2)
    systems(c, t)
    left_card(c, t)
    answer(c, t)
    search_card(c, t)
    c.restore()


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
    out = G.setup(height)
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
