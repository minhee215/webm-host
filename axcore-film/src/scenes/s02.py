"""SCENE 02 · 15–31s · "It starts by understanding the work."

Pull-out from the selected point reveals real data sources at different depths
→ the diamond scans each one → orthogonal connectors → cards fold into chips
that dock under one process flow → the flow line contracts and morphs into the
AXpoint search pill → white UI space floods out of the pill.
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx, tracks
from ..compositing.background import navy_space, white_space
from ..compositing.plates import Plate
from ..compositing import ui_axpoint as ui
from ..motion.camera import Camera
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, in_cubic,
                             house, house_io, clamp)

CX, CY = DESIGN_W / 2, DESIGN_H / 2

# source cards: (world x, y, depth z, kind label, title, docks under flow node idx, renderer)
CARDS = [
    (430, 300, 0.20, "문서", "작업표준서", 1, "doc"),
    (870, 215, 0.40, "Excel", "재고현황", 2, "sheet"),
    (1440, 290, 0.10, "ERP", "수주 · 출하", 0, "table"),
    (1560, 700, 0.30, "MES", "생산실적", 3, "bars"),
    (1150, 850, -0.10, "설비 데이터", "PLC · 센서", 3, "gauge"),
    (640, 820, 0.00, "수기 기록", "일일 점검표", 4, "paper"),
    (270, 640, 0.25, "작업자", "현장 업무", 3, "worker"),
]
CARD_W, CARD_H = 330, 220
FLOW = ["수주", "설계", "구매", "생산", "품질", "출하"]
FLOW_Y = 560
FLOW_X0, FLOW_DX = 410, 220
SCAN_T0, SCAN_DT = 2.0, 0.95
T_FOLD = (8.9, 11.6)
T_TAGS = 11.7
T_MERGE = (13.0, 14.1)
T_PILL = (13.7, 14.6)
T_FLOOD = (14.5, 15.5)

SFX = [(0.1, "push_rev", 0.6)] + \
      [(SCAN_T0 + i * SCAN_DT + 0.3, "scan", 0.55) for i in range(len(CARDS))] + \
      [(SCAN_T0 + i * SCAN_DT + 0.62, "node", 0.35) for i in range(len(CARDS))] + \
      [(8.95, "line", 0.6), (9.6, "connector", 0.5), (10.4, "connector", 0.5), (11.75, "ui_tick", 0.5),
       (12.05, "ui_tick", 0.5), (13.05, "line_rev", 0.55), (14.45, "swell", 0.7), (15.3, "ui_open", 0.5)]


def motion_blur(t):
    if 0.0 <= t <= 0.9:
        return 5
    return 1


def _cam(t):
    z = lerp(0.12, 1.0, prog(t, 0.0, 2.2, house))
    # camera drifts toward the diamond while scanning, recentres for the flow
    dx, dy = _diamond_pos(t)
    w = 0.22 * prog(t, 1.8, 2.6) * (1 - prog(t, 8.6, 9.6))
    return Camera(lerp(CX, dx, w), lerp(CY, dy, w), z)


def _card_center(i, t):
    x, y, z, *_ = CARDS[i]
    return x, y


def _scan_idx(t):
    return int(clamp((t - SCAN_T0) / SCAN_DT, 0, len(CARDS) - 0.001))


def _diamond_pos(t):
    if t < SCAN_T0 - 0.45:
        return CX, CY
    if t >= SCAN_T0 + len(CARDS) * SCAN_DT:
        # after scanning: diamond returns to the start of the flow line
        p = prog(t, SCAN_T0 + len(CARDS) * SCAN_DT, 9.6, house_io)
        lx, ly = _corner(len(CARDS) - 1)
        return lerp(lx, FLOW_X0 - 90, p), lerp(ly, FLOW_Y, p)
    i = int((t - (SCAN_T0 - 0.45)) // SCAN_DT)
    i = min(i, len(CARDS) - 1)
    t_i = SCAN_T0 - 0.45 + i * SCAN_DT
    p = prog(t, t_i, t_i + 0.45, house_io)
    prev = (CX, CY) if i == 0 else _corner(i - 1)
    return lerp2(prev, _corner(i), p)


def _corner(i):
    x, y, *_ = CARDS[i]
    return x - CARD_W / 2 - 4, y - CARD_H / 2 - 4


# --- card contents -------------------------------------------------------------
def _content(c, kind, x, y, w, h, t, a):
    if kind == "doc" or kind == "paper":
        if kind == "paper":
            pl = Plate("V3")
            img = pl.image(1.0)
            # crop the real handwritten checklist from the top-down plate
            ui_src = (150, 115, 210, 140)
            gfx.draw_image(c, img, x, y, w, h, a, src=ui_src)
            return
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), gfx.fill("#FAFBFD", a))
        gfx.text(c, "작업표준서", x + 18, y + 26, 20, 700, "ink", a)
        for k in range(6):
            c.drawRect(skia.Rect.MakeXYWH(x + 18, y + 52 + k * 20, w * (0.8 - 0.1 * (k % 3)), 6),
                       gfx.fill("border", a))
    elif kind == "sheet":
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), gfx.fill("#FAFBFD", a))
        for r_ in range(7):
            yy = y + 10 + r_ * (h - 20) / 7
            c.drawLine(x + 6, yy, x + w - 6, yy, gfx.stroke("border", 1.2, a))
        for k in range(5):
            xx = x + 8 + k * (w - 16) / 5
            c.drawLine(xx, y + 6, xx, y + h - 6, gfx.stroke("border", 1.2, a))
        c.drawRect(skia.Rect.MakeXYWH(x + 8, y + 10, w - 16, (h - 20) / 7), gfx.fill("#E7F6EE", a))
    elif kind == "table":
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), gfx.fill("#FAFBFD", a))
        for r_ in range(5):
            yy = y + 18 + r_ * 34
            c.drawRect(skia.Rect.MakeXYWH(x + 14, yy, 60, 14), gfx.fill("tint", a))
            c.drawRect(skia.Rect.MakeXYWH(x + 86, yy, w - 160, 14), gfx.fill("border", a))
            c.drawRect(skia.Rect.MakeXYWH(x + w - 62, yy, 46, 14), gfx.fill("border", a))
    elif kind == "bars":
        c.drawRect(skia.Rect.MakeXYWH(x, y, w, h), gfx.fill("#FAFBFD", a))
        for k in range(7):
            bh = (0.35 + 0.5 * abs(math.sin(k * 1.7 + 0.4))) * (h - 40)
            c.drawRRect(gfx.rrect(x + 20 + k * (w - 40) / 7, y + h - 16 - bh, (w - 40) / 7 - 12, bh, 4),
                        gfx.fill("axblue" if k == 5 else "#BFD0FF", a))
    elif kind == "gauge":
        img = Plate("V5").image(2.0)
        gfx.draw_image(c, img, x, y, w, h, a, src=(520, 40, 150, 100))
        path = skia.Path()
        for k in range(40):
            xx = x + 10 + k * (w - 20) / 39
            yy = y + h - 30 - 18 * math.sin(k * 0.5 + t * 3) * (0.6 + 0.4 * math.sin(k * 0.13))
            (path.moveTo if k == 0 else path.lineTo)(xx, yy)
        gfx.glow_path(c, path, "light", 2.5, a, 0.6)
    elif kind == "worker":
        img = Plate("V2").image(2.4)
        gfx.draw_image(c, img, x, y, w, h, a, src=(380, 160, 180, 120))


def _card(c, i, t, a, fold=0.0):
    x, y, z, kind_label, title, dock, kind = CARDS[i]
    if a <= 0:
        return
    w, h = CARD_W, CARD_H
    c.save()
    c.translate(x, y)
    s = 1 - 0.0 * fold
    c.scale(s, s)
    c.drawRRect(gfx.rrect(-w / 2, -h / 2 + 10, w, h, 16), gfx.fill("#000000", 0.35 * a, blur=22))
    c.drawRRect(gfx.rrect(-w / 2, -h / 2, w, h, 16), gfx.fill("surface", a))
    c.save()
    c.clipRRect(gfx.rrect(-w / 2 + 8, -h / 2 + 8, w - 16, h - 16, 10), True)
    _content(c, kind, -w / 2 + 8, -h / 2 + 8, w - 16, h - 16, t, a)
    c.restore()
    c.restore()


def _scan_overlay(c, i, t):
    t_i = SCAN_T0 + i * SCAN_DT
    x, y, *_ = CARDS[i]
    w, h = CARD_W, CARD_H
    sp = prog(t, t_i - 0.05, t_i + 0.45, in_out_cubic)
    if 0 < sp < 1:
        yy = y - h / 2 + h * sp
        c.drawRect(skia.Rect.MakeXYWH(x - w / 2, yy - 2, w, 4), gfx.fill("light", 0.9))
        c.drawRect(skia.Rect.MakeXYWH(x - w / 2, yy - 30, w, 30), gfx.fill("line", 0.12, blur=10))
    lp = prog(t, t_i + 0.3, t_i + 0.7)
    fade = 1 - prog(t, T_FOLD[0], T_FOLD[0] + 0.5)
    if lp > 0:
        gfx.brackets(c, x - w / 2, y - h / 2, w, h, "light", lp * fade, 26, 3, lp, pad=12)
        kind_label, title = CARDS[i][3], CARDS[i][4]
        gfx.text_rise(c, kind_label, x - w / 2, y - h / 2 - 46, lp * fade, 36, 700, "white")
        kw = gfx.text_width(kind_label, 36, 700)
        gfx.text_rise(c, title, x - w / 2 + kw + 14, y - h / 2 - 46, lp * fade, 30, 500, "ice")


def _connector_path(i):
    x, y, *_ = CARDS[i]
    nx = FLOW_X0 + CARDS[i][5] * FLOW_DX
    sy = y + (CARD_H / 2 if y < FLOW_Y else -CARD_H / 2)
    return gfx.ortho_path(x, sy, nx, FLOW_Y + (-14 if y < FLOW_Y else 14), 28, horizontal_first=False)


def _flow(c, t, a=1.0):
    """Process flow line + nodes; contracts toward centre during merge."""
    pm = prog(t, *T_MERGE, ease=house_io)
    pl = prog(t, T_FOLD[0], T_FOLD[0] + 1.0, in_out_cubic)
    xs = [lerp(FLOW_X0 + k * FLOW_DX, CX, pm) for k in range(len(FLOW))]
    x0 = lerp(FLOW_X0 - 90, CX - 380, prog(t, T_MERGE[0] + 0.3, T_PILL[1], house_io))
    x1 = lerp(FLOW_X0 + 5 * FLOW_DX + 90, CX + 380, prog(t, T_MERGE[0] + 0.3, T_PILL[1], house_io))
    ph = prog(t, *T_PILL, ease=house_io)
    # line → pill outline
    if ph <= 0 and pl > 0:
        gfx.glow_line(c, x0, FLOW_Y, lerp(x0, x1, pl), FLOW_Y, "line", 2.2, a, 0.8)
    elif ph > 0:
        h = lerp(0, 84, ph)
        rr = gfx.rrect(CX - 380, FLOW_Y - h / 2, 760, h, h / 2)
        c.drawRRect(rr, gfx.stroke("line", 2.2, a))
        c.drawRRect(rr, gfx.stroke("line", 7, 0.3 * a, blur=6))
    na = a * (1 - prog(t, T_MERGE[0], T_MERGE[0] + 0.35))
    for k, name in enumerate(FLOW):
        pk = prog(t, T_FOLD[0] + 0.2 + k * 0.13, T_FOLD[0] + 0.6 + k * 0.13)
        if pk <= 0:
            continue
        gfx.node(c, xs[k], FLOW_Y, 9 * out_cubic(pk), "line", na, glow=0.6)
        c.drawCircle(xs[k], FLOW_Y, 17, gfx.stroke("light", 1.5, na * pk * 0.7))
        gfx.text_rise(c, name, xs[k], FLOW_Y - 56, pk, 36, 600, "white", na, "center")
    # DX / AX markers on the flow (where change is needed)
    for k, kind in ((2, "DX"), (3, "AX"), (4, "DX"), (0, "AX")):
        pt = prog(t, T_TAGS + 0.25 * (k % 3), T_TAGS + 0.4 + 0.25 * (k % 3)) * na
        if pt <= 0:
            continue
        y = FLOW_Y - 118
        w = 70
        if kind == "AX":
            gfx.pill(c, xs[k] - w / 2, y - 20, w, 40, "axblue", pt)
            gfx.text(c, kind, xs[k], y, 24, 700, "white", pt, "center")
        else:
            gfx.pill(c, xs[k] - w / 2, y - 20, w, 40, None, pt, "light", 1.8)
            gfx.text(c, kind, xs[k], y, 24, 700, "light", pt, "center")


def _chips(c, t):
    """Folded cards travel along their connectors and dock under flow nodes."""
    docked = {}
    for i in range(len(CARDS)):
        pf = prog(t, T_FOLD[0] + 0.5 + i * 0.12, T_FOLD[0] + 1.9 + i * 0.12, in_out_cubic)
        if pf <= 0 or t > T_MERGE[1]:
            continue
        path = _connector_path(i)
        x, y = gfx.point_at(path, pf)
        d = CARDS[i][5]
        slot = docked.get(d, 0)
        docked[d] = slot + 1
        pd = prog(t, T_FOLD[0] + 1.9 + i * 0.12, T_FOLD[0] + 2.4 + i * 0.12, house)
        tx = FLOW_X0 + d * FLOW_DX
        ty = FLOW_Y + 70 + slot * 54
        x, y = lerp(x, tx, pd), lerp(y, ty, pd)
        ma = 1 - prog(t, T_MERGE[0], T_MERGE[0] + 0.5)
        gfx.chip(c, x, y, CARDS[i][3], 24, 600, "navy", "ice", None, ma, dot="axblue", pad=14)


def render(c, t):
    navy_space(c, bloom=(CX, CY + 80), intensity=prog(t, 0.0, 1.6))
    flat = 1 - prog(t, 0.0, 1.4, in_out_cubic)   # matches the flat navy of S01's last frame
    if flat > 0:
        c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("navy", flat))
    cam = _cam(t)
    flood = prog(t, *T_FLOOD, ease=in_out_cubic)
    # --- cards with parallax depth -------------------------------------------
    order = sorted(range(len(CARDS)), key=lambda i: -CARDS[i][2])
    for i in order:
        x, y, z, *_ = CARDS[i]
        appear = prog(t, 0.2 + 0.08 * i, 1.4 + 0.08 * i)
        fold = prog(t, T_FOLD[0] + 0.3 + i * 0.12, T_FOLD[0] + 0.9 + i * 0.12, in_out_cubic)
        a = appear * (1 - fold)
        c.save()
        cam.apply(c, z * (1 - prog(t, 8.6, 9.6)))
        if a > 0:
            dimmed = 0.55 + 0.45 * (prog(t, SCAN_T0 + i * SCAN_DT - 0.1, SCAN_T0 + i * SCAN_DT + 0.3))
            c.save()
            c.translate(x, y)
            s = lerp(1.0, 0.25, fold)
            c.scale(s, s)
            c.translate(-x, -y)
            _card(c, i, t, a * dimmed)
            c.restore()
            _scan_overlay(c, i, t)
        c.restore()
    c.save()
    cam.apply(c, 0.0)
    # connectors
    for i in range(len(CARDS)):
        t_i = SCAN_T0 + i * SCAN_DT
        pcn = prog(t, t_i + 0.45, t_i + 1.1, in_out_cubic)
        ca = 1 - prog(t, T_MERGE[0], T_MERGE[0] + 0.6)
        if pcn > 0:
            gfx.glow_path(c, _connector_path(i), "line", 1.6, 0.75 * ca, 0.5, 0, pcn)
    _flow(c, t)
    _chips(c, t)
    # diamond (core node): scanning cursor → rests at the line start → into the pill
    dx, dy = _diamond_pos(t)
    pm = prog(t, T_MERGE[0], T_PILL[1], house_io)
    dx, dy = lerp(dx, CX - 380 + 46, pm), lerp(dy, FLOW_Y, pm)
    c.restore()
    sx, sy = cam.project(dx, dy, 0.0)
    r = lerp(16, 12, prog(t, 0.4, 2.0))
    gfx.diamond(c, sx, sy, r, "axblue", 1 - prog(t, T_FLOOD[0], T_FLOOD[0] + 0.4),
                glow=lerp(0.8, 0.6, prog(t, 0, 2)), edge="light")
    # --- white UI floods out of the pill (shape-driven reveal, not a dissolve) ---
    if flood > 0:
        path = skia.Path()
        rad = lerp(0, 1250, flood)
        w = 760 + 2 * rad
        h = 84 + 2 * rad
        path.addRRect(gfx.rrect(CX - w / 2, FLOW_Y - h / 2, w, h, min(h / 2, 42 + rad)))
        c.save()
        c.clipPath(path, skia.ClipOp.kIntersect, True)
        white_space(c)
        ui.landing(c, CX, FLOW_Y, head=prog(t, 15.0, 15.6), sub=prog(t, 15.2, 15.8), caret=(t % 1.0) < 0.55,
                   focus=1.0)
        ui.topbar(c, 0, 0, DESIGN_W, -1, prog(t, 15.2, 15.8))
        c.restore()
        if flood < 1:
            c.drawPath(path, gfx.stroke("line", 2.0, 1 - flood))
