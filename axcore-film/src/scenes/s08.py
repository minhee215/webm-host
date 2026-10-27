"""SCENE 08 · 116–120s · Logo.

Network, lines and orbits converge calmly into the diamond (no flash); the
diamond travels to its true position in the logo and the wordmark is revealed
outward from it; then the tagline.
"""
from ..utils.config import DESIGN_W, DESIGN_H
from ..compositing import gfx
from ..compositing import ui_axpoint as ui
from ..compositing.background import navy_space
from ..motion.easing import prog, lerp, in_out_cubic, house, house_io, out_cubic
from . import s07

CX, CY = DESIGN_W / 2, DESIGN_H / 2
LOGO_H = 150
LOGO_W = LOGO_H * ui.logo_parts()["size"][0] / ui.logo_parts()["size"][1]
LOGO_X, LOGO_Y = CX - LOGO_W / 2, CY - LOGO_H / 2 - 50

SFX = [(0.05, "converge", 0.6), (1.3, "logo", 0.8), (2.6, "ui_tick", 0.3)]


def render(c, t):
    navy_space(c, bloom=(CX, CY), intensity=0.9)
    conv = prog(t, 0.0, 1.3, in_out_cubic)
    if conv < 1:
        s07.draw_network(c, 10.0 + t, a=1 - conv, conv_extra=conv * 0.95)
    dx, dy, dr = ui.logo_diamond_pos(LOGO_X, LOGO_Y, LOGO_H)
    mv = prog(t, 1.1, 1.9, house_io)
    x = lerp(CX, dx, mv)
    y = lerp(s07.CY, dy, mv)
    r = lerp(20, dr, mv)
    wipe = prog(t, 1.75, 2.75, house)
    if wipe > 0:
        ui.draw_logo(c, LOGO_X, LOGO_Y, LOGO_H, a=1.0, wipe=wipe, diamond=False)
    gfx.diamond(c, x, y, r, "axblue", 1.0, glow=1.0 - 0.7 * wipe, edge="light" if wipe < 1 else None)
    gfx.text_rise(c, "AI 전환의 가장 쉬운 시작.", CX, LOGO_Y + LOGO_H + 120, prog(t, 2.55, 3.25), 54, 500,
                  "white", 1.0, "center")
