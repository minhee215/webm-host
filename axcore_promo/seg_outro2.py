"""Outro v2 00:01:49:02-00:01:59:15 (253 frames, same length as seg_outro) - client notes on the collage outro:
more footage, packed and moving like the reference (Jongga "Kimchi Blast": a few big splits with cuts inside the
panels, every column pushing in from the frame's edge, dark gutters between them); an indigo
gothic "AX" in the centre instead of the logo; once all is in, the mosaic is drawn into the AX (it draws back into
the letters while they grow, the panels outside them clear to white from the edges in, the footage that shows through
the letters keeps playing), the AX turns solid, comes down to the mark's size and its strokes become the strokes of
the AXCORE mark ("/", "/", the diamond, the X - as in the film's first FIN); then CORE, the E and the caption.
  0.00  seg_sphere's last frame (plain white) clears onto the main shot
  0.85  the left column pushes in, 1.55 the right one (the AX comes up slowly); rows come in, cuts inside the
        panels; 3.20 / 3.55 / 4.10 / 4.40 the outer columns push in from the edges - the reference's last frame:
        main in the centre, two columns of three rows each side, the outermost columns whole
  5.30  drawn into the AX (to 6.70); 7.00 solid indigo; 7.30 down to the mark; 7.85 the strokes become the mark
  8.25  C O R E, the E, the caption; 9.20 a light runs over the logo; holds to the end (10.54)
Usage: python3 seg_outro2.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import seg_ai as AI
import seg_outro as O
from engine import W, H, R, lerp, prog, clamp, e_io_cubic, e_io_sine, e_out_cubic, paint_fill, colint

TL0 = O.TL0                                       # same frames as seg_outro (the client's cut moved it by +1)
NF = O.NF
BAR = O.BAR
INDIGO = "#3340C9"
GREY = "#5E5F64"
LBLUE = "#0053FC"
CX, CY = W / 2, H / 2

# ---------------------------------------------------------------- the mosaic, after the reference's last frame: the
# main shot in a full-height centre column; on each side two columns of three rows (rows staggered) and an outermost
# full-height column. Every column comes in the same way - it pushes in from the frame's edge and the others make
# room (dark gutters between the panels from the first push on); no camera move.
HH = O.Y1 - O.Y0
GUT = 3.5                                         # half the gutter between panels
COLS = ["L3", "L2", "L1", "A", "R1", "R2", "R3"]
STAGES = [(-1.0, (0, 0, 0, 1920, 0, 0, 0)),
          (0.85, (0, 0, 760, 1160, 0, 0, 0)),     # the left column pushes in
          (1.55, (0, 0, 640, 640, 640, 0, 0)),    # the right one: three columns round the main shot
          (3.20, (0, 360, 500, 560, 500, 0, 0)),  # the next ones, from the edges
          (3.55, (0, 330, 380, 520, 380, 310, 0)),
          (4.10, (230, 290, 290, 500, 300, 310, 0)),
          (4.40, (193, 262, 262, 486, 262, 262, 193))]
START = {"g_cubes": 2.6, "g_chart": 2.4, "g_map": 1.2}     # where in a clip a panel starts (past an empty opening)


def _colkeys(name):
    i = COLS.index(name)
    keys = []
    for t, ws in STAGES:
        k = (float(sum(ws[:i])), float(ws[i]))
        if not keys or keys[-1][1] != k:
            keys.append((t, k))
    return keys


def _panel(clip, col, rows, t0=0.0, side=None, cuts=()):
    return dict(clip=clip, cols=_colkeys(col), rows=rows, t0=t0, side=side, cuts=list(cuts))


def build_layout():
    P = {}
    P["A"] = _panel(O.MAIN, "A", [(-1, (0.0, 1.0))], t0=-1.0)
    P["L1a"] = _panel("o1_chip", "L1", [(-1, (0, 1)), (2.15, (0.35, 1)), (2.85, (0.35, 0.75))], 0.85, "L",
                      [(1.60, "o3_drones"), (3.70, "22_city")])
    P["L1t"] = _panel("o2_warehouse", "L1", [(-1, (0, 0)), (2.15, (0, 0.35))], 2.15, "T", [(4.70, "o10_chip2")])
    P["L1b"] = _panel("g_wave", "L1", [(-1, (1, 1)), (2.85, (0.75, 1))], 2.85, "B")
    P["R1a"] = _panel("17_robot", "R1", [(-1, (0, 1)), (2.40, (0.33, 1)), (3.10, (0.33, 0.57))], 1.55, "R",
                      [(2.60, "10_datacenter"), (4.25, "o9_weld")])
    P["R1t"] = _panel("o7_hologram", "R1", [(-1, (0, 0)), (2.40, (0, 0.33))], 2.40, "T", [(4.85, "q5_city")])
    P["R1b"] = _panel("g_chart", "R1", [(-1, (1, 1)), (3.10, (0.57, 1))], 3.10, "B")
    for j, (rw, clip, cut) in enumerate((((0, 0.55), "g_net", (4.95, "n3_evline")), ((0.55, 0.81), "o4_wafer", None),
                                         ((0.81, 1), "n6_server", (5.05, "g_floor")))):
        P["L2%d" % j] = _panel(clip, "L2", [(-1, rw)], 3.20, "L", [cut] if cut else [])
    for j, (rw, clip, cut) in enumerate((((0, 0.27), "g_map", None), ((0.27, 0.77), "18_factory", (5.00, "19_aerial")),
                                         ((0.77, 1), "o5_cobots", None))):
        P["R2%d" % j] = _panel(clip, "R2", [(-1, rw)], 3.55, "R", [cut] if cut else [])
    P["L3"] = _panel("o8_servers", "L3", [(-1, (0, 1))], 4.10, "L", [(5.10, "n2_warehouse")])
    P["R3"] = _panel("s03_robot", "R3", [(-1, (0, 1))], 4.40, "R")
    for p in P.values():
        p["sw"] = max(v[1] for _, v in p["cols"])
        p["sh"] = max(v[1] - v[0] for _, v in p["rows"]) * HH
    return P


PANELS = build_layout()


def keyed(keys, s):
    """The value as the sum of each key's move (fast in, slow drift - the reference's split move)."""
    cur = list(keys[0][1])
    prev = keys[0][1]
    for (t, v) in keys[1:]:
        q = O.snap(s - t)
        for i in range(len(cur)):
            cur[i] += (v[i] - prev[i]) * q
        prev = v
    return cur


def rect_at(p, s):
    x, w = keyed(p["cols"], s)
    f0, f1 = keyed(p["rows"], s)
    return x, O.Y0 + f0 * HH, w, (f1 - f0) * HH


def clip_frame(name, t0, s):
    """The panel's frame: it plays from its start (slowed when needed so it never runs out before the end)."""
    info = media.clip_info(name)
    off = START.get(name, 0.0)
    dur = info["dur"] - 0.1 - off
    life = O.ft(O.TL1) - max(0.0, t0)
    rate = min(1.0, dur / max(life, 0.1))
    ct = off + min(dur, max(0.0, (s - max(0.0, t0)) * rate) + (0.3 if rate >= 1 else 0.0))
    if name not in O._READERS:
        big = name == O.MAIN
        size = (1920, 1080) if (big and O.HD) else ((1280, 720) if (big or O.HD) else (960, 540))
        O._READERS[name] = O.Reader(name, size)
    return O._READERS[name].get(int(ct * 24))


def draw_panel(c, name, s):
    p = PANELS[name]
    x, y, w, h = rect_at(p, s)
    if w < 1 or h < 1:
        return
    clip, t0 = p["clip"], p["t0"]
    for (tc, cc) in p["cuts"]:
        if s >= tc:
            clip, t0 = cc, tc
    img = clip_frame(clip, t0, s)
    if img is None:
        return
    sw, sh = p["sw"], p["sh"]
    if name == "A":                                  # the main shot just covers its panel
        sw, sh = w, h
    k = max(sw / img.width(), sh / img.height()) * 1.04
    k *= 1.0 + 0.05 * prog(s, max(0.0, t0), 6.0)          # every panel keeps pushing in a little
    iw, ih = img.width() * k, img.height() * k
    side = p["side"]
    cx = x + w - sw / 2 if side == "L" else (x + sw / 2 if side == "R" else x + w / 2)
    cy = y + h - sh / 2 if side == "T" else (y + sh / 2 if side == "B" else y + h / 2)
    if name == "A":
        cx = x + w / 2 + clamp((0.5 - 0.44) * iw, -(iw - w) / 2, (iw - w) / 2)
    c.save()
    c.clipRect(R(x + GUT, y + GUT, w - 2 * GUT, h - 2 * GUT))
    pt = skia.Paint(AntiAlias=True)
    pt.setColorFilter(O.grade(clip))
    c.drawImageRect(img, R(cx - iw / 2, cy - ih / 2, iw, ih), skia.SamplingOptions(skia.FilterMode.kLinear), pt)
    c.restore()


# ---------------------------------------------------------------- the AX (gothic, in letter-height units)
AX_PIECES = [  # name, polygon, mark target
    ("AL_low", [(0.162, 0.55), (0.362, 0.55), (0.20, 1.0), (0.0, 1.0)], "s1"),
    ("AL_up", [(0.36, 0.0), (0.46, 0.0), (0.46, 0.2778), (0.362, 0.55), (0.162, 0.55)], "s2"),
    ("AR", [(0.46, 0.0), (0.56, 0.0), (0.92, 1.0), (0.72, 1.0), (0.46, 0.2778)], "dia"),
    ("AB", [(0.344, 0.60), (0.576, 0.60), (0.634, 0.76), (0.286, 0.76)], "dia"),
    ("XUL", [(1.02, 0.0), (1.23, 0.0), (1.495, 0.358), (1.39, 0.5)], "xul"),
    ("XUR", [(1.76, 0.0), (1.97, 0.0), (1.60, 0.5), (1.495, 0.358)], "xur"),
    ("XLL", [(1.39, 0.5), (1.495, 0.642), (1.23, 1.0), (1.02, 1.0)], "xll"),
    ("XLR", [(1.495, 0.642), (1.60, 0.5), (1.97, 1.0), (1.76, 1.0)], "xlr"),
    ("XC", [(1.495, 0.358), (1.60, 0.5), (1.495, 0.642), (1.39, 0.5)], "xc"),
]
AX_CX, AX_CY = 0.985, 0.5
# the mark's strokes in the client's SVG (viewBox units)
MARK = {"s1": [(30.44, 291.9), (54.56, 291.9), (135.85, 210.76), (123.75, 198.74)],
        "s2": [(228.37, 93.91), (147.15, 175.21), (159.17, 187.23), (252.53, 93.91)],
        "dia": [(278.38, 192.82), (260.13, 174.56), (241.76, 192.82), (260.13, 211.06)],
        "xul": [(333.99, 160.68), (280.99, 107.69), (268.93, 119.74), (322.0, 172.66)],
        "xur": [(464.89, 94.0), (440.78, 94.0), (374.1, 160.67), (386.2, 172.7)],
        "xll": [(243.08, 291.9), (267.06, 291.9), (334.01, 224.96), (321.98, 212.94)],
        "xlr": [(374.1, 224.96), (441.05, 291.9), (465.17, 291.9), (386.2, 212.94)],
        "xc": [(354.1, 191.8), (355.1, 192.8), (354.1, 193.8), (353.1, 192.8)]}

TXT0, TXT_D = 1.55, 0.90                          # the AX comes up slowly as the three columns settle
TXT_W = 104.0                                     # its letter height on the mosaic (px)
ABS0, ABS_D = 5.30, 1.40                          # drawn into the AX
ABS_Z = 0.70                                      # the mosaic draws back to this as the letters grow
BIG_H = 560.0
SOLID0 = 7.00
SHR0, SHR_D = 7.30, 0.62                          # the solid AX comes down to the mark's size and place
MARK_H = 104.0
MORPH0, MORPH_D = 7.85, 0.55
CORE0 = 8.25
GLINT = 9.20
LOGO_W = 640.0


def zoom(s):
    return 1.0


def absorb(s):
    return e_io_cubic(prog(s, ABS0, ABS_D))


def cam(s):
    return zoom(min(s, ABS0)) * math.exp(math.log(ABS_Z) * absorb(s))


def ax_xf(hpx, cx=CX, cy=CY):
    return lambda u, v: (cx + (u - AX_CX) * hpx, cy + (v - AX_CY) * hpx)


def mark_xf():
    k = LOGO_W / O.LOGO_VB[0]
    x0, y0 = CX - LOGO_W / 2, CY - O.LOGO_VB[1] * k / 2
    return lambda x, y: (x0 + x * k, y0 + y * k)


def poly(pts):
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    p.close()
    return p


def union(paths):
    out = paths[0]
    for p in paths[1:]:
        out = skia.Op(out, p, skia.PathOp.kUnion_PathOp)
    return out


def resample(pts, n=64):
    """Points spaced evenly round a polygon, clockwise on screen, starting from its top-left-most corner,
    so two polygons can be blended point by point."""
    a = np.array(pts, float)
    area = 0.5 * np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1])
    if area < 0:
        a = a[::-1]
    i0 = int(np.argmin(a[:, 0] + a[:, 1]))
    a = np.roll(a, -i0, 0)
    b = np.vstack([a, a[:1]])
    seg = np.hypot(*(b[1:] - b[:-1]).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    out = []
    for d in np.linspace(0, cum[-1], n, endpoint=False):
        j = min(int(np.searchsorted(cum, d, "right")) - 1, len(seg) - 1)
        f = (d - cum[j]) / max(seg[j], 1e-9)
        out.append(b[j] + (b[j + 1] - b[j]) * f)
    return np.array(out)


def mixc(c0, c1, q, a=1.0):
    x, y = skia.Color4f(colint(c0)), skia.Color4f(colint(c1))
    return skia.Color4f(lerp(x.fR, y.fR, q), lerp(x.fG, y.fG, q), lerp(x.fB, y.fB, q), a)


SQUARES = []                                      # the reference's small blue squares round the letters
_rr = np.random.default_rng(7)
for _j in range(12):
    _u = _rr.uniform(-0.55, 2.55)
    _v = _rr.uniform(-0.12, 1.12) if not (-0.05 < _u < 2.02) else (_rr.choice([-0.16, 1.16]) + _rr.uniform(-0.05, 0.05))
    SQUARES.append((_u, _v, _rr.uniform(9, 22), _rr.uniform(0, 0.5), LBLUE if _j % 3 else INDIGO))


def letters(s):
    """The AX's screen transform: on the mosaic it rides with the camera; drawn in, it grows to BIG_H; then it comes
    down to the mark's size and place."""
    a = absorb(s)
    h0 = TXT_W * zoom(min(s, ABS0))
    hpx = math.exp(lerp(math.log(h0), math.log(BIG_H), a))
    sq = e_io_cubic(prog(s, SHR0, SHR_D))
    mcx, mcy = mark_xf()(247.8, 192.9)
    return ax_xf(math.exp(lerp(math.log(hpx), math.log(MARK_H), sq)), lerp(CX, mcx, sq), lerp(CY, mcy, sq))


# ---------------------------------------------------------------- frame
def render(c, t):
    s = t - TL0 / 24.0
    xf = letters(s)
    pieces = [(nm, [xf(u, v) for (u, v) in pts], tgt) for (nm, pts, tgt) in AX_PIECES]
    ax = union([poly(p) for _, p, _ in pieces])
    bgw = e_io_sine(prog(s, ABS0, 0.35))          # the gutters / background go white as it is drawn in
    solid_done = s >= SOLID0 + 0.035 * len(pieces) + 0.26
    morph = prog(s, MORPH0, MORPH_D)
    c.drawRect(R(0, 0, W, H), skia.Paint(Color4f=mixc("#07090F", "#FFFFFF", bgw)))
    z = cam(s)
    if not solid_done:
        c.save()
        if s >= ABS0 + ABS_D:
            c.clipPath(ax, skia.ClipOp.kIntersect, True)
        c.translate(CX, CY)
        c.scale(z, z)
        c.translate(-CX, -CY)
        for name in PANELS:
            if name != "A":
                draw_panel(c, name, s)
        draw_panel(c, "A", s)
        c.restore()
        if s > ABS0:                              # outside the letters each panel clears to white, from the edges in
            c.save()
            c.clipPath(ax, skia.ClipOp.kDifference, True)
            dmax = math.hypot(CX, CY)
            for name, p in PANELS.items():
                x, y, w, h = rect_at(p, s)
                d = math.hypot(x + w / 2 - CX, y + h / 2 - CY) / dmax
                wa = e_io_sine(prog(s, ABS0 + 0.05 + 0.60 * (1 - clamp(d)), 0.42))
                if wa > 0:
                    r = R(CX + (x - CX) * z - 1, CY + (y - CY) * z - 1, w * z + 2, h * z + 2)
                    c.drawRect(r, paint_fill("#FFFFFF", wa))
            c.restore()
    # thin guide lines and the small squares (reference vocabulary) on the white
    deco = e_io_sine(prog(s, ABS0 + 0.9, 0.5)) * (1 - e_io_sine(prog(s, SHR0 - 0.1, 0.35)))
    if deco > 0:
        for (u, v, sz, d0, colr) in SQUARES:
            a = deco * e_out_cubic(prog(s, ABS0 + 0.95 + d0, 0.3))
            x, y = xf(u, v)
            k = sz * (0.6 + 0.4 * a)
            c.drawRect(R(x - k / 2, y - k / 2, k, k), paint_fill(colr, 0.9 * a))
        for v in (0.0, 1.0):
            _, y = xf(0, v)
            c.drawRect(R(0, y - 0.5, W, 1.0), paint_fill("#AFC3E6", 0.45 * deco))
        for u in (0.0, 1.97):
            x, _ = xf(u, 0)
            c.drawRect(R(x - 0.5, 0, 1.0, H), paint_fill("#AFC3E6", 0.45 * deco))
    # the letters
    txt_in = e_io_sine(prog(s, TXT0, TXT_D))
    fill_out = e_io_sine(prog(s, ABS0 + 0.45, 0.55))       # the indigo gives way to the footage behind it
    if morph <= 0:
        if txt_in > 0 and fill_out < 1:
            a = txt_in * (1 - fill_out)
            c.save()
            c.translate(0, 10 * (1 - txt_in))
            g = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.38 * a * (1 - bgw)))
            g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 18))
            c.drawPath(ax, g)                        # a soft light behind it so it reads on the shot
            c.drawPath(ax, skia.Paint(AntiAlias=True, Color4f=mixc(INDIGO, INDIGO, 0, a)))
            c.restore()
        for j, (nm, pts, tgt) in enumerate(pieces):          # solid indigo, one stroke after another
            sa = e_io_sine(prog(s, SOLID0 + 0.035 * j, 0.26))
            if sa > 0:
                c.drawPath(poly(pts), paint_fill(INDIGO, sa))
    mx = mark_xf()
    if morph > 0:                                    # the strokes become the mark
        for j, (nm, pts, tgt) in enumerate(pieces):
            mq = e_io_cubic(prog(s, MORPH0 + 0.025 * j, MORPH_D - 0.2))
            A = resample(pts)
            B = resample([mx(x, y) for x, y in MARK[tgt]])
            Pm = A * (1 - mq) + B * mq
            c1 = LBLUE if tgt in ("dia", "xc") else GREY
            a = 1.0 - (e_io_sine(prog(s, MORPH0 + 0.3, 0.3)) if tgt == "xc" else 0.0)
            c.drawPath(poly([tuple(p) for p in Pm]), skia.Paint(AntiAlias=True, Color4f=mixc(INDIGO, c1, mq, a)))
    if s >= CORE0 - 0.05:
        logo_rest(c, s)


ORDER = [("C", 0.00), ("O", 0.06), ("R", 0.12), ("bars", 0.20), ("kor", 0.36)]


def logo_rest(c, s):
    """C O R E, the E's bars and the caption (the client's SVG, own colours); the light over the logo."""
    if not O.LOGO:
        O.LOGO.update(O.load_logo())
    L = O.LOGO
    k = LOGO_W / O.LOGO_VB[0]
    c.save()
    c.translate(CX - LOGO_W / 2, CY - O.LOGO_VB[1] * k / 2)
    c.scale(k, k)
    full = R(0, 0, O.LOGO_VB[0], O.LOGO_VB[1])
    smp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
    for grp, d in ORDER:
        q = prog(s, CORE0 + d, 0.40)
        if q <= 0:
            continue
        img = L[grp + "@o"][0]
        a = e_io_sine(clamp(q * 1.5))
        c.save()
        c.translate((-140 if grp == "bars" else -60) * (1 - e_out_cubic(q)), 0)
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(a)
        if q < 1:
            p.setImageFilter(skia.ImageFilters.Blur(5 * (1 - q), 5 * (1 - q)))
        c.drawImageRect(img, full, smp, p)
        c.restore()
    if s >= MORPH0 + MORPH_D + 0.1:               # the mark itself as the artwork from here (no seams)
        for grp in ("s1", "s2", "X", "dia"):
            c.drawImageRect(L[grp + "@o"][0], full, smp, skia.Paint(AntiAlias=True))
    glint = prog(s, GLINT, 0.9)
    if 0 < glint < 1:
        gx = lerp(-200, O.LOGO_VB[0] + 200, e_io_sine(glint))
        sh = skia.GradientShader.MakeLinear([skia.Point(gx - 140, 0), skia.Point(gx + 140, O.LOGO_VB[1])],
                                            [colint("#9FD2FF", 0), colint("#CFE8FF", 0.85), colint("#9FD2FF", 0)])
        c.saveLayer(None, None)
        for grp in L:
            if not grp.endswith("@o"):
                c.drawImageRect(L[grp][0], full, smp, skia.Paint(AntiAlias=True))
        c.drawPaint(skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcIn))
        c.restore()
    c.restore()


def render_all(c, t):
    s = t - TL0 / 24.0
    render(c, t)
    m = e_io_sine(prog(s, 0.0, 0.55))
    if m < 1:                                     # in: seg_sphere's white clears onto the main shot
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", 1 - m))


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    HD = height > 1080
    O.HD = HD
    AI.HD = HD
    media.MAX_READERS = 4
    E.configure(E.SEED, E.CHAOS)
    SCV = max(1.0, height / H)
    SW, SH = int(round(W * SCV)), int(round(H * SCV))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    finish = E.Finish(size=(SW, SH))
    width = int(round(height * 16 / 9 / 2)) * 2
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (O.FPS_NUM, O.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    bar = int(round(BAR * SCV))
    for f in range(F0, F1):
        tl = TL0 + f
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        render_all(c, tl / 24.0)
        c.restore()
        fr = finish.apply(surf, tl - 48)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
