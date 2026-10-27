"""SCENE 04 · 50–73s · Workspace → Connectors → OCR / standardisation → Ontology.

The report banner is pushed into and becomes the Workspace builder (a defocused
factory plate sits behind it). Selected functions assemble a workspace; pulling
out reveals navy space where in-house systems, files, SaaS and equipment
plug in through connectors. A handwritten sheet is read by OCR, inconsistent
names collapse into one standard code, and everything converges on the
diamond, which organises the data into six entities and their relations.
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx
from ..compositing import ui_axpoint as ui
from ..compositing.background import navy_space, orbit_field
from ..compositing.plates import Plate
from ..motion.camera import Camera
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, in_cubic, house,
                             house_io, clamp)
from . import s03
from .common import cursor

CX, CY = DESIGN_W / 2, DESIGN_H / 2

FUNCS = [  # IR Deck p.11 — 8대 핵심 기능
    ("경영관리", ["인사", "급여", "자재", "회계", "구매"]),
    ("제품설계", ["도면", "설계", "BOM"]),
    ("생산관리", ["모니터링", "작업 지시", "공정 병목"]),
    ("장비관리", ["AI 정비 예측", "정비 관리"]),
    ("품질검사", ["불량 분석", "품질관리"]),
    ("재고·물류", ["실시간 재고", "안전 재고", "입출고 검수"]),
    ("영업관리", ["수주 관리", "AI 수요 예측", "단가 견적"]),
    ("고객지원", ["AS 접수", "AS 트래킹", "VOC 분석"]),
]
PICK = [2, 3, 4, 5, 6]
PICK_T = [2.25, 2.6, 2.95, 3.3, 3.65]

# systems around the workspace: (label, sub, side, slot)
SYSTEMS = [
    ("ERP", "수주 · 회계", "L", 0), ("MES", "생산실적", "L", 1), ("CRM", "고객 · 영업", "L", 2),
    ("Excel", "재고현황", "R", 0), ("문서", "작업표준서 · 도면", "R", 1), ("SaaS", "메일 · 메신저 · 협업", "R", 2),
    ("설비", "PLC · 센서", "B", 0),
]
WS_SMALL = (CX - 330, CY - 200, 660, 400)     # workspace panel after pull-out

T_PUSH = (0.0, 1.0)
T_CLICK = 1.05
T_EXPAND = (1.2, 1.95)
T_ASSEMBLE = (4.0, 5.0)
T_PULL = (5.0, 6.3)
T_SYS = 6.0
T_CONN = 7.0
T_OCR = (9.4, 14.0)
T_CONVERGE = (14.0, 15.6)
T_CLOUD = (15.0, 17.0)
T_ORGANISE = (17.0, 19.0)
T_REL = (18.6, 20.2)
T_PATH = (20.2, 22.0)



SFX = [(0.05, "push", 0.6), (T_CLICK, "select", 0.7), (1.25, "ui_open", 0.6)] + \
      [(t, "select", 0.5) for t in PICK_T] + \
      [(4.05, "air", 0.35), (4.6, "chip_land", 0.4), (5.05, "pull", 0.55)] + \
      [(T_SYS + 0.12 * i, "ui_tick", 0.3) for i in range(7)] + \
      [(T_CONN + 0.3 * i + 0.55, "connector", 0.5) for i in range(7)] + \
      [(9.5, "push", 0.45), (10.25, "scan_long", 0.6), (11.1, "chip_land", 0.4), (11.4, "chip_land", 0.4),
       (11.7, "chip_land", 0.4), (12.5, "merge", 0.55), (13.7, "air", 0.35), (14.1, "swell", 0.55),
       (15.1, "data_rise", 0.45), (17.0, "resolve", 0.5)] + \
      [(14.9 + 0.42 * i, "node", 0.4) for i in range(6)] + \
      [(18.3, "line", 0.5), (19.6, "connector", 0.45)] + \
      [(20.9, "ui_open", 0.45)]


def motion_blur(t):
    for a, b in ((0.2, 1.0), (T_EXPAND[0], T_EXPAND[1]), (T_ASSEMBLE[0] + 0.1, T_ASSEMBLE[1]),
                 (T_PULL[0], T_PULL[0] + 0.8), (T_CONVERGE[0], T_CONVERGE[0] + 0.8)):
        if a <= t <= b:
            return 5
    return 1


# --- 4A: banner → workspace builder ---------------------------------------------------
def _banner_screen(cam):
    x, y, w, h = s03.banner_rect()
    x0, y0 = cam.project(x, y)
    x1, y1 = cam.project(x + w, y + h)
    return x0, y0, x1 - x0, y1 - y0


def _push_cam(t):
    x, y, w, h = s03.banner_rect()
    p = prog(t, *T_PUSH, ease=house_io)
    end = s03._cam(19.0)
    return Camera(lerp(end.x, x + w / 2, p), lerp(end.y, y + h / 2, p), lerp(end.z, 0.62, p))


BUILDER = (120, 110, 1680, 930)


def _builder_rect(t):
    """Banner rect (screen) → full frame → builder panel (card push-in / settle)."""
    bx, by, bw, bh = _banner_screen(_push_cam(T_EXPAND[0]))
    p1 = prog(t, T_EXPAND[0], T_EXPAND[1] - 0.25, house_io)
    p2 = prog(t, T_EXPAND[1] - 0.3, T_EXPAND[1] + 0.35, house)
    full = (-40, -40, DESIGN_W + 80, DESIGN_H + 80)
    r = [lerp(a, b, p1) for a, b in zip((bx, by, bw, bh), full)]
    return [lerp(a, b, p2) for a, b in zip(r, BUILDER)]


def _func_rect(i):
    col, row = i % 4, i // 4
    x0, y0 = BUILDER[0] + 60, BUILDER[1] + 190
    w, h = (BUILDER[2] - 120 - 3 * 28) / 4, 330
    return x0 + col * (w + 28), y0 + row * (h + 28), w, h


def _func_card(c, i, x, y, w, h, a, sel, check):
    name, subs = FUNCS[i]
    gfx.card(c, x, y, w, h, 20, gfx.mix("surface", "#F5F8FF", sel), a, gfx.mix("border", "axblue", sel), 0.05,
             1.5 + 1.5 * sel)
    gfx.text(c, name, x + 28, y + 52, 32, 700, "ink", a)
    for k, sname in enumerate(subs[:4]):
        gfx.chip(c, x + 28, y + 112 + k * 52, sname, 21, 500, "ink2", "bg", None, a, align="left", pad=14)
    cx_, cy_ = x + w - 40, y + 50
    if sel > 0:
        c.drawCircle(cx_, cy_, 17, gfx.fill("axblue", a * sel))
        ui.icon_check(c, cx_, cy_, 24, "white", a, check)
    else:
        c.drawCircle(cx_, cy_, 16, gfx.stroke("border", 2, a))


def _workspace_layout(c, x, y, w, h, a, t, build=1.0):
    """Assembled workspace: sidebar of selected functions + dashboard widgets."""
    gfx.card(c, x, y, w, h, 22 * w / 1680, "surface", a, "border", 0.1)
    s = w / 1680
    c.save()
    c.translate(x, y)
    c.scale(s, s)
    c.drawRect(skia.Rect.MakeXYWH(0, 0, 330, 930), gfx.fill("bg", a))
    ui.draw_logo(c, 34, 34, 26, dark=True, a=a)
    gfx.text(c, "데모기업 워크스페이스", 34, 110, 24, 700, "ink", a)
    items = ["AI 대화"] + [FUNCS[i][0] for i in PICK]
    for k, it in enumerate(items):
        pk = prog(build, 0.1 + k * 0.08, 0.5 + k * 0.08)
        yy = 170 + k * 66
        if k == 0:
            c.drawRRect(gfx.rrect(20, yy - 26, 290, 52, 12), gfx.fill("tint", a * pk))
        gfx.diamond(c, 46, yy, 7, "axblue" if k == 0 else "ink3", a * pk)
        gfx.text(c, it, 66, yy, 24, 600 if k == 0 else 500, "axblue" if k == 0 else "ink", a * pk)
    gfx.text(c, "주요 정보", 380, 70, 30, 700, "ink", a)
    # widgets (shapes only — no invented numbers)
    W = [(380, 120, 620, 360), (1030, 120, 610, 360), (380, 510, 1260, 380)]
    for k, (wx, wy, ww, wh) in enumerate(W):
        pk = prog(build, 0.3 + k * 0.12, 0.8 + k * 0.12)
        gfx.card(c, wx, wy + (1 - pk) * 20, ww, wh, 18, "surface", a * pk, "border", 0.0)
        if k == 0:
            gfx.text(c, "생산 현황", wx + 30, wy + 46, 22, 600, "ink2", a * pk)
            for j in range(7):
                bh = (0.3 + 0.55 * abs(math.sin(j * 1.9 + 0.3))) * (wh - 110) * pk
                c.drawRRect(gfx.rrect(wx + 40 + j * 80, wy + wh - 30 - bh, 48, bh, 6),
                            gfx.fill("axblue" if j in (2, 5) else "#BFD0FF", a * pk))
        elif k == 1:
            gfx.text(c, "재고 상태", wx + 30, wy + 46, 22, 600, "ink2", a * pk)
            cx_, cy_ = wx + ww / 2, wy + wh / 2 + 25
            c.drawCircle(cx_, cy_, 110, gfx.stroke("tint", 36, a * pk))
            path = skia.Path()
            path.addArc(skia.Rect.MakeXYWH(cx_ - 110, cy_ - 110, 220, 220), -90, 260 * pk)
            c.drawPath(path, gfx.stroke("axblue", 36, a * pk, cap="butt"))
        else:
            gfx.text(c, "품질 추이", wx + 30, wy + 46, 22, 600, "ink2", a * pk)
            path = skia.Path()
            for j in range(30):
                xx = wx + 40 + j * (ww - 80) / 29
                yy = wy + wh * 0.6 - 70 * math.sin(j * 0.33) * 0.6 - 30 * math.sin(j * 0.9)
                (path.moveTo if j == 0 else path.lineTo)(xx, yy)
            gfx.glow_path(c, path, "axblue", 4, a * pk, 0.0, 0, pk)
    c.restore()


def _builder(c, t):
    x, y, w, h = _builder_rect(t)
    p_settle = prog(t, T_EXPAND[1] - 0.3, T_EXPAND[1] + 0.35)
    # defocused factory plate behind the builder (the space this workspace serves)
    if p_settle > 0:
        Plate("V2").draw_blurred(c, 1.5 + t * 0.35, sigma=20, veil="navy_deep", veil_a=0.25)
    else:
        orbit_field(c, 19.0 + t, defocus=12)
    gfx.card(c, x, y, w, h, 24, "surface", 1.0, "border", 0.18 * p_settle)
    ca = prog(t, T_EXPAND[1] - 0.1, T_EXPAND[1] + 0.4) * (1 - prog(t, T_ASSEMBLE[0] + 0.5, T_ASSEMBLE[1]))
    if ca <= 0:
        return
    gfx.text(c, "워크스페이스 구성", BUILDER[0] + 60, BUILDER[1] + 76, 42, 700, "ink", ca)
    gfx.text(c, "필요한 기능만 선택하세요", BUILDER[0] + 60, BUILDER[1] + 128, 24, 500, "ink2", ca)
    for i in range(len(FUNCS)):
        fx, fy, fw, fh = _func_rect(i)
        pi = prog(t, T_EXPAND[1] - 0.05 + i * 0.04, T_EXPAND[1] + 0.4 + i * 0.04)
        sel = 0.0
        if i in PICK:
            k = PICK.index(i)
            sel = prog(t, PICK_T[k], PICK_T[k] + 0.2)
            # selected cards fly into the sidebar of the workspace
            pf = prog(t, T_ASSEMBLE[0] + k * 0.06, T_ASSEMBLE[0] + 0.6 + k * 0.06, house_io)
            if pf > 0:
                tx, ty = BUILDER[0] + 20, BUILDER[1] + 170 + (k + 1) * 66 - 26
                fx, fy = lerp(fx, tx, pf), lerp(fy, ty, pf)
                fw, fh = lerp(fw, 290, pf), lerp(fh, 52, pf)
                if pf > 0.95:
                    continue
                c.save()
                c.translate(fx, fy)
                c.scale(fw / _func_rect(i)[2], fh / _func_rect(i)[3])
                _func_card(c, i, 0, 0, _func_rect(i)[2], _func_rect(i)[3], pi, sel, 1.0)
                c.restore()
                continue
        else:
            pi *= 1 - prog(t, T_ASSEMBLE[0], T_ASSEMBLE[0] + 0.3) * 0.0
            pi *= 1 - 0.65 * prog(t, PICK_T[-1] + 0.2, PICK_T[-1] + 0.5)
            pi *= 1 - prog(t, T_ASSEMBLE[0], T_ASSEMBLE[0] + 0.4)
        c.save()
        c.translate(0, (1 - pi) * 18)
        _func_card(c, i, fx, fy, fw, fh, pi, sel, prog(t, PICK_T[PICK.index(i)], PICK_T[PICK.index(i)] + 0.3) if i in PICK else 0)
        c.restore()
    # cursor
    if PICK_T[0] - 0.4 < t < PICK_T[-1] + 0.4:
        k = int(clamp((t - (PICK_T[0] - 0.35)) / 0.35, 0, len(PICK) - 1))
        fx, fy, fw, fh = _func_rect(PICK[k])
        px, py = fx + fw - 40, fy + 50
        if k > 0:
            q = _func_rect(PICK[k - 1])
            ppx, ppy = q[0] + q[2] - 40, q[1] + 50
        else:
            ppx, ppy = px + 160, py + 260
        m = prog(t, PICK_T[k] - 0.3, PICK_T[k] - 0.02, house_io)
        a = prog(t, PICK_T[0] - 0.4, PICK_T[0] - 0.2) * (1 - prog(t, PICK_T[-1] + 0.2, PICK_T[-1] + 0.4))
        cursor(c, lerp(ppx, px, m), lerp(ppy, py, m), prog(t, PICK_T[k], PICK_T[k] + 0.3), a)


def _ws_rect(t):
    p = prog(t, *T_PULL, ease=house_io)
    return [lerp(a, b, p) for a, b in zip(BUILDER, WS_SMALL)]


# --- 4B: systems + connectors -------------------------------------------------------------
def _sys_pos(i):
    label, sub, side, slot = SYSTEMS[i]
    if side == "L":
        return 250, 300 + slot * 240
    if side == "R":
        return DESIGN_W - 250, 300 + slot * 240
    return CX, DESIGN_H - 120


def _port(i):
    x, y, w, h = WS_SMALL
    label, sub, side, slot = SYSTEMS[i]
    if side == "L":
        return x, y + 90 + slot * 110
    if side == "R":
        return x + w, y + 90 + slot * 110
    return x + w / 2, y + h


def _sys_block(c, i, t, a):
    label, sub, side, slot = SYSTEMS[i]
    x, y = _sys_pos(i)
    pin = prog(t, T_SYS + i * 0.12, T_SYS + 0.7 + i * 0.12, house)
    off = {"L": (-300, 0), "R": (300, 0), "B": (0, 200)}[side]
    x, y = x + off[0] * (1 - pin), y + off[1] * (1 - pin)
    a *= pin
    if a <= 0:
        return
    w, h = 300, 128
    c.drawRRect(gfx.rrect(x - w / 2, y - h / 2, w, h, 18), gfx.fill("navy_mid", 0.85 * a))
    c.drawRRect(gfx.rrect(x - w / 2, y - h / 2, w, h, 18), gfx.stroke("line", 1.6, 0.8 * a))
    gfx.text(c, label, x - w / 2 + 28, y - 18, 36, 700, "white", a)
    gfx.text(c, sub, x - w / 2 + 28, y + 28, 21, 500, "ice", a)


def _conn_path(i):
    sx, sy = _sys_pos(i)
    px, py = _port(i)
    side = SYSTEMS[i][2]
    if side == "L":
        return gfx.ortho_path(sx + 150, sy, px, py, 26)
    if side == "R":
        return gfx.ortho_path(sx - 150, sy, px, py, 26)
    return gfx.ortho_path(sx, sy - 64, px, py, 26, horizontal_first=False)


def _connectors(c, t, a=1.0):
    for i in range(len(SYSTEMS)):
        t0 = T_CONN + 0.3 * i
        pl = prog(t, t0, t0 + 0.55, in_out_cubic)
        if pl <= 0:
            continue
        path = _conn_path(i)
        gfx.glow_path(c, path, "line", 2.0, 0.9 * a, 0.6, 0, pl)
        # connector chip rides the line and snaps into the port
        pc = prog(t, t0 + 0.15, t0 + 0.6, house_io)
        x, y = gfx.point_at(path, pc)
        snapped = pc >= 1
        w_, h_ = 132, 40
        c.drawRRect(gfx.rrect(x - w_ / 2, y - h_ / 2, w_, h_, h_ / 2), gfx.fill("axblue" if snapped else "navy", a))
        c.drawRRect(gfx.rrect(x - w_ / 2, y - h_ / 2, w_, h_, h_ / 2), gfx.stroke("light", 1.5, a))
        gfx.text(c, "Connector", x, y, 19, 600, "white", a, "center")
        gfx.ripple(c, x, y, prog(t, t0 + 0.6, t0 + 1.1), 20, 70, "light", a)
        # data pulse flowing into the workspace afterwards
        if t > t0 + 0.7:
            for k in range(2):
                pp = ((t - t0 - 0.7) * 0.8 + k * 0.5) % 1.0
                px, py = gfx.point_at(path, pp)
                gfx.node(c, px, py, 4, "light", a * 0.9, glow=0.8)


# --- 4C: OCR + standardisation ---------------------------------------------------------
OCR_ROWS = [("유압 확인", "정상", "작업자 A"), ("윤활 상태", "보충 필요", "작업자 A"), ("소음·진동", "정상", "작업자 B")]
NAMES = ["프레스3", "#3 Press", "3호기"]


def _ocr(c, t):
    a = prog(t, T_OCR[0], T_OCR[0] + 0.5) * (1 - prog(t, T_CONVERGE[0] - 0.2, T_CONVERGE[0] + 0.3))
    if a <= 0:
        return
    # paper: the real handwritten checklist from the desk plate (V3)
    px, py, pw, ph = 330, 190, 520, 660
    sx, sy = _sys_pos(4)
    pe = prog(t, T_OCR[0], T_OCR[0] + 0.7, house)
    x = lerp(sx - 60, px, pe)
    y = lerp(sy - 40, py, pe)
    w = lerp(120, pw, pe)
    h = lerp(150, ph, pe)
    c.drawRRect(gfx.rrect(x, y + 12, w, h, 10), gfx.fill("#000000", 0.4 * a, blur=24))
    gfx.draw_image(c, Plate("V3").image(0.2), x, y, w, h, a, src=(200, 160, 175, 270))
    # scan beam + recognised field boxes
    sp = prog(t, 10.2, 11.2, in_out_cubic)
    if 0 < sp < 1:
        yy = y + h * sp
        c.drawRect(skia.Rect.MakeXYWH(x - 10, yy - 2, w + 20, 4), gfx.fill("light", a))
        c.drawRect(skia.Rect.MakeXYWH(x, yy - 60, w, 60), gfx.fill("line", 0.18 * a, blur=12))
    for k in range(3):
        fy = y + h * (0.22 + k * 0.17)
        bp = prog(t, 10.35 + k * 0.25, 10.6 + k * 0.25)
        if bp > 0:
            c.drawRRect(gfx.rrect(x + 22, fy, w - 44, h * 0.1, 6), gfx.stroke("axblue", 3, a * bp))
            c.drawRRect(gfx.rrect(x + 22, fy, w - 44, h * 0.1, 6), gfx.fill("axblue", 0.12 * a * bp))
    gfx.text_rise(c, "OCR", x, y - 40, prog(t, 10.0, 10.4), 34, 700, "white", a)
    gfx.text_rise(c, "수기 점검표 → 구조화 데이터", x + 90, y - 40, prog(t, 10.1, 10.5), 24, 500, "ice", a)
    # structured table
    tx, ty, tw = 960, 250, 640
    ta = prog(t, 10.9, 11.3) * a
    if ta > 0:
        gfx.card(c, tx, ty, tw, 380, 20, "surface", ta, "border", 0.2)
        gfx.text(c, "인식 결과", tx + 34, ty + 52, 26, 700, "ink", ta)
        ui.tag(c, tx + tw - 110, ty + 52, "DEMO", "gray", ta, 18)
        cols = [tx + 34, tx + 260, tx + 450]
        for j, hname in enumerate(("점검 항목", "결과", "담당")):
            gfx.text(c, hname, cols[j], ty + 112, 20, 600, "ink3", ta)
        c.drawLine(tx + 30, ty + 136, tx + tw - 30, ty + 136, gfx.stroke("border", 1.5, ta))
        for r, row in enumerate(OCR_ROWS):
            rp = prog(t, 11.1 + r * 0.3, 11.5 + r * 0.3, house)
            if rp <= 0:
                continue
            # each row flies from its box on the paper
            fy = y + h * (0.22 + r * 0.17) + h * 0.05
            ry = ty + 180 + r * 66
            for j, v in enumerate(row):
                vx = lerp(x + 40 + j * 120, cols[j], rp)
                vy = lerp(fy, ry, rp)
                gfx.text(c, v, vx, vy, 25, 600 if j == 1 else 500,
                         "red" if v == "보충 필요" else "ink", ta * min(1, rp * 2))
    # standardisation: three names for the same machine → one code
    sa = prog(t, 12.2, 12.5) * a
    if sa > 0:
        merge = prog(t, 12.5, 13.2, house_io)
        cxs = [1080, 1280, 1480]
        for k, n in enumerate(NAMES):
            x_ = lerp(cxs[k], 1280, merge)
            y_ = lerp(760 + (k - 1) * 18, 760, merge)
            gfx.chip(c, x_, y_, n, 26, 600, "ink", "surface", "border", sa * (1 - prog(merge, 0.7, 1.0)))
        if merge > 0.7:
            pa = prog(merge, 0.7, 1.0)
            fly = prog(t, 13.6, 14.3, in_cubic)
            gx, gy = lerp(1280, AI_POS[0], fly), lerp(760, AI_POS[1], fly)
            gfx.chip(c, gx, gy, "EQ-PRS-03", 28, 700, "white", "axblue", None, pa * (1 - fly), dot="white")
            gfx.text_rise(c, "표준 코드", gx, gy + 56, pa * (1 - fly), 22, 600, "ice", 1.0, "center")


# --- 4D: ontology (2.5D glass plane, entity tiles, AI node, process timeline) ----------------
# Layout follows the AXCORE Ontology frame supplied by the client; rebuilt as vectors.
PLANE_W, PLANE_H = 1000.0, 600.0
PLANE_Q = [(430, 395), (1530, 412), (1715, 790), (215, 762)]      # tl, tr, br, bl (design px)
AI_POS = (CX + 20, 318)
ENT = [  # (label, icon, plane u, v, chip style)
    ("설비", "gear", 0.12, 0.47, "sky"), ("자재", "cube", 0.30, 0.12, "white"),
    ("공정", "factory", 0.47, 0.45, "sky"), ("제품", "cube", 0.67, 0.16, "sky"),
    ("사람", "person", 0.62, 0.70, "white"), ("업무", "doc", 0.86, 0.47, "sky"),
]
RELS = [(0, 1), (1, 2), (0, 2), (2, 3), (2, 4), (3, 5), (4, 5), (0, 4)]
STAGES = ["시작", "수주", "생산 계획", "자재 구매", "생산", "품질 검사", "출하", "끝"]
TL_Y0, TL_Y1, TL_X0, TL_X1 = 860, 885, 215, 1700
ENT_TO_STAGE = {1: 3, 2: 4, 4: 5, 5: 6, 0: 2}
T_PLANE = (15.2, 16.4)
T_ENT = 16.2
T_REL = (17.6, 18.8)
T_AI = (18.2, 19.2)
T_TL = (19.0, 20.4)
T_FLOW = (20.6, 22.4)

_H_PLANE = None


def _plane_H():
    global _H_PLANE
    if _H_PLANE is None:
        import cv2
        src = np.float32([(0, 0), (PLANE_W, 0), (PLANE_W, PLANE_H), (0, PLANE_H)])
        _H_PLANE = cv2.getPerspectiveTransform(src, np.float32(PLANE_Q))
    return _H_PLANE


def plane_pt(u, v):
    H = _plane_H()
    x, y, w = H @ np.array([u * PLANE_W, v * PLANE_H, 1.0])
    return x / w, y / w


def ent_pos(i, t=99.0):
    """Top of the entity tile (where lines from the AI node land)."""
    _, _, u, v, _ = ENT[i]
    x, y = plane_pt(u, v)
    return x, y - 70


def _stage_x(k):
    return lerp(TL_X0, TL_X1, k / (len(STAGES) - 1))


def _stage_y(k):
    return lerp(TL_Y0, TL_Y1, k / (len(STAGES) - 1))


def _icon(c, kind, x, y, s, a):
    st = gfx.stroke("white", s * 0.075, a)
    if kind == "gear":
        c.drawCircle(x, y, s * 0.18, st)
        for k in range(8):
            ang = math.radians(k * 45)
            c.drawLine(x + math.cos(ang) * s * 0.27, y + math.sin(ang) * s * 0.27,
                       x + math.cos(ang) * s * 0.38, y + math.sin(ang) * s * 0.38, st)
    elif kind == "cube":
        r = s * 0.32
        top = [(x, y - r), (x + r * 0.87, y - r * 0.5), (x, y), (x - r * 0.87, y - r * 0.5)]
        p = skia.Path()
        p.addPoly([skia.Point(*q) for q in top], True)
        p.moveTo(x - r * 0.87, y - r * 0.5)
        p.lineTo(x - r * 0.87, y + r * 0.5)
        p.lineTo(x, y + r)
        p.lineTo(x + r * 0.87, y + r * 0.5)
        p.lineTo(x + r * 0.87, y - r * 0.5)
        p.moveTo(x, y)
        p.lineTo(x, y + r)
        c.drawPath(p, st)
    elif kind == "factory":
        p = skia.Path()
        p.addPoly([skia.Point(x - s * 0.36, y + s * 0.3), skia.Point(x - s * 0.36, y - s * 0.05),
                   skia.Point(x - s * 0.12, y + s * 0.08), skia.Point(x - s * 0.12, y - s * 0.05),
                   skia.Point(x + s * 0.12, y + s * 0.08), skia.Point(x + s * 0.12, y - s * 0.32),
                   skia.Point(x + s * 0.36, y - s * 0.32), skia.Point(x + s * 0.36, y + s * 0.3)], True)
        c.drawPath(p, st)
    elif kind == "person":
        c.drawCircle(x, y - s * 0.14, s * 0.14, st)
        p = skia.Path()
        p.addArc(skia.Rect.MakeXYWH(x - s * 0.3, y + s * 0.08, s * 0.6, s * 0.5), 180, 180)
        c.drawPath(p, st)
    else:  # doc
        c.drawRRect(gfx.rrect(x - s * 0.24, y - s * 0.32, s * 0.48, s * 0.64, s * 0.05), st)
        for k in range(3):
            c.drawLine(x - s * 0.13, y - s * 0.08 + k * s * 0.12, x + s * 0.13, y - s * 0.08 + k * s * 0.12, st)


def _cloud_specs():
    if "s" not in _cloud:
        rng = np.random.default_rng(3)
        _cloud["s"] = [(rng.uniform(0, 2 * math.pi), rng.uniform(120, 560), rng.uniform(0.5, 1.6),
                        int(rng.integers(0, 6)), rng.uniform(0, 2 * math.pi)) for _ in range(110)]
    return _cloud["s"]


_cloud = {}


def _onto_bg(c, a):
    """Horizon glow + faint perspective floor (part of the ontology space)."""
    hy = 690
    sh = skia.GradientShader.MakeLinear([skia.Point(0, hy - 140), skia.Point(0, hy + 140)],
                                        [gfx.color("light", 0.0), gfx.color("light", 0.16 * a),
                                         gfx.color("light", 0.0)], [0.0, 0.5, 1.0])
    c.drawRect(skia.Rect.MakeXYWH(0, hy - 140, DESIGN_W, 280), skia.Paint(Shader=sh))
    c.drawLine(0, hy, DESIGN_W, hy, gfx.stroke("ice", 1.5, 0.35 * a, blur=2))
    for k in range(-6, 7):
        c.drawLine(CX + k * 60, hy, CX + k * 420, DESIGN_H, gfx.stroke("light", 1.0, 0.08 * a))


def draw_ontology(c, t, a=1.0, labels=True):
    """AXCORE Ontology frame (S05 also draws this as the monitor content)."""
    pp = prog(t, *T_PLANE, ease=in_out_cubic)
    if pp > 0:
        _onto_bg(c, a * pp)
    # header: real logo + "Ontology"
    ha = prog(t, 15.4, 16.0) * a
    if ha > 0:
        ui.draw_logo(c, CX - 350, 70 + (1 - ha) * 10, 64, a=ha)
        gfx.text(c, "Ontology", CX + 60, 108 + (1 - ha) * 10, 64, 500, "white", ha)
    # glass plane (draw-on border, then fill + thickness)
    if pp > 0:
        path = skia.Path()
        path.addPoly([skia.Point(*q) for q in PLANE_Q], True)
        thick = skia.Path()
        thick.addPoly([skia.Point(*PLANE_Q[3]), skia.Point(*PLANE_Q[2]), skia.Point(PLANE_Q[2][0] - 4, PLANE_Q[2][1] + 22),
                       skia.Point(PLANE_Q[3][0] + 4, PLANE_Q[3][1] + 22)], True)
        c.drawPath(thick, gfx.fill("light", 0.18 * a * pp))
        c.drawPath(path, gfx.fill("ice", 0.10 * a * pp))
        gfx.glow_path(c, path, "ice", 2.0, 0.75 * a, 0.5, 0, pp)
    # data cloud settles onto the plane (complex → structured)
    for k, (ang, rad, sp, ent, ph) in enumerate(_cloud_specs()):
        pa = prog(t, 14.6 + (k % 20) * 0.02, 15.2 + (k % 20) * 0.02)
        if pa <= 0:
            continue
        po = prog(t, 15.6 + (k % 11) * 0.06, 16.9 + (k % 11) * 0.06, in_out_cubic)
        aa = ang + t * 0.35 * sp
        x0, y0 = AI_POS[0] + rad * math.cos(aa) * 1.3, 560 + rad * math.sin(aa) * 0.6
        _, _, u, v, _ = ENT[ent]
        ex, ey = plane_pt(u + 0.05 * math.cos(ph), v + 0.08 * math.sin(ph))
        x, y = lerp(x0, ex, po), lerp(y0, ey, po)
        x, y = lerp(AI_POS[0], x, pa), lerp(AI_POS[1], y, pa)
        c.drawCircle(x, y, 3.2, gfx.fill("light" if k % 3 else "white", a * pa * (1 - 0.8 * prog(t, 17.0, 17.6))))
    H = _plane_H()
    # relations (dashed, on the plane)
    for j, (s_, e_) in enumerate(RELS):
        pr = prog(t, T_REL[0] + j * 0.1, T_REL[0] + 0.5 + j * 0.1, in_out_cubic)
        if pr <= 0:
            continue
        (x0, y0), (x1, y1) = plane_pt(*ENT[s_][2:4]), plane_pt(*ENT[e_][2:4])
        c.drawLine(x0, y0, lerp(x0, x1, pr), lerp(y0, y1, pr), gfx.stroke("ice", 1.6, 0.55 * a, dash=(8, 8)))
    # timeline + entity drops
    pt_ = prog(t, *T_TL, ease=in_out_cubic)
    flow = prog(t, *T_FLOW, ease=in_out_cubic)
    if pt_ > 0:
        gfx.glow_line(c, TL_X0, TL_Y0, lerp(TL_X0, TL_X1, pt_), lerp(TL_Y0, TL_Y1, pt_), "sky", 4, a, 1.0)
        for k, name in enumerate(STAGES):
            ps = prog(pt_, k / len(STAGES), k / len(STAGES) + 0.2)
            if ps <= 0:
                continue
            sx, sy = _stage_x(k), _stage_y(k)
            kk = k / (len(STAGES) - 1)
            lit = window(flow, kk - 0.05, kk + 0.3, 0.05, 0.2)
            sq = 11 if k in (0, len(STAGES) - 1) else 8
            c.drawRect(skia.Rect.MakeXYWH(sx - sq, sy - sq, sq * 2, sq * 2), gfx.fill(gfx.mix("sky", "white", lit), a * ps))
            if labels:
                end = k in (0, len(STAGES) - 1)
                gfx.chip(c, sx, sy + 62, name, 26, 700, "white" if not end else "navy_deep",
                         "axblue" if not end else "sky", "sky", a * ps, pad=18)
        if flow > 0:   # one pulse runs the whole process
            fx = lerp(TL_X0, TL_X1, flow)
            gfx.node(c, fx, lerp(TL_Y0, TL_Y1, flow), 9, "white", a, glow=1.2)
    # entity tiles (billboards standing on their pads)
    order = sorted(range(len(ENT)), key=lambda i: ENT[i][3])
    for i in order:
        label, icon, u, v, chip_style = ENT[i]
        pe = prog(t, T_ENT + i * 0.18, T_ENT + 0.6 + i * 0.18)
        if pe <= 0:
            continue
        px, py = plane_pt(u, v)
        # pad = circle on the plane
        c.save()
        c.concat(gfx.homography_matrix(H))
        r = 70 * out_cubic(pe)
        cu, cv = u * PLANE_W, v * PLANE_H
        c.drawCircle(cu, cv, r, gfx.fill("ice", 0.12 * a))
        c.drawCircle(cu, cv, r, gfx.stroke("sky", 2.5, 0.8 * a))
        c.drawCircle(cu, cv, r * 1.3, gfx.stroke("sky", 1.2, 0.35 * a))
        c.restore()
        # drop line to the process timeline
        if i in ENT_TO_STAGE and pt_ > 0:
            k = ENT_TO_STAGE[i]
            sx, sy = _stage_x(k), _stage_y(k)
            path = skia.Path()
            path.moveTo(px, py)
            path.cubicTo(px, py + 120, sx, sy - 160, sx, sy)
            kk = k / (len(STAGES) - 1)
            lit = window(flow, kk - 0.06, kk + 0.3, 0.06, 0.2)
            gfx.glow_path(c, path, gfx.mix("sky", "white", lit), 2.2 + 1.5 * lit, a, 0.9 + lit, 0, pt_)
        lit_e = 0.0
        if i in ENT_TO_STAGE:
            k = ENT_TO_STAGE[i]
            lit_e = window(flow, k / (len(STAGES) - 1) - 0.04, k / (len(STAGES) - 1) + 0.25, 0.04, 0.15)
        ty = py - 70 - (1 - pe) * 30
        s = 116
        c.drawRRect(gfx.rrect(px - s / 2, ty - s / 2 + 8, s, s, 22), gfx.fill("#000000", 0.35 * a * pe, blur=14))
        c.drawRRect(gfx.rrect(px - s / 2, ty - s / 2, s, s, 22), gfx.fill(gfx.mix("navy", "navy_mid", lit_e), 0.95 * a * pe))
        c.drawRRect(gfx.rrect(px - s / 2, ty - s / 2, s, s, 22), gfx.stroke(gfx.mix("sky", "white", lit_e), 2.5, a * pe))
        if lit_e > 0:
            c.drawRRect(gfx.rrect(px - s / 2 - 8, ty - s / 2 - 8, s + 16, s + 16, 26), gfx.stroke("sky", 10, 0.3 * lit_e * a, blur=10))
        _icon(c, icon, px, ty, s * 0.78, a * pe)
        if labels:
            gfx.chip(c, px, ty - s / 2 - 34, label, 26, 700, "navy_deep", chip_style, None, a * pe, pad=18)
    # AI node with rings; lines to every entity
    pa = prog(t, *T_AI, ease=house)
    core = prog(t, T_CONVERGE[0] + 0.6, T_CONVERGE[1])
    if core > 0:
        ax, ay = AI_POS
        for k, rr in enumerate((58, 84, 112)):
            c.drawCircle(ax, ay, rr * (0.6 + 0.4 * pa), gfx.stroke("sky", 1.6, (0.55 - k * 0.15) * a * core))
        c.drawCircle(ax, ay, 150, gfx.fill("line", 0.12 * a * core, blur=40))
        c.drawCircle(ax, ay, 50, gfx.fill("navy_deep", a * core))
        c.drawCircle(ax, ay, 50, gfx.stroke("sky", 2.5, a * core))
        ta = prog(t, T_AI[0], T_AI[0] + 0.4)
        gfx.diamond(c, ax, ay, 14 * (1 - ta) + 0.01, "axblue", a * core * (1 - ta), glow=0.8, edge="light")
        gfx.text(c, "AI", ax, ay, 40, 700, "white", a * ta, "center")
        for i in range(len(ENT)):
            pl = prog(t, T_AI[0] + i * 0.08, T_AI[0] + 0.5 + i * 0.08, in_out_cubic)
            if pl > 0:
                ex, ey = ent_pos(i)
                c.drawLine(ax, ay + 50, lerp(ax, ex, pl), lerp(ay + 50, ey - 50, pl), gfx.stroke("ice", 1.2, 0.45 * a))


# --- ontology footage (client-supplied scene, used as-is) ------------------------------------
ONTO_START = 14.2     # scene time at which the clip starts
BAND_H = DESIGN_W * 536 / 1280
BAND_Y = (DESIGN_H - BAND_H) / 2


def draw_onto_clip(c, ct, a=1.0):
    """Cinemascope clip in a 16:9 frame: bars filled by its own defocused image."""
    pl = Plate("ONTO")
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("navy_deep", a))
    pl.draw_blurred(c, ct, sigma=40, a=a, scale=1.25)
    c.saveLayer(None, None)
    gfx.draw_image(c, pl.image(ct), 0, BAND_Y, DESIGN_W, BAND_H, a)
    mask = skia.Paint(BlendMode=skia.BlendMode.kDstIn)
    mask.setShader(skia.GradientShader.MakeLinear(
        [skia.Point(0, BAND_Y), skia.Point(0, BAND_Y + BAND_H)],
        [gfx.color("white", 0), gfx.color("white", 1), gfx.color("white", 1), gfx.color("white", 0)],
        [0.0, 0.12, 0.88, 1.0]))
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), mask)
    c.restore()


# --- frame -------------------------------------------------------------------------------
def render(c, t):
    if t < T_EXPAND[0]:
        s03.draw_world(c, 19.0, _push_cam(t))
        ui.topbar(c, 0, 0, DESIGN_W, 5, 1.0 - prog(t, 0.6, 1.0))
        bx, by, bw, bh = _banner_screen(_push_cam(t))
        # cursor clicks "체험하기"
        ca = prog(t, 0.55, 0.75)
        px, py = bx + bw * (125 / 1120), by + bh * (262 / 330)
        cursor(c, lerp(px + 180, px, prog(t, 0.6, 1.0, house_io)), lerp(py + 120, py, prog(t, 0.6, 1.0, house_io)),
               prog(t, T_CLICK, T_CLICK + 0.3), ca)
        return
    if t < T_PULL[0]:
        _builder(c, t)
        if t > T_ASSEMBLE[0]:
            build = prog(t, T_ASSEMBLE[0] + 0.3, T_ASSEMBLE[1] + 0.2)
            _workspace_layout(c, *BUILDER, a=prog(t, T_ASSEMBLE[0] + 0.2, T_ASSEMBLE[0] + 0.5), t=t, build=build)
        return
    # pull-out: the workspace becomes one panel in navy space; the factory plate
    # behind it shrinks with it (closer layer) and is occluded by the panel
    navy_space(c, bloom=(CX, CY + 40), intensity=1.0)
    pp = prog(t, *T_PULL, ease=house_io)
    ws = _ws_rect(t)
    if pp < 1:
        fx, fy, fw, fh = [lerp(a, b, prog(t, T_PULL[0], T_PULL[1] - 0.15, house_io))
                          for a, b in zip((-40, -40, DESIGN_W + 80, DESIGN_H + 80), WS_SMALL)]
        c.save()
        c.clipRRect(gfx.rrect(fx, fy, fw, fh, 26), True)
        Plate("V2").draw_blurred(c, 1.5 + t * 0.35, sigma=20, veil="navy_deep", veil_a=0.25 + 0.5 * pp)
        c.restore()
    fade_ws = 1 - prog(t, T_CONVERGE[0], T_CONVERGE[0] + 0.9)
    shrink = prog(t, T_CONVERGE[0], T_CONVERGE[1], in_cubic)
    sa = 1 - prog(t, T_CONVERGE[0] + 0.2, T_CONVERGE[0] + 1.0)
    c.save()
    if shrink > 0:  # systems + workspace recede into the core
        c.translate(AI_POS[0], AI_POS[1])
        c.scale(1 - 0.92 * shrink, 1 - 0.92 * shrink)
        c.translate(-CX, -CY)
    ocr_dim = window(t, T_OCR[0], T_OCR[1], 0.4, 0.4)
    _connectors(c, t, sa * (1 - 0.6 * ocr_dim))
    for i in range(len(SYSTEMS)):
        _sys_block(c, i, t, sa * (1 - 0.6 * ocr_dim))
    _workspace_layout(c, *ws, a=fade_ws * (1 - 0.6 * ocr_dim), t=t, build=1.0)
    c.restore()
    if t >= T_SYS:
        la = prog(t, T_SYS + 0.4, T_SYS + 0.9) * (1 - prog(t, T_OCR[0], T_OCR[0] + 0.3))
        gfx.text_rise(c, "사내 시스템", 250, 160, la, 26, 600, "ice", 1.0, "center")
        gfx.text_rise(c, "업무 파일 · 외부 SaaS", DESIGN_W - 250, 160, la, 26, 600, "ice", 1.0, "center")
    _ocr(c, t)
    if t >= ONTO_START:
        # the clip opens from the convergence point (shape reveal, not a dissolve)
        rp = prog(t, ONTO_START, ONTO_START + 1.0, in_out_cubic)
        c.save()
        if rp < 1:
            path = skia.Path()
            path.addCircle(AI_POS[0], AI_POS[1], lerp(1, 2300, rp))
            c.clipPath(path, skia.ClipOp.kIntersect, True)
        draw_onto_clip(c, t - ONTO_START)
        c.restore()
        if rp < 1:
            c.drawCircle(AI_POS[0], AI_POS[1], lerp(1, 2300, rp), gfx.stroke("sky", 2.5, 1 - rp))
