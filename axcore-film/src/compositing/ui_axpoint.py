"""AXpoint / Workspace UI, rebuilt as motion-friendly vector components.

Source of truth: axpoint_UI_캡쳐.png + IR Deck p.9–11, p.34–37. Information
architecture and labels follow the product; only the presentation layer is
simplified (larger type, fewer rows) so it reads at 480p.
"""
from functools import lru_cache
import math

import cv2
import numpy as np
import skia

from ..utils.config import ASSETS
from . import gfx
from ..motion.easing import prog, lerp, out_cubic, clamp

STEPS = ["자료 올리기", "자료 정리", "진단 결과", "개선 과제", "로드맵", "보고서"]


# --- logo -----------------------------------------------------------------------
@lru_cache(maxsize=None)
def logo_parts():
    """Split the real AXCORE logo PNG into wordmark / diamond / blue bars.

    Returns dict of BGRA arrays (full logo canvas) + diamond centre/size.
    Only the top wordmark row is used (the Korean line is cropped off).
    """
    img = cv2.imread(str(ASSETS / "logo" / "AXCORE_logo_w2.png"), cv2.IMREAD_UNCHANGED)
    img = img[:200]                                   # wordmark row only
    b, g, r, a = [img[..., i].astype(np.int16) for i in range(4)]
    blue = (b > 180) & (r < 120) & (a > 40)
    white = (~blue) & (a > 10)
    # the diamond is the blue blob left of x=300; the bars are blue at right
    ys, xs = np.where(blue[:, :300])
    dcx, dcy = xs.mean(), ys.mean()
    dr = (xs.max() - xs.min()) / 2
    diamond_mask = np.zeros_like(blue)
    diamond_mask[:, :300] = blue[:, :300]
    bars_mask = blue & ~diamond_mask

    def layer(mask, bgr):
        out = np.zeros_like(img)
        out[..., 0], out[..., 1], out[..., 2] = bgr
        out[..., 3] = np.where(mask, img[..., 3], 0)
        return out
    return {
        "size": (img.shape[1], img.shape[0]),
        "white": layer(white, (255, 255, 255)),
        "ink": layer(white, (37, 21, 14)),
        "bars": layer(bars_mask, (252, 83, 0)),
        "diamond_c": (float(dcx), float(dcy)),
        "diamond_r": float(dr),
    }


@lru_cache(maxsize=None)
def logo_image(part):
    return gfx.to_image(logo_parts()[part])


def draw_logo(c, x, y, h, dark=False, a=1.0, wipe=1.0, diamond=True, bars=True):
    """Logo with its top-left at (x, y), height h. wipe reveals from the diamond."""
    lp = logo_parts()
    W, H = lp["size"]
    s = h / H
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    if wipe < 1:
        dcx = lp["diamond_c"][0]
        half = max(W - dcx, dcx) * wipe
        c.clipRect(skia.Rect.MakeLTRB(dcx - half, -10, dcx + half, H + 10))
    gfx.draw_image(c, logo_image("ink" if dark else "white"), 0, 0, W, H, a)
    if bars:
        gfx.draw_image(c, logo_image("bars"), 0, 0, W, H, a)
    c.restore()
    if diamond:
        dcx, dcy = lp["diamond_c"]
        gfx.diamond(c, x + dcx * s, y + dcy * s, lp["diamond_r"] * s, "axblue", a)


def logo_diamond_pos(x, y, h):
    lp = logo_parts()
    s = h / lp["size"][1]
    return x + lp["diamond_c"][0] * s, y + lp["diamond_c"][1] * s, lp["diamond_r"] * s


# --- icons ----------------------------------------------------------------------
def icon_search(c, x, y, s, col="ink3", a=1.0):
    c.drawCircle(x - s * 0.12, y - s * 0.12, s * 0.32, gfx.stroke(col, s * 0.09, a))
    c.drawLine(x + s * 0.12, y + s * 0.12, x + s * 0.38, y + s * 0.38, gfx.stroke(col, s * 0.09, a))


def icon_check(c, x, y, s, col="white", a=1.0, p=1.0):
    path = skia.Path()
    path.moveTo(x - s * 0.3, y)
    path.lineTo(x - s * 0.08, y + s * 0.22)
    path.lineTo(x + s * 0.32, y - s * 0.22)
    gfx.glow_path(c, path, col, s * 0.12, a, 0.0, 0, p)


def icon_doc(c, x, y, s, col="ink3", a=1.0, fill_col=None):
    w, h = s * 0.72, s * 0.92
    if fill_col:
        c.drawRRect(gfx.rrect(x - w / 2, y - h / 2, w, h, s * 0.08), gfx.fill(fill_col, a))
    c.drawRRect(gfx.rrect(x - w / 2, y - h / 2, w, h, s * 0.08), gfx.stroke(col, s * 0.06, a))
    for k in range(3):
        yy = y - h * 0.18 + k * h * 0.2
        c.drawLine(x - w * 0.28, yy, x + w * 0.28, yy, gfx.stroke(col, s * 0.05, a))


def icon_upload(c, x, y, s, col="axblue", a=1.0):
    c.drawLine(x, y + s * 0.25, x, y - s * 0.3, gfx.stroke(col, s * 0.08, a))
    path = skia.Path()
    path.moveTo(x - s * 0.22, y - s * 0.1)
    path.lineTo(x, y - s * 0.32)
    path.lineTo(x + s * 0.22, y - s * 0.1)
    c.drawPath(path, gfx.stroke(col, s * 0.08, a))
    c.drawLine(x - s * 0.34, y + s * 0.38, x + s * 0.34, y + s * 0.38, gfx.stroke(col, s * 0.08, a))


def tag(c, x, y, label, kind="blue", a=1.0, size=20):
    styles = {
        "blue": ("tint", "axblue"), "red": ("red_tint", "red"), "gray": ("bg", "ink2"),
        "solid": ("axblue", "white"), "green": ("#E7F6EE", "green"),
    }
    bg, fg = styles[kind]
    w = gfx.text_width(label, size, 600) + size * 1.1
    h = size * 1.6
    gfx.pill(c, x, y - h / 2, w, h, bg, a)
    gfx.text(c, label, x + size * 0.55, y, size, 600, fg, a)
    return w


# --- shell ----------------------------------------------------------------------
def topbar(c, x, y, w, step=-1, a=1.0, done_p=1.0):
    """AXpoint top bar: logo, 6-step progress, user chip."""
    c.drawRect(skia.Rect.MakeXYWH(x, y, w, 76), gfx.fill("surface", a))
    c.drawLine(x, y + 76, x + w, y + 76, gfx.stroke("border", 1.5, a))
    draw_logo(c, x + 40, y + 24, 28, dark=True, a=a)
    if step >= 0:
        sw = 168
        sx = x + w / 2 - sw * len(STEPS) / 2
        for i, name in enumerate(STEPS):
            cx = sx + i * sw + 22
            active = i == step
            done = i < step
            col = "axblue" if (active or done) else "ink3"
            if active:
                c.drawCircle(cx, y + 38, 11, gfx.fill("axblue", a))
            elif done:
                c.drawCircle(cx, y + 38, 11, gfx.fill("tint", a))
                icon_check(c, cx, y + 38, 18, "axblue", a)
            else:
                c.drawCircle(cx, y + 38, 10, gfx.stroke("ink3", 2, a))
            gfx.text(c, name, cx + 20, y + 38, 22, 600 if active else 500, col if active else ("ink2" if done else "ink3"), a)
    gfx.pill(c, x + w - 150, y + 20, 110, 36, "tint", a)
    gfx.text(c, "데모기업", x + w - 95, y + 38, 18, 600, "axblue", a, "center")


def headline_landing(c, cx, y, a=1.0, size=64):
    parts = [("제조 ", "ink"), ("AX", "axblue"), ("를 위한 ", "ink"), ("AI", "axblue"), (" 컨설턴트", "ink")]
    total = sum(gfx.text_width(s, size, 600) for s, _ in parts)
    x = cx - total / 2
    for s, col in parts:
        x += gfx.text(c, s, x, y, size, 600, col, a)


def search_pill(c, cx, cy, w=760, h=84, typed="", caret=False, btn=0.0, press=0.0, a=1.0,
                focus=0.0, placeholder="사업자명 또는 기업명"):
    x, y = cx - w / 2, cy - h / 2
    c.drawRRect(gfx.rrect(x, y + 6, w, h, h / 2), gfx.fill("#101828", 0.06 * a, blur=14))
    gfx.pill(c, x, y, w, h, "surface", a, gfx.mix("border", "axblue", focus), 2.0)
    icon_search(c, x + 46, cy, 30, "ink3", a)
    if typed:
        tw = gfx.text(c, typed, x + 80, cy, 30, 500, "ink", a)
        if caret:
            c.drawRect(skia.Rect.MakeXYWH(x + 84 + tw, cy - 18, 2.5, 36), gfx.fill("axblue", a))
    else:
        gfx.text(c, placeholder, x + 80, cy, 28, 400, "ink3", a)
        if caret:
            c.drawRect(skia.Rect.MakeXYWH(x + 80, cy - 18, 2.5, 36), gfx.fill("axblue", a))
    bw, bh = 176, h - 20
    bx, by = x + w - bw - 10, y + 10
    s = 1 - 0.04 * math.sin(math.pi * clamp(press))
    c.save()
    c.translate(bx + bw / 2, by + bh / 2)
    c.scale(s, s)
    gfx.pill(c, -bw / 2, -bh / 2, bw, bh, gfx.mix("#9DB8FF", "axblue", btn), a)
    gfx.text(c, "기업 찾기  →", 0, 0, 24, 600, "white", a, "center")
    c.restore()


def landing(c, cx, cy, a=1.0, head=1.0, sub=1.0, **pill):
    gfx.text_rise(c, "", cx, cy, 0)
    if head > 0:
        c.save()
        c.translate(0, (1 - head) * 16)
        headline_landing(c, cx, cy - 170, a * head)
        c.restore()
    gfx.text_rise(c, "조사·분석·진단·설계까지, One-stop 맞춤형 솔루션", cx, cy - 98, sub, 28, 500,
                  "ink2", a, "center")
    search_pill(c, cx, cy, a=a, **pill)


# --- panels used in S03 ---------------------------------------------------------
UPLOAD_FILES = [  # file names shown in IR Deck p.35 (AXpoint STEP 2)
    ("3월 생산일지_v3.pdf", "PDF", "생산관리"),
    ("작업표준_양식_2026.xlsx", "XLSX", "생산관리"),
    ("발주서 묶음(5~6월).pdf", "PDF", "구매·자재"),
    ("거래명세서_6월.pdf", "PDF", "영업관리"),
    ("재고현황_202606.xlsx", "XLSX", "구매·자재"),
    ("검사성적서_3월 (스캔).pdf", "PDF", "품질관리"),
]


def panel(c, x, y, w, h, a=1.0, r=24):
    gfx.card(c, x, y, w, h, r, "surface", a, "border", 0.07)


def file_row(c, x, y, w, name, kind, a=1.0, prog_p=1.0, tag_label=None, tag_p=0.0):
    h = 74
    c.drawRRect(gfx.rrect(x, y, w, h, 14), gfx.fill("bg", a))
    icon_doc(c, x + 40, y + h / 2, 36, "axblue" if kind == "XLSX" else "ink2", a)
    gfx.text(c, name, x + 76, y + h / 2 - 2, 26, 500, "ink", a)
    gfx.text(c, kind, x + w - 30, y + h / 2, 20, 600, "ink3", a, "right")
    if prog_p < 1:
        c.drawRRect(gfx.rrect(x + 76, y + h - 14, (w - 120), 5, 2.5), gfx.fill("border", a))
        c.drawRRect(gfx.rrect(x + 76, y + h - 14, (w - 120) * prog_p, 5, 2.5), gfx.fill("axblue", a))
    if tag_label and tag_p > 0:
        tw = gfx.text_width(tag_label, 20, 600) + 22
        tag(c, x + w - 90 - tw + (1 - tag_p) * 20, y + h / 2, tag_label, "blue", a * tag_p)


RADAR = [("AI전환전략", 34.1), ("조직문화", 56.3), ("업무체계 및 인재역량", 45.0),
         ("AI인프라 및 기술", 47.2), ("AI 활용 및 성과", 25.0)]   # IR Deck p.9


def radar(c, cx, cy, r, p_grid=1.0, p_val=1.0, a=1.0, labels=True):
    n = len(RADAR)
    pts = lambda rr: [(cx + rr * math.cos(math.radians(-90 + 360 * i / n)),
                       cy + rr * math.sin(math.radians(-90 + 360 * i / n))) for i in range(n)]
    for k in (0.25, 0.5, 0.75, 1.0):
        poly = pts(r * k * p_grid)
        path = skia.Path()
        path.addPoly([skia.Point(*q) for q in poly], True)
        c.drawPath(path, gfx.stroke("border", 1.5, a))
    for q in pts(r * p_grid):
        c.drawLine(cx, cy, q[0], q[1], gfx.stroke("border", 1.5, a))
    vals = [(cx + r * (v / 100) * p_val * math.cos(math.radians(-90 + 360 * i / n)),
             cy + r * (v / 100) * p_val * math.sin(math.radians(-90 + 360 * i / n)))
            for i, (_, v) in enumerate(RADAR)]
    path = skia.Path()
    path.addPoly([skia.Point(*q) for q in vals], True)
    c.drawPath(path, gfx.fill("axblue", 0.16 * a * p_val))
    c.drawPath(path, gfx.stroke("axblue", 3, a * p_val))
    for q in vals:
        c.drawCircle(q[0], q[1], 5, gfx.fill("axblue", a * p_val))
    if labels:
        for i, q in enumerate(pts(r + 46)):
            gfx.text(c, RADAR[i][0], q[0], q[1], 20, 500, "ink2", a * p_grid, "center")
    return vals


def score_bars(c, x, y, w, p=1.0, a=1.0, highlight=-1, hl=0.0, gap=86):
    """AX 전환 5대 지수 bars. Returns end points of each bar (for morphs)."""
    ends = []
    for i, (name, v) in enumerate(RADAR):
        yy = y + i * gap
        pi = prog(p, i * 0.08, 0.6 + i * 0.08)
        hot = (i == highlight) * hl
        gfx.text(c, name, x, yy, 26, 600 if hot else 500, gfx.mix("ink", "red", hot), a)
        gfx.text(c, f"{v * pi:.1f}", x + w, yy, 26, 700, gfx.mix("axblue", "red", hot), a, "right")
        c.drawRRect(gfx.rrect(x, yy + 22, w, 12, 6), gfx.fill("bg", a))
        c.drawRRect(gfx.rrect(x, yy + 22, w * v / 100 * pi, 12, 6),
                    gfx.fill(gfx.mix("axblue", "red", hot), a))
        ends.append((x + w * v / 100 * pi, yy + 28))
    return ends


TASKS = [  # IR Deck p.10 / p.36 (개선 과제 후보)
    ("데이터 공유 체계 정리", "경영", "AX"),
    ("일일 작업일보 디지털 전환", "생산관리", "DX"),
    ("검사성적서 전자화 + 불량 코드 체계", "품질검사", "DX"),
    ("품목·거래처 코드 표준화", "영업관리", "DX"),
    ("재고·발주점 자동 알림", "재고·물류", "AX"),
    ("숙련자 노하우 기록·전수", "생산관리", "AX"),
]


def task_card(c, x, y, w, h, title, dept, kind, a=1.0, selected=0.0, check_p=0.0):
    border = gfx.mix("border", "axblue", selected)
    bg = gfx.mix("surface", "#F5F8FF", selected)
    gfx.card(c, x, y, w, h, 18, bg, a, border, 0.05, 1.5 + 1.5 * selected)
    tw = tag(c, x + 22, y + 34, dept, "gray", a, 18)
    tag(c, x + 30 + tw, y + 34, kind, "solid" if kind == "AX" else "blue", a, 18)
    gfx.text(c, title, x + 22, y + 92, 25, 600, "ink", a)
    gfx.text(c, "예상 효과 · 우선순위 분석", x + 22, y + h - 32, 19, 500, "ink3", a)
    cx, cy = x + w - 36, y + 34
    if selected > 0:
        c.drawCircle(cx, cy, 15, gfx.fill("axblue", a * selected))
        icon_check(c, cx, cy, 22, "white", a, check_p)
    else:
        c.drawCircle(cx, cy, 14, gfx.stroke("border", 2, a))
