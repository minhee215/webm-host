"""Backgrounds shared by all dark / bright scenes (one spatial system)."""
import skia

from ..utils.config import DESIGN_W, DESIGN_H
from . import gfx


def navy_space(c, bloom=(DESIGN_W * 0.5, DESIGN_H * 0.62), bloom_r=900, intensity=1.0,
               lift=0.0):
    """Deep navy with a soft blue light bloom (never flat black)."""
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("navy_deep"))
    base = skia.GradientShader.MakeRadial(
        skia.Point(DESIGN_W / 2, DESIGN_H * 0.45), DESIGN_W * 0.75,
        [gfx.color(gfx.mix("navy", "navy_mid", lift)), gfx.color("navy_deep"), gfx.color("void")],
        [0.0, 0.62, 1.0])
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), skia.Paint(Shader=base))
    if intensity > 0:
        glow = skia.GradientShader.MakeRadial(
            skia.Point(*bloom), bloom_r,
            [gfx.color("axblue", 0.22 * intensity), gfx.color("axblue", 0.06 * intensity),
             gfx.color("axblue", 0.0)], [0.0, 0.45, 1.0])
        c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), skia.Paint(Shader=glow))


def white_space(c, tint=1.0):
    """Bright UI space: off-white with a faint cool gradient at the bottom (ref4)."""
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), gfx.fill("bg"))
    if tint > 0:
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(0, DESIGN_H * 0.55), skia.Point(0, DESIGN_H)],
            [gfx.color("tint", 0.0), gfx.color("tint", 0.9 * tint)])
        c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), skia.Paint(Shader=sh))


def orbit_field(c, t, defocus=10.0, a=1.0, drift=(0.0, 0.0)):
    """Defocused motion-graphic plate: the film's orbit language, out of focus,
    used behind UI panels (the MG counterpart of a blurred stock plate)."""
    import math
    navy_space(c, bloom=(DESIGN_W * 0.62 + drift[0], DESIGN_H * 0.55 + drift[1]), intensity=a)
    cx, cy = DESIGN_W * 0.5 + drift[0], DESIGN_H * 0.56 + drift[1]
    for k in range(5):
        rx = 420 + k * 230
        ry = 120 + k * 70
        rot = -12 + 6 * math.sin(t * 0.25 + k)
        path = gfx.ellipse_path(cx, cy, rx, ry, rot)
        c.drawPath(path, gfx.stroke("line", 3.0 + k, 0.55 * a, blur=defocus + k * 2))
    for k in range(9):
        ang = t * 0.35 + k * 0.7
        x = cx + (500 + 120 * (k % 3)) * math.cos(ang)
        y = cy + (150 + 40 * (k % 3)) * math.sin(ang)
        c.drawCircle(x, y, 10 + 6 * (k % 3), gfx.fill("light", 0.35 * a, blur=defocus + 6))


def vignette(c, a=0.35):
    sh = skia.GradientShader.MakeRadial(
        skia.Point(DESIGN_W / 2, DESIGN_H / 2), DESIGN_W * 0.72,
        [gfx.color("void", 0.0), gfx.color("void", 0.0), gfx.color("void", a)], [0.0, 0.6, 1.0])
    c.drawRect(skia.Rect.MakeWH(DESIGN_W, DESIGN_H), skia.Paint(Shader=sh))
