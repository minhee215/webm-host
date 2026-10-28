"""Segment 00:00:57:21-00:01:02:19 (119 frames) - "업무 파일은 데이터로, / 수기 정보는 OCR을 통해 연결합니다."

  57:21  hard cut to the digital-city plate (clips/bg_ocr_lo, from the client's upload), which falls out of focus
         at once; the "업무 파일" folder rises from below, the cursor clicks it and it opens
         (the client's reference: folder -> click -> open -> zoom out over a field of documents -> they swirl into
         a ring)
  58.9s  the files (the names used earlier in the film, contents unreadable, a type badge on each: XLSX, PDF, DOCX,
         HWP, JPG) burst out of the folder while the camera pulls back
  59.8s  they swirl into a tilted ring and pour into a data table, whose rows fill one by one
  60.6s  the table moves left; a handwritten work-log card rises on the right, a scan line with a diamond sweeps
         down it and the handwriting turns into digital fields (OCR); the record flies into the table as its new row
Frame f is timeline frame 1389 + f; film time = timeline frame / 24 (narration at its original timing).
23.976 fps, 21:9 letterbox.
Usage: python3 seg_ocr.py <out.mp4> [height=480] [first last]
"""
import math
import os
import subprocess
import sys

import numpy as np
import skia

import engine as E
import seg_axpoint as A
from engine import (W, H, R, BLUE, INK, STEEL_200, STEEL_400, WHITE, NAVY_950, CYAN, lerp, prog, clamp,
                    e_io_cubic, e_io_sine, e_out_cubic, e_out_expo, e_in_cubic, paint_fill, paint_stroke,
                    rrect, rrect_stroke, text, text_w, icon, poly, colint)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 57 * 24 + 21              # 00:00:57:21
NF = 62 * 24 + 19 - F_TL + 1     # through 00:01:02:19 (119 frames)
T0 = F_TL / 24.0
VIOLET = "#8B6CFF"
BG_DIR = os.path.join(E.HERE, "clips", "bg_ocr_lo")
BG_DIR_HI = os.path.join(E.HERE, "clips", "bg_ocr_hi")
BG_SHARP = 12                    # frames 0-11 sharp (640 wide); later frames come pre-blurred (480 wide, sigma 2.2)
BG_PRE = 2.2 * W / 480           # their blur in logical px
BG_BLUR = 30.0
SCV = 1.0

# beats, in seconds from the cut
S_FOLD = 0.12                    # the folder rises
S_HOVER, S_CLICK, S_OPEN = 0.62, 0.80, 0.86
S_BURST = 0.98                   # the files burst out, the camera pulls back
S_SWIRL = 1.70                   # ... swirl into the ring
S_TABLE = 1.95                   # the data table
S_POUR = 2.15                    # files pour into it
S_SHIFT = 2.55                   # table to the left, the handwritten card rises
S_SCAN, S_SCAN_D = 2.92, 0.68
S_SEND, SEND_D = 3.62, 0.95      # the recognised record flies to the table (unhurried: the next shot's
S_LAND = S_SEND + SEND_D - 0.1   # transition starts from this frame)


def ft(f):
    return (F_TL + f) / 24.0


# ---------------------------------------------------------------- background
_BG = {}


def bg_img(i):
    i = max(0, min(NF - 1, i))
    if i not in _BG:
        hi = os.path.join(BG_DIR_HI, "%03d.jpg" % i)          # the first frames, still sharp, at full size
        _BG[i] = skia.Image.open(hi if SCV > 1 and os.path.exists(hi) else os.path.join(BG_DIR, "%03d.png" % i))
    return _BG[i]


def background(c, s):
    c.drawRect(R(0, 0, W, H), paint_fill("#071230", 1.0))
    i = int(round(s * 24))
    img = bg_img(i)
    k = max(W / img.width(), H / img.height())
    z = 1.02 + 0.05 * s / 5.0                             # a slow push the whole time
    target = BG_BLUR * e_io_sine(prog(s, 0.10, 0.45))
    blur = target if i < BG_SHARP else math.sqrt(max(0.0, BG_BLUR ** 2 - BG_PRE ** 2))
    p = skia.Paint(AntiAlias=True)
    p.setColorFilter(E.grade_filter(bright=1.0, contrast=1.02, sat=0.95))
    if blur > 0.1:
        p.setImageFilter(skia.ImageFilters.Blur(blur / k, blur / k, skia.TileMode.kClamp))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(z * k, z * k)
    c.translate(-img.width() / 2, -img.height() / 2)
    d = e_io_sine(prog(s, 0.10, 0.5))
    p.setAlphaf(1 - 0.5 * d)                              # it goes soft and half transparent over the navy
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()
    c.drawRect(R(0, 0, W, H), paint_fill(NAVY_950, 0.30 * d))
    sh = skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), 1150,
                                        [colint(NAVY_950, 0.0), colint(NAVY_950, 0.45 * d)], [0.35, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


# ---------------------------------------------------------------- folder
FOLD = (960, 500)
FW, FH = 250, 188
CYAN_A, CYAN_B = "#5EE0FF", "#22AEE6"


def folder(c, x, y, s, a, opened, hi):
    if a <= 0.003:
        return
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if hi > 0:                                           # selected: the soft box behind it (reference)
        rrect(c, R(-FW / 2 - 34, -FH / 2 - 30, FW + 68, FH + 120), 18, WHITE, 0.14 * hi * a)
        rrect_stroke(c, R(-FW / 2 - 34, -FH / 2 - 30, FW + 68, FH + 120), 18, WHITE, 0.25 * hi * a, 1.2)
    L, T = -FW / 2, -FH / 2
    rrect(c, R(L, T + 18, FW, FH - 18).makeOffset(0, 12), 16, NAVY_950, 0.35 * a, blur=18)
    back = skia.Path()
    back.addRRect(skia.RRect.MakeRectXY(R(L, T + 16, FW, FH - 16), 14, 14))
    back.addRRect(skia.RRect.MakeRectXY(R(L, T, FW * 0.42, 40), 12, 12))
    sh = skia.GradientShader.MakeLinear([skia.Point(0, T), skia.Point(0, T + FH)], [colint("#2FC2F2", a),
                                                                                       colint("#1690CF", a)])
    c.drawPath(back, skia.Paint(AntiAlias=True, Shader=sh))
    if opened > 0:                                       # paper peeking out
        rrect(c, R(L + 16, T + 22 - 10 * opened, FW - 32, FH - 40), 6, WHITE, 0.92 * a * opened)
    # front flap: tilts open (its top edge drops forward)
    o = opened
    ft_ = T + 34 + 26 * o
    fl = L - 10 * o
    fr = L + FW + 10 * o
    front = poly([(fl + 6 * o, ft_), (fr - 6 * o, ft_), (L + FW, T + FH), (L, T + FH)], True)
    sh2 = skia.GradientShader.MakeLinear([skia.Point(0, ft_), skia.Point(0, T + FH)], [colint(CYAN_A, a),
                                                                                       colint(CYAN_B, a)])
    fp = skia.Paint(AntiAlias=True, Shader=sh2)
    fp.setPathEffect(skia.CornerPathEffect.Make(12))
    c.drawPath(front, fp)
    c.drawLine(fl + 18, ft_ + 1, fr - 18, ft_ + 1, paint_stroke(WHITE, 0.35 * a, 1.4))
    c.restore()


# ---------------------------------------------------------------- documents
TYPES = {"XLSX": ("X", "#1E9E5A"), "PDF": ("P", "#E5484D"), "DOCX": ("W", "#2F6BFF"), "HWP": ("H", "#1AA3D8"),
         "JPG": ("J", "#8A63D2")}
DOCS = [("생산일보_2026_09", "XLSX"), ("품질검사 성적서_Q3", "PDF"), ("작업표준서_가공라인", "DOCX"),
        ("설비 점검표_2026", "HWP"), ("수주 · 출하 현황", "XLSX"), ("BOM_제품A-12", "PDF"), ("재고 현황_10월", "XLSX"),
        ("공정 개선 회의록", "DOCX"), ("현장사진_3라인", "JPG"), ("작업지시서_A-12", "PDF"), ("자재수불대장", "XLSX"),
        ("부적합 보고서", "HWP"), ("출하 성적서_10월", "PDF"), ("설비 사진_0914", "JPG"), ("수입검사 성적서", "PDF"),
        ("시정조치 요구서", "HWP"), ("VOC 대장", "XLSX"), ("제품 도면_A-12", "PDF"), ("공정 검사 체크", "XLSX"),
        ("검수 사진_0921", "JPG"), ("규격서_가공품", "DOCX"), ("생산 계획_11월", "XLSX")]
DW, DH = 170, 226
_DOC_IMG = {}


def _doc_draw(c, i):
    name, kind = DOCS[i]
    letter, colr = TYPES[kind]
    r = R(0, 0, DW, DH)
    rrect(c, r, 6, "#F7F8FA", 1.0)
    rr = np.random.default_rng(100 + i)
    if kind == "JPG":                                    # a photo: soft blocks of colour
        img_r = R(12, 14, DW - 24, DH - 70)
        sh = skia.GradientShader.MakeLinear([skia.Point(0, img_r.top()), skia.Point(0, img_r.bottom())],
                                            [colint("#8FA3B8"), colint("#4E5F72")])
        c.drawRRect(skia.RRect.MakeRectXY(img_r, 4, 4), skia.Paint(AntiAlias=True, Shader=sh))
        for _ in range(4):
            x, y = rr.uniform(img_r.left(), img_r.right() - 40), rr.uniform(img_r.top() + 30, img_r.bottom() - 30)
            rrect(c, R(x, y, rr.uniform(20, 50), rr.uniform(14, 40)), 3, "#C7D2DE", 0.55)
    else:
        rrect(c, R(DW / 2 - 34, 18, 68, 7), 3.5, "#9AA3AF", 0.9)          # title
        y = 40
        while y < DH - 64:
            if kind == "XLSX" and y < DH - 90:                              # a table
                for col in range(4):
                    rrect(c, R(14 + col * 37, y, 31, 5), 2.5, "#B9C1CC", 0.9)
                c.drawLine(12, y + 10, DW - 12, y + 10, paint_stroke("#DDE2E8", 1.0, 1.0))
                y += 15
            else:
                w_ = rr.uniform(0.55, 0.95) * (DW - 28)
                rrect(c, R(14, y, w_, 4.5), 2.2, "#B9C1CC", 0.85)
                y += 11
        if kind in ("PDF", "HWP"):                                         # a stamp
            rrect_stroke(c, R(DW - 42, DH - 92, 22, 22), 3, "#E5484D", 0.55, 1.4)
    # file strip at the bottom: type badge + name
    rrect(c, R(0, DH - 40, DW, 40), 6, WHITE, 1.0)
    c.drawLine(0, DH - 40, DW, DH - 40, paint_stroke("#E3E7EE", 1.0, 1.0))
    rrect(c, R(9, DH - 31, 22, 22), 5, colr, 1.0)
    text(c, letter, 20, DH - 15, 12, "Bold", WHITE, 1.0, "center")
    nm = name
    while text_w(nm, 11, "SemiBold") > DW - 46 and len(nm) > 3:
        nm = nm[:-2] + "…"
    text(c, nm, 38, DH - 15.5, 11, "SemiBold", INK, 1.0)
    # type tag on the corner (reference: PDF / JPG / HWP marks)
    tw = text_w(kind, 10, "Bold") + 12
    rrect(c, R(DW - tw - 8, 8, tw, 18), 4, colr, 1.0)
    text(c, kind, DW - 8 - tw / 2, 21, 10, "Bold", WHITE, 1.0, "center")


def doc_img(i):
    if i not in _DOC_IMG:
        k = SCV * 1.7
        info = skia.ImageInfo.Make(int(DW * k) + 2, int(DH * k) + 2, skia.ColorType.kRGBA_8888_ColorType,
                                   skia.AlphaType.kPremul_AlphaType)
        s = skia.Surface.MakeRaster(info)
        cc = s.getCanvas()
        cc.clear(skia.Color4f(0, 0, 0, 0))
        cc.scale(k, k)
        _doc_draw(cc, i)
        _DOC_IMG[i] = s.makeImageSnapshot()
    return _DOC_IMG[i]


def _field():
    """Each document's resting place: (x, y) offset from the folder at depth 1, depth z, tilt."""
    rr = np.random.default_rng(7)
    out = []
    cols, rows = 7, 4
    cells = [(cx, cy) for cy in range(rows) for cx in range(cols)]
    rr.shuffle(cells)
    for i in range(len(DOCS)):
        cx, cy = cells[i]
        x = (cx - (cols - 1) / 2) * 300 + rr.uniform(-60, 60)
        y = (cy - (rows - 1) / 2) * 250 + rr.uniform(-40, 40)
        if abs(x) < 180 and abs(y) < 160:                # keep the folder visible
            x += 230 * (1 if x >= 0 else -1)
        out.append((x, y, rr.uniform(0.85, 1.55), rr.uniform(-5, 5), rr.uniform(0, 0.18)))
    return out


FIELD = _field()
RING_C = (960, 540)
RING_RX, RING_RY, RING_TILT = 640, 205, -9.0


def ring_pt(th):
    x, y = RING_RX * math.cos(th), RING_RY * math.sin(th)
    ca, sa = math.cos(math.radians(RING_TILT)), math.sin(math.radians(RING_TILT))
    return RING_C[0] + x * ca - y * sa, RING_C[1] + x * sa + y * ca


def cam_pull(s):
    return 0.42 * e_out_cubic(prog(s, S_OPEN, 1.6))      # the camera pulls back from the folder


def doc_state(i, s):
    """(x, y, scale, rot, alpha, motion blur px, absorbed) of document i."""
    fx, fy, z, rot, delay = FIELD[i]
    u = e_out_expo(prog(s, S_BURST + delay, 0.75))
    pull = cam_pull(s)
    zz = z + pull
    x = FOLD[0] + u * fx / zz * 1.25
    y = FOLD[1] + u * fy / zz * 1.25
    sc = lerp(0.18, 1.0, e_out_cubic(prog(s, S_BURST + delay, 0.5))) / zz * 1.4
    a = clamp((s - S_BURST - delay) / 0.08)
    mb = 26 * (1 - u) if u > 0 else 0
    # swirl onto the ring
    th0 = math.atan2(y - RING_C[1], (x - RING_C[0]) * RING_RY / RING_RX)
    q = e_io_cubic(prog(s, S_SWIRL + 0.01 * i, 0.55))
    if q > 0:
        spin = 2.2 * e_in_cubic(prog(s, S_SWIRL, 0.9)) + 1.4 * max(0.0, s - S_SWIRL - 0.9)
        rx, ry = ring_pt(th0 + spin)
        x, y = lerp(x, rx, q), lerp(y, ry, q)
        sc = lerp(sc, 0.36, q)
        rot = lerp(rot, 0, q)
        mb = max(mb, 30 * math.sin(math.pi * clamp(q)) + 14 * q)
    # pour into the table
    tp = pour_time(i)
    w = e_in_cubic(prog(s, tp, 0.32))
    absorbed = s >= tp + 0.32
    if w > 0:
        tx, ty = table_rect(s).centerX(), table_rect(s).centerY() - 20
        x, y = lerp(x, tx, w), lerp(y, ty, w)
        sc *= (1 - 0.85 * w)
        a *= 1 - w
    return x, y, sc, rot, a, mb, absorbed


def pour_time(i):
    return S_POUR + 0.022 * ((i * 7) % len(DOCS))


def documents(c, s):
    order = sorted(range(len(DOCS)), key=lambda i: FIELD[i][2], reverse=True)       # far ones first
    for i in order:
        x, y, sc, rot, a, mb, absorbed = doc_state(i, s)
        if a <= 0.003 or absorbed:
            continue
        img = doc_img(i)
        k = SCV * 1.7
        c.save()
        c.translate(x, y)
        c.rotate(rot)
        c.scale(sc / k, sc / k)
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(clamp(a))
        if mb > 0.5:
            p.setImageFilter(skia.ImageFilters.Blur(mb * 0.5 * k / max(sc, 0.2), mb * 0.25 * k / max(sc, 0.2),
                                                    skia.TileMode.kDecal))
        rrect(c, R(-DW * k / 2 + 6 * k, -DH * k / 2 + 14 * k, DW * k, DH * k), 8 * k, NAVY_950, 0.35 * a,
              blur=14 * k)
        c.drawImage(img, -img.width() / 2, -img.height() / 2, E.SAMP, p)
        c.restore()


def ring_len():
    pts = [ring_pt(th) for th in np.linspace(0, 2 * math.pi, 181)]
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def ring_trail(c, s):
    """The glowing orbit the swirl leaves (reference), fading once the table takes over."""
    d = e_io_cubic(prog(s, S_SWIRL + 0.15, 0.7))
    a = d * (1 - e_io_sine(prog(s, S_SHIFT - 0.1, 0.5)))
    if a <= 0.003:
        return
    pts = [ring_pt(th) for th in np.linspace(0, 2 * math.pi, 181)]
    pth = poly(pts, True)
    sh = skia.GradientShader.MakeSweep(RING_C[0], RING_C[1], [colint("#5AB8FF", a), colint(VIOLET, a),
                                                              colint(WHITE, a), colint("#5AB8FF", a)], None)
    for wdt, al, bl in ((12, 0.22, 10), (3.2, 1.0, 0)):
        p = skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=wdt, Shader=sh)
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setAlphaf(al)
        if bl:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
        p.setPathEffect(skia.DashPathEffect.Make([ring_len() * d + 1, 1e5], 0))
        c.drawPath(pth, p)


# ---------------------------------------------------------------- data table
TW_, TH_ = 520, 372
N_ROWS = 6


def table_rect(s):
    q = e_io_cubic(prog(s, S_SHIFT, 0.55))
    cx, cy = lerp(RING_C[0], 590, q), lerp(RING_C[1], 548, q)
    sc = lerp(1.05, 1.12, q)
    return R(cx - TW_ * sc / 2, cy - TH_ * sc / 2, TW_ * sc, TH_ * sc)


def row_fill(j, s):
    """Rows fill as the documents pour in."""
    n = sum(1 for i in range(len(DOCS)) if s >= pour_time(i) + 0.32)
    return clamp(n / len(DOCS) * N_ROWS - j)


def records(s):
    n = sum(1 for i in range(len(DOCS)) if s >= pour_time(i) + 0.32)
    v = int(round(1248 * n / len(DOCS)))
    if s >= S_LAND:
        v += 1
    return v


def table(c, s):
    k, dy, bl = A.blur_in(s, S_TABLE, 0.6)
    if k <= 0.003:
        return
    r0 = table_rect(s)
    z = lerp(0.92, 1.0, e_out_cubic(prog(s, S_TABLE, 0.6)))
    c.save()
    c.translate(r0.centerX(), r0.centerY() + dy)
    c.scale(z * r0.width() / TW_, z * r0.width() / TW_)
    c.translate(-TW_ / 2, -TH_ / 2)
    A.blur_layer(c, bl, k)
    r = R(0, 0, TW_, TH_)
    rrect(c, r.makeOffset(0, 14), 22, NAVY_950, 0.45, blur=26)
    rrect(c, r, 22, WHITE, 0.95)
    rrect_stroke(c, r, 22, WHITE, 1.0, 1.2)
    text(c, "데이터 테이블", 30, 48, 22, "Bold", INK)
    text(c, "레코드 %s건" % format(records(s), ","), 30, 72, 13, "SemiBold", STEEL_400)
    icon(c, "db", TW_ - 44, 44, 28, BLUE, 1.0, 2.2)
    xs = [30, 150, 270, 390]
    c.drawLine(24, 96, TW_ - 24, 96, paint_stroke("#E3E7EE", 1.0, 1.0))
    for x in xs:
        rrect(c, R(x, 108, 92, 9), 4.5, BLUE, 1.0)
    rr = np.random.default_rng(3)
    widths = rr.uniform(0.45, 0.95, (N_ROWS + 1, 4))
    for j in range(N_ROWS + 1):
        y = 134 + j * 32
        c.drawLine(24, y - 8, TW_ - 24, y - 8, paint_stroke("#EEF1F5", 1.0, 1.0))
        if j < N_ROWS:
            f = e_out_cubic(row_fill(j, s))
            for col, x in enumerate(xs):
                rrect(c, R(x, y + 4, 92 * widths[j, col], 8), 4, "#EEF1F5", 1.0)
                if f > 0:
                    rrect(c, R(x, y + 4, 92 * widths[j, col] * f, 8), 4, "#C3CAD4", 1.0)
            if 0 < row_fill(j, s) < 1:
                rrect(c, R(18, y - 4, TW_ - 36, 28), 8, BLUE, 0.06)
        else:                                            # the OCR row
            f = e_out_cubic(prog(s, S_LAND - 0.05, 0.45))
            hl = e_io_sine(prog(s, S_LAND - 0.05, 0.3))
            if f > 0:
                rrect(c, R(18, y - 4, TW_ - 36, 28), 8, CYAN, 0.10 * f + 0.10 * hl)
                rrect_stroke(c, R(18, y - 4, TW_ - 36, 28), 8, "#29B6E8", 0.6 * hl, 1.2)
                vals = ["09.14", "3라인", "건조온도 편차", "재작업 12EA"]
                for col, x in enumerate(xs):
                    text(c, vals[col], x, y + 15, 13, "SemiBold", INK, f)
                tw = text_w("OCR", 10, "Bold") + 12
                rrect(c, R(TW_ - 30 - tw, y + 1, tw, 18), 5, "#1AA3D8", f)
                text(c, "OCR", TW_ - 30 - tw / 2, y + 14, 10, "Bold", WHITE, f, "center")
    c.restore()
    c.restore()


# ---------------------------------------------------------------- the handwritten card + OCR
CARD = R(1000, 392, 700, 312)
CUT = 18
HAND = None


def hand_font(size):
    global HAND
    if HAND is None:
        HAND = skia.Typeface.MakeFromFile(os.path.join(E.FONT_DIR, "NanumPenScript-Regular.ttf"))
    f = skia.Font(HAND, size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def handwrite(c, s_, x, y, size, color, a, seed):
    """Handwriting: each letter with a little drift in size, angle and baseline."""
    f = hand_font(size)
    rr = np.random.default_rng(seed)
    p = paint_fill(color, a)
    for ch in s_:
        w = f.measureText(ch)
        if ch != " ":
            c.save()
            c.translate(x, y + rr.uniform(-2.0, 2.0))
            c.rotate(rr.uniform(-4, 4))
            c.scale(rr.uniform(0.94, 1.06), rr.uniform(0.94, 1.06))
            c.drawString(ch, 0, 0, f, p)
            c.restore()
        x += w * 1.02
    return x


def chamfer(r, k):
    return poly([(r.left() + k, r.top()), (r.right() - k, r.top()), (r.right(), r.top() + k),
                 (r.right(), r.bottom() - k), (r.right() - k, r.bottom()), (r.left() + k, r.bottom()),
                 (r.left(), r.bottom() - k), (r.left(), r.top() + k)], True)


LINES = [("9/14   3라인  건조온도 편차", 128), ("→  재작업 12EA 확인", 232)]
FIELDS = [[("일자", "09.14", 0), ("라인", "3라인", 170), ("항목", "건조온도 편차", 330)],
          [("조치", "재작업 12EA 확인", 0)]]


def scan_y(s):
    return lerp(CARD.top() - 30, CARD.bottom() + 30, e_io_sine(prog(s, S_SCAN, S_SCAN_D)))


def card(c, s):
    k, dy, bl = A.blur_in(s, S_SHIFT + 0.12, 0.6)
    if k <= 0.003:
        return
    rise = 180 * (1 - e_out_cubic(prog(s, S_SHIFT + 0.12, 0.7)))
    c.save()
    c.translate(0, rise)
    A.blur_layer(c, bl, k)
    pth = chamfer(CARD, CUT)
    c.save()
    c.clipPath(pth, True)
    bf = skia.ImageFilters.Blur(24, 24, skia.TileMode.kClamp)
    rec = skia.Canvas.SaveLayerRec(None, None, bf, 0)
    c.saveLayer(rec)
    c.restore()
    c.restore()
    c.drawPath(pth, paint_fill(NAVY_950, 0.72))
    for j in range(1, 6):                                # ruled lines, like a work-log page
        y = CARD.top() + 52 * j + 20
        c.drawLine(CARD.left() + 26, y, CARD.right() - 26, y, paint_stroke("#9FB4D6", 0.10, 1.0))
    c.drawPath(pth, paint_stroke("#C9D6EA", 0.55, 1.2))
    # header tag above the card
    done = e_io_sine(prog(s, S_SCAN + S_SCAN_D - 0.05, 0.3))
    hx, hy = CARD.left(), CARD.top() - 40
    lab0, lab1 = "수기 작업일지", "디지털 데이터"
    w0 = text_w(lab0, 14, "SemiBold") + 44
    rrect(c, R(hx, hy, w0, 28), 14, NAVY_950, 0.55)
    rrect_stroke(c, R(hx, hy, w0, 28), 14, CYAN if done > 0.5 else "#C9D6EA", 0.6, 1.0)
    icon(c, "check" if done > 0.5 else "note", hx + 18, hy + 14, 14, CYAN if done > 0.5 else WHITE, 1.0, 1.6)
    text(c, lab0, hx + 32, hy + 19, 14, "SemiBold", WHITE, 1 - done)
    text(c, lab1, hx + 32, hy + 19, 14, "SemiBold", CYAN, done)
    # OCR result badge
    ok = e_io_sine(prog(s, S_SCAN + S_SCAN_D, 0.35))
    if ok > 0:
        b = "OCR 인식 완료 · 98.7%"
        bw = text_w(b, 13, "SemiBold") + 28
        rrect(c, R(CARD.right() - bw, hy + 1, bw, 26), 13, CYAN, 0.16 * ok)
        text(c, b, CARD.right() - bw / 2, hy + 19, 13, "SemiBold", CYAN, ok, "center")
    sy = scan_y(s) - rise * 0
    # the handwriting below the scan line, the digital fields above it
    c.save()
    c.clipRect(R(CARD.left(), sy, CARD.width(), CARD.bottom() - sy + 40))
    for j, (ln, by) in enumerate(LINES):
        handwrite(c, ln, CARD.left() + 44, CARD.top() + by, 58, "#EEF4FF", 0.95, 30 + j)
    c.restore()
    c.save()
    c.clipRect(R(CARD.left(), CARD.top() - 60, CARD.width(), max(0.0, sy - CARD.top() + 60)))
    for j, row in enumerate(FIELDS):
        base = CARD.top() + LINES[j][1]
        reveal = e_out_cubic(clamp((sy - (base - 34)) / 60))
        for lab, val, dx in row:
            x = CARD.left() + 44 + dx
            text(c, lab, x, base - 38, 15, "SemiBold", "#8FA6C8", reveal)
            text(c, val, x, base + 2, 32, "SemiBold", WHITE, reveal)
    c.restore()
    # recognition brackets just ahead of the line
    for j, (ln, by) in enumerate(LINES):
        base = CARD.top() + by
        q = clamp(1 - abs(sy - (base - 12)) / 70)
        if q > 0:
            w_ = hand_font(58).measureText(ln) + 16
            E.corner_brackets(c, R(CARD.left() + 32, base - 56, w_, 74), 12, CYAN, 0.9 * q, 2.0)
    # the scan line with its diamond (it overhangs the card, like the reference)
    on = clamp(prog(s, S_SCAN - 0.05, 0.12)) * (1 - clamp(prog(s, S_SCAN + S_SCAN_D, 0.15)))
    if on > 0:
        x0, x1 = CARD.left() - 26, CARD.right() + 60
        sh = skia.GradientShader.MakeLinear([skia.Point(0, sy - 46), skia.Point(0, sy)],
                                            [colint(CYAN, 0.0), colint(CYAN, 0.16 * on)])
        c.save()
        c.clipPath(pth, True)
        c.drawRect(R(CARD.left(), sy - 46, CARD.width(), 46), skia.Paint(Shader=sh))
        c.restore()
        c.drawLine(x0, sy, x1, sy, paint_stroke(CYAN, 0.35 * on, 7, blur=6))
        c.drawLine(x0, sy, x1, sy, paint_stroke("#7FE3FF", on, 1.8))
        A.diamond(c, x0, sy, 9, "#7FE3FF", on, 0)
        E.glow_dot(c, x0, sy, 18, CYAN, 0.6 * on)
    c.restore()
    c.restore()


def send(c, s):
    """The recognised record leaves the card for the table's new row; a link stays between them."""
    tr = table_rect(s)
    p0 = (CARD.left(), CARD.centerY())
    sc = tr.width() / TW_
    row_y = tr.top() + (134 + N_ROWS * 32 + 10) * sc
    p1 = (tr.right(), row_y)
    g = e_io_cubic(prog(s, S_SEND - 0.15, 0.8))
    if g > 0:
        pth = E.curve(p0, p1, 0.45)
        E.line(c, pth, CYAN, 0.9, 1.8, (0, g), glow=0.8)
        if s > S_SEND + 0.65:
            E.pulse(c, pth, ((s - S_SEND - 0.65) * 0.7) % 1.0, CYAN, 0.8, 12, 0.15)
    q = e_io_cubic(prog(s, S_SEND, SEND_D))
    if 0 < q < 1:
        x = lerp(p0[0] + 120, tr.centerX(), q)
        y = lerp(p0[1], row_y, q) - 60 * math.sin(math.pi * q)
        a = math.sin(math.pi * min(1.0, q * 1.15))
        s_ = lerp(1.0, 0.7, q)
        lab = "09.14 · 3라인 · 건조온도 편차 · 재작업 12EA"
        w = text_w(lab, 14, "SemiBold") + 34
        c.save()
        c.translate(x, y)
        c.scale(s_, s_)
        rrect(c, R(-w / 2, -18, w, 36), 18, NAVY_950, 0.75 * a)
        rrect_stroke(c, R(-w / 2, -18, w, 36), 18, CYAN, 0.8 * a, 1.2)
        text(c, lab, 0, 5, 14, "SemiBold", WHITE, a, "center")
        c.restore()


# ---------------------------------------------------------------- the folder beat
def folder_beat(c, s):
    rise = e_out_cubic(prog(s, S_FOLD, 0.55))
    a = e_io_sine(prog(s, S_FOLD, 0.4)) * (1 - e_io_sine(prog(s, S_SWIRL - 0.05, 0.35)))
    if a <= 0.003:
        return
    pull = cam_pull(s)
    shrink = lerp(1.0, 0.62, e_io_cubic(prog(s, S_OPEN, 0.45)))
    sc = shrink / (1 + pull)
    y = FOLD[1] + 300 * (1 - rise)
    blur = 12 * (1 - e_io_sine(prog(s, S_FOLD, 0.45)))
    press = math.sin(math.pi * clamp(prog(s, S_CLICK, 0.16)))
    hi = e_io_sine(prog(s, S_HOVER, 0.15)) * (1 - e_io_sine(prog(s, S_OPEN + 0.1, 0.3)))
    opened = e_out_cubic(prog(s, S_OPEN, 0.25))
    A.blur_layer(c, blur, a)
    folder(c, FOLD[0], y, sc * (1 - 0.04 * press), 1.0, opened, hi)
    text(c, "업무 파일", FOLD[0], y + (FH / 2 + 48) * sc, 28 * max(sc, 0.75), "SemiBold", WHITE, 1.0, "center")
    c.restore()
    # cursor: in from lower right, click, away
    ca = clamp(prog(s, S_HOVER - 0.32, 0.12)) * (1 - clamp(prog(s, S_OPEN + 0.12, 0.15)))
    m = e_io_cubic(prog(s, S_HOVER - 0.32, 0.36))
    cx = lerp(1240, FOLD[0] + 52, m) + 90 * e_in_cubic(prog(s, S_OPEN, 0.3))
    cy = lerp(800, FOLD[1] + 30, m) + 60 * e_in_cubic(prog(s, S_OPEN, 0.3))
    A.ripple(c, FOLD[0] + 52, FOLD[1] + 30, s, S_CLICK, WHITE, 70)
    A.cursor(c, cx, cy, ca, press)


def render(c, t):
    s = t - T0
    background(c, s)
    folder_beat(c, s)
    ring_trail(c, s)
    table(c, s)
    documents(c, s)
    card(c, s)
    send(c, s)


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


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = A.setup(height)
    SCV = A.SCV
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
