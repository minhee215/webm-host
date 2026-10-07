"""AXCORE promo film - rendering engine (skia-python, CPU raster).

Shared building blocks used by every scene:
palette, easing and stop-motion entrances, seeded chaos, plates with a 2.5D
camera, frosted glass cards, typography, glowing connection lines, icons, the
AXCORE logo rig, scene transitions and the film finish.
"""
import math
import os
import zlib

import numpy as np
import skia

W, H, FPS = 1920, 1080, 24
HERE = os.path.dirname(os.path.abspath(__file__))
PLATE_DIR = os.environ.get("AXP_PLATES", os.path.join(HERE, "plates"))

# ------------------------------------------------------------------ palette
NAVY_950 = "#050B1C"
NAVY_900 = "#081229"
NAVY_800 = "#0C1A3A"
NAVY_700 = "#13264F"
NAVY = "#0A2C73"        # reference-style navy blocks
BLUE = "#0054FE"        # AXCORE logo blue (hero accent on light scenes)
INDIGO = "#4C57E6"
CYAN = "#3CD3FF"        # controlled AXCORE cyan highlight (hero accent on dark scenes)
CYAN_SOFT = "#9BE6FF"
STEEL = "#5E6064"       # AXCORE logo gray
STEEL_400 = "#8C939D"
STEEL_200 = "#C9CED5"
WARM_W = "#F5F4EF"
PAPER = "#FBFAF6"
WHITE = "#FFFFFF"
INK = "#1A2233"


def col(h, a=1.0):
    h = h.lstrip("#")
    return skia.Color4f(int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def colint(h, a=1.0):
    return col(h, a).toColor()


# ------------------------------------------------------------- seed / chaos
SEED = 20261007
CHAOS = 0.35


def configure(seed=None, chaos=None):
    global SEED, CHAOS
    if seed is not None:
        SEED = int(seed)
    if chaos is not None:
        CHAOS = float(chaos)


def rng(key):
    """Deterministic generator per (seed, key): same seed + chaos -> identical frame."""
    return np.random.default_rng([SEED, zlib.crc32(key.encode())])


def jit(key, n=1, scale=1.0):
    """Chaos-scaled jitter in [-scale, scale]. At chaos 0 everything is registered."""
    v = rng(key).uniform(-1, 1, n) * scale * CHAOS
    return v if n > 1 else float(v[0])


# ------------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def lerp(a, b, t):
    return a + (b - a) * t


def prog(t, t0, d):
    if d <= 0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / d)


def e_out_expo(x):
    x = clamp(x)
    return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)


def e_in_expo(x):
    x = clamp(x)
    return 0.0 if x <= 0 else 2 ** (10 * x - 10)


def e_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def e_in_cubic(x):
    x = clamp(x)
    return x ** 3


def e_io_cubic(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def e_io_sine(x):
    x = clamp(x)
    return -(math.cos(math.pi * x) - 1) / 2


def e_io_expo(x):
    x = clamp(x)
    if x <= 0 or x >= 1:
        return x
    return 2 ** (20 * x - 10) / 2 if x < 0.5 else (2 - 2 ** (-20 * x + 10)) / 2


def settle(x, over=0.045):
    """Ease-out expo with a small overshoot, then settle back to 1."""
    x = clamp(x)
    if x < 0.62:
        return (1 + over) * e_out_expo(x / 0.62)
    return 1 + over * (1 - e_io_sine((x - 0.62) / 0.38)) - over * 0.0


def enter(t, t0, d=0.6, step=True, over=0.045):
    """Entrance progress (0..1+overshoot).

    Stop-motion cadence is applied only at the moment of entrance: the first 40%
    of the entrance is sampled on 12 fps steps, after that it interpolates smoothly.
    """
    if t <= t0:
        return 0.0
    dt = t - t0
    if step and dt < 0.4 * d:
        dt = math.floor(dt * 12) / 12
    return settle(dt / d, over)


def leave(t, t1, d=0.4):
    """1 -> 0 exit fade starting at t1."""
    return 1 - e_in_cubic(prog(t, t1, d))


def vis(t, t0, d_in=0.6, t1=1e9, d_out=0.4, step=True):
    return clamp(enter(t, t0, d_in, step)) * leave(t, t1, d_out)


def drift(t, dur):
    """Never-still drift parameter: mostly linear (continues past the cut for
    transitions) with a gentle eased component inside the shot."""
    p = t / dur
    return 0.72 * p + 0.28 * e_io_sine(p)


# ------------------------------------------------------------------- fonts
FONT_DIR = os.path.join(HERE, "fonts")
_TF = {}
_FONTS = {}


def typeface(w="Medium"):
    if w not in _TF:
        _TF[w] = skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, "Inter-%s.otf" % w))
    return _TF[w]


def font(size, w="Medium"):
    k = (round(size * 4) / 4, w)
    if k not in _FONTS:
        f = skia.Font(typeface(w), k[0])
        f.setSubpixel(True)
        f.setEdging(skia.Font.Edging.kAntiAlias)
        f.setHinting(skia.FontHinting.kNone)
        _FONTS[k] = f
    return _FONTS[k]


def text_w(s, size, w="Medium", tracking=0.0):
    f = font(size, w)
    if not tracking:
        return f.measureText(s)
    return sum(f.measureText(ch) for ch in s) + tracking * size * max(0, len(s) - 1)


def text(c, s, x, y, size=20, w="Medium", color=WHITE, alpha=1.0, align="left", tracking=0.0):
    if alpha <= 0.003 or not s:
        return 0.0
    f = font(size, w)
    tw = text_w(s, size, w, tracking)
    if align == "center":
        x -= tw / 2
    elif align == "right":
        x -= tw
    p = skia.Paint(AntiAlias=True, Color4f=col(color, clamp(alpha)))
    if not tracking:
        c.drawString(s, x, y, f, p)
    else:
        for ch in s:
            c.drawString(ch, x, y, f, p)
            x += f.measureText(ch) + tracking * size
    return tw


# ------------------------------------------------------------------ shapes
def paint_fill(color, alpha=1.0, blur=0.0, blend=None):
    p = skia.Paint(AntiAlias=True, Color4f=col(color, clamp(alpha)))
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    return p


def paint_stroke(color, alpha=1.0, width=1.5, blur=0.0, cap=skia.Paint.kRound_Cap, blend=None):
    p = skia.Paint(AntiAlias=True, Color4f=col(color, clamp(alpha)), Style=skia.Paint.kStroke_Style,
                   StrokeWidth=width, StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend is not None:
        p.setBlendMode(blend)
    return p


def R(x, y, w, h):
    return skia.Rect.MakeXYWH(x, y, w, h)


def rrect(c, rect, r, color, alpha=1.0, blur=0.0):
    if alpha > 0.003:
        c.drawRRect(skia.RRect.MakeRectXY(rect, r, r), paint_fill(color, alpha, blur))


def rrect_stroke(c, rect, r, color, alpha=1.0, width=1.2, blur=0.0):
    if alpha > 0.003:
        c.drawRRect(skia.RRect.MakeRectXY(rect, r, r), paint_stroke(color, alpha, width, blur))


def square(c, x, y, s, color=NAVY, alpha=1.0):
    if alpha > 0.003:
        c.drawRect(R(x - s / 2, y - s / 2, s, s), paint_fill(color, alpha))


def glow_dot(c, x, y, r, color=CYAN, alpha=1.0, core=0.35):
    if alpha <= 0.003:
        return
    cc = col(color, 1.0)
    shader = skia.GradientShader.MakeRadial(
        skia.Point(x, y), r,
        [skia.Color4f(cc.fR, cc.fG, cc.fB, clamp(alpha)).toColor(),
         skia.Color4f(cc.fR, cc.fG, cc.fB, clamp(alpha) * 0.35).toColor(),
         skia.Color4f(cc.fR, cc.fG, cc.fB, 0).toColor()],
        [0.0, core, 1.0])
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Shader=shader, BlendMode=skia.BlendMode.kScreen))
    c.drawCircle(x, y, max(1.2, r * 0.12), paint_fill(WHITE, alpha * 0.9))


def corner_brackets(c, rect, ln=18, color=WHITE, alpha=1.0, width=2.0):
    if alpha <= 0.003:
        return
    p = paint_stroke(color, alpha, width, cap=skia.Paint.kSquare_Cap)
    l, t, r_, b = rect.left(), rect.top(), rect.right(), rect.bottom()
    ln = min(ln, rect.width() / 2.5, rect.height() / 2.5)
    for (x, y, dx, dy) in ((l, t, 1, 1), (r_, t, -1, 1), (l, b, 1, -1), (r_, b, -1, -1)):
        c.drawLine(x, y, x + dx * ln, y, p)
        c.drawLine(x, y, x, y + dy * ln, p)


def dot_grid(c, spacing=44, color=STEEL_400, alpha=0.35, radius=1.3, ox=0.0, oy=0.0, scale=1.0, cx=W / 2, cy=H / 2):
    if alpha <= 0.003:
        return
    sp = spacing * scale
    x0 = (cx + ox) % sp - sp
    y0 = (cy + oy) % sp - sp
    xs = np.arange(x0, W + sp, sp)
    ys = np.arange(y0, H + sp, sp)
    pts = [skia.Point(float(x), float(y)) for y in ys for x in xs]
    p = paint_stroke(color, alpha, radius * 2 * scale)
    c.drawPoints(skia.Canvas.kPoints_PointMode, pts, p)


def vgrad(c, rect, top, bot, a_top=1.0, a_bot=1.0, blend=None):
    sh = skia.GradientShader.MakeLinear(
        [skia.Point(rect.left(), rect.top()), skia.Point(rect.left(), rect.bottom())],
        [colint(top, a_top), colint(bot, a_bot)])
    p = skia.Paint(Shader=sh)
    if blend is not None:
        p.setBlendMode(blend)
    c.drawRect(rect, p)


def radial(c, x, y, r, color, alpha, blend=skia.BlendMode.kScreen):
    if alpha <= 0.003:
        return
    sh = skia.GradientShader.MakeRadial(skia.Point(x, y), r, [colint(color, alpha), colint(color, 0)])
    c.drawCircle(x, y, r, skia.Paint(AntiAlias=True, Shader=sh, BlendMode=blend))


# ------------------------------------------------------------------- paths
def poly(points, closed=False):
    p = skia.Path()
    p.moveTo(*points[0])
    for pt in points[1:]:
        p.lineTo(*pt)
    if closed:
        p.close()
    return p


def curve(p0, p1, bend=0.35, horizontal=True):
    """Smooth S-curve (connector) between two points."""
    p = skia.Path()
    p.moveTo(*p0)
    if horizontal:
        dx = (p1[0] - p0[0]) * bend * 2
        p.cubicTo(p0[0] + dx, p0[1], p1[0] - dx, p1[1], p1[0], p1[1])
    else:
        dy = (p1[1] - p0[1]) * bend * 2
        p.cubicTo(p0[0], p0[1] + dy, p1[0], p1[1] - dy, p1[0], p1[1])
    return p


def arc_path(p0, p1, lift=0.25):
    """Quadratic arc used for flying cards / dragged chips."""
    p = skia.Path()
    p.moveTo(*p0)
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    p.quadTo(mx - dy * lift, my + dx * lift, p1[0], p1[1])
    return p


def path_len(path):
    return skia.PathMeasure(path, False, 1).getLength()


def path_seg(path, a, b):
    pm = skia.PathMeasure(path, False, 1)
    L = pm.getLength()
    dst = skia.Path()
    a, b = clamp(a), clamp(b)
    if b > a:
        pm.getSegment(a * L, b * L, dst, True)
    return dst


def path_at(path, f):
    pm = skia.PathMeasure(path, False, 1)
    L = pm.getLength()
    pos, tan = pm.getPosTan(clamp(f) * L)
    return pos.x(), pos.y(), math.atan2(tan.y(), tan.x())


def line(c, path, color=CYAN, alpha=1.0, width=1.6, trim=(0.0, 1.0), glow=0.0, glow_w=6.0, dash=None):
    """Precise connection line: crisp core + optional localized glow."""
    if alpha <= 0.003 or trim[1] <= trim[0]:
        return
    seg = path if (trim[0] <= 0 and trim[1] >= 1) else path_seg(path, trim[0], trim[1])
    if glow > 0:
        c.drawPath(seg, paint_stroke(color, alpha * glow, width * 3.2, blur=glow_w, blend=skia.BlendMode.kScreen))
    p = paint_stroke(color, alpha, width)
    if dash:
        p.setPathEffect(skia.DashPathEffect.Make(dash, 0))
    c.drawPath(seg, p)


def pulse(c, path, f, color=CYAN, alpha=1.0, r=14, tail=0.12, width=2.2):
    """Light pulse travelling along a path with a fading tail."""
    if alpha <= 0.003 or f <= 0 or f >= 1.0:
        return
    steps = 6
    for i in range(steps):
        a0 = f - tail * (i + 1) / steps
        a1 = f - tail * i / steps
        line(c, path, color, alpha * (1 - i / steps) * 0.8, width, (a0, a1))
    x, y, _ = path_at(path, f)
    glow_dot(c, x, y, r, color, alpha)


def streak(c, p0, p1, head, length=0.35, width=3.0, color=CYAN, alpha=1.0):
    """Cinematic light streak (reference-style) running from p0 to p1; head in 0..1+length."""
    if alpha <= 0.003:
        return
    a, b = head - length, head
    if b <= 0 or a >= 1:
        return
    a, b = clamp(a), clamp(b)
    x0, y0 = lerp(p0[0], p1[0], a), lerp(p0[1], p1[1], a)
    x1, y1 = lerp(p0[0], p1[0], b), lerp(p0[1], p1[1], b)
    cc = col(color)
    sh = skia.GradientShader.MakeLinear(
        [skia.Point(x0, y0), skia.Point(x1, y1)],
        [skia.Color4f(cc.fR, cc.fG, cc.fB, 0).toColor(), skia.Color4f(cc.fR, cc.fG, cc.fB, alpha).toColor()])
    for wmul, blur, am in ((7.0, 14.0, 0.55), (2.6, 4.0, 0.9), (1.0, 0.0, 1.0)):
        p = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=width * wmul,
                       StrokeCap=skia.Paint.kRound_Cap, BlendMode=skia.BlendMode.kScreen)
        p.setAlphaf(am)
        if blur:
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        c.drawLine(x0, y0, x1, y1, p)
    sh2 = skia.GradientShader.MakeLinear(
        [skia.Point(x0, y0), skia.Point(x1, y1)], [colint(WHITE, 0), colint(WHITE, alpha)])
    c.drawLine(x0, y0, x1, y1, skia.Paint(AntiAlias=True, Shader=sh2, Style=skia.Paint.kStroke_Style,
                                          StrokeWidth=width * 0.45, StrokeCap=skia.Paint.kRound_Cap))
    if b < 1:
        glow_dot(c, x1, y1, width * 9, color, alpha * 0.9)


# ------------------------------------------------------------------ plates
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)
_PLATES = {}


def _to_skimage(arr):
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    arr = np.ascontiguousarray(arr)
    return skia.Image.fromarray(arr, colorType=skia.ColorType.kRGBA_8888_ColorType).withDefaultMipmaps()


def plate(name, blurred=False):
    key = (name, blurred)
    if key not in _PLATES:
        from PIL import Image, ImageFilter
        path = os.path.join(PLATE_DIR, name + ".jpg")
        if os.path.exists(path):
            im = Image.open(path).convert("RGB")
        else:  # placeholder so the engine can run without plates (layout tests)
            im = placeholder_plate(name)
        if blurred:
            im = im.resize((im.width // 4, im.height // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
        _PLATES[key] = _to_skimage(np.asarray(im))
    return _PLATES[key]


def placeholder_plate(name):
    from PIL import Image, ImageDraw
    r = rng("ph" + name)
    a = np.zeros((1296, 2304, 3), np.uint8)
    top = r.integers(20, 200, 3)
    bot = r.integers(20, 200, 3)
    g = np.linspace(0, 1, 1296)[:, None, None]
    a[:] = (top * (1 - g) + bot * g).astype(np.uint8)
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    for i in range(0, 2304, 230):
        d.line([(i, 0), (i, 1296)], fill=(255, 255, 255), width=2)
    for j in range(0, 1296, 130):
        d.line([(0, j), (2304, j)], fill=(255, 255, 255), width=2)
    d.text((40, 40), name, fill=(255, 255, 0))
    return im


class Cam:
    """2.5D camera for a plate: scale s (1 = cover fit), screen offset (ox, oy), roll in degrees.
    map(u, v) converts plate-normalized coordinates to screen pixels so overlays stay tracked."""

    def __init__(self, img, s=1.0, ox=0.0, oy=0.0, rot=0.0):
        self.iw, self.ih = img.width(), img.height()
        self.k = max(W / self.iw, H / self.ih) * s
        m = skia.Matrix()
        m.setTranslate(W / 2 + ox, H / 2 + oy)
        m.preRotate(rot)
        m.preScale(self.k, self.k)
        m.preTranslate(-self.iw / 2, -self.ih / 2)
        self.m = m
        self.s = s

    def map(self, u, v):
        p = self.m.mapXY(u * self.iw, v * self.ih)
        return p.x(), p.y()

    def rect(self, u0, v0, u1, v1):
        x0, y0 = self.map(u0, v0)
        x1, y1 = self.map(u1, v1)
        return skia.Rect.MakeLTRB(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def grade_filter(bright=1.0, contrast=1.0, sat=1.0, tint=(0.0, 0.0, 0.0)):
    """Colour matrix: saturation, contrast around mid grey, brightness, additive tint (0..1)."""
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    s = sat
    m = np.array([
        [lr * (1 - s) + s, lg * (1 - s), lb * (1 - s)],
        [lr * (1 - s), lg * (1 - s) + s, lb * (1 - s)],
        [lr * (1 - s), lg * (1 - s), lb * (1 - s) + s]]) * contrast * bright
    off = (0.5 - 0.5 * contrast) * bright
    rows = []
    for i in range(3):
        rows += list(m[i]) + [0.0, off + tint[i]]
    rows += [0, 0, 0, 1, 0]
    return skia.ColorFilters.Matrix([float(v) for v in rows])


def draw_plate(c, name, t, dur, s=(1.04, 1.10), x=(0, 0), y=(0, 0), r=(0, 0), alpha=1.0,
               defocus=0.0, grade=None, beats=()):
    """Draw a plate with a continuous camera drift; returns the Cam for tracked overlays.
    beats: [(time, extra_scale)] decisive push-ins landing on the hero."""
    img = plate(name)
    p = drift(t, dur)
    sc = lerp(s[0], s[1], p)
    for bt, amt in beats:
        sc += amt * e_out_expo(prog(t, bt, 0.9))
    cam = Cam(img, sc, lerp(x[0], x[1], p), lerp(y[0], y[1], p), lerp(r[0], r[1], p))
    if alpha <= 0.003:
        return cam
    paint = skia.Paint(AntiAlias=True)
    paint.setAlphaf(clamp(alpha))
    if grade is not None:
        paint.setColorFilter(grade)
    c.save()
    c.concat(cam.m)
    c.drawImage(img, 0, 0, SAMP, paint)
    if defocus > 0.01:
        bimg = plate(name, True)
        pb = skia.Paint(AntiAlias=True)
        pb.setAlphaf(clamp(alpha * defocus))
        if grade is not None:
            pb.setColorFilter(grade)
        c.drawImageRect(bimg, skia.Rect.MakeWH(cam.iw, cam.ih), SAMP, pb)
    c.restore()
    return cam


def draw_image_cover(c, name, rect, alpha=1.0, zoom=1.0, focus=(0.5, 0.5), radius=0.0, grade=None):
    """Plate cropped into a rect (photo tiles / thumbnails)."""
    if alpha <= 0.003 or rect.width() < 1 or rect.height() < 1:
        return
    img = plate(name)
    iw, ih = img.width(), img.height()
    k = max(rect.width() / iw, rect.height() / ih) * zoom
    sw, sh = rect.width() / k, rect.height() / k
    sx = clamp(focus[0] * iw - sw / 2, 0, iw - sw)
    sy = clamp(focus[1] * ih - sh / 2, 0, ih - sh)
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if grade is not None:
        p.setColorFilter(grade)
    c.save()
    if radius > 0:
        c.clipRRect(skia.RRect.MakeRectXY(rect, radius, radius), skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, skia.Rect.MakeXYWH(sx, sy, sw, sh), rect, SAMP, p)
    c.restore()


# ------------------------------------------------------------- glass cards
def glass(c, rect, radius=18, alpha=1.0, tint=WHITE, tint_a=0.14, blur=22, border=0.55,
          shadow=0.22, glow=0.0, glow_col=CYAN, solid=0.0, solid_col=None, highlight=0.18):
    """Frosted translucent card (glassmorphism): backdrop blur, tint, specular top edge,
    hairline border, soft contact shadow, optional localized edge glow.
    solid 0..1 morphs the card into an opaque UI surface."""
    if alpha <= 0.003 or rect.width() < 2 or rect.height() < 2:
        return
    rr = skia.RRect.MakeRectXY(rect, radius, radius)
    if shadow > 0:
        sr = skia.RRect.MakeRectXY(rect.makeOffset(0, 14), radius, radius)
        c.drawRRect(sr, paint_fill(NAVY_950, shadow * alpha, blur=26))
    c.save()
    c.clipRRect(rr, skia.ClipOp.kIntersect, True)
    lp = skia.Paint()
    lp.setAlphaf(clamp(alpha))
    bf = skia.ImageFilters.Blur(blur, blur, skia.TileMode.kClamp)
    rec = skia.Canvas.SaveLayerRec(rect, lp, bf, 0)
    c.saveLayer(rec)
    fill_a = lerp(tint_a, 1.0, clamp(solid))
    c.drawRect(rect, paint_fill(tint if solid_col is None or solid <= 0 else solid_col, fill_a))
    if highlight > 0:
        vgrad(c, skia.Rect.MakeLTRB(rect.left(), rect.top(), rect.right(), rect.top() + min(90, rect.height())),
              WHITE, WHITE, highlight, 0.0)
    c.restore()
    c.restore()
    if border > 0:
        sh = skia.GradientShader.MakeLinear(
            [skia.Point(rect.left(), rect.top()), skia.Point(rect.right(), rect.bottom())],
            [colint(WHITE, border * alpha), colint(WHITE, border * alpha * 0.25), colint(WHITE, border * alpha * 0.6)],
            [0.0, 0.6, 1.0])
        bp = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=1.2)
        c.drawRRect(rr, bp)
    if glow > 0:
        c.drawRRect(rr, paint_stroke(glow_col, glow * alpha * 0.85, 5, blur=9, blend=skia.BlendMode.kScreen))
        c.drawRRect(rr, paint_stroke(glow_col, glow * alpha, 1.6))


def layer_alpha(c, alpha, bounds=None):
    """Begin a group fade (pair with c.restore())."""
    p = skia.Paint()
    p.setAlphaf(clamp(alpha))
    c.saveLayer(bounds, p)


# -------------------------------------------------------------------- icons
def icon(c, kind, cx, cy, s=22, color=WHITE, alpha=1.0, width=None):
    """Minimal line icons drawn on a s x s grid."""
    if alpha <= 0.003:
        return
    w = width or max(1.4, s * 0.085)
    p = paint_stroke(color, alpha, w)
    pf = paint_fill(color, alpha)
    h = s / 2
    L, T, Rr, B = cx - h, cy - h, cx + h, cy + h
    if kind == "doc":
        pa = poly([(L + s * .2, T), (L + s * .62, T), (Rr - s * .15, T + s * .25), (Rr - s * .15, B), (L + s * .2, B)], True)
        c.drawPath(pa, p)
        for k in (.45, .62, .79):
            c.drawLine(L + s * .35, T + s * k, Rr - s * .3, T + s * k, p)
    elif kind == "search":
        c.drawCircle(cx - s * .08, cy - s * .08, s * .3, p)
        c.drawLine(cx + s * .14, cy + s * .14, Rr - s * .05, B - s * .05, p)
    elif kind == "chart":
        c.drawPath(poly([(L + s * .05, B - s * .2), (L + s * .35, cy), (L + s * .58, cy + s * .15), (Rr - s * .05, T + s * .15)]), p)
        c.drawLine(L, B, Rr, B, p)
    elif kind == "bars":
        for i, hh in enumerate((.35, .6, .85)):
            x = L + s * (.18 + i * .3)
            c.drawRect(skia.Rect.MakeLTRB(x - s * .08, B - s * hh, x + s * .08, B), pf)
    elif kind == "scan":
        corner_brackets(c, skia.Rect.MakeLTRB(L, T, Rr, B), s * .28, color, alpha, w)
        c.drawLine(L + s * .15, cy, Rr - s * .15, cy, p)
    elif kind == "flow":
        c.drawRect(R(L, T, s * .34, s * .3), p)
        c.drawRect(R(Rr - s * .34, B - s * .3, s * .34, s * .3), p)
        c.drawPath(poly([(L + s * .17, T + s * .3), (L + s * .17, cy + s * .15), (Rr - s * .34, cy + s * .15)]), p)
    elif kind == "report":
        c.drawRect(skia.Rect.MakeLTRB(L + s * .12, T, Rr - s * .12, B), p)
        c.drawRect(skia.Rect.MakeLTRB(L + s * .3, cy, L + s * .42, B - s * .15), pf)
        c.drawRect(skia.Rect.MakeLTRB(L + s * .55, cy - s * .2, L + s * .67, B - s * .15), pf)
    elif kind == "chat":
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(L, T + s * .1, Rr, B - s * .2), s * .18, s * .18), p)
        c.drawPath(poly([(L + s * .25, B - s * .2), (L + s * .2, B), (L + s * .45, B - s * .2)]), p)
    elif kind == "robot":
        c.drawPath(poly([(L + s * .1, B), (L + s * .3, cy + s * .05), (cx + s * .05, T + s * .25), (Rr - s * .1, T + s * .1)]), p)
        c.drawCircle(L + s * .3, cy + s * .05, s * .08, pf)
        c.drawCircle(cx + s * .05, T + s * .25, s * .08, pf)
        c.drawLine(L, B, L + s * .3, B, p)
    elif kind == "mail":
        c.drawRect(skia.Rect.MakeLTRB(L, T + s * .18, Rr, B - s * .18), p)
        c.drawPath(poly([(L, T + s * .18), (cx, cy + s * .05), (Rr, T + s * .18)]), p)
    elif kind == "hash":
        for k in (.38, .62):
            c.drawLine(L + s * k + s * .05, T + s * .1, L + s * k - s * .05, B - s * .1, p)
            c.drawLine(L + s * .12, T + s * k, Rr - s * .12, T + s * k, p)
    elif kind == "note":
        c.drawRect(skia.Rect.MakeLTRB(L + s * .1, T, Rr - s * .1, B), p)
        c.drawPath(poly([(L + s * .32, B - s * .25), (L + s * .32, T + s * .25), (Rr - s * .32, B - s * .25), (Rr - s * .32, T + s * .25)]), p)
    elif kind == "calendar":
        c.drawRect(skia.Rect.MakeLTRB(L, T + s * .12, Rr, B), p)
        c.drawLine(L, T + s * .38, Rr, T + s * .38, p)
        c.drawLine(L + s * .28, T, L + s * .28, T + s * .22, p)
        c.drawLine(Rr - s * .28, T, Rr - s * .28, T + s * .22, p)
    elif kind == "drive":
        c.drawPath(poly([(cx, T + s * .08), (Rr, B - s * .15), (L, B - s * .15)], True), p)
    elif kind == "db":
        c.drawOval(skia.Rect.MakeLTRB(L + s * .1, T, Rr - s * .1, T + s * .3), p)
        c.drawLine(L + s * .1, T + s * .15, L + s * .1, B - s * .15, p)
        c.drawLine(Rr - s * .1, T + s * .15, Rr - s * .1, B - s * .15, p)
        c.drawArc(skia.Rect.MakeLTRB(L + s * .1, B - s * .3, Rr - s * .1, B), 0, 180, False, p)
        c.drawArc(skia.Rect.MakeLTRB(L + s * .1, cy - s * .15, Rr - s * .1, cy + s * .15), 0, 180, False, p)
    elif kind == "gear":
        c.drawCircle(cx, cy, s * .2, p)
        for k in range(8):
            a = k * math.pi / 4
            c.drawLine(cx + math.cos(a) * s * .3, cy + math.sin(a) * s * .3,
                       cx + math.cos(a) * s * .45, cy + math.sin(a) * s * .45, p)
    elif kind == "check":
        c.drawPath(poly([(L + s * .15, cy), (L + s * .42, B - s * .22), (Rr - s * .12, T + s * .22)]), p)
    elif kind == "plus":
        c.drawLine(cx, T + s * .2, cx, B - s * .2, p)
        c.drawLine(L + s * .2, cy, Rr - s * .2, cy, p)
    elif kind == "minus":
        c.drawLine(L + s * .2, cy, Rr - s * .2, cy, p)
    elif kind == "alert":
        c.drawPath(poly([(cx, T + s * .05), (Rr, B - s * .05), (L, B - s * .05)], True), p)
        c.drawLine(cx, cy - s * .12, cx, cy + s * .12, p)
        c.drawCircle(cx, B - s * .2, w * .7, pf)
    elif kind == "box":
        c.drawPath(poly([(cx, T), (Rr, T + s * .25), (Rr, B - s * .25), (cx, B), (L, B - s * .25), (L, T + s * .25)], True), p)
        c.drawPath(poly([(L, T + s * .25), (cx, T + s * .5), (Rr, T + s * .25)]), p)
        c.drawLine(cx, T + s * .5, cx, B, p)
    elif kind == "user":
        c.drawCircle(cx, T + s * .3, s * .2, p)
        c.drawArc(skia.Rect.MakeLTRB(L + s * .1, cy + s * .05, Rr - s * .1, B + s * .45), 180, 180, False, p)
    elif kind == "cube":
        icon(c, "box", cx, cy, s, color, alpha, width)
    elif kind == "factory":
        c.drawPath(poly([(L, B), (L, cy), (L + s * .3, cy - s * .2), (L + s * .3, cy), (L + s * .6, cy - s * .2),
                         (L + s * .6, cy), (Rr, cy - s * .2), (Rr, B)], True), p)
        c.drawLine(Rr - s * .15, cy - s * .15, Rr - s * .15, T, p)
    elif kind == "spark":
        c.drawPath(poly([(cx, T), (cx + s * .12, cy - s * .12), (Rr, cy), (cx + s * .12, cy + s * .12), (cx, B),
                         (cx - s * .12, cy + s * .12), (L, cy), (cx - s * .12, cy - s * .12)], True), pf)
    elif kind == "link":
        c.drawRRect(skia.RRect.MakeRectXY(R(L, cy - s * .16, s * .55, s * .32), s * .16, s * .16), p)
        c.drawRRect(skia.RRect.MakeRectXY(R(Rr - s * .55, cy - s * .16, s * .55, s * .32), s * .16, s * .16), p)
    else:
        c.drawCircle(cx, cy, s * .35, p)


# ------------------------------------------------------------------- logo
class Logo:
    """AXCORE logo rig built from the supplied artwork.
    Splits the mark into: gray glyphs, blue diamond, the three blue bars (the 'E').
    The hero (blue) parts can be animated separately and arrive last."""

    def __init__(self):
        from PIL import Image
        a = np.asarray(Image.open(os.path.join(HERE, "assets", "axcore_logo.png")).convert("RGBA")).copy()
        self.h, self.w = a.shape[:2]
        rgb = a[..., :3].astype(int)
        blue = (rgb[..., 2] > 180) & (rgb[..., 0] < 90) & (a[..., 3] > 0)
        gray = (a[..., 3] > 0) & ~blue
        ys, xs = np.where(blue)
        split = self.w * 0.5
        dia = blue & (np.arange(self.w)[None, :] < split)
        bars = blue & ~dia
        rows = np.where(bars.any(1))[0]
        groups, start = [], rows[0]
        for i in range(1, len(rows)):
            if rows[i] != rows[i - 1] + 1:
                groups.append((start, rows[i - 1]))
                start = rows[i]
        groups.append((start, rows[-1]))
        self.bar_rows = groups[:3]

        def masked(m, recolor=None):
            b = np.zeros_like(a)
            b[m] = a[m]
            if recolor is not None:
                rc = np.array([int(recolor[1:3], 16), int(recolor[3:5], 16), int(recolor[5:7], 16)], np.uint8)
                b[m, :3] = rc
            return b

        self.gray = _to_skimage(masked(gray))
        self.gray_w = _to_skimage(masked(gray, "#E9EEF6"))
        self.dia = _to_skimage(masked(dia))
        self.dia_c = _to_skimage(masked(dia, "#3CC8FF"))
        self.bars = []
        for (r0, r1) in self.bar_rows:
            m = bars.copy()
            m[:r0] = False
            m[r1 + 1:] = False
            self.bars.append(_to_skimage(masked(m)))
        dys, dxs = np.where(dia)
        self.dia_c_xy = (dxs.mean(), dys.mean())
        bxs = np.where(bars.any(0))[0]
        self.bar_x = (bxs.min(), bxs.max())
        self.kor_bottom = groups[0][0] - 4  # Korean caption sits above the first bar

    def draw(self, c, cx, cy, width, reveal=1.0, dia=1.0, bars=(1.0, 1.0, 1.0), on_dark=False, alpha=1.0,
             glint=-1.0):
        """reveal: gray glyph wipe 0..1; dia: diamond pop; bars: per-bar slide-in."""
        if alpha <= 0.003:
            return
        k = width / self.w
        c.save()
        c.translate(cx - width / 2, cy - self.h * k / 2)
        c.scale(k, k)
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(clamp(alpha))
        if reveal > 0:
            c.save()
            soft = 60
            edge = lerp(-soft, self.w * 0.86 + soft, clamp(reveal))
            c.clipRect(skia.Rect.MakeLTRB(-10, -10, edge, self.h + 10), True)
            c.drawImage(self.gray_w if on_dark else self.gray, 0, 0, SAMP, p)
            c.restore()
            if reveal < 1 and reveal > 0:
                pass
        if dia > 0:
            dx, dy = self.dia_c_xy
            c.save()
            c.translate(dx, dy)
            sc = clamp(dia, 0, 1.3)
            c.scale(sc, sc)
            c.rotate((1 - clamp(dia)) * 90)
            c.translate(-dx, -dy)
            c.drawImage(self.dia_c if on_dark else self.dia, 0, 0, SAMP, p)
            c.restore()
        for i, b in enumerate(bars):
            if b <= 0:
                continue
            off = (1 - clamp(b)) * 160
            pb = skia.Paint(AntiAlias=True)
            pb.setAlphaf(clamp(alpha * clamp(b * 1.6)))
            c.save()
            c.translate(off, 0)
            c.drawImage(self.bars[i], 0, 0, SAMP, pb)
            c.restore()
        if 0 <= glint <= 1:
            gx = lerp(-200, self.w + 200, glint)
            sh = skia.GradientShader.MakeLinear([skia.Point(gx - 120, 0), skia.Point(gx + 120, self.h)],
                                                [colint(WHITE, 0), colint(WHITE, 0.75), colint(WHITE, 0)])
            gp = skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcATop)
            c.saveLayer(skia.Rect.MakeWH(self.w, self.h), None)
            c.drawImage(self.gray_w if on_dark else self.gray, 0, 0, SAMP, p)
            c.drawRect(skia.Rect.MakeWH(self.w, self.h), gp)
            c.restore()
        c.restore()


_LOGO = None


def logo():
    global _LOGO
    if _LOGO is None:
        _LOGO = Logo()
    return _LOGO


# -------------------------------------------------------------- transitions
def _img_paint(alpha=1.0):
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    return p


def draw_scaled(c, img, scale, fx=W / 2, fy=H / 2, alpha=1.0, dx=0.0, dy=0.0):
    c.save()
    c.translate(fx + dx, fy + dy)
    c.scale(scale, scale)
    c.translate(-fx, -fy)
    c.drawImage(img, 0, 0, SAMP, _img_paint(alpha))
    c.restore()


def light_leak(c, p, color="#FFC9A0", x=0.78, y=0.25, amount=0.32):
    a = math.sin(math.pi * clamp(p)) * amount
    if a > 0.003:
        radial(c, W * x, H * y, W * 0.75, color, a)
        radial(c, W * (1 - x) * 0.6, H * (1 - y), W * 0.5, "#7FD8FF", a * 0.45)


def tr_dissolve(c, A, B, p, leak=False, **kw):
    c.drawImage(A, 0, 0)
    c.drawImage(B, 0, 0, SAMP, _img_paint(e_io_sine(p)))
    if leak:
        light_leak(c, p)


def tr_zoom(c, A, B, p, focus=(W / 2, H / 2), leak=True, **kw):
    """Zoom-through: the outgoing shot pushes into a focus point, the next settles in."""
    fx, fy = focus
    q = e_io_cubic(p)
    draw_scaled(c, A, 1 + 0.9 * e_in_expo(p) * 0.6 + 0.08 * p, fx, fy, 1.0)
    # velocity blur on the incoming plate: ghosted scales (directional, radial)
    sb = lerp(1.18, 1.0, e_out_expo(p))
    for i, (ds, aa) in enumerate(((0.0, 1.0), (0.03, 0.35), (0.06, 0.18))):
        draw_scaled(c, B, sb + ds * (1 - p), fx, fy, q * aa)
    if leak:
        light_leak(c, p, amount=0.22)


def tr_whip(c, A, B, p, direction=-1, **kw):
    """Horizontal whip pan with directional (velocity) blur only along the move."""
    q = e_io_expo(p)
    vel = math.sin(math.pi * p)
    off = direction * W * q
    for k, a in ((0, 1.0), (1, 0.35), (2, 0.2), (3, 0.12)):
        sh = -direction * k * 28 * vel
        c.drawImage(A, off + sh, 0, SAMP, _img_paint(a if k == 0 else a * vel))
        c.drawImage(B, off - direction * W + sh, 0, SAMP, _img_paint(a if k == 0 else a * vel))


def tr_streak(c, A, B, p, angle=-28.0, color=CYAN, reverse=False, **kw):
    """A cyan light bar sweeps across; the next shot is revealed behind it."""
    q = e_io_cubic(p)
    ang = math.radians(angle)
    nx, ny = math.cos(ang), math.sin(ang)          # bar direction
    px_, py_ = -ny, nx                              # sweep normal
    if reverse:
        px_, py_ = -px_, -py_
    span = abs(px_) * W + abs(py_) * H
    d = lerp(-span / 2 - 120, span / 2 + 120, q)
    cx, cy = W / 2 + px_ * d, H / 2 + py_ * d
    c.drawImage(A, 0, 0)
    big = 4000
    poly_pts = [(cx + nx * big, cy + ny * big), (cx - nx * big, cy - ny * big),
                (cx - nx * big - px_ * big, cy - ny * big - py_ * big),
                (cx + nx * big - px_ * big, cy + ny * big - py_ * big)]
    c.save()
    c.clipPath(poly(poly_pts, True), skia.ClipOp.kIntersect, True)
    draw_scaled(c, B, lerp(1.06, 1.0, q), alpha=1.0)
    c.restore()
    a = math.sin(math.pi * p)
    p0 = (cx + nx * 1400, cy + ny * 1400)
    p1 = (cx - nx * 1400, cy - ny * 1400)
    for wmul, blur, am in ((60, 40, 0.25), (14, 10, 0.6), (3, 2, 1.0)):
        c.drawLine(p0[0], p0[1], p1[0], p1[1],
                   paint_stroke(color, a * am, wmul, blur=blur, blend=skia.BlendMode.kScreen))
    c.drawLine(p0[0], p0[1], p1[0], p1[1], paint_stroke(WHITE, a * 0.9, 1.4))


def tr_blocks(c, A, B, p, color=NAVY, cols=12, key="blocks", **kw):
    """Reference-style navy mosaic: squares cover the outgoing shot, then clear off the next."""
    rows = math.ceil(H / (W / cols))
    s = W / cols
    order = rng(key).permutation(cols * rows)
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    n = len(order)
    if p < 0.5:
        c.drawImage(A, 0, 0)
        q = p / 0.5
    else:
        c.drawImage(B, 0, 0)
        q = (p - 0.5) / 0.5
    paint = paint_fill(color, 1.0)
    paint2 = paint_fill(BLUE, 1.0)
    for idx in range(n):
        i, j = idx % cols, idx // cols
        f = rank[idx] / n
        if p < 0.5:
            k = clamp((q - f * 0.65) / 0.35)
            k = math.floor(k * 6) / 6 if k < 1 else 1.0
        else:
            k = 1 - clamp((q - f * 0.65) / 0.35)
            k = math.floor(k * 6) / 6 if k > 0 else 0.0
        if k <= 0:
            continue
        ss = s * k
        x = i * s + (s - ss) / 2
        y = j * s + (s - ss) / 2
        c.drawRect(R(x, y, ss + 0.5, ss + 0.5), paint2 if (idx * 7 + 3) % 23 == 0 else paint)


def _lerp_rect(r0, r1, q):
    return skia.Rect.MakeLTRB(lerp(r0.left(), r1.left(), q), lerp(r0.top(), r1.top(), q),
                              lerp(r0.right(), r1.right(), q), lerp(r0.bottom(), r1.bottom(), q))


def _draw_cover_in(c, img, rect, radius, alpha=1.0):
    k = max(rect.width() / W, rect.height() / H)
    sw, sh = rect.width() / k, rect.height() / k
    src = skia.Rect.MakeXYWH((W - sw) / 2, (H - sh) / 2, sw, sh)
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(rect, radius, radius), skia.ClipOp.kIntersect, True)
    c.drawImageRect(img, src, rect, SAMP, _img_paint(alpha))
    c.restore()


def tr_shrink(c, A, B, p, rect=None, radius=10, **kw):
    """The whole outgoing frame shrinks into a tile of the incoming layout."""
    q = e_io_expo(p)
    c.drawImage(B, 0, 0, SAMP, _img_paint(clamp(p * 3)))
    r = _lerp_rect(skia.Rect.MakeWH(W, H), rect, q)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, 18), radius, radius), paint_fill(NAVY_950, 0.25 * q, blur=30))
    _draw_cover_in(c, A, r, radius * q)


def tr_expand(c, A, B, p, rect=None, radius=12, **kw):
    """A card of the outgoing layout expands to become the next shot."""
    q = e_io_expo(p)
    c.drawImage(A, 0, 0)
    r = _lerp_rect(rect, skia.Rect.MakeWH(W, H), q)
    c.drawRRect(skia.RRect.MakeRectXY(r.makeOffset(0, 18), radius, radius), paint_fill(NAVY_950, 0.3 * (1 - q), blur=30))
    _draw_cover_in(c, B, r, radius * (1 - q))


TRANSITIONS = {
    "dissolve": tr_dissolve, "zoom": tr_zoom, "whip": tr_whip, "streak": tr_streak,
    "blocks": tr_blocks, "shrink": tr_shrink, "expand": tr_expand,
}


# ------------------------------------------------------------- film finish
class Finish:
    """Film finish applied to every frame:
    - restrained radial chromatic aberration (edges only)
    - soft focusing vignette
    - fine grain gated to shadows/midtones so highlights and white UI stay clean."""

    def __init__(self, grain=0.035, vignette=0.22, ca=1.0013):
        self.grain_amt = grain
        self.ca = ca
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2
        self.vig = (1 - vignette * np.clip(r2 / 2, 0, 1) ** 1.35)[..., None].astype(np.float32)
        g = rng("grain").standard_normal((4, H // 2, W // 2)).astype(np.float32)
        self.grain = [np.repeat(np.repeat(x, 2, 0), 2, 1)[..., None] for x in g]
        self.cf_gb = skia.ColorFilters.Matrix([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0])
        self.cf_r = skia.ColorFilters.Matrix([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])

    def apply(self, surface, fidx, grain_scale=1.0):
        c = surface.getCanvas()
        if self.ca and self.ca != 1.0:
            img = surface.makeImageSnapshot()
            c.clear(skia.Color4f(0, 0, 0, 1))
            c.drawImage(img, 0, 0, SAMP, skia.Paint(ColorFilter=self.cf_gb))
            c.save()
            c.translate(W / 2, H / 2)
            c.scale(self.ca, self.ca)
            c.translate(-W / 2, -H / 2)
            c.drawImage(img, 0, 0, SAMP, skia.Paint(ColorFilter=self.cf_r, BlendMode=skia.BlendMode.kPlus))
            c.restore()
        a = surface.makeImageSnapshot().toarray()[..., :3].astype(np.float32)
        luma = (a[..., 0:1] * 0.2126 + a[..., 1:2] * 0.7152 + a[..., 2:3] * 0.0722) / 255.0
        gate = np.clip(1.15 - luma, 0, 1) ** 1.3
        # the vignette relaxes on bright (white UI / paper) frames so whites stay clean
        mean = float(a[::16, ::16].mean()) / 255.0
        k = 1.0 - 0.7 * clamp((mean - 0.55) / 0.3)
        a *= 1.0 - k * (1.0 - self.vig)
        a += self.grain[fidx % 4] * (self.grain_amt * grain_scale * 255) * gate
        return np.clip(a, 0, 255).astype(np.uint8)
