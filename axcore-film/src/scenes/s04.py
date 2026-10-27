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

ENT = [  # (ko, en, angle deg)
    ("공정", "Process", -90), ("제품", "Product", -30), ("업무", "Task", 30),
    ("사람", "Person", 90), ("설비", "Equipment", 150), ("자재", "Material", 210),
]
RELS = [(5, 0, "투입"), (4, 0, "수행"), (0, 1, "생산"), (3, 2, "담당"), (2, 0, "관리"), (3, 4, "운전")]
PATH = [1, 0, 4, 3, 2]   # 제품(불량) → 공정 → 설비 → 사람 → 업무
RX, RY = 420, 300

SFX = [(0.05, "push", 0.6), (T_CLICK, "select", 0.7), (1.25, "ui_open", 0.6)] + \
      [(t, "select", 0.5) for t in PICK_T] + \
      [(4.05, "air", 0.35), (4.6, "chip_land", 0.4), (5.05, "pull", 0.55)] + \
      [(T_SYS + 0.12 * i, "ui_tick", 0.3) for i in range(7)] + \
      [(T_CONN + 0.3 * i + 0.55, "connector", 0.5) for i in range(7)] + \
      [(9.5, "push", 0.45), (10.25, "scan_long", 0.6), (11.1, "chip_land", 0.4), (11.4, "chip_land", 0.4),
       (11.7, "chip_land", 0.4), (12.5, "merge", 0.55), (13.7, "air", 0.35), (14.1, "swell", 0.55),
       (15.1, "data_rise", 0.45), (17.0, "resolve", 0.5)] + \
      [(T_ORGANISE[0] + 0.3 + 0.18 * i, "node", 0.4) for i in range(6)] + \
      [(T_REL[0] + 0.22 * i, "line", 0.25) for i in range(6)] + \
      [(T_PATH[0] + 0.35 * i, "node_soft", 0.5) for i in range(5)] + [(21.0, "ui_open", 0.4)]


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
            gx, gy = lerp(1280, CX, fly), lerp(760, CY, fly)
            gfx.chip(c, gx, gy, "EQ-PRS-03", 28, 700, "white", "axblue", None, pa * (1 - fly), dot="white")
            gfx.text_rise(c, "표준 코드", gx, gy + 56, pa * (1 - fly), 22, 600, "ice", 1.0, "center")


# --- 4D: ontology -------------------------------------------------------------------------
def ent_pos(i, t=99.0):
    ang = math.radians(ENT[i][2] + 4 * math.sin(t * 0.3))
    return CX + RX * math.cos(ang), CY + RY * math.sin(ang)


_cloud = {}


def _cloud_specs():
    if "s" not in _cloud:
        rng = np.random.default_rng(3)
        _cloud["s"] = [(rng.uniform(0, 2 * math.pi), rng.uniform(120, 620), rng.uniform(0.5, 1.6),
                        int(rng.integers(0, 6)), rng.uniform(0, 2 * math.pi), rng.uniform(40, 95))
                       for _ in range(140)]
    return _cloud["s"]


def draw_ontology(c, t, a=1.0, labels=True):
    """Also used by S05 as the monitor content (same object, same layout)."""
    pc = prog(t, *T_CONVERGE, ease=house_io)
    po = prog(t, *T_ORGANISE, ease=in_out_cubic)
    # slow orbits around the core
    oa = a * prog(t, 15.2, 16.4)
    for k, (rx, ry, rot) in enumerate(((560, 380, -8), (300, 210, 12), (720, 470, 4))):
        gfx.orbit(c, CX, CY, rx, ry, rot + t * (2 + k), "line", 1.3, 0.35 * oa, 0.3,
                  prog(t, 15.2 + k * 0.2, 16.6 + k * 0.2), start=t * 12 + k * 90)
    # data cloud → clustered satellites of each entity
    pos = []
    for k, (ang, rad, sp, ent, ph, orb) in enumerate(_cloud_specs()):
        pa = prog(t, T_CLOUD[0] + (k % 20) * 0.03, T_CLOUD[0] + 0.6 + (k % 20) * 0.03)
        if pa <= 0:
            continue
        aa = ang + t * 0.35 * sp
        x0, y0 = CX + rad * math.cos(aa) * 1.25, CY + rad * math.sin(aa) * 0.78
        ex, ey = ent_pos(ent, t)
        x1 = ex + orb * math.cos(ph + t * 0.6)
        y1 = ey + orb * 0.7 * math.sin(ph + t * 0.6)
        x, y = lerp(x0, x1, po), lerp(y0, y1, po)
        x, y = lerp(CX, x, pa), lerp(CY, y, pa)
        pos.append((x, y, ent))
        c.drawCircle(x, y, lerp(3.5, 2.8, po), gfx.fill("light" if k % 3 else "white", a * pa * lerp(0.85, 0.55, po)))
    # messy links while unorganised
    ml = a * window(t, T_CLOUD[0] + 0.4, T_ORGANISE[0] + 0.8, 0.5, 0.9)
    if ml > 0 and len(pos) > 20:
        for k in range(0, len(pos) - 7, 3):
            x0, y0, _ = pos[k]
            x1, y1, _ = pos[k + 7]
            c.drawLine(x0, y0, x1, y1, gfx.stroke("line", 1.0, 0.35 * ml))
    # entities
    for i, (ko, en, ang) in enumerate(ENT):
        pe = prog(t, T_ORGANISE[0] + 0.3 + i * 0.18, T_ORGANISE[0] + 0.8 + i * 0.18)
        if pe <= 0:
            continue
        x, y = ent_pos(i, t)
        c.drawLine(CX, CY, x, y, gfx.stroke("line", 1.2, 0.25 * a * pe, dash=(6, 8)))
        hl = _path_hl(i, t)
        c.drawCircle(x, y, 58, gfx.fill("navy", 0.95 * a * pe))
        c.drawCircle(x, y, 58, gfx.stroke(gfx.mix("line", "white", hl), 2 + 2 * hl, a * pe))
        if hl > 0:
            c.drawCircle(x, y, 74, gfx.stroke("light", 6, 0.25 * hl * a, blur=8))
        if labels:
            gfx.text(c, ko, x, y - 8, 34, 700, "white", a * pe, "center")
            gfx.text(c, en, x, y + 26, 18, 500, "ice", a * pe, "center")
    # relations
    for j, (s_, e_, verb) in enumerate(RELS):
        pr = prog(t, T_REL[0] + j * 0.22, T_REL[0] + 0.5 + j * 0.22, in_out_cubic)
        if pr <= 0:
            continue
        (x0, y0), (x1, y1) = ent_pos(s_, t), ent_pos(e_, t)
        d = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / d, (y1 - y0) / d
        ax, ay = x0 + ux * 64, y0 + uy * 64
        bx, by = x1 - ux * 64, y1 - uy * 64
        hl = _edge_hl(s_, e_, t)
        col = gfx.mix("line", "white", hl)
        gfx.glow_line(c, ax, ay, bx, by, col, 2.2 + 1.5 * hl, a, 0.6 + hl, pr)
        if pr >= 1:  # arrow head
            hx, hy = bx, by
            path = skia.Path()
            path.moveTo(hx - ux * 14 - uy * 8, hy - uy * 14 + ux * 8)
            path.lineTo(hx, hy)
            path.lineTo(hx - ux * 14 + uy * 8, hy - uy * 14 - ux * 8)
            c.drawPath(path, gfx.stroke(col, 2.2, a))
        if labels:
            mx, my = (ax + bx) / 2, (ay + by) / 2
            gfx.chip(c, mx, my, verb, 20, 600, "white", "navy_mid", "line", a * prog(pr, 0.6, 1.0), pad=12)
    # core
    core = a * max(pc, prog(t, 0, 0.01) * 0)
    if core > 0:
        gfx.diamond(c, CX, CY, lerp(10, 26, pc), "axblue", core, glow=1.0, edge="light")
    # context path tags
    if labels:
        for i, txt, kind in ((1, "불량 발생", "red"), (4, "PRS-03", "blue"), (3, "정비 담당", "blue")):
            pt = prog(t, T_PATH[0] + PATH.index(i) * 0.35, T_PATH[0] + PATH.index(i) * 0.35 + 0.3) * a
            if pt > 0:
                x, y = ent_pos(i, t)
                w = ui.tag(c, x - 50, y + 88, txt, kind, pt, 20)
        la = prog(t, 21.0, 21.6) * a
        if la > 0:
            gfx.text_rise(c, "AXCORE Ontology", CX, DESIGN_H - 70, la, 34, 700, "white", 1.0, "center")


def _path_hl(i, t):
    if i not in PATH:
        return 0.0
    k = PATH.index(i)
    return prog(t, T_PATH[0] + k * 0.35, T_PATH[0] + k * 0.35 + 0.25)


def _edge_hl(s_, e_, t):
    for k in range(len(PATH) - 1):
        a_, b_ = PATH[k], PATH[k + 1]
        if {a_, b_} == {s_, e_}:
            return prog(t, T_PATH[0] + (k + 1) * 0.35 - 0.2, T_PATH[0] + (k + 1) * 0.35 + 0.1)
    return 0.0


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
        c.translate(CX, CY)
        c.scale(1 - 0.85 * shrink, 1 - 0.85 * shrink)
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
    if t >= T_CONVERGE[0]:
        draw_ontology(c, t)
