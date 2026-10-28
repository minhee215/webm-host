"""Segment 00:00:28:12-00:00:44:02 - "AI 컨설턴트 AXpoint는 / 사내 문서와 데이터에서 / 실제 업무 흐름과 변화의
우선순위를 찾아냅니다. / 필요한 기능은 M-AI Works 안에서 직접 선택해 / 우리 회사에 맞는 워크스페이스로 구성합니다."

Look and motion after the client's reference 4: full-bleed light product UI shot close with slow gliding camera
moves, soft blur-in transitions, chips and typed prompts, a glowing core with documents orbiting it; deep navy and
AXpoint blue fields in between.
  intro    28:12  the previous segment (seg_insight, S5_FRONT_END = "line") ends on a line and a diamond on the navy
                  stage; the line opens into the search-bar outline, the diamond becomes the "기업 찾기" button, the
                  bar fills white and the white spreads over the frame: the AXpoint landing page (the client's
                  opening video, rebuilt). The company name is typed, the button pressed - the camera dives into it
  docs            files slide into the prompt box, the request is typed and sent (파일 업로드); the files lift off and
                  orbit the AXpoint core while it reads them (자료 확인)
  diag            from the core a blue field opens (the AXpoint title card look): rings and axis names first, then
                  the rings turn into the pentagon and the AX index polygon blooms; work-flow weak points (진단 결과)
  cands           the light page slides up: the recommended improvement-task candidates arrive in order (개선 과제)
  monitor  36:03  the page turns into a browser window and goes transparent: through it the man looking at it
                  (live action, locked-off)
  ceiling         low-angle shot of him at his desk (locked-off); M-AI Works feature cards with toggles hang under
                  the ceiling, his choices switch them on, then the chosen ones become his company's M-AI Works
                  workspace.
                  The UI is laid on the ceiling with one fixed perspective (the camera does not move), so it cannot
                  drift or shake.
Frame f is timeline frame 684 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_axpoint.py <out.mp4> [height=480] [first last]
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
import skia

import engine as E
import scenes as S
from engine import (W, H, R, BLUE, INK, STEEL, STEEL_200, STEEL_400, WHITE, NAVY_950, lerp, prog, clamp,
                    e_io_cubic, e_io_sine, e_out_cubic, e_out_expo, enter, paint_fill, paint_stroke,
                    rrect, rrect_stroke, text, text_w, icon, poly, line, pulse, radial, colint)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 684                      # timeline frame of f = 0 (00:00:28:12)
NF = 375                        # ... through 00:00:44:02
COMPANY = "(주)에이엑스코어"
LINE = "#E3E7EE"
ORANGE = "#FF9D5C"
VIOLET = "#7B5CFF"
LINE_BLUE = S.LINE_BLUE
SEARCH = R(600, 508, 720, 68)   # landing search bar (screen = page at the start)
BTN = R(1152, 516, 160, 52)     # its "기업 찾기" button; the diamond of the previous segment sits at its centre

# shot boundaries (film time)
T_DOCS, T_DIAG, T_CANDS, T_MON, T_CEIL = 30.50, 33.36, 34.55, 36.10, 37.45
XB = 0.22                       # cross-blur length intro -> docs


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- camera (per shot, page coordinates)
CAM_INTRO = [(28.50, 960, 540, 1.0), (29.55, 960, 540, 1.0), (30.05, 1000, 560, 1.30), (30.38, 1150, 555, 1.48),
             (30.70, 1232, 542, 2.7)]
CAM_DOCS = [(30.50, 1240, 520, 1.95), (30.78, 1180, 520, 1.55), (31.20, 1240, 505, 1.48), (31.45, 1010, 530, 1.30),
            (31.95, 960, 548, 1.08), (32.22, 960, 556, 1.0), (32.60, 560, 420, 1.52), (33.05, 1200, 500, 1.48),
            (33.42, 1470, 760, 1.40)]
CAM_DIAG = [(33.36, 860, 528, 1.32), (33.95, 960, 548, 1.0), (34.70, 975, 560, 1.03)]
CAM_CANDS = [(34.55, 960, 560, 1.0), (34.95, 700, 488, 1.40), (35.55, 1180, 600, 1.34), (36.00, 960, 548, 1.01),
             (36.20, 960, 540, 1.0)]


def _hermite(keys, t):
    ts = [k[0] for k in keys]
    if t <= ts[0]:
        return keys[0][1:]
    if t >= ts[-1]:
        return keys[-1][1:]
    i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
    vals = [(k[1], k[2], math.log(k[3])) for k in keys]

    def tan(j):
        if j == 0 or j == len(ts) - 1:
            return (0.0, 0.0, 0.0)
        return tuple((vals[j + 1][q] - vals[j - 1][q]) / (ts[j + 1] - ts[j - 1]) for q in range(3))

    h = ts[i + 1] - ts[i]
    u = (t - ts[i]) / h
    h00, h10, h01, h11 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u, -2 * u ** 3 + 3 * u ** 2, u ** 3 - u ** 2
    m0, m1 = tan(i), tan(i + 1)
    out = [h00 * vals[i][q] + h10 * h * m0[q] + h01 * vals[i + 1][q] + h11 * h * m1[q] for q in range(3)]
    return out[0], out[1], math.exp(out[2])


def cam(keys, t):
    fx, fy, z = _hermite(keys, t)
    dt = 1 / 48
    ax, ay, _ = _hermite(keys, t - dt)
    bx, by, _ = _hermite(keys, t + dt)
    vx = (bx - ax) / (2 * dt) * z / W
    vy = (by - ay) / (2 * dt) * z / W
    return fx, fy, z, clamp(-vx * 8.0, -5.0, 5.0), clamp(vy * 6.0, -3.5, 3.5)


def persp(yaw, pitch, f=1900.0):
    a, b = math.radians(yaw), math.radians(pitch)
    Ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(b), -math.sin(b)], [0, math.sin(b), math.cos(b)]])
    K = np.diag([f, f, 1.0])
    M = K @ Ry @ Rx @ np.linalg.inv(K)
    return skia.Matrix.MakeAll(*(M / M[2, 2]).flatten().tolist())


def to_screen(keys, t, x, y):
    """Page point -> screen (the camera without its small tilt)."""
    fx, fy, z, _, _ = cam(keys, t)
    return W / 2 + (x - fx) * z, H / 2 + (y - fy) * z


def apply_cam(c, keys, t):
    fx, fy, z, yaw, pitch = cam(keys, t)
    c.translate(W / 2, H / 2)
    c.concat(persp(yaw, pitch))
    c.scale(z, z)
    c.translate(-fx, -fy)


# ---------------------------------------------------------------- shared look
def light_bg(c):
    c.drawRect(R(-2000, -2000, W + 4000, H + 4000), paint_fill(WHITE))
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 520), skia.Point(0, 1080)],
                                        [colint("#FFFFFF", 0.0), colint("#E8EBFF", 1.0)])
    c.drawRect(R(-2000, 520, W + 4000, 560), skia.Paint(Shader=sh))
    c.drawRect(R(-2000, 1080, W + 4000, 2000), paint_fill("#E8EBFF"))
    radial(c, 340, 1010, 760, "#E4DAFF", 0.55, blend=skia.BlendMode.kSrcOver)
    radial(c, 1600, 990, 760, "#D8E4FF", 0.6, blend=skia.BlendMode.kSrcOver)


def gtext(c, s, x, y, size, w, a, c0=BLUE, c1=VIOLET, align="left"):
    """Text with a blue -> violet gradient (reference-4 highlight)."""
    if a <= 0.003 or not s:
        return 0.0
    f = E.font(size, w)
    tw = f.measureText(s)
    if align == "center":
        x -= tw / 2
    elif align == "right":
        x -= tw
    sh = skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x + tw, y)], [colint(c0, a), colint(c1, a)])
    c.drawString(s, x, y, f, skia.Paint(AntiAlias=True, Shader=sh))
    return tw


def mixed(c, parts, x, y, size, w, a, align="left"):
    """[(text, kind)] kind: None ink, 'g' gradient, or a colour - drawn as one line."""
    tw = sum(text_w(s, size, w) for s, _ in parts)
    if align == "center":
        x -= tw / 2
    for s, k in parts:
        if k == "g":
            x += gtext(c, s, x, y, size, w, a)
        else:
            x += text(c, s, x, y, size, w, k or INK, a)
    return tw


def chip(c, s, x, y, size, fg, bg, a, w="SemiBold", h=None, right=False, pad=10):
    tw = text_w(s, size, w) + 2 * pad
    h = h or size + 12
    rx = x - tw if right else x
    rrect(c, R(rx, y, tw, h), h / 2, bg, a)
    text(c, s, rx + pad, y + h / 2 + size * 0.36, size, w, fg, a)
    return tw


def colint_mix(c0, c1, k):
    a, b = E.col(c0), E.col(c1)
    k = clamp(k)
    return "#%02X%02X%02X" % tuple(int(round(255 * lerp(getattr(a, ch), getattr(b, ch), k))) for ch in ("fR", "fG", "fB"))


def diamond(c, x, y, r, color, a, rot=0.0):
    c.save()
    c.translate(x, y)
    c.rotate(rot)
    c.drawPath(poly([(0, -r), (r, 0), (0, r), (-r, 0)], True), paint_fill(color, a))
    c.restore()


def blur_layer(c, sigma, alpha=1.0):
    p = skia.Paint()
    p.setAlphaf(clamp(alpha))
    if sigma > 0.05:
        p.setImageFilter(skia.ImageFilters.Blur(sigma, sigma, skia.TileMode.kDecal))
    c.saveLayer(None, p)


def blur_in(t, t0, d=0.5):
    """(alpha, y offset, blur) of a soft blur-in entrance."""
    k = e_out_cubic(prog(t, t0, d))
    return k, 14 * (1 - k), 9 * (1 - k)


STEPS = ["파일 업로드", "자료 확인", "진단 결과", "개선 과제", "보고서"]


def nav(c, t, a, cur):
    """Top bar of the product page: logo, stepper (cur = active step or -1), the company."""
    if a <= 0.003:
        return
    text(c, "AXpoint", 96, 186, 22, "Bold", INK, a)
    if cur >= 0:
        x0, step = 960 - 2 * 128, 128
        for i, lab in enumerate(STEPS):
            x = x0 + i * step
            on, done = i == cur, i < cur
            colr = BLUE if on else (INK if done else STEEL_400)
            dx = x - text_w(lab, 13, "SemiBold") / 2 - 12
            c.drawCircle(dx, 181, 7.5, paint_fill(BLUE if (on or done) else "#D9DEE7", a))
            if done:
                icon(c, "check", dx, 181, 9, WHITE, a, 1.8)
            text(c, lab, x + 2, 186, 13, "SemiBold" if on else "Medium", colr, a, "center")
            if i < 4:
                text(c, "›", x + step / 2, 186, 13, "Medium", STEEL_200, a, "center")
    k = clamp((t - 30.45) / 0.3)
    if k > 0:
        tw = text_w(COMPANY, 14, "SemiBold")
        r = R(1824 - tw - 52, 164, tw + 52, 34)
        rrect(c, r, 17, WHITE, a * k)
        rrect_stroke(c, r, 17, LINE, a * k, 1.2)
        c.drawCircle(r.left() + 18, r.centerY(), 8, paint_fill("#E6EEFF", a * k))
        text(c, COMPANY, r.left() + 34, r.centerY() + 5, 14, "SemiBold", INK, a * k)


def cursor(c, x, y, a, press=0.0):
    if a <= 0.003:
        return
    s = 1.0 - 0.12 * press
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    pth = poly([(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 18), (21, 18)], True)
    c.drawPath(pth, paint_fill(NAVY_950, a * 0.25, blur=4))
    c.drawPath(pth, paint_fill(WHITE, a))
    c.drawPath(pth, paint_stroke(INK, a, 1.6))
    c.restore()


def ripple(c, x, y, t, t0, color=BLUE, size=60):
    q = prog(t, t0, 0.6)
    if 0 < q < 1:
        c.drawCircle(x, y, size * e_out_cubic(q), paint_stroke(color, 0.6 * (1 - q), 2.0))
        c.drawCircle(x, y, size * 0.6 * e_out_cubic(q), paint_fill(color, 0.12 * (1 - q)))


# ---------------------------------------------------------------- 1 intro (landing page)
TYPE0, TYPE_D = 29.74, 0.46
CLICK_SEARCH = 30.36


def intro(c, t):
    p1 = e_io_cubic(prog(t, 28.50, 0.40))          # line -> bar outline
    p2 = e_out_cubic(prog(t, 28.78, 0.30))         # the bar fills white
    p3 = e_io_cubic(prog(t, 28.98, 0.52))          # the white spreads over the frame
    q = e_io_cubic(prog(t, 28.52, 0.48))           # diamond -> button
    if p3 < 1:
        # the navy stage of the previous segment, unchanged (its line and diamond are drawn below)
        S.S5_FRONT, S.S5_FRONT_END, S.S5_LINE_HIDE = True, "line", True
        T = t - 1.0
        S.sc05(c, T, T - S.SC05_T0, 10.0)
        S.S5_LINE_HIDE = False
    c.save()
    apply_cam(c, CAM_INTRO, t)
    if p3 > 0:
        r0 = SEARCH
        big = R(-420, -560, W + 840, H + 1120)
        rr = skia.Rect.MakeLTRB(lerp(r0.left(), big.left(), p3), lerp(r0.top(), big.top(), p3),
                                lerp(r0.right(), big.right(), p3), lerp(r0.bottom(), big.bottom(), p3))
        rad = lerp(34, 900, p3)
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(rr, rad, rad), skia.ClipOp.kIntersect, True)
        light_bg(c)
        c.restore()
        if p3 < 1:
            c.drawRRect(skia.RRect.MakeRectXY(rr, rad, rad), paint_stroke("#9DB8FF", 0.6 * (1 - p3), 3, blur=6))
    landing(c, t, p3)
    # the bar
    h = lerp(2.2, SEARCH.height(), p1)
    x0, x1 = lerp(S.BAR_LINE[1], SEARCH.left(), p1), lerp(S.BAR_LINE[0], SEARCH.right(), p1)
    br = R(x0, SEARCH.centerY() - h / 2, x1 - x0, h)
    if p3 > 0:
        c.drawRRect(skia.RRect.MakeRectXY(br.makeOffset(0, 8), h / 2, h / 2), paint_fill("#3A55B8", 0.10 * p3, blur=18))
    if p2 > 0:
        rrect(c, br, h / 2, WHITE, p2)
    glow = (1 - p3) * (0.5 + 0.5 * p2)
    rrect_stroke(c, br, h / 2, LINE_BLUE, 0.5 * glow, 7, blur=8)
    rrect_stroke(c, br, h / 2, LINE_BLUE, 1.0, lerp(2.2, 1.8, p3))
    if p2 > 0 and p3 < 1:
        radial(c, br.centerX(), br.centerY(), 520, "#9DB8FF", 0.35 * p2 * (1 - p3))
    search_content(c, t, p2, p3)
    # diamond -> button
    bx, by = BTN.centerX(), BTN.centerY()
    w_, h_ = lerp(15.6, BTN.width(), q), lerp(15.6, BTN.height(), q)
    typed = clamp((t - (TYPE0 + TYPE_D)) / 0.2)
    col_ = LINE_BLUE if p3 < 1 else ("#9DB4FF" if typed <= 0 else BLUE)
    press = math.sin(math.pi * prog(t, CLICK_SEARCH - 0.05, 0.22))
    c.save()
    c.translate(bx, by)
    c.rotate(45 * (1 - q))
    c.scale(1 - 0.05 * press, 1 - 0.05 * press)
    rr_ = R(-w_ / 2, -h_ / 2, w_, h_)
    if q < 1:
        c.drawRRect(skia.RRect.MakeRectXY(rr_, 11, 11), paint_fill(LINE_BLUE, 0.5 * (1 - q), blur=8))
    rad_ = min(lerp(1.5, 26, q), h_ / 2)
    c.drawRRect(skia.RRect.MakeRectXY(rr_, rad_, rad_), paint_fill(col_))
    if q < 0.5:
        c.drawRRect(skia.RRect.MakeRectXY(rr_, rad_, rad_), paint_stroke(WHITE, 1 - 2 * q, 1.2))
    c.restore()
    ta = e_out_cubic(prog(t, 29.05, 0.35))
    text(c, "기업 찾기  →", bx, by + 6, 16, "Bold", WHITE, ta, "center")
    ripple(c, bx, by, t, CLICK_SEARCH, WHITE, 90)
    # dropdown with the found company
    dk = e_out_expo(prog(t, TYPE0 + TYPE_D - 0.02, 0.4))
    if dk > 0:
        r = R(SEARCH.left(), SEARCH.bottom() + 14 + 10 * (1 - dk), SEARCH.width(), 74)
        rrect(c, r.makeOffset(0, 8), 18, "#3A55B8", 0.10 * dk, blur=16)
        rrect(c, r, 18, WHITE, dk)
        rrect_stroke(c, r, 18, LINE, dk, 1.2)
        rrect(c, R(r.left() + 8, r.top() + 8, r.width() - 16, r.height() - 16), 12, "#F2F5FF", dk)
        rrect(c, R(r.left() + 22, r.top() + 19, 36, 36), 10, "#E1E9FF", dk)
        icon(c, "factory", r.left() + 40, r.top() + 37, 20, BLUE, dk)
        text(c, COMPANY, r.left() + 72, r.top() + 34, 17, "Bold", INK, dk)
        text(c, "제조업  ·  경기도 화성시  ·  사업자 확인 완료", r.left() + 72, r.top() + 56, 13, "Medium", STEEL, dk)
        icon(c, "check", r.right() - 36, r.centerY(), 18, BLUE, dk, 2.2)
    # cursor to the button
    ca = clamp((t - 29.95) / 0.15) * (1 - clamp((t - 30.55) / 0.1))
    cq = e_io_cubic(prog(t, 29.98, 0.34))
    cursor(c, lerp(1520, bx + 6, cq), lerp(760, by + 4, cq), ca, press)
    c.restore()


def landing(c, t, p3):
    if p3 <= 0:
        return
    k, dy, bl = blur_in(t, 29.22, 0.55)
    if k > 0:
        blur_layer(c, bl, k)
        mixed(c, [("제조 ", None), ("AX", BLUE), ("를 위한 ", None), ("AI", BLUE), (" 컨설턴트", None)],
              960, 418 + dy, 54, "Bold", 1.0, "center")
        text(c, "조사 · 분석 · 진단 · 설계까지, One-stop 맞춤형 솔루션", 960, 466 + dy, 20, "Medium", STEEL, 1.0, "center")
        c.restore()
    nav(c, t, e_out_cubic(prog(t, 29.40, 0.5)), -1)


def search_content(c, t, p2, p3):
    a = p2
    if a <= 0:
        return
    ix, iy = 642, SEARCH.centerY()
    c.drawCircle(ix - 3, iy - 3, 8, paint_stroke(STEEL_400, a, 2.0))
    c.drawLine(ix + 3, iy + 3, ix + 9, iy + 9, paint_stroke(STEEL_400, a, 2.0))
    n = len(COMPANY)
    k = int(clamp((t - TYPE0) / TYPE_D) * n + 1e-6) if t >= TYPE0 else 0
    if k == 0:
        text(c, "사업자명 또는 기업명", 668, iy + 7, 18, "Medium", STEEL_400, a * clamp(p3 * 2 + p2 - 1))
        tw = 0
    else:
        tw = text(c, COMPANY[:k], 668, iy + 7, 19, "SemiBold", INK, a)
    if p3 > 0.5 and t < CLICK_SEARCH and (int(t * 2.4) % 2 == 0 or TYPE0 - 0.1 < t < TYPE0 + TYPE_D):
        c.drawLine(670 + tw, iy - 12, 670 + tw, iy + 12, paint_stroke(BLUE, a, 1.8))


# ---------------------------------------------------------------- 2 docs (upload -> orbit)
FILES = [("X", "#1E9E5A", "생산일보_2026_09", "XLSX · 2.4MB"), ("P", "#E5484D", "품질검사 성적서_Q3", "PDF · 6.8MB"),
         ("W", "#2F6BFF", "작업표준서_가공라인", "DOCX · 1.1MB"), ("H", "#1AA3D8", "설비 점검표_2026", "HWP · 0.9MB"),
         ("X", "#1E9E5A", "수주 · 출하 현황", "XLSX · 3.2MB"), ("P", "#E5484D", "BOM_제품A-12", "PDF · 0.7MB"),
         ("X", "#1E9E5A", "재고 현황_10월", "XLSX · 1.6MB"), ("W", "#2F6BFF", "공정 개선 회의록", "DOCX · 0.4MB")]
BOX = R(420, 410, 1080, 210)
CHIP_H = 58
CHIP0 = 30.62
PROMPT = [("사내 자료 33건을 올렸어요. ", None), ("업무 흐름과 개선 과제", "g"), ("를 진단해 주세요.", None)]
PROMPT0, PROMPT_D = 30.86, 0.42
SEND = 31.36
ORBIT0 = 31.42
CORE = (960, 560)
RINGS = (153, 230, 330)


def chip_w(i):
    return text_w(FILES[i][2], 14, "SemiBold") + 96


def file_chip(c, i, x, y, a, s=1.0, check=0.0):
    letter, colr, name, meta = FILES[i]
    w = chip_w(i)
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    r = R(0, 0, w, CHIP_H)
    rrect(c, r.makeOffset(0, 4), 14, "#3A55B8", a * 0.08, blur=8)
    rrect(c, r, 14, WHITE, a)
    rrect_stroke(c, r, 14, LINE, a, 1.2)
    rrect(c, R(12, 13, 32, 32), 8, colr, a)
    text(c, letter, 28, 35, 16, "Bold", WHITE, a, "center")
    text(c, name, 54, 26, 14, "SemiBold", INK, a)
    text(c, meta, 54, 44, 11, "Medium", STEEL_400, a)
    if check > 0:
        c.drawCircle(w - 22, 29, 10 * e_out_expo(clamp(check)), paint_fill(BLUE, a))
        icon(c, "check", w - 22, 29, 11, WHITE, a * clamp(check), 2.0)
    else:
        text(c, "×", w - 22, 34, 15, "Medium", STEEL_400, a, "center")
    c.restore()


def row_xs():
    xs, x = [], BOX.left() + 24
    for i in range(len(FILES)):
        xs.append(x)
        x += chip_w(i) + 10
    return xs


def scroll_at(t):
    """The row scrolls left to keep the newest chip in view (eased toward it)."""
    xs = row_xs()
    acc = 0.0
    for k in range(int(max(0.0, t - CHIP0) * 24) + 1):
        tt = CHIP0 + k / 24
        n_in = sum(1 for i in range(len(FILES)) if tt >= CHIP0 + i * 0.075)
        tgt = 0.0
        if n_in:
            tgt = max(0.0, xs[n_in - 1] + chip_w(n_in - 1) - (BOX.right() - 24))
        acc += (tgt - acc) * 0.3
    return acc


def orbit_pos(i, t):
    ring = RINGS[1 + i % 2]
    a0 = -math.pi / 2 + i * (2 * math.pi / len(FILES)) + (0.35 if i % 2 else 0)
    ang = a0 + 0.22 * (t - ORBIT0)
    return CORE[0] + ring * math.cos(ang), CORE[1] + ring * 0.94 * math.sin(ang)


def docs(c, t):
    c.save()
    apply_cam(c, CAM_DOCS, t)
    light_bg(c)
    o = e_io_cubic(prog(t, ORBIT0, 0.62))
    nav(c, t, 1.0, 0 if t < ORBIT0 + 0.05 else 1)
    ha = 1 - e_io_cubic(prog(t, ORBIT0 - 0.05, 0.3))
    if ha > 0:
        mixed(c, [(COMPANY, "g"), (" 자료를 올려 주세요", None)], 960, 332, 36, "Bold", ha, "center")
        text(c, "문서 · 엑셀 · PDF · 한글 파일을 그대로 올리면 AXpoint가 읽고 분류해요", 960, 372, 17, "Medium", STEEL,
             ha, "center")
    # the prompt box
    ba = 1 - o
    if ba > 0.003:
        blur_layer(c, 10 * o, ba)
        rrect(c, BOX.makeOffset(0, 10), 26, "#3A55B8", 0.10, blur=22)
        rrect(c, BOX, 24, WHITE, 1.0)
        sh = skia.GradientShader.MakeLinear([skia.Point(BOX.left(), 0), skia.Point(BOX.right(), 0)],
                                            [colint(BLUE, 0.9), colint(VIOLET, 0.9)])
        c.drawRRect(skia.RRect.MakeRectXY(BOX, 24, 24),
                    skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=1.8))
        n = sum(len(s) for s, _ in PROMPT)
        k = int(clamp((t - PROMPT0) / PROMPT_D) * n) if t >= PROMPT0 else 0
        x, done = BOX.left() + 28, 0
        for s, kind in PROMPT:
            part = s[:max(0, k - done)]
            done += len(s)
            if not part:
                break
            x += gtext(c, part, x, BOX.top() + 148, 19, "SemiBold", 1.0) if kind == "g" else \
                text(c, part, x, BOX.top() + 148, 19, "Medium", INK, 1.0)
        if k == 0:
            text(c, "요청할 내용을 입력해 주세요", BOX.left() + 28, BOX.top() + 148, 19, "Medium", STEEL_400, 1.0)
        elif t < SEND and int(t * 2.4) % 2 == 0:
            c.drawLine(x + 2, BOX.top() + 132, x + 2, BOX.top() + 154, paint_stroke(BLUE, 1.0, 1.8))
        text(c, "+", BOX.left() + 30, BOX.bottom() - 22, 24, "Light", STEEL, 1.0)
        sk = clamp((t - (PROMPT0 + PROMPT_D)) / 0.15)
        sx, sy = BOX.right() - 42, BOX.bottom() - 34
        press = math.sin(math.pi * prog(t, SEND - 0.05, 0.22))
        c.drawCircle(sx, sy, 20 * (1 - 0.08 * press), paint_fill("#D9DEE7" if sk <= 0 else BLUE))
        up = paint_stroke(WHITE, 1.0, 2.2)
        c.drawLine(sx, sy + 7, sx, sy - 7, up)
        c.drawPath(poly([(sx - 6, sy - 1), (sx, sy - 7), (sx + 6, sy - 1)]), up)
        ripple(c, sx, sy, t, SEND, BLUE, 50)
        if 0 < t - SEND + 0.4 < 0.55:
            cq = e_io_cubic(prog(t, SEND - 0.4, 0.36))
            cursor(c, lerp(1640, sx + 4, cq), lerp(760, sy + 4, cq), 1.0, press)
        c.restore()
    # files: in the row, lifted into orbit, then sorted into the work flow
    xs = row_xs()
    scr = scroll_at(t)
    clip = o <= 0
    if clip:
        c.save()
        c.clipRRect(skia.RRect.MakeRectXY(BOX.makeInset(2, 2), 22, 22), skia.ClipOp.kIntersect, True)
    gq = e_io_cubic(prog(t, GRAPH0, 0.3))        # orbit -> graph
    # orbit: rings and the reading core (behind the files)
    if o > 0 and gq < 1:
        oa = o * (1 - gq)
        for j, r in enumerate(RINGS):
            c.drawOval(R(CORE[0] - r, CORE[1] - r * 0.94, 2 * r, 2 * r * 0.94),
                       paint_stroke("#BFCBF2", 0.9 * oa * (0.6 if j == 0 else 1.0), 1.3))
        ck = e_out_expo(prog(t, ORBIT0 + 0.15, 0.6)) * (1 - gq)
        radial(c, CORE[0], CORE[1], 180, "#A9B8FF", 0.55 * ck, blend=skia.BlendMode.kSrcOver)
        sh = skia.GradientShader.MakeLinear([skia.Point(CORE[0] - 48, CORE[1] - 48), skia.Point(CORE[0] + 48, CORE[1] + 48)],
                                            [colint(BLUE, ck), colint(VIOLET, ck)])
        c.drawCircle(CORE[0], CORE[1], 48 * ck, skia.Paint(AntiAlias=True, Shader=sh))
        diamond(c, CORE[0], CORE[1], 20 * ck, WHITE, ck, rot=90 * (1 - ck))
        g = e_io_sine(prog(t, 31.6, 0.42))
        if g > 0.005:
            c.drawArc(R(CORE[0] - 66, CORE[1] - 66, 132, 132), -90, 360 * g, False, paint_stroke(BLUE, ck, 3.2))
    if t > GRAPH0:
        graph(c, t)
    for i in range(len(FILES)):
        k = e_out_cubic(prog(t, CHIP0 + i * 0.075, 0.35))
        if k <= 0:
            continue
        rx, ry = xs[i] - scr + 60 * (1 - k), BOX.top() + 22
        if o <= 0:
            file_chip(c, i, rx, ry, k)
            continue
        ox, oy = orbit_pos(i, min(t, GRAPH0))
        w = chip_w(i) * 0.9
        q = e_io_cubic(prog(t, ORBIT0 + i * 0.03, 0.62))
        x = lerp(rx, ox - w / 2, q)
        y = lerp(ry, oy - CHIP_H * 0.45, q) - 40 * math.sin(math.pi * q)
        s_ = lerp(1.0, 0.9, q)
        m = e_io_cubic(prog(t, GRAPH0 + i * 0.03, 0.45))     # into its node
        if m > 0:
            nr = node_rect(FILE_NODE[i])
            x, y = lerp(x, nr.left(), m), lerp(y, nr.top(), m) - 30 * math.sin(math.pi * m)
            s_ = lerp(s_, 0.8, m)
        if m < 1:
            file_chip(c, i, x, y, 1.0 - m, s_, check=prog(t, 31.65 + i * 0.04, 0.22))
    if clip:
        c.restore()
    if o > 0:
        g = e_io_sine(prog(t, 31.6, 0.42))
        k1 = e_out_cubic(prog(t, ORBIT0 + 0.2, 0.4)) * (1 - e_out_cubic(prog(t, GRAPH0 + 0.02, 0.22)))
        k2, dy, _ = blur_in(t, GRAPH0 + 0.12, 0.45)
        mixed(c, [("자료 ", None), ("%d건" % int(round(33 * g)), "g"), ("을 확인하고 있어요", None)], 960, 222, 32, "Bold",
              k1, "center")
        mixed(c, [("흩어진 자료를 ", None), ("업무 흐름", "g"), ("으로 정리했어요", None)], 960, 250 + dy, 32, "Bold", k2,
              "center")
    c.restore()


# work flow (ontology) the documents are sorted into: (title, category, documents, x, y, broken record)
GRAPH0 = 32.02
CAT_COL = {"영업관리": "#4A78E8", "제품설계": "#8A63D2", "생산관리": "#2E9E5B", "품질검사": "#D08A2E",
           "장비관리": "#2AA7C8", "재고물류": "#C8508A", "고객지원": "#5B8DEF", "경영지원": "#7A8699"}
NODES = [("수주 접수", "영업관리", ["수주 현황"], 230, 290), ("초도 설계 승인", "제품설계", ["제품 도면", "규격서"], 470, 290),
         ("황삭 가공 작업지시", "생산관리", ["작업지시서"], 730, 290), ("정삭 가공", "생산관리", ["작업표준서", "생산 일보"], 990, 290),
         ("공정 검사", "품질검사", ["공정 검사 체크"], 1250, 290), ("출하 검사", "품질검사", ["출하 성적서"], 1500, 290),
         ("수입 검사", "품질검사", ["수입검사 성적서"], 230, 460), ("자재 수불 관리", "재고물류", ["자재수불대장"], 520, 460),
         ("외주 열처리", "생산관리", ["제조/QC 공정도"], 820, 460), ("부적합 보고", "품질검사", ["부적합 보고서"], 1110, 460),
         ("시정 · 예방조치", "품질검사", ["시정조치 요구서"], 1410, 460),
         ("설비 일상 점검", "장비관리", [], 230, 630), ("견적 산출", "영업관리", [], 820, 630),
         ("BOM 관리", "제품설계", ["BOM"], 520, 630), ("납품 · 출하", "재고물류", ["출하 현황"], 1110, 630),
         ("고객 클레임 접수", "고객지원", ["VOC 대장"], 1410, 630)]
BROKEN = {11, 12}
EDGES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (6, 2), (7, 2), (2, 8), (8, 3), (4, 9), (9, 10), (13, 7, "d"),
         (5, 14), (15, 10, "d"), (11, 6, "r"), (12, 8, "r")]
FILE_NODE = [3, 4, 3, 11, 0, 13, 7, 9]           # which node each uploaded file belongs to
NW, NH = 200, 72
DIAG_BTN = R(1510, 838, 214, 50)
CLICK_DIAG = GRAPH0 + 1.24


def node_rect(j):
    return R(NODES[j][3], NODES[j][4], NW, NH)


def node_time(j):
    return GRAPH0 + 0.12 + (NODES[j][3] - 230) / 1300 * 0.35 + (NODES[j][4] - 290) / 340 * 0.08


def edge_path(a, b):
    ra, rb = node_rect(a), node_rect(b)
    pth = skia.Path()
    if abs(ra.top() - rb.top()) < 1 and rb.left() > ra.left():
        x0, y0, x1 = ra.right(), ra.centerY(), rb.left()
        pth.moveTo(x0, y0)
        pth.lineTo(x1, y0)
        return pth
    x0, y0 = (ra.right(), ra.centerY()) if rb.left() > ra.right() else (ra.centerX(), ra.top() if rb.top() < ra.top()
                                                                       else ra.bottom())
    x1, y1 = (rb.left(), rb.centerY()) if rb.left() > ra.right() else (rb.centerX(), rb.bottom() if rb.top() < ra.top()
                                                                       else rb.top())
    pth.moveTo(x0, y0)
    if rb.left() > ra.right():
        mx = (x0 + x1) / 2
        pth.cubicTo(mx, y0, mx, y1, x1, y1)
    else:
        my = (y0 + y1) / 2
        pth.cubicTo(x0, my, x1, my, x1, y1)
    return pth


def graph(c, t):
    for e in EDGES:
        a, b = e[0], e[1]
        kind = e[2] if len(e) > 2 else ""
        g = e_out_cubic(prog(t, max(node_time(a), node_time(b)) + 0.12, 0.4))
        if g <= 0:
            continue
        pth = edge_path(a, b)
        colr = "#E5484D" if kind == "r" else "#4D7BEA"
        p = paint_stroke(colr, 0.9, 1.6)
        if kind in ("d", "r"):
            p.setPathEffect(skia.DashPathEffect.Make([7, 6], 0))
        meas = skia.PathMeasure(pth, False)
        seg = skia.Path()
        meas.getSegment(0, meas.getLength() * g, seg, True)
        c.drawPath(seg, p)
        if g >= 1:
            pos, tan_ = meas.getPosTan(meas.getLength())
            ang = math.atan2(tan_.fY, tan_.fX)
            ex, ey = pos.fX, pos.fY
            c.drawPath(poly([(ex - 8 * math.cos(ang) - 4 * math.sin(ang), ey - 8 * math.sin(ang) + 4 * math.cos(ang)),
                             (ex, ey),
                             (ex - 8 * math.cos(ang) + 4 * math.sin(ang), ey - 8 * math.sin(ang) - 4 * math.cos(ang))]),
                       paint_stroke(colr, 0.9, 1.6))
        if kind != "r":
            pulse(c, pth, ((t - GRAPH0 - 0.5) * 0.7 + a * 0.17) % 1.0 if t > GRAPH0 + 0.5 else 0, BLUE, 0.8, 6, 0.18)
    for j, (title, cat, docs_, x, y) in enumerate(NODES):
        k, dy, bl = blur_in(t, node_time(j), 0.4)
        if k <= 0:
            continue
        r = node_rect(j).makeOffset(0, dy)
        broken = j in BROKEN
        flag = e_out_expo(prog(t, GRAPH0 + 0.85, 0.35)) if broken else 0.0
        blur_layer(c, bl, k)
        rrect(c, r.makeOffset(0, 4), 12, "#3A55B8", 0.06, blur=8)
        rrect(c, r, 12, colint_mix(WHITE, "#FDECEE", flag), 1.0)
        rrect_stroke(c, r, 12, colint_mix(CAT_COL[cat], "#E5484D", flag), 1.0, 1.6)
        text(c, title, r.left() + 14, r.top() + 27, 15, "Bold", INK, 1.0)
        x_ = r.left() + 14
        for d in docs_:
            x_ += chip(c, d, x_, r.top() + 40, 10, STEEL, "#F0F2F6", 1.0, w="Medium", h=20, pad=7) + 5
        if broken:
            text(c, "기록 끊김", r.right() - 12, r.top() + 27, 12, "Bold", "#E5484D", flag, "right")
            text(c, "문서 없음", r.left() + 14, r.top() + 55, 11, "Medium", "#E5484D", flag)
            q = prog(t, GRAPH0 + 0.85, 0.7)
            if 0 < q < 1:
                rrect_stroke(c, r.makeOutset(14 * q, 14 * q), 14, "#E5484D", 0.6 * (1 - q), 2.0)
        c.restore()
    # legend, finding, the next step
    k, dy, _ = blur_in(t, GRAPH0 + 0.7, 0.45)
    if k > 0:
        items = list(CAT_COL.items()) + [("기록 끊김 2곳", "#E5484D")]
        tw = sum(text_w(n, 13, "Medium") + 34 for n, _ in items)
        x = 960 - tw / 2
        for n, colr in items:
            rrect_stroke(c, R(x, 776 + dy, 16, 10), 4, colr, k, 1.6)
            x += 22 + text(c, n, x + 22, 786 + dy, 13, "SemiBold" if colr == "#E5484D" else "Medium",
                           "#E5484D" if colr == "#E5484D" else STEEL, k) + 12
        text(c, "표준 대비 기록 미확인 업무 26건  ·  설비 점검 · 견적 산출 기록이 끊겨 있어요", 960, 816 + dy, 14,
             "Medium", STEEL, k, "center")
    kb = e_out_expo(prog(t, GRAPH0 + 0.9, 0.4))
    if kb > 0:
        press = math.sin(math.pi * prog(t, CLICK_DIAG - 0.05, 0.22))
        b = DIAG_BTN
        c.save()
        c.translate(b.centerX(), b.centerY())
        c.scale(1 - 0.05 * press, 1 - 0.05 * press)
        c.translate(-b.centerX(), -b.centerY())
        rrect(c, b.makeOffset(0, 6), 14, BLUE, 0.25 * kb, blur=12)
        rrect(c, b, 14, BLUE, kb)
        text(c, "진단 결과 보기  →", b.centerX(), b.centerY() + 6, 17, "Bold", WHITE, kb, "center")
        c.restore()
        ripple(c, b.centerX(), b.centerY(), t, CLICK_DIAG, WHITE, 80)
        cq = e_io_cubic(prog(t, CLICK_DIAG - 0.38, 0.34))
        ca = clamp((t - (CLICK_DIAG - 0.4)) / 0.1)
        cursor(c, lerp(1760, b.centerX() + 30, cq), lerp(700, b.centerY() + 6, cq), ca, press)


# ---------------------------------------------------------------- 3 diag (blue field, pentagon radar)
AXES = [("AI 전략", 36.4), ("조직 · 문화", 54.8), ("업무 · 인재", 46.2), ("인프라 · 기술", 49.5), ("활용 · 성과", 28.7)]
FLOW = [("수주", None), ("생산 계획", "AI 적용"), ("자재 구매", None), ("가공 · 조립", "수기 기록"),
        ("품질 검사", "병목"), ("출하", None)]
RC, RR = (760, 520), 230
MORPH0, POLY0 = 33.66, 33.95


def ring_path(cx, cy, r, m, n=100):
    """Circle (m = 0) -> pentagon (m = 1) of circumradius r, vertex up."""
    pts = []
    for j in range(n):
        th = -math.pi / 2 + 2 * math.pi * j / n
        loc = ((th + math.pi / 2) % (2 * math.pi / 5)) - math.pi / 5
        rp = r * math.cos(math.pi / 5) / math.cos(loc)
        pts.append((cx + lerp(r, rp, m) * math.cos(th), cy + lerp(r, rp, m) * math.sin(th)))
    return poly(pts, True)


def axis_pt(i, r, cx=RC[0], cy=RC[1]):
    a = math.radians(-90 + 72 * i)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def diag(c, t):
    c.save()
    apply_cam(c, CAM_DIAG, t)
    c.drawRect(R(-2000, -2000, W + 4000, H + 4000), paint_fill(BLUE))
    radial(c, RC[0], RC[1], 900, "#2C72FF", 0.55, blend=skia.BlendMode.kSrcOver)
    m = e_io_cubic(prog(t, MORPH0, 0.42))
    g = e_out_expo(prog(t, T_DIAG + 0.02, 0.5))
    for ring, al in ((1 / 3, 0.32), (2 / 3, 0.40), (1.0, 0.6)):
        c.drawPath(ring_path(RC[0], RC[1], RR * ring, m), paint_stroke(WHITE, al * g, 1.3))
    sp = e_out_cubic(prog(t, MORPH0 + 0.2, 0.35))
    for i in range(5):
        line(c, poly([RC, axis_pt(i, RR)]), WHITE, 0.30, 1.0, (0, sp))
    lx = lerp(-200, 2200, e_io_cubic(prog(t, T_DIAG + 0.10, 0.5)))
    c.drawLine(-200, RC[1], lx, RC[1], paint_stroke(WHITE, 0.85, 1.6))
    if t > POLY0:
        vals = []
        for i, (_, v) in enumerate(AXES):
            k = enter(t, POLY0 + i * 0.06, 0.6, step=False, over=0.06)
            vals.append(axis_pt(i, RR * v / 70.0 * k))
        pg = poly(vals, True)
        c.drawPath(pg, paint_fill(WHITE, 0.22))
        c.drawPath(pg, paint_stroke(WHITE, 1.0, 3.0))
        for i, (x, y) in enumerate(vals):
            k = e_out_expo(prog(t, POLY0 + 0.25 + i * 0.06, 0.35))
            diamond(c, x, y, 7 * k, WHITE, 1.0)
    diamond(c, RC[0], RC[1], 22, WHITE, 1.0)
    for i, (name, v) in enumerate(AXES):
        k = e_out_cubic(prog(t, T_DIAG + 0.12 + i * 0.04, 0.35))
        x, y = axis_pt(i, RR + 34)
        al = "center" if i == 0 else ("left" if i in (1, 2) else "right")
        y += {0: -8, 1: 6, 2: 22, 3: 22, 4: 6}[i]
        num = v * clamp(prog(t, POLY0 + i * 0.06, 0.6))
        text(c, name if t < POLY0 else "%s  %.1f" % (name, num), x, y, 17, "Bold", WHITE, k, al)
    k, dy, bl = blur_in(t, T_DIAG + 0.35, 0.45)
    text(c, "AX 진단 결과", 330, 268 + dy, 16, "SemiBold", WHITE, 0.75 * k)
    text(c, "%.1f" % max(0.0, 43.1 * e_io_sine(prog(t, POLY0, 0.8))), 328, 330 + dy, 56, "Bold", WHITE, k)
    text(c, "AX 지수  ·  2단계 데이터화", 330, 362 + dy, 15, "SemiBold", WHITE, 0.85 * k)
    lo = min(range(5), key=lambda i: AXES[i][1])
    k, dy, _ = blur_in(t, POLY0 + 0.05, 0.45)
    text(c, "영역별 진단", 1190, 330 + dy, 16, "SemiBold", WHITE, 0.75 * k)
    for i, (name, v) in enumerate(AXES):
        yy = 378 + i * 44 + dy
        text(c, name, 1190, yy + 6, 16, "SemiBold", WHITE, k)
        bb = R(1330, yy - 4, 200, 7)
        rrect(c, bb, 3.5, WHITE, 0.22 * k)
        gg = e_out_expo(prog(t, POLY0 + 0.12 + i * 0.05, 0.7))
        rrect(c, R(bb.left(), bb.top(), bb.width() * v / 70 * gg, 7), 3.5, ORANGE if i == lo else WHITE, k)
        text(c, "%.1f" % (v * gg), 1592, yy + 6, 16, "Bold", ORANGE if i == lo else WHITE, k, "right")
    c.restore()


# ---------------------------------------------------------------- 4 cands (improvement-task candidates)
CANDS = [("생산관리", "수기 작업일보 전산화", "1~2"), ("생산관리", "작업자 노하우 · 암묵지 구조화", "2~4"),
         ("경영지원", "종이 문서 데이터화", "1~2"), ("장비관리", "공정 · 설비 데이터 네트워크", "2~3"),
         ("경영지원", "데이터 공유 체계 정리", "1"), ("경영지원", "기준정보(마스터 코드) 표준화", "2~3"),
         ("제품설계", "도면 · 설계문서 중앙 관리", "1~2"), ("제품설계", "설계변경(ECO) 이력 관리", "1~2"),
         ("경영지원", "전자결재 · 문서 중앙화", "1~2"), ("품질검사", "검사성적서 · 검사기록 전산화", "1~2"),
         ("경영지원", "경영 KPI 통합 대시보드", "2~3")]
FILTERS = [("★ 추천", 11), ("전체", 68), ("생산관리", 16), ("경영지원", 9), ("장비관리", 11), ("제품설계", 4),
           ("품질검사", 10), ("재고물류", 10), ("영업관리", 4), ("고객지원", 4)]
CW, CH, CX0, CY0 = 300, 120, 330, 446


def card_time(i):
    return T_CANDS + 0.36 + i * 0.08


def clock(c, x, y, r, color, a):
    c.drawCircle(x, y, r, paint_stroke(color, a, 1.2))
    c.drawLine(x, y, x, y - r * 0.55, paint_stroke(color, a, 1.2))
    c.drawLine(x, y, x + r * 0.45, y, paint_stroke(color, a, 1.2))


def cands_page(c, t):
    light_bg(c)
    nav(c, t, 1.0, 3)
    k, dy, bl = blur_in(t, T_CANDS + 0.2, 0.5)
    text(c, "개선 과제 후보", 330, 300 + dy, 38, "Bold", INK, k)
    text(c, "진단 결과로 도출한 과제예요", 330, 338 + dy, 17, "Medium", STEEL, k)
    text(c, "예상 기간은 정부 스마트공장 사업 표준 일정 기준이에요", 330, 364 + dy, 13, "Medium", STEEL_400, k)
    n = int(round(11 * clamp(prog(t, card_time(0), card_time(10) - card_time(0) + 0.15))))
    tw = text_w("개 추천 과제", 17, "SemiBold")
    text(c, "개 추천 과제", 1590, 330 + dy, 17, "SemiBold", STEEL, k, "right")
    gtext(c, str(n), 1580 - tw, 334 + dy, 56, "Bold", k, align="right")
    x = 330
    for j, (lab, cnt) in enumerate(FILTERS):
        kk = e_out_cubic(prog(t, T_CANDS + 0.3 + j * 0.03, 0.4))
        on = j == 0
        x += chip(c, "%s %d" % (lab, cnt), x, 390 + 8 * (1 - kk), 13, WHITE if on else STEEL,
                  BLUE if on else "#EEF1F6", kk, h=34, pad=14) + 8
    for i, (field, title, months) in enumerate(CANDS):
        kk, dyy, bl = blur_in(t, card_time(i), 0.45)
        if kk <= 0:
            continue
        r = R(CX0 + (i % 4) * (CW + 20), CY0 + (i // 4) * (CH + 20) + dyy * 1.6, CW, CH)
        blur_layer(c, bl, kk)
        rrect(c, r.makeOffset(0, 6), 16, "#3A55B8", 0.07, blur=10)
        rrect(c, r, 16, WHITE, 1.0)
        rrect_stroke(c, r, 16, LINE, 1.0, 1.2)
        w1 = chip(c, field, r.left() + 18, r.top() + 16, 11, STEEL, "#EEF1F6", 1.0, h=22, pad=9)
        sk = e_out_expo(prog(t, card_time(i) + 0.15, 0.35))
        chip(c, "★ 추천", r.left() + 24 + w1, r.top() + 16, 11, BLUE, "#E6EEFF", sk, h=22, pad=9)
        c.drawCircle(r.right() - 26, r.top() + 27, 10, paint_stroke(STEEL_200, 1.0, 1.4))
        text(c, title, r.left() + 18, r.top() + 72, 17, "Bold", INK, 1.0)
        clock(c, r.left() + 24, r.bottom() - 22, 6, STEEL_400, 1.0)
        text(c, "예상 %s개월" % months, r.left() + 36, r.bottom() - 17, 13, "Medium", STEEL, 1.0)
        text(c, "자세히  ›", r.right() - 18, r.bottom() - 17, 13, "Medium", STEEL, 1.0, "right")
        c.restore()
    kb = e_out_expo(prog(t, card_time(10) + 0.2, 0.5))
    if kb > 0:
        bar = R(330, 866 + 10 * (1 - kb), 1260, 58)
        rrect(c, bar.makeOffset(0, 4), 14, "#3A55B8", kb * 0.08, blur=10)
        rrect(c, bar, 14, WHITE, kb)
        rrect_stroke(c, bar, 14, LINE, kb, 1.2)
        text(c, "과제 0개 담음", bar.left() + 22, bar.top() + 25, 15, "Bold", INK, kb)
        text(c, "정부 지원사업 1회 신청 단위: 2~3개", bar.left() + 22, bar.top() + 45, 12, "Medium", STEEL, kb)
        b = R(bar.right() - 232, bar.top() + 10, 220, 38)
        rrect(c, b, 10, "#A9C3FF", kb)
        text(c, "이 과제로 로드맵 보기  →", b.centerX(), b.centerY() + 5, 14, "Bold", WHITE, kb, "center")


def cands(c, t):
    c.save()
    apply_cam(c, CAM_CANDS, t)
    cands_page(c, t)
    c.restore()


# ---------------------------------------------------------------- compositing helpers
SCV = 1.0
POOL = []


def surf_get(i):
    while len(POOL) <= i:
        info = skia.ImageInfo.Make(int(round(W * SCV)), int(round(H * SCV)), skia.ColorType.kRGBA_8888_ColorType,
                                   skia.AlphaType.kPremul_AlphaType)
        POOL.append(skia.Surface.MakeRaster(info))
    return POOL[i]


def snap(i, fn):
    s = surf_get(i)
    cc = s.getCanvas()
    cc.clear(skia.Color4f(0, 0, 0, 1))
    cc.save()
    cc.scale(SCV, SCV)
    fn(cc)
    cc.restore()
    return s.makeImageSnapshot()


def draw_img(c, img, alpha=1.0, blur=0.0, scale=1.0, cx=W / 2, cy=H / 2, dy=0.0):
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if blur > 0.05:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp))
    c.save()
    c.translate(cx, cy + dy)
    c.scale(scale, scale)
    c.translate(-cx, -cy)
    c.drawImageRect(img, R(0, 0, W, H), E.SAMP, p)
    c.restore()


# ---------------------------------------------------------------- part A shots
def part_a(c, t):
    if t < T_DOCS:
        intro(c, t)
        return
    if t < T_DOCS + XB:
        p = e_io_sine((t - T_DOCS) / XB)
        A = snap(1, lambda cc: intro(cc, t))
        B = snap(2, lambda cc: docs(cc, t))
        draw_img(c, A, 1.0, 14 * p, 1 + 0.10 * p, BTN.centerX(), BTN.centerY())
        draw_img(c, B, p, 12 * (1 - p))
        return
    if t < T_DIAG:
        docs(c, t)
        return
    if t < T_DIAG + 0.40:
        u = e_io_cubic((t - T_DIAG) / 0.40)
        docs(c, t)
        B = snap(1, lambda cc: diag(cc, t))
        c.save()
        pth = skia.Path()
        wx, wy = to_screen(CAM_DOCS, t, DIAG_BTN.centerX(), DIAG_BTN.centerY())
        pth.addCircle(wx, wy, 30 + 2300 * u)
        c.clipPath(pth, skia.ClipOp.kIntersect, True)
        draw_img(c, B)
        c.restore()
        c.drawCircle(wx, wy, 30 + 2300 * u, paint_stroke(WHITE, 0.6 * (1 - u), 3, blur=6))
        return
    if t < T_CANDS:
        diag(c, t)
        return
    if t < T_CANDS + 0.42:
        u = e_io_cubic((t - T_CANDS) / 0.42)
        A = snap(1, lambda cc: diag(cc, t))
        draw_img(c, A, 1.0, 10 * u, 1 - 0.04 * u)
        c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, 0.25 * u))
        B = snap(2, lambda cc: cands(cc, t))
        dy = (1 - u) * H * 0.75
        c.drawRRect(skia.RRect.MakeRectXY(R(0, dy - 10, W, H + 60), 40, 40), paint_fill(NAVY_950, 0.25, blur=30))
        c.save()
        rad = 40 * (1 - u)
        c.clipRRect(skia.RRect.MakeRectXY(R(0, dy, W, H + 60), rad, rad), skia.ClipOp.kIntersect, True)
        draw_img(c, B, 1.0, 0.0, 1.0, dy=dy)
        c.restore()
        return
    cands(c, t)


# ---------------------------------------------------------------- frame
def render(c, t):
    if t < T_MON:
        part_a(c, t)
    else:
        part_b(c, t)


# ---------------------------------------------------------------- part B: live action (locked-off plates)
CDN = "https://d8j0ntlcm91z4.cloudfront.net/user_3JwpXeeJ8WaJK5V5Ms4Pu2KVkZS/"
LIVE = {"monitor": ("b1_monitor.mp4", CDN + "hf_20261028_004148_2c7c34cb-57f6-4ff4-bf5b-c490635e2911.mp4", T_MON),
        "ceiling": ("b2_ceiling.mp4", CDN + "hf_20261028_004148_e420303e-6979-4516-a9f1-db1d85ee86d8.mp4", T_CEIL)}


class Plate:
    """Sequential reader of a locked-off live-action clip (24 fps), frames as skia images at the render size."""

    def __init__(self, key):
        name, url, self.t0 = LIVE[key]
        path = os.path.join(E.HERE, "clips", name)
        if not os.path.exists(path):
            subprocess.run(["curl", "-sS", "-o", path, url], check=True)
        self.cap = cv2.VideoCapture(path)
        self.n = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.idx, self.img = -1, None

    def at(self, t):
        j = int(min(max(0, round((t - self.t0) * 24)), self.n - 1))
        while self.idx < j:
            ok, fr = self.cap.read()
            if not ok:
                break
            self.idx += 1
            if self.idx == j:
                fr = cv2.resize(fr, (int(round(W * SCV)), int(round(H * SCV))), interpolation=cv2.INTER_AREA)
                self.img = skia.Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGBA),
                                                colorType=skia.ColorType.kRGBA_8888_ColorType)
        return self.img


PLATES = {}


def plate(key, t):
    if key not in PLATES:
        PLATES[key] = Plate(key)
    return PLATES[key].at(t)


def chrome(c, a, y0):
    """Browser chrome (tab row + address row) along the top of the 21:9 band."""
    if a <= 0.003:
        return
    c.drawRect(R(0, y0, W, 80), paint_fill("#F3F4F8", a))
    tab = R(18, y0 + 8, 330, 34)
    rrect(c, tab, 10, WHITE, a)
    diamond(c, tab.left() + 22, tab.centerY(), 7, BLUE, a)
    text(c, "AXpoint · AI 컨설턴트", tab.left() + 40, tab.centerY() + 5, 13, "SemiBold", INK, a)
    text(c, "×", tab.right() - 18, tab.centerY() + 5, 15, "Medium", STEEL, a, "center")
    text(c, "+", tab.right() + 22, tab.centerY() + 6, 18, "Medium", STEEL, a, "center")
    for j, s in enumerate(("←", "→", "↻")):
        text(c, s, 36 + j * 34, y0 + 67, 16, "Medium", STEEL, a, "center")
    url = R(150, y0 + 48, 1620, 26)
    rrect(c, url, 13, "#E6E8EF", a)
    c.drawCircle(url.left() + 16, url.centerY(), 5, paint_stroke(STEEL_400, a, 1.4))
    text(c, "axpoint  /  개선 과제 후보", url.left() + 34, url.centerY() + 5, 13, "Medium", STEEL, a)
    c.drawLine(0, y0 + 80, W, y0 + 80, paint_stroke("#DADDE6", a, 1.0))


def monitor(c, t):
    """The page becomes a browser window and turns transparent; behind it, the man reading it (seen from the
    screen)."""
    k1 = e_io_cubic(prog(t, T_MON, 0.35))           # the chrome comes in, the page settles under it
    k2 = e_io_cubic(prog(t, T_MON + 0.25, 0.9))     # the page turns transparent
    img = plate("monitor", t)
    if k2 > 0 and img is not None:
        p = skia.Paint(AntiAlias=True)
        sg = lerp(10, 3.0, k2) * SCV
        p.setImageFilter(skia.ImageFilters.Blur(sg, sg, skia.TileMode.kClamp))
        c.save()
        c.translate(W / 2, BAR)
        c.scale(1.1, 1.1)                   # the plate's lower edge (desk-side screen) stays below the band
        c.translate(-W / 2, -BAR)
        c.drawImageRect(img, R(0, 0, W, H), E.SAMP, p)
        c.restore()
    ui = snap(1, lambda cc: cands(cc, t))
    c.save()
    c.translate(W / 2, BAR + 80 * k1)
    c.scale(lerp(1.0, 0.93, k1), lerp(1.0, 0.93, k1))
    c.translate(-W / 2, -BAR)
    draw_img(c, ui, lerp(1.0, 0.45, k2))
    c.restore()
    c.drawRect(R(0, 0, W, H), paint_fill(WHITE, 0.22 * k2))
    c.save()
    c.translate(0, -80 * (1 - k1))
    chrome(c, lerp(1.0, 0.55, k2) * k1, BAR)
    c.restore()


# the ceiling plane, from the plate (1920 x 1080): its two seam families meet at vanishing points on one horizon;
# being at right angles they give the focal length, and with it the plane's true perspective. The UI lies in that
# plane, turned so that its rows run level across the frame (like the reference), receding toward the horizon.
VP_D, VP_C = (507.0, 933.0), (3483.0, 919.0)      # depth seams, cross seams
UW, UH = 2280.0, 680.0                             # UI plane size (units)
UI_NEAR_L, UI_NEAR_W = (110.0, 176.0), 1080.0      # where its near-left corner sits, the near edge's length (px)
UI_TILT = 0.45                                     # panels hang tilted toward the camera (0: flush with the ceiling)


def _plane_h():
    pp = np.array([W / 2, H / 2])
    f = math.sqrt(-np.dot(np.array(VP_D) - pp, np.array(VP_C) - pp))
    K = np.array([[f, 0, pp[0]], [0, f, pp[1]], [0, 0, 1.0]])
    Ki = np.linalg.inv(K)
    rd = Ki @ np.array([*VP_D, 1.0])
    rc = Ki @ np.array([*VP_C, 1.0])
    rd, rc = rd / np.linalg.norm(rd), rc / np.linalg.norm(rc)
    n = np.cross(rd, rc)
    th = math.atan2(-rc[2], rd[2])                 # in-plane direction parallel to the image plane: level rows
    e1 = math.cos(th) * rc + math.sin(th) * rd
    e1 /= np.linalg.norm(e1)
    if e1[0] < 0:
        e1 = -e1
    e2 = np.cross(n, e1)
    e2 /= np.linalg.norm(e2)
    if e2[2] < 0:
        e2 = -e2                                   # +v recedes, toward the horizon
    e2 = (1 - UI_TILT) * e2 + UI_TILT * np.array([0.0, 1.0, 0.0])
    e2 /= np.linalg.norm(e2)
    P0 = Ki @ np.array([*UI_NEAR_L, 1.0])          # depth 1
    sc = UI_NEAR_W / (f * UW)
    return K @ np.column_stack([sc * e1, sc * e2, P0])


_PM = []


def plane_matrix():
    if not _PM:
        M = _plane_h()
        _PM.append(skia.Matrix.MakeAll(*(M / M[2, 2]).flatten().tolist()))
    return _PM[0]


def plane_pt(u, v):
    q = _plane_h() @ np.array([u, v, 1.0])
    return q[0] / q[2], q[1] / q[2]


MODS = [("경영관리", "인사 · 급여 · 회계", "user"), ("제품설계", "도면 · BOM", "cube"),
        ("생산관리", "작업 지시 · 모니터링", "factory"), ("장비관리", "정비 예측 · 노후 설비", "gear"),
        ("품질검사", "불량 분석 · 검수", "scan"), ("재고·물류", "실시간 재고 · 수요 예측", "box"),
        ("영업관리", "수주 · 단가 견적", "chart"), ("고객지원", "AS · VOC 분석", "chat")]
ON_T = {1: 38.35, 2: 38.75, 3: 39.15, 4: 39.55, 5: 39.95}     # module -> switched on
MW, MH, MG = 540.0, 300.0, 40.0
WS0 = 40.50                                                  # the chosen ones become the workspace
WS_RECTS = {2: R(0, 190, 740, 230), 4: R(770, 190, 740, 230), 3: R(1540, 190, 740, 230),
            1: R(385, 450, 740, 230), 5: R(1155, 450, 740, 230)}
WS_TITLE = {1: "도면 · BOM", 2: "생산 실적", 3: "설비 가동률", 4: "불량률 추이", 5: "실시간 재고"}


def mod_rect(i):
    return R((i % 4) * (MW + MG), (i // 4) * (MH + MG), MW, MH)


def toggle(c, x, y, k, a):
    w, h = 104, 54
    r = R(x - w, y, w, h)
    rrect(c, r, h / 2, colint_mix("#D5DAE4", BLUE, k), a)
    kx = lerp(r.left() + h / 2, r.right() - h / 2, e_io_cubic(k))
    c.drawCircle(kx, r.centerY() + 2, h * 0.38, paint_fill(NAVY_950, 0.15 * a, blur=3))
    c.drawCircle(kx, r.centerY(), h * 0.38, paint_fill(WHITE, a))


def ceiling_card(c, r, a, lit=0.0):
    """Translucent glass panel hanging under the ceiling (reference look): the ceiling shows through, softened;
    a light colour fringe on the edge."""
    rad = 34
    rr = skia.RRect.MakeRectXY(r, rad, rad)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(8, 16), rad, rad), paint_fill("#5A6A90", 0.10 * a, blur=26))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    lp = skia.Paint()
    lp.setAlphaf(clamp(a))
    bf = skia.ImageFilters.Blur(5, 5, skia.TileMode.kClamp)
    rec = skia.Canvas.SaveLayerRec(r, lp, bf, 0)
    c.saveLayer(rec)
    sh = skia.GradientShader.MakeLinear([skia.Point(r.left(), r.top()), skia.Point(r.left(), r.bottom())],
                                        [colint(WHITE, 0.62), colint("#F2F5FF", 0.46)])
    c.drawRect(r, skia.Paint(Shader=sh))
    c.restore()
    c.restore()
    rrect_stroke(c, r.makeOffset(-3, 0), rad, "#FF6B8A", 0.22 * a, 2.0)
    rrect_stroke(c, r.makeOffset(3, 0), rad, "#4FD1FF", 0.26 * a, 2.0)
    rrect_stroke(c, r, rad, WHITE, 0.85 * a, 2.0)
    if lit > 0:
        rrect_stroke(c, r, rad, BLUE, 0.75 * a * lit, 4.5)
        c.drawRRect(rr, paint_stroke(BLUE, 0.30 * a * lit, 18, blur=16))


def mod_card(c, i, r, a, on):
    name, sub, ic = MODS[i]
    ceiling_card(c, r, a, on)
    rrect(c, R(r.left() + 40, r.top() + 40, 84, 84), 24, colint_mix("#EEF1F6", "#E3EBFF", on), a)
    icon(c, ic, r.left() + 82, r.top() + 82, 46, colint_mix(STEEL_400, BLUE, on), a, 4.2)
    text(c, name, r.left() + 44, r.top() + 196, 58, "Bold", colint_mix("#9AA1AB", INK, on), a)
    text(c, sub, r.left() + 46, r.top() + 250, 30, "Medium", colint_mix(STEEL_400, STEEL, on), a)
    toggle(c, r.right() - 40, r.top() + 46, on, a)


def widget(c, key, r, t, a):
    """Workspace widget: the switched-on feature at work."""
    g = e_out_cubic(prog(t, WS0 + 0.55, 0.9))
    text(c, MODS[key][0], r.left() + 40, r.top() + 60, 26, "SemiBold", STEEL, a)
    text(c, WS_TITLE[key], r.left() + 40, r.top() + 104, 38, "Bold", INK, a)
    x0, y0, x1, y1 = r.left() + 330, r.top() + 50, r.right() - 40, r.bottom() - 40
    if key == 2:
        pts = [(lerp(x0, x1, j / 7), lerp(y1, y0, v)) for j, v in
               enumerate((0.35, 0.42, 0.38, 0.55, 0.6, 0.58, 0.75, 0.82))]
        line(c, poly(pts), BLUE, a, 6, (0, g))
        text(c, "+12%", r.left() + 40, r.bottom() - 42, 40, "Bold", BLUE, a * g)
    elif key == 4:
        for j, v in enumerate((0.8, 0.7, 0.62, 0.5, 0.42, 0.3)):
            bw, bx = (x1 - x0) / 6 * 0.6, lerp(x0, x1, j / 6)
            rrect(c, R(bx, y1 - (y1 - y0) * v * g, bw, (y1 - y0) * v * g), 6, "#9DB8F5" if j < 5 else BLUE, a)
        text(c, "−38%", r.left() + 40, r.bottom() - 42, 40, "Bold", BLUE, a * g)
    elif key == 3:
        cx, cy, rr = (x0 + x1) / 2 + 40, y1 - 10, 120
        c.drawArc(R(cx - rr, cy - rr, 2 * rr, 2 * rr), 180, 180, False, paint_stroke("#E3E7EE", a, 26))
        if g > 0.01:
            c.drawArc(R(cx - rr, cy - rr, 2 * rr, 2 * rr), 180, 180 * 0.92 * g, False,
                      paint_stroke(BLUE, a, 26, cap=skia.Paint.kRound_Cap))
        text(c, "%d%%" % int(round(92 * g)), r.left() + 40, r.bottom() - 42, 40, "Bold", BLUE, a)
    elif key == 1:
        for j, s in enumerate(("A-12 도면 Rev.3", "BOM 변경 2건", "ECO 승인 대기")):
            yy = y0 + 20 + j * 52
            c.drawCircle(x0 + 10, yy, 7, paint_fill(BLUE if j == 0 else "#9DB8F5", a * g))
            text(c, s, x0 + 32, yy + 10, 26, "Medium", INK, a * g)
        text(c, "3건", r.left() + 40, r.bottom() - 42, 40, "Bold", BLUE, a * g)
    elif key == 5:
        pts = [(lerp(x0, x1, j / 9), lerp(y1, y0, v)) for j, v in
               enumerate((0.5, 0.48, 0.62, 0.55, 0.52, 0.66, 0.6, 0.7, 0.64, 0.68))]
        line(c, poly(pts), "#1E9E5A", a, 6, (0, g))
        text(c, "1,284 EA", r.left() + 40, r.bottom() - 42, 40, "Bold", INK, a * g)


def ceiling_ui(c, t):
    """The UI under the ceiling, in plane units."""
    w = e_io_cubic(prog(t, WS0, 0.75))         # 0: feature cards with toggles, 1: the workspace
    for i in range(8):
        k = e_out_cubic(prog(t, T_CEIL + 0.18 + (i % 4) * 0.07 + (i // 4) * 0.12, 0.6))
        if k <= 0:
            continue
        on = e_io_cubic(prog(t, ON_T[i], 0.25)) if i in ON_T else 0.0
        r0 = mod_rect(i).makeOffset(0, 160 * (1 - k))
        if i not in ON_T:
            a = k * (1 - w)
            if a > 0.003:
                blur_layer(c, 8 * (1 - k) + 8 * w, a)
                mod_card(c, i, r0.makeOffset(0, 60 * w), 1.0, 0.0)
                c.restore()
            continue
        r1 = WS_RECTS[i]
        r = skia.Rect.MakeLTRB(lerp(r0.left(), r1.left(), w), lerp(r0.top(), r1.top(), w),
                               lerp(r0.right(), r1.right(), w), lerp(r0.bottom(), r1.bottom(), w))
        if w < 0.5:
            blur_layer(c, 8 * (1 - k), k * (1 - w * 1.2))
            mod_card(c, i, r, 1.0, on)
            c.restore()
            q = prog(t, ON_T[i], 0.6)
            if 0 < q < 1:
                c.drawRRect(skia.RRect.MakeRectXY(r.makeOutset(30 * q, 30 * q), 40, 40), paint_stroke(BLUE, 0.6 * (1 - q), 4))
        else:
            ceiling_card(c, r, 1.0, 0.0)
            widget(c, i, r, t, e_out_cubic((w - 0.5) * 2))
    if w > 0:
        a = e_out_cubic(prog(t, WS0 + 0.35, 0.6))
        hr = R(0, 0, UW, 160).makeOffset(0, 60 * (1 - a))
        blur_layer(c, 8 * (1 - a), a)
        ceiling_card(c, hr, 1.0, 0.0)
        diamond(c, hr.left() + 70, hr.centerY(), 24, BLUE, 1.0)
        text(c, COMPANY, hr.left() + 118, hr.centerY() - 8, 30, "SemiBold", STEEL, 1.0)
        mixed(c, [("M-AI Works", "g"), (" 워크스페이스", None)], hr.left() + 118, hr.centerY() + 44, 48, "Bold", 1.0)
        chip(c, "기능 5개 연결됨", hr.right() - 40, hr.centerY() - 26, 26, BLUE, "#E6EEFF", 1.0, h=52, right=True, pad=24)
        c.restore()


def caption(c, t):
    """Lower-left title over the shot (reference look)."""
    for t0, t1, small, big in ((37.85, WS0 - 0.1, "필요한 기능만 골라 켜는", "M-AI Works 워크스페이스"),
                               (WS0 + 0.2, 99, "우리 회사에 맞게 구성된", "M-AI Works 워크스페이스")):
        k = e_out_cubic(prog(t, t0, 0.5)) * (1 - e_io_cubic(prog(t, t1, 0.3)))
        if k <= 0:
            continue
        dy = 12 * (1 - k)
        c.save()
        c.translate(300, 860)
        c.scale(1.0, 0.42)
        radial(c, 0, 0, 620, NAVY_950, 0.42 * k, blend=skia.BlendMode.kSrcOver)
        c.restore()
        for col_, bl, al in ((NAVY_950, 6, 0.55), (WHITE, 0, 1.0)):
            p_ = skia.Paint(AntiAlias=True, Color4f=E.col(col_, clamp(k * al)))
            if bl:
                p_.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
            c.drawString(small, 96, 820 + dy, E.font(24, "SemiBold"), p_)
            c.drawString(big, 96, 876 + dy, E.font(46, "Bold"), p_)


def ceiling(c, t):
    img = plate("ceiling", t)
    if img is not None:
        c.drawImageRect(img, R(0, 0, W, H), E.SAMP, skia.Paint(AntiAlias=True))
    c.save()
    c.concat(plane_matrix())                # one fixed perspective: the camera is locked off
    lp = skia.Paint()
    lp.setAlphaf(0.92)
    c.saveLayer(None, lp)
    ceiling_ui(c, t)
    c.restore()
    c.restore()
    caption(c, t)


def part_b(c, t):
    if t < T_CEIL:
        monitor(c, t)
        return
    if t < T_CEIL + 0.25:
        u = e_io_cubic((t - T_CEIL) / 0.25)
        A = snap(2, lambda cc: monitor(cc, t))
        B = snap(3, lambda cc: ceiling(cc, t))
        draw_img(c, B, 1.0, 10 * (1 - u))
        draw_img(c, A, 1 - u, 12 * u, 1.0, dy=-260 * u)
        return
    ceiling(c, t)


def frame(f, surf, finish):
    t = ft(f)
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    c.save()
    c.scale(SCV, SCV)
    render(c, t)
    c.restore()
    raw = surf.makeImageSnapshot().toarray()[..., :3].astype(np.float32)
    fin = finish.apply(surf, F_TL + f).astype(np.float32)
    w = e_io_sine(clamp(f / 30))          # the film finish eases in (the previous segment has none)
    img = raw * (1 - w) + fin * w
    bar = int(round(BAR * SCV))
    img[:bar] = 0
    img[-bar:] = 0
    return np.clip(img + 0.5, 0, 255).astype(np.uint8)


def setup(height):
    global SCV
    E.configure(E.SEED, E.CHAOS)
    SCV = max(1.0, height / H)
    POOL.clear()
    SWD, SHD = int(round(W * SCV)), int(round(H * SCV))
    info = skia.ImageInfo.Make(SWD, SHD, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info), E.Finish(size=(SWD, SHD)), SWD, SHD


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
