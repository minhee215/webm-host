"""SCENE 05 · 73–89s · One question, every source.

The ontology from S04 shrinks into the engineer's monitor (pull-out reveals
the real office, V8). Its core diamond opens into the AI assistant; a question
is typed; search lines leave the screen and travel to source panels that live
on the window plane (homography-tracked); matching items light up and return.
The camera then pushes into the screen while the room racks out of focus, and
the answer panel (situation / cause / context) floats in front of it.
"""
import math

import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx, tracks
from ..compositing import ui_axpoint as ui
from ..compositing.background import navy_space
from ..compositing.plates import Plate
from ..motion.easing import (prog, window, lerp, lerp2, out_cubic, in_out_cubic, in_cubic, house,
                             house_io, clamp)
from . import s04
from .common import P, H_design, warp, screen

CX, CY = DESIGN_W / 2, DESIGN_H / 2
SPEED = 0.5                       # V8 is 8 s; scene is 16 s
QUESTION = "이번 주 2라인 불량이 늘어난 원인은?"

T_SHRINK = (0.15, 2.1)
T_OPEN = (1.7, 2.6)
T_TYPE = (2.7, 4.3)
T_SEND = 4.5
T_ZOOM1 = (2.2, 3.0)              # virtual push toward the screen while typing
T_ZOOM1_OUT = (4.6, 5.4)
T_SEARCH = 5.4
T_RETURN = 8.6
T_PUSH = (10.2, 11.6)
T_ANSWER = 11.4
T_EXIT = (14.6, 16.0)

SOURCES = [  # (label, selected item, plate anchor on the window plane, frame 0)
    ("ERP", "2라인 출하 일정", (712, 34)),
    ("MES", "2라인 불량 실적", (842, 88)),
    ("문서", "작업표준서 개정 이력", (712, 146)),
    ("생산 데이터", "금형 온도 로그", (842, 200)),
    ("품질 데이터", "외관 불량 유형", (712, 258)),
]

SFX = [(0.2, "pull", 0.55), (1.8, "ui_open", 0.55)] + \
      [(T_TYPE[0] + i * 0.08, "type", 0.25) for i in range(0, len(QUESTION), 2)] + \
      [(T_SEND, "select", 0.7), (T_SEARCH, "line", 0.6)] + \
      [(T_SEARCH + 0.35 + i * 0.32, "scan", 0.4) for i in range(5)] + \
      [(T_SEARCH + 1.6 + i * 0.25, "node", 0.35) for i in range(5)] + \
      [(T_RETURN, "line_rev", 0.5), (T_PUSH[0], "push", 0.6), (T_ANSWER + 0.1, "ui_open", 0.5),
       (T_ANSWER + 0.7, "ui_tick", 0.45), (T_ANSWER + 1.3, "ui_tick", 0.45), (T_ANSWER + 1.9, "ui_tick", 0.45),
       (T_EXIT[0], "push", 0.5)]


def motion_blur(t):
    for a, b in ((0.3, 1.9), (T_PUSH[0] + 0.3, T_PUSH[1]), (T_EXIT[0] + 0.6, T_EXIT[1])):
        if a <= t <= b:
            return 5
    return 1


def _pt(t):
    return t * SPEED


def _quad(t):
    qs = tracks.v8_screen()
    return [P(p) for p in qs[min(len(qs) - 1, int(_pt(t) * 24))]]


def _plane(t):
    Hs = tracks.v8_plane()
    return H_design(Hs[min(len(Hs) - 1, int(_pt(t) * 24))])


# --- screen content ------------------------------------------------------------------
SW, SH = 1600, 1000


def _assistant(c, t, answer_hint=0.0):
    c.drawRect(skia.Rect.MakeWH(SW, SH), gfx.fill("surface"))
    c.drawRect(skia.Rect.MakeXYWH(0, 0, 300, SH), gfx.fill("bg"))
    ui.draw_logo(c, 36, 40, 30, dark=True)
    for k, it in enumerate(["AI 대화", "생산관리", "품질검사", "장비관리", "영업관리"]):
        yy = 150 + k * 70
        if k == 0:
            c.drawRRect(gfx.rrect(18, yy - 28, 264, 56, 12), gfx.fill("tint"))
        gfx.text(c, it, 50, yy, 26, 600 if k == 0 else 500, "axblue" if k == 0 else "ink2")
    gfx.diamond(c, 950, 330, 16, "axblue")
    gfx.text(c, "여러가지 작업을 진행해 보세요.", 950, 410, 50, 700, "ink", 1.0, "center")
    # input
    x, y, w, h = 400, 560, 1100, 120
    c.drawRRect(gfx.rrect(x, y, w, h, 24), gfx.fill("surface"))
    c.drawRRect(gfx.rrect(x, y, w, h, 24), gfx.stroke(gfx.mix("border", "axblue", 1.0), 3))
    n = int(len(QUESTION) * prog(t, *T_TYPE, ease=lambda v: v))
    if n == 0:
        gfx.text(c, "무엇이든 물어보세요", x + 40, y + h / 2, 38, 400, "ink3")
    tw = gfx.text(c, QUESTION[:n], x + 40, y + h / 2, 40, 600, "ink")
    if T_TYPE[0] <= t < T_SEND and (t % 0.8) < 0.45:
        c.drawRect(skia.Rect.MakeXYWH(x + 46 + tw, y + 34, 3, 52), gfx.fill("axblue"))
    press = prog(t, T_SEND, T_SEND + 0.3)
    s = 1 - 0.08 * math.sin(math.pi * press)
    c.save()
    c.translate(x + w - 70, y + h / 2)
    c.scale(s, s)
    c.drawCircle(0, 0, 38, gfx.fill("axblue"))
    path = skia.Path()
    path.moveTo(-12, 0)
    path.lineTo(12, 0)
    path.moveTo(2, -12)
    path.lineTo(12, 0)
    path.lineTo(2, 12)
    c.drawPath(path, gfx.stroke("white", 5))
    c.restore()
    if t > T_SEND + 0.2:  # searching state under the input
        k = int((t * 3) % 4)
        gfx.text(c, "관련 데이터 검색 중" + "." * k, x + 40, y + h + 70, 30, 500, "axblue",
                 1 - prog(t, T_RETURN + 0.6, T_RETURN + 1.0))


def _screen_content(t):
    def draw(c):
        open_p = prog(t, *T_OPEN, ease=in_out_cubic)
        if open_p < 1:
            c.save()
            c.scale(SW / DESIGN_W, SH / DESIGN_H)
            s04.draw_onto_clip(c, min(9.6, 23.0 - s04.ONTO_START + t))
            c.restore()
        if open_p > 0:  # the core diamond opens into the assistant (flood from the object)
            path = skia.Path()
            path.addCircle(SW / 2, SH / 2, lerp(0, 1100, open_p))
            c.save()
            c.clipPath(path, skia.ClipOp.kIntersect, True)
            _assistant(c, t)
            c.restore()
    return draw


# --- environmental source panels -------------------------------------------------------
def _source_panels(c, t, H, quad):
    sx, sy = (quad[1][0] + quad[2][0]) / 2, (quad[1][1] + quad[2][1]) / 2   # screen right edge
    for i, (label, item, anchor) in enumerate(SOURCES):
        t0 = T_SEARCH + i * 0.32
        pa = prog(t, t0 - 0.2, t0 + 0.3) * (1 - prog(t, T_PUSH[0], T_PUSH[0] + 0.4))
        if pa <= 0:
            continue
        ax, ay = warp(H, [P(anchor)])[0]
        w, h = 300, 150
        # search line from the screen to the panel
        path = skia.Path()
        path.moveTo(sx, sy)
        path.cubicTo(sx + 120, sy, ax - 120, ay + h / 2, ax, ay + h / 2)
        pl = prog(t, t0, t0 + 0.45, in_out_cubic)
        back = prog(t, T_RETURN, T_RETURN + 0.6, in_out_cubic)
        gfx.glow_path(c, path, "light", 2.0, 0.9 * pa, 0.7, back, pl)
        if T_RETURN <= t <= T_RETURN + 0.8:   # data returns along the line
            px, py = gfx.point_at(path, 1 - back)
            gfx.node(c, px, py, 7, "white", 1.0, glow=1.0)
        # glass panel on the window plane
        c.drawRRect(gfx.rrect(ax, ay, w, h, 16), gfx.fill("white", 0.82 * pa))
        c.drawRRect(gfx.rrect(ax, ay, w, h, 16), gfx.stroke("white", 1.5, pa))
        gfx.text(c, label, ax + 22, ay + 32, 24, 700, "ink", pa)
        sel = prog(t, T_SEARCH + 1.6 + i * 0.25, T_SEARCH + 1.9 + i * 0.25)
        for r in range(2):
            yy = ay + 72 + r * 44
            if r == 0:
                c.drawRRect(gfx.rrect(ax + 12, yy - 18, w - 24, 36, 8),
                            gfx.fill(gfx.mix("bg", "axblue", sel), pa))
                gfx.text(c, item, ax + 24, yy, 20, 600, gfx.mix("ink", "white", sel), pa)
            else:
                c.drawRect(skia.Rect.MakeXYWH(ax + 24, yy - 4, w * 0.55, 8), gfx.fill("border", pa))
        # scan sweep when the line arrives
        sp = prog(t, t0 + 0.4, t0 + 0.8)
        if 0 < sp < 1:
            c.drawRect(skia.Rect.MakeXYWH(ax, ay + h * sp - 2, w, 4), gfx.fill("axblue", 0.8 * pa))


# --- answer panel ---------------------------------------------------------------------------
AW, AH = 1560, 860
CAUSE_LINE = [(0, 0.62), (0.15, 0.58), (0.3, 0.6), (0.45, 0.45), (0.6, 0.38), (0.75, 0.22), (0.9, 0.18), (1.0, 0.12)]


def _answer(c, x, y, t, a=1.0):
    gfx.card(c, x, y, AW, AH, 28, "surface", a, "border", 0.25)
    gfx.diamond(c, x + 60, y + 64, 12, "axblue", a)
    gfx.text(c, QUESTION, x + 90, y + 64, 32, 700, "ink", a)
    ui.tag(c, x + AW - 130, y + 64, "DEMO", "gray", a, 20)
    secs = [
        ("현재 상황", "2라인 외관 불량 증가", ["MES 생산실적"]),
        ("원인", "금형 온도 편차 구간과 불량 발생 시점 일치", ["생산 데이터", "품질 데이터"]),
        ("맥락", "설비 점검 지연 · 작업표준서 개정 전 공정", ["문서", "ERP"]),
    ]
    for k, (title, body, srcs) in enumerate(secs):
        ps = prog(t, T_ANSWER + 0.5 + k * 0.6, T_ANSWER + 1.0 + k * 0.6) * a
        if ps <= 0:
            continue
        sy = y + 150 + k * 230 + (1 - ps) * 14
        c.drawRRect(gfx.rrect(x + 50, sy, AW - 100, 200, 20), gfx.fill("bg", ps))
        c.drawRect(skia.Rect.MakeXYWH(x + 50, sy + 24, 6, 152), gfx.fill("axblue", ps))
        gfx.text(c, title, x + 90, sy + 50, 26, 700, "axblue", ps)
        gfx.text(c, body, x + 90, sy + 108, 34, 700, "ink", ps)
        tx = x + 90
        for s_ in srcs:
            tx += ui.tag(c, tx, sy + 160, "출처 · " + s_, "blue", ps, 20) + 12
        if k == 1:   # the cause trend line (handed to S06)
            lx, ly, lw, lh = x + AW - 560, sy + 30, 440, 140
            path = _cause_path(lx, ly, lw, lh)
            gfx.glow_path(c, path, "axblue", 4, ps, 0.3, 0, prog(t, T_ANSWER + 1.2, T_ANSWER + 2.0))


def _cause_path(lx, ly, lw, lh):
    return gfx.polyline_path([(lx + u * lw, ly + v * lh) for u, v in CAUSE_LINE], smooth=0.4)


def answer_rect():
    return CX - AW / 2, CY - AH / 2 + 10


def cause_line_end():
    x, y = answer_rect()
    sy = y + 150 + 230
    lx, ly, lw, lh = x + AW - 560, sy + 30, 440, 140
    return lx + lw, ly + CAUSE_LINE[-1][1] * lh


# --- frame ----------------------------------------------------------------------------------
def render(c, t):
    pt = _pt(t)
    quad = _quad(t)
    H = _plane(t)
    # virtual camera: push toward the screen while typing, then into it for the answer
    z1 = window(t, T_ZOOM1[0], T_ZOOM1_OUT[1], T_ZOOM1[1] - T_ZOOM1[0], T_ZOOM1_OUT[1] - T_ZOOM1_OUT[0],
                in_out_cubic)
    zp = prog(t, *T_PUSH, ease=in_out_cubic)
    qc = np.mean(quad, axis=0)
    zoom = 1 + 0.75 * z1 + 0.9 * zp
    focus = (lerp(CX, qc[0], max(z1, zp) * 0.9), lerp(CY, qc[1], max(z1, zp) * 0.9))
    if t < T_SHRINK[1]:
        # pull out of the ontology: the screen quad starts beyond the frame
        p = prog(t, *T_SHRINK, ease=house_io)
        full = [(-60, -40), (DESIGN_W + 60, -40), (DESIGN_W + 60, DESIGN_H + 40), (-60, DESIGN_H + 40)]
        quad = [lerp2(f, q, p) for f, q in zip(full, quad)]
    rack = prog(t, T_PUSH[0] + 0.2, T_PUSH[1], in_out_cubic)
    if rack > 0:   # focus pull: the whole room (screen included) goes soft
        lp = skia.Paint()
        lp.setImageFilter(skia.ImageFilters.Blur(16 * rack, 16 * rack))
        c.saveLayer(None, lp)
    c.save()
    c.translate(CX, CY)
    c.scale(zoom, zoom)
    c.translate(-focus[0], -focus[1])
    Plate("V8").draw(c, pt)
    screen(c, quad, SW, SH, _screen_content(t), glow=0.4)
    if t >= T_SEARCH - 0.3:
        _source_panels(c, t, H, quad)
    c.restore()
    if rack > 0:
        c.restore()
        c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("navy_deep", 0.35 * rack))
    # the answer panel comes forward out of the screen
    pa = prog(t, T_ANSWER, T_ANSWER + 0.6, house)
    if pa > 0:
        ex = prog(t, *T_EXIT, ease=in_cubic)
        ax, ay = answer_rect()
        c.save()
        if ex > 0:   # push into the cause trend line (hand-off to S06)
            lx, ly = cause_line_end()
            z = lerp(1.0, 5.0, ex)
            c.translate(lerp(lx, CX, ex), lerp(ly, CY + 60, ex))
            c.scale(z, z)
            c.translate(-lx, -ly)
        s = lerp(0.8, 1.0, pa)
        c.translate(CX, CY)
        c.scale(s, s)
        c.translate(-CX, -CY)
        _answer(c, ax, ay, t, pa)
        c.restore()
