"""Patch 00:00:39:14-00:00:44:02 (109 frames) of seg_axpoint: the improvement-task candidates page is replaced by
the M-AI Works window (the AXCORE app: sidebar with the core features, the feature cards with their toggles - the
ones the ceiling shot switches on next). Same motion as before: it comes out of the diagnosis on the soft
cross-blur, the parts blur in one by one under the slow camera, the page becomes a browser window, turns
transparent over the man at his desk and hands over to the ceiling shot. Everything else is seg_axpoint's own
render, so the first and the last frame join the delivered file.
Usage: python3 seg_maiworks.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import skia

import engine as E
import seg_axpoint as A
from engine import (W, R, BLUE, INK, STEEL, STEEL_200, STEEL_400, WHITE, lerp, prog, clamp, e_io_sine,
                    e_out_cubic, paint_fill, paint_stroke, rrect, rrect_stroke, text, text_w, icon)

F0, F1 = 950 - A.F_TL, 1058 - A.F_TL + 1      # timeline 39:14 .. 44:02
T0 = A.T_CANDS
LINE = A.LINE
SIDE_W = 300
NAV_TOP = [("주요 정보", "grid"), ("AI대화", "chat"), ("자료실", "folder"), ("알림", "bell"),
           ("M-AI Works", "spark")]
FEATS = [("경영지원", "인사 · 급여 · 회계", "user"), ("제품설계", "도면 · BOM", "cube"),
         ("생산관리", "작업 지시 · 모니터링", "factory"), ("장비관리", "정비 예측 · 노후 설비", "gear"),
         ("품질검사", "불량 분석 · 검수", "scan"), ("재고·물류", "실시간 재고 · 수요 예측", "box"),
         ("영업관리", "수주 · 단가 견적", "chart"), ("고객지원", "AS · VOC 분석", "chat")]
GX0, GY0, GW, GH, GG = 380, 350, 345, 196, 20


def card_time(i):
    return T0 + 0.5 + i * 0.12


def side_time(j):
    return T0 + 0.25 + j * 0.035


def small_toggle(c, x, y, k, a):
    w, h = 50, 28
    r = R(x - w, y, w, h)
    rrect(c, r, h / 2, A.colint_mix("#D5DAE4", BLUE, k), a)
    kx = lerp(r.left() + h / 2, r.right() - h / 2, k)
    c.drawCircle(kx, r.centerY() + 1, h * 0.36, paint_fill("#0B1B3F", 0.12 * a, blur=2))
    c.drawCircle(kx, r.centerY(), h * 0.36, paint_fill(WHITE, a))


def nav_icon(c, kind, x, y, col, a):
    """Line icons of the app's sidebar that engine.icon lacks (grid, folder, bell)."""
    p = paint_stroke(col, a, 1.6)
    if kind == "grid":
        for dx in (-5.5, 5.5):
            for dy in (-5.5, 5.5):
                c.drawRRect(skia.RRect.MakeRectXY(R(x + dx - 4, y + dy - 4, 8, 8), 2, 2), p)
    elif kind == "folder":
        pth = skia.Path()
        pth.moveTo(x - 9, y - 6)
        pth.lineTo(x - 3, y - 6)
        pth.lineTo(x - 1, y - 3)
        pth.lineTo(x + 9, y - 3)
        pth.lineTo(x + 9, y + 7)
        pth.lineTo(x - 9, y + 7)
        pth.close()
        c.drawPath(pth, p)
    elif kind == "bell":
        pth = skia.Path()
        pth.moveTo(x - 7, y + 5)
        pth.cubicTo(x - 6, y + 2, x - 6, y - 1, x - 6, y - 2)
        pth.cubicTo(x - 6, y - 7, x - 3, y - 9, x, y - 9)
        pth.cubicTo(x + 3, y - 9, x + 6, y - 7, x + 6, y - 2)
        pth.cubicTo(x + 6, y - 1, x + 6, y + 2, x + 7, y + 5)
        pth.close()
        c.drawPath(pth, p)
        c.drawLine(x - 2, y + 8, x + 2, y + 8, p)
    else:
        icon(c, kind, x, y, 18, col, a, 1.6)


def sidebar(c, t):
    c.drawRect(R(-2000, -2000, 2000 + SIDE_W, 6000), paint_fill("#F6F7FA"))
    c.drawLine(SIDE_W, -2000, SIDE_W, 4000, paint_stroke("#E6E8EE", 1.0, 1.2))
    k, dy, bl = A.blur_in(t, T0 + 0.2, 0.5)
    E.logo().draw(c, 104, 186 + dy, 128, 1.0, 1.0, (1.0, 1.0, 1.0), False, k)
    text(c, "‹", SIDE_W - 34, 192 + dy, 22, "Medium", STEEL_400, k, "center")
    y = 236
    for j, (lab, ic) in enumerate(NAV_TOP):
        kk, dyy, _ = A.blur_in(t, side_time(j), 0.45)
        on = lab == "M-AI Works"
        if on:
            r = R(18, y + dyy - 21, SIDE_W - 36, 42)
            rrect(c, r.makeOffset(0, 2), 10, "#3A55B8", 0.06 * kk, blur=6)
            rrect(c, r, 10, WHITE, kk)
            rrect_stroke(c, r, 10, LINE, kk, 1.0)
        nav_icon(c, ic, 46, y + dyy, BLUE if on else STEEL, kk)
        text(c, lab, 70, y + dyy + 6, 16, "Bold" if on else "SemiBold", INK if on else "#2B3342", kk)
        y += 44
    kk, dyy, _ = A.blur_in(t, side_time(len(NAV_TOP)), 0.45)
    text(c, "핵심 기능", 34, y + 22 + dyy, 12, "SemiBold", STEEL_400, kk)
    y += 56
    for j, (lab, _, ic) in enumerate(FEATS):
        kk, dyy, _ = A.blur_in(t, side_time(len(NAV_TOP) + 1 + j), 0.45)
        icon(c, ic, 46, y + dyy, 16, STEEL, kk, 1.5)
        text(c, lab, 70, y + dyy + 5, 15, "Medium", "#2B3342", kk)
        y += 40
    kk, dyy, _ = A.blur_in(t, side_time(len(NAV_TOP) + 9), 0.45)
    c.drawLine(0, 852, SIDE_W, 852, paint_stroke("#E6E8EE", kk, 1.0))
    rrect(c, R(30, 870 + dyy, 40, 40), 10, WHITE, kk)
    rrect_stroke(c, R(30, 870 + dyy, 40, 40), 10, LINE, kk, 1.0)
    c.drawCircle(44, 904 + dyy, 8, paint_fill("#1B2333", kk))
    text(c, A.COMPANY, 84, 886 + dyy, 15, "Bold", INK, kk)
    text(c, "홍길동 · 소유자", 84, 906 + dyy, 12, "Medium", STEEL, kk)
    text(c, "⌃", SIDE_W - 34, 896 + dyy, 14, "Medium", STEEL_400, kk, "center")


def works_page(c, t):
    A.light_bg(c)
    sidebar(c, t)
    k, dy, bl = A.blur_in(t, T0 + 0.2, 0.5)
    x0 = GX0
    text(c, "M-AI Works", x0, 226 + dy, 34, "Bold", INK, k)
    text(c, "필요한 기능만 골라 켜세요", x0 + text_w("M-AI Works", 34, "Bold") + 18, 224 + dy, 16, "Medium", STEEL, k)
    n = int(round(8 * clamp(prog(t, card_time(0), card_time(7) - card_time(0) + 0.15))))
    tw = text_w("개 기능", 17, "SemiBold")
    xr = GX0 + 4 * GW + 3 * GG
    text(c, "개 기능", xr, 226 + dy, 17, "SemiBold", STEEL, k, "right")
    A.gtext(c, str(n), xr - tw - 10, 232 + dy, 50, "Bold", k, align="right")
    # briefing bar (as the app's home)
    kb, dyb, _ = A.blur_in(t, T0 + 0.32, 0.5)
    br = R(x0, 262 + dyb, xr - x0, 58)
    rrect(c, br, 14, "#EAF0FF", kb)
    rrect_stroke(c, br, 14, "#DCE5FB", kb, 1.0)
    icon(c, "spark", br.left() + 28, br.centerY(), 18, BLUE, kb, 1.6)
    text(c, "홍길동 님, 우리 회사에 필요한 기능을 켜 보세요", br.left() + 52, br.centerY() + 6, 16, "Bold", INK, kb)
    text(c, "AI 추천 5개", br.left() + 52 + text_w("홍길동 님, 우리 회사에 필요한 기능을 켜 보세요", 16, "Bold") + 14,
         br.centerY() + 6, 14, "Medium", STEEL, kb)
    text(c, "전체 보기  ›", br.right() - 24, br.centerY() + 6, 14, "Medium", STEEL, kb, "right")
    # feature cards with their toggles (all off: the ceiling shot switches them on)
    for i, (name, sub, ic) in enumerate(FEATS):
        kk, dyy, bl = A.blur_in(t, card_time(i), 0.45)
        if kk <= 0:
            continue
        r = R(GX0 + (i % 4) * (GW + GG), GY0 + (i // 4) * (GH + GG) + dyy * 1.6, GW, GH)
        A.blur_layer(c, bl, kk)
        rrect(c, r.makeOffset(0, 6), 16, "#3A55B8", 0.07, blur=10)
        rrect(c, r, 16, WHITE, 1.0)
        rrect_stroke(c, r, 16, LINE, 1.0, 1.2)
        rrect(c, R(r.left() + 22, r.top() + 22, 52, 52), 14, "#EEF1F6", 1.0)
        icon(c, ic, r.left() + 48, r.top() + 48, 26, STEEL_400, 1.0, 2.4)
        small_toggle(c, r.right() - 22, r.top() + 34, 0.0, 1.0)
        text(c, name, r.left() + 24, r.top() + 128, 22, "Bold", INK, 1.0)
        text(c, sub, r.left() + 24, r.top() + 158, 14, "Medium", STEEL, 1.0)
        sk = e_io_sine(prog(t, card_time(i) + 0.2, 0.5))
        if i in (1, 2, 3, 4, 5):
            A.chip(c, "★ AI 추천", r.right() - 22, r.bottom() - 40, 11, BLUE, "#E6EEFF", sk, h=22, right=True, pad=9)
        c.restore()
    kb = e_io_sine(prog(t, card_time(7) + 0.2, 0.6))
    if kb > 0:
        bar = R(x0, 792 + 10 * (1 - kb), xr - x0, 58)
        rrect(c, bar.makeOffset(0, 4), 14, "#3A55B8", kb * 0.08, blur=10)
        rrect(c, bar, 14, WHITE, kb)
        rrect_stroke(c, bar, 14, LINE, kb, 1.2)
        text(c, "켜진 기능 0개", bar.left() + 22, bar.top() + 25, 15, "Bold", INK, kb)
        text(c, "켠 기능으로 우리 회사 AI 워크스페이스를 구성해요", bar.left() + 22, bar.top() + 45, 12, "Medium", STEEL, kb)
        b = R(bar.right() - 252, bar.top() + 10, 240, 38)
        rrect(c, b, 10, "#A9C3FF", kb)
        text(c, "워크스페이스 구성하기  →", b.centerX(), b.centerY() + 5, 14, "Bold", WHITE, kb, "center")


def works(c, t):
    c.save()
    A.apply_cam(c, A.CAM_CANDS, t)
    works_page(c, t)
    c.restore()


def chrome(c, a, y0):
    """Browser chrome along the top of the band (as seg_axpoint's, for the AXCORE app)."""
    if a <= 0.003:
        return
    c.drawRect(R(0, y0, W, 80), paint_fill("#F3F4F8", a))
    tab = R(18, y0 + 8, 330, 34)
    rrect(c, tab, 10, WHITE, a)
    A.diamond(c, tab.left() + 22, tab.centerY(), 7, BLUE, a)
    text(c, "AXCORE · M-AI Works", tab.left() + 40, tab.centerY() + 5, 13, "SemiBold", INK, a)
    text(c, "×", tab.right() - 18, tab.centerY() + 5, 15, "Medium", STEEL, a, "center")
    text(c, "+", tab.right() + 22, tab.centerY() + 6, 18, "Medium", STEEL, a, "center")
    for j, s in enumerate(("←", "→", "↻")):
        text(c, s, 36 + j * 34, y0 + 67, 16, "Medium", STEEL, a, "center")
    url = R(150, y0 + 48, 1620, 26)
    rrect(c, url, 13, "#E6E8EF", a)
    c.drawCircle(url.left() + 16, url.centerY(), 5, paint_stroke(STEEL_400, a, 1.4))
    text(c, "axcore  /  M-AI Works", url.left() + 34, url.centerY() + 5, 13, "Medium", STEEL, a)
    c.drawLine(0, y0 + 80, W, y0 + 80, paint_stroke("#DADDE6", a, 1.0))


_cands = A.cands
TA = (950 / 24.0, 0.30)          # first frames: the incoming page (still faint and blurred) turns from the original


def works_or_orig(c, t):
    m = e_io_sine(prog(t, *TA))
    if m < 1:
        _cands(c, t)
        p = skia.Paint()
        p.setAlphaf(m)
        c.saveLayer(None, p)
    works(c, t)
    if m < 1:
        c.restore()


A.cands = works_or_orig  # part_a's cross-blur from the diagnosis and the monitor shot both draw it
A.chrome = chrome

if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    a, b = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (F0, F1)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = A.setup(height)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(a, b):
        enc.stdin.write(A.frame(f, surf, finish).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
