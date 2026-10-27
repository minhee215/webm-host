"""SCENE 07 · 106–116s · The more it connects, the faster it understands.

Pull-out from one node reveals a clean network around the core diamond; extra
links fade, pulses accelerate, three short keywords; nodes begin to converge.
"""
import math

import skia

from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx
from ..compositing.background import navy_space
from ..motion.easing import prog, window, lerp, out_cubic, in_out_cubic, house, house_io

CX, CY = DESIGN_W / 2, DESIGN_H / 2 - 40
NODES = ["데이터", "문서", "시스템", "워크스페이스", "사람", "설비"]
RX, RY = 560, 290
KEYWORDS = [("더 빠른 판단", 1.3, 3.6), ("더 효율적인 실행", 3.7, 6.0), ("더 높은 업무 생산성", 6.1, 10.0)]
CROSS = [(0, 2), (1, 4), (2, 5), (3, 0), (4, 1), (5, 3)]

SFX = [(0.05, "pull", 0.5), (0.6, "swell", 0.5)] + [(0.5 + 0.12 * i, "node_soft", 0.3) for i in range(6)] + \
      [(1.3, "ui_tick", 0.45), (3.7, "ui_tick", 0.45), (6.1, "ui_tick", 0.5), (4.0, "air", 0.25)] + \
      [(6.5 + 0.35 * i * (1 - i * 0.06), "node_soft", 0.25) for i in range(9)]


def motion_blur(t):
    return 4 if t < 0.8 else 1


def node_pos(i, t):
    conv = prog(t, 7.8, 10.0, in_out_cubic)
    ang = math.radians(-90 + 60 * i + 6 * t)
    r = 1 - 0.45 * conv
    return CX + RX * r * math.cos(ang), CY + RY * r * math.sin(ang)


def draw_network(c, t, a=1.0, conv_extra=0.0):
    pull = prog(t, 0.0, 1.4, house)
    s = lerp(3.5, 1.0, pull) * (1 - conv_extra)
    c.save()
    c.translate(CX, CY)
    c.scale(s, s)
    c.translate(-CX, -CY)
    # orbits
    for k, (rx, ry, rot) in enumerate(((640, 340, -6), (360, 190, 10))):
        gfx.orbit(c, CX, CY, rx, ry, rot + t * (3 + k), "line", 1.4, 0.4 * a, 0.4, prog(t, 0.3, 1.6), start=t * 20)
    speed_phase = 0.35 * t + 0.09 * t * t     # pulses accelerate
    pos = [node_pos(i, t) for i in range(len(NODES))]
    cross_a = a * prog(t, 0.6, 1.4) * (1 - prog(t, 3.8, 5.2))
    for i, j in CROSS:
        c.drawLine(*pos[i], *pos[j], gfx.stroke("line", 1.2, 0.35 * cross_a))
    for i in range(len(NODES)):
        pe = prog(t, 0.4 + 0.12 * i, 1.0 + 0.12 * i)
        x, y = pos[i]
        nx, ny = pos[(i + 1) % len(NODES)]
        c.drawLine(x, y, nx, ny, gfx.stroke("line", 1.6, 0.55 * a * pe))
        gfx.glow_line(c, CX, CY, x, y, "line", 2.0, 0.7 * a * pe, 0.6)
        for k in range(2):
            u = (speed_phase + k * 0.5 + i * 0.17) % 1.0
            gfx.node(c, lerp(CX, x, u), lerp(CY, y, u), 5, "white", a * pe, glow=1.0)
        c.drawCircle(x, y, 44, gfx.fill("navy", a * pe))
        c.drawCircle(x, y, 44, gfx.stroke("sky", 2.5, a * pe))
        c.drawCircle(x, y, 9, gfx.fill("sky", a * pe))
        gfx.text(c, NODES[i], x, y + 80, 32, 600, "white", a * pe, "center")
    c.restore()


def render(c, t):
    navy_space(c, bloom=(CX, CY + 40), intensity=0.9)
    draw_network(c, t)
    gfx.diamond(c, CX, CY, 20, "axblue", 1.0, glow=1.0, edge="light")
    for word, a0, a1 in KEYWORDS:
        w = window(t, a0, a1, 0.5, 0.45)
        if w > 0:
            gfx.text_rise(c, word, CX, DESIGN_H - 150, w, 60, 600, "white", 1.0, "center")
