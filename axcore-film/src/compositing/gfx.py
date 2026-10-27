"""Skia drawing primitives shared by every scene (one graphic system).

All coordinates are design pixels (1920x1080). Colors are hex strings.
"""
import math
from functools import lru_cache

import numpy as np
import skia

from ..utils.config import FONTS, FONT_HAND, C

SAMPLING = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


# --- color / paint -----------------------------------------------------------
@lru_cache(maxsize=None)
def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def color(hexstr, a=1.0):
    r, g, b = _rgb(C.get(hexstr, hexstr))
    return skia.Color(r, g, b, int(max(0, min(1, a)) * 255))


def mix(h1, h2, p):
    a, b = _rgb(C.get(h1, h1)), _rgb(C.get(h2, h2))
    return "#%02X%02X%02X" % tuple(int(x + (y - x) * p) for x, y in zip(a, b))


def fill(col, a=1.0, blur=0.0, shader=None):
    p = skia.Paint(AntiAlias=True, Color=color(col, a))
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(a)
    return p


def stroke(col, w=2.0, a=1.0, blur=0.0, cap="round", dash=None):
    p = skia.Paint(AntiAlias=True, Color=color(col, a), Style=skia.Paint.kStroke_Style,
                   StrokeWidth=w)
    p.setStrokeCap(skia.Paint.kRound_Cap if cap == "round" else skia.Paint.kButt_Cap)
    p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if dash:
        p.setPathEffect(skia.DashPathEffect.Make(list(dash), 0))
    return p


# --- text --------------------------------------------------------------------
@lru_cache(maxsize=None)
def typeface(weight):
    return skia.Typeface.MakeFromFile(str(FONTS[weight]))


@lru_cache(maxsize=None)
def font(size, weight=500):
    f = skia.Font(typeface(weight), size)
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


@lru_cache(maxsize=None)
def hand_font(size):
    f = skia.Font(skia.Typeface.MakeFromFile(str(FONT_HAND)), size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def hand_text(c, s, x, y, size=40, col="white", a=1.0):
    if a > 0:
        c.drawString(s, x, y + size * 0.32, hand_font(size), fill(col, a))


def text_width(s, size, weight=500):
    return font(size, weight).measureText(s)


def text(c, s, x, y, size=28, weight=500, col="white", a=1.0, align="left",
         valign="middle", blur=0.0):
    """Draw a single line. letter-spacing is always 0 (Pretendard default)."""
    if a <= 0.003 or not s:
        return 0
    f = font(size, weight)
    w = f.measureText(s)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    if valign == "middle":
        y += size * 0.36
    elif valign == "top":
        y += size * 0.86
    c.drawString(s, x, y, f, fill(col, a, blur))
    return w


def text_rise(c, s, x, y, p, size=28, weight=500, col="white", a=1.0, align="left",
              rise=14, valign="middle"):
    """Line-level reveal used everywhere: fade + short rise (ref grammar)."""
    if p <= 0:
        return 0
    return text(c, s, x, y + (1 - p) * rise, size, weight, col, a * p, align, valign)


def text_wipe(c, s, x, y, p, size=28, weight=500, col="white", a=1.0, align="left"):
    """Left-to-right mask reveal of a line of text."""
    if p <= 0:
        return 0
    w = text_width(s, size, weight)
    x0 = x - (w / 2 if align == "center" else w if align == "right" else 0)
    c.save()
    c.clipRect(skia.Rect.MakeXYWH(x0 - 4, y - size, (w + 8) * p, size * 2))
    text(c, s, x0, y, size, weight, col, a, "left")
    c.restore()
    return w


# --- shapes ------------------------------------------------------------------
def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


def card(c, x, y, w, h, r=16, bg="surface", a=1.0, border="border", shadow=0.08,
         border_w=1.5):
    if a <= 0:
        return
    rr = rrect(x, y, w, h, r)
    if shadow > 0:
        c.drawRRect(rrect(x, y + h * 0.03 + 4, w, h, r), fill("#101828", shadow * a, blur=18))
    c.drawRRect(rr, fill(bg, a))
    if border:
        c.drawRRect(rr, stroke(border, border_w, a))


def chamfer_path(x, y, w, h, cut=22):
    """Octagonal card outline (45-degree cut corners, like the AXCORE wordmark)."""
    p = skia.Path()
    p.addPoly([skia.Point(x + cut, y), skia.Point(x + w - cut, y), skia.Point(x + w, y + cut),
               skia.Point(x + w, y + h - cut), skia.Point(x + w - cut, y + h), skia.Point(x + cut, y + h),
               skia.Point(x, y + h - cut), skia.Point(x, y + cut)], True)
    return p


def dark_card(c, x, y, w, h, a=1.0, border="sky", fill_col="card_dark", cut=22, bw=2.0, glow=0.0,
              fill_a=0.94):
    if a <= 0:
        return
    p = chamfer_path(x, y, w, h, cut)
    c.drawPath(p, fill(fill_col, fill_a * a))
    if glow > 0:
        c.drawPath(p, stroke(border, bw * 4, 0.25 * glow * a, blur=8))
    c.drawPath(p, stroke(border, bw, a))


def toggle(c, x, y, on=1.0, a=1.0, w=66, h=36):
    """Switch; (x, y) is the left-centre."""
    if a <= 0:
        return
    bg = mix("#1A2234", "sky", on)
    c.drawRRect(rrect(x, y - h / 2, w, h, h / 2), fill(bg, a))
    c.drawRRect(rrect(x, y - h / 2, w, h, h / 2), stroke(mix("edge_dark", "sky", on), 1.5, a))
    kx = x + h / 2 + (w - h) * on
    c.drawCircle(kx, y, h * 0.34, fill(mix("#3A4256", "navy_deep", on), a))


def pill(c, x, y, w, h, bg, a=1.0, border=None, bw=1.5):
    rr = rrect(x, y, w, h, h / 2)
    if bg:
        c.drawRRect(rr, fill(bg, a))
    if border:
        c.drawRRect(rr, stroke(border, bw, a))


def chip(c, cx, cy, label, size=22, weight=500, fg="ink", bg="surface", border="border",
         a=1.0, dot=None, pad=16, h=None, align="center"):
    """Pill label. Returns its rect (x, y, w, h)."""
    tw = text_width(label, size, weight)
    dw = (size * 0.9) if dot else 0
    w = tw + pad * 2 + dw
    h = h or size * 1.9
    x = cx - w / 2 if align == "center" else cx
    y = cy - h / 2
    pill(c, x, y, w, h, bg, a, border)
    if dot:
        c.drawCircle(x + pad + size * 0.25, cy, size * 0.22, fill(dot, a))
    text(c, label, x + pad + dw, cy, size, weight, fg, a)
    return x, y, w, h


def diamond_path(cx, cy, r, rot=0.0):
    """AXCORE diamond: a square rotated 45 deg. r = center-to-vertex distance."""
    p = skia.Path()
    for i in range(4):
        ang = math.radians(rot + 90 * i - 90)
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        (p.moveTo if i == 0 else p.lineTo)(x, y)
    p.close()
    return p


def diamond(c, cx, cy, r, col="axblue", a=1.0, glow=0.0, rot=0.0, edge=None, outline=False):
    """The brand anchor. Flat 2D: fill + optional soft bloom, never 3D/gem."""
    if a <= 0 or r <= 0.05:
        return
    p = diamond_path(cx, cy, r, rot)
    if glow > 0:
        c.drawPath(diamond_path(cx, cy, r * 1.6, rot), fill("line", 0.35 * glow * a, blur=r * 1.4 + 4))
        c.drawCircle(cx, cy, r * 5, fill("line", 0.10 * glow * a, blur=r * 4 + 10))
    if outline:
        c.drawPath(p, stroke(col, max(1.5, r * 0.12), a))
    else:
        c.drawPath(p, fill(col, a))
    if edge:
        c.drawPath(p, stroke(edge, max(1.0, r * 0.08), a * 0.8))


def polyline_path(pts, smooth=0.0):
    p = skia.Path()
    if not pts:
        return p
    p.moveTo(*pts[0])
    if smooth <= 0 or len(pts) < 3:
        for q in pts[1:]:
            p.lineTo(*q)
        return p
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        dx = (x1 - x0) * smooth
        p.cubicTo(x0 + dx, y0, x1 - dx, y1, x1, y1)
    return p


def ortho_path(x0, y0, x1, y1, r=24, horizontal_first=True):
    """Orthogonal connector with rounded elbow (structured, not spider-web)."""
    p = skia.Path()
    p.moveTo(x0, y0)
    if horizontal_first:
        mx = (x0 + x1) / 2
        p.lineTo(mx, y0)
        p.lineTo(mx, y1)
        p.lineTo(x1, y1)
    else:
        my = (y0 + y1) / 2
        p.lineTo(x0, my)
        p.lineTo(x1, my)
        p.lineTo(x1, y1)
    if r > 0:
        p2 = skia.Path()
        skia.CornerPathEffect.Make(r).filterPath(p2, p, skia.StrokeRec(skia.StrokeRec.kHairline_InitStyle), None)
        return p2
    return p


def trim(path, t0, t1):
    """Sub-path between fractions t0..t1 of total length (draw-on animation)."""
    if t1 <= t0:
        return None
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    if L <= 0:
        return None
    out = skia.Path()
    pm.getSegment(L * max(0, t0), L * min(1, t1), out, True)
    return out


def point_at(path, t):
    pm = skia.PathMeasure(path, False)
    L = pm.getLength()
    pos = pm.getPosTan(L * max(0.0, min(1.0, t)))
    if not pos:
        return 0.0, 0.0
    pt = pos[0]
    return pt.x(), pt.y()


def glow_path(c, path, col="line", w=2.0, a=1.0, glow=0.6, t0=0.0, t1=1.0, dash=None):
    if path is None or a <= 0:
        return
    sub = path if (t0 <= 0 and t1 >= 1) else trim(path, t0, t1)
    if sub is None:
        return
    if glow > 0:
        c.drawPath(sub, stroke(col, w * 3.5, a * 0.35 * glow, blur=w * 2.2 + 2, dash=dash))
    c.drawPath(sub, stroke(col, w, a, dash=dash))


def glow_line(c, x0, y0, x1, y1, col="line", w=2.0, a=1.0, glow=0.6, p=1.0):
    path = skia.Path()
    path.moveTo(x0, y0)
    path.lineTo(x0 + (x1 - x0) * p, y0 + (y1 - y0) * p)
    glow_path(c, path, col, w, a, glow)


def ellipse_path(cx, cy, rx, ry, rot=0.0, start=0.0):
    """Ellipse as path, starting at angle `start` (deg) so trims can sweep."""
    p = skia.Path()
    n = 96
    for i in range(n + 1):
        ang = math.radians(start + 360 * i / n)
        x, y = rx * math.cos(ang), ry * math.sin(ang)
        r = math.radians(rot)
        X, Y = cx + x * math.cos(r) - y * math.sin(r), cy + x * math.sin(r) + y * math.cos(r)
        (p.moveTo if i == 0 else p.lineTo)(X, Y)
    return p


def orbit(c, cx, cy, rx, ry, rot=0.0, col="line", w=1.6, a=1.0, glow=0.5, p=1.0, start=-90):
    glow_path(c, ellipse_path(cx, cy, rx, ry, rot, start), col, w, a, glow, 0, p)


def node(c, x, y, r=8, col="line", a=1.0, ring=0.0, filled=True, glow=0.3):
    if a <= 0:
        return
    if glow > 0:
        c.drawCircle(x, y, r * 2.2, fill(col, 0.3 * glow * a, blur=r * 1.5 + 2))
    if filled:
        c.drawCircle(x, y, r, fill(col, a))
    else:
        c.drawCircle(x, y, r, stroke(col, 2, a))
    if ring > 0:
        c.drawCircle(x, y, r + 10 + 26 * ring, stroke(col, 2, a * (1 - ring)))


def brackets(c, x, y, w, h, col="line", a=1.0, ln=22, sw=2.5, p=1.0, pad=10):
    """Scan/lock-on corner brackets. p animates them from outside to the box."""
    if a <= 0:
        return
    off = pad + (1 - p) * 40
    x0, y0, x1, y1 = x - off, y - off, x + w + off, y + h + off
    pt = stroke(col, sw, a, cap="butt")
    for (px, py, sx, sy) in [(x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)]:
        path = skia.Path()
        path.moveTo(px, py + sy * ln)
        path.lineTo(px, py)
        path.lineTo(px + sx * ln, py)
        c.drawPath(path, pt)


def ripple(c, x, y, p, r0=10, r1=70, col="line", a=1.0, w=2.0):
    if 0 < p < 1:
        c.drawCircle(x, y, r0 + (r1 - r0) * p, stroke(col, w, a * (1 - p) ** 1.5))


# --- images ------------------------------------------------------------------
def to_image(arr_bgra):
    return skia.Image.fromarray(np.ascontiguousarray(arr_bgra), colorType=skia.kBGRA_8888_ColorType)


def draw_image(c, img, x, y, w, h, a=1.0, src=None):
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(max(0.0, min(1.0, a)))
    dst = skia.Rect.MakeXYWH(x, y, w, h)
    if src is not None:
        c.drawImageRect(img, skia.Rect.MakeXYWH(*src), dst, SAMPLING, p)
    else:
        c.drawImageRect(img, dst, SAMPLING, p)


def quad_matrix(src_wh, quad):
    """Matrix mapping rect (0,0,w,h) onto a 4-point quad (tl, tr, br, bl)."""
    w, h = src_wh
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(0, 0), skia.Point(w, 0), skia.Point(w, h), skia.Point(0, h)],
                    [skia.Point(*q) for q in quad])
    return m


def homography_matrix(H):
    """3x3 numpy homography -> skia.Matrix."""
    H = np.asarray(H, dtype=np.float64)
    H = H / H[2, 2]
    return skia.Matrix.MakeAll(float(H[0, 0]), float(H[0, 1]), float(H[0, 2]),
                               float(H[1, 0]), float(H[1, 1]), float(H[1, 2]),
                               float(H[2, 0]), float(H[2, 1]), float(H[2, 2]))


def clip_quad(c, quad):
    path = skia.Path()
    path.moveTo(*quad[0])
    for q in quad[1:]:
        path.lineTo(*q)
    path.close()
    c.clipPath(path, skia.ClipOp.kIntersect, True)
