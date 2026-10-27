"""Helpers shared by scenes: plate-space conversion, environmental labels,
screen replacement, cursor. Keeps every scene on the same graphic grammar."""
import numpy as np
import skia

from ..utils.config import DESIGN_W, DESIGN_H, PLATE_W, PLATE_H
from ..compositing import gfx
from ..motion.easing import prog, out_cubic, clamp

SX, SY = DESIGN_W / PLATE_W, DESIGN_H / PLATE_H
D = np.diag([SX, SY, 1.0])
D_INV = np.linalg.inv(D)


def P(pt):
    """plate pixel -> design pixel"""
    return pt[0] * SX, pt[1] * SY


def H_design(H):
    return D @ np.asarray(H) @ D_INV


def warp(H, pts):
    pts = np.array(pts, np.float64).reshape(-1, 3 - 1)
    ones = np.ones((len(pts), 1))
    v = (np.asarray(H) @ np.hstack([pts, ones]).T).T
    return [(x / w, y / w) for x, y, w in v]


def affine_apply(M, pts):
    M = np.asarray(M)
    return [(M[0, 0] * x + M[0, 1] * y + M[0, 2], M[1, 0] * x + M[1, 1] * y + M[1, 2]) for x, y in pts]


# --- environmental UI on live plates ------------------------------------------
def env_label(c, anchor, label_pos, text, p, sub=None, a=1.0, size=26, style="glass"):
    """Anchor dot + leader line + label pill that lives in the plate's space.

    p: 0..1 appear progress (line draws first, then the pill rises in).
    """
    if p <= 0 or a <= 0:
        return
    ax, ay = anchor
    lx, ly = label_pos
    pl = prog(p, 0.0, 0.45, out_cubic)
    pp = prog(p, 0.3, 1.0)
    gfx.node(c, ax, ay, 5, "line", a * pl, glow=0.6)
    c.drawCircle(ax, ay, 11, gfx.stroke("white", 1.5, a * pl * 0.8))
    path = skia.Path()
    path.moveTo(ax, ay)
    path.lineTo(lx, ly)
    gfx.glow_path(c, path, "white", 1.5, a * 0.85, 0.0, 0, pl)
    if pp <= 0:
        return
    tw = gfx.text_width(text, size, 600)
    sw = gfx.text_width(sub, size * 0.72, 500) if sub else 0
    w = max(tw, sw) + 44 + 18
    h = size * (2.9 if sub else 1.85)
    x = lx - (0 if lx >= ax else w)
    y = ly - h / 2 + (1 - pp) * 12
    al = a * pp
    if style == "glass":
        c.drawRRect(gfx.rrect(x, y + 6, w, h, 14), gfx.fill("#101828", 0.18 * al, blur=14))
        c.drawRRect(gfx.rrect(x, y, w, h, 14), gfx.fill("white", 0.86 * al))
        c.drawRRect(gfx.rrect(x, y, w, h, 14), gfx.stroke("white", 1.5, al))
        fg, fg2 = "ink", "ink2"
    else:
        c.drawRRect(gfx.rrect(x, y, w, h, 14), gfx.fill("navy", 0.72 * al))
        c.drawRRect(gfx.rrect(x, y, w, h, 14), gfx.stroke("line", 1.5, al))
        fg, fg2 = "white", "ice"
    gfx.diamond(c, x + 24, y + (size * 0.95 if sub else h / 2), 6, "axblue", al)
    if sub:
        gfx.text(c, text, x + 40, y + size * 0.95, size, 600, fg, al)
        gfx.text(c, sub, x + 40, y + size * 2.05, size * 0.72, 500, fg2, al)
    else:
        gfx.text(c, text, x + 40, y + h / 2, size, 600, fg, al)


def screen(c, quad, w, h, draw_fn, a=1.0, glow=0.0):
    """Screen replacement: draw a w×h UI (local coords) into a tracked quad."""
    if a <= 0:
        return
    c.save()
    gfx.clip_quad(c, quad)
    c.concat(gfx.quad_matrix((w, h), quad))
    if a < 1:
        c.saveLayerAlpha(None, int(a * 255))
    draw_fn(c)
    if a < 1:
        c.restore()
    c.restore()
    if glow > 0:
        path = skia.Path()
        path.moveTo(*quad[0])
        for q in quad[1:]:
            path.lineTo(*q)
        path.close()
        c.drawPath(path, gfx.stroke("white", 10, 0.10 * glow * a, blur=16))


def cursor(c, x, y, click=0.0, a=1.0, r=11):
    """Diamond-as-cursor (Data Node -> Cursor role of the brand anchor)."""
    if a <= 0:
        return
    s = 1 - 0.18 * np.sin(np.pi * clamp(click))
    c.drawPath(gfx.diamond_path(x + 2, y + 4, r * s * 1.1), gfx.fill("#0E1525", 0.25 * a, blur=5))
    gfx.diamond(c, x, y, r * s, "axblue", a, edge="white")
    if 0 < click < 1:
        gfx.ripple(c, x, y, click, r, r + 46, "axblue", a, 2.5)


def full_rect():
    return skia.Rect.MakeWH(DESIGN_W, DESIGN_H)


def dim(c, a):
    if a > 0:
        c.drawRect(full_rect(), gfx.fill("navy_deep", a))
