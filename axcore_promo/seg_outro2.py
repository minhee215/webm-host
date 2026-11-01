"""Outro v2 00:01:49:02-00:01:59:15 (253 frames, same length as seg_outro) - client notes on the collage outro:
more footage, packed like the reference (a dense mosaic on both sides of the main shot); instead of the AXCORE logo
on the main shot an indigo gothic "AX" sits in the centre; once every panel is in, the collage is drawn into the AX
(the letters grow, everything outside them clears to white, the letters hold the footage - each facet its own shot,
after the client's third reference), the AX turns solid and its strokes become the strokes of the AXCORE mark
("/", "/", the diamond, the X - as in the film's first FIN), then CORE, the E and the caption arrive.
  0.00  seg_sphere's last frame (plain white) clears onto the main shot; 0.50 the AX comes up
  0.80  the splits begin (a new panel about every 0.14 s, from both sides), all in by ~4.3
  4.40  the collage is drawn into the AX (letters grow, outside -> white)
  5.15  each facet of the letters takes its own shot; 5.82 they turn solid indigo
  6.02  the solid AX comes down to the mark's size; 6.48 its strokes morph into the mark;
  6.86  C O R E + caption (the narration says "AXCORE" at ~6.9)
  7.80  a light runs over the logo; holds to the end
Usage: python3 seg_outro2.py <out.mp4> [height=480] [first last]
"""
import math
import os
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

# ---------------------------------------------------------------- the mosaic (splits as before, many more)
OPS = [(0.80, "A", "L", 0.35, "o1_chip"), (0.96, "A", "R", 0.53, "17_robot"), (1.10, "B", "B", 0.45, "g_wave"),
       (1.24, "C", "T", 0.40, "o2_warehouse"), (1.38, "B", "L", 0.42, "o4_wafer"), (1.52, "C", "R", 0.40, "g_map"),
       (1.66, "D", "R", 0.48, "10_datacenter"), (1.80, "E", "L", 0.45, "o3_drones"), (1.94, "F", "B", 0.52, "g_cubes"),
       (2.08, "G", "T", 0.45, "18_factory"), (2.22, "D", "T", 0.45, "o5_cobots"), (2.36, "E", "B", 0.48, "g_chart"),
       (2.50, "H", "B", 0.50, "o6_amr"), (2.64, "I", "T", 0.50, "22_city"), (2.78, "B", "T", 0.40, "o7_hologram"),
       (2.92, "C", "L", 0.42, "s03_robot"), (3.06, "J", "R", 0.45, "g_net"), (3.20, "K", "L", 0.45, "n6_server"),
       (3.34, "L", "R", 0.42, "19_aerial"), (3.48, "G", "B", 0.45, "o8_servers"), (3.62, "F", "T", 0.50, "g_floor"),
       (3.76, "E", "R", 0.45, "o10_chip2"), (3.90, "B", "L", 0.45, "n3_evline"), (4.04, "C", "B", 0.45, "q5_city")]
NAMES = "BCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"


def build_layout():
    full = (0.0, O.Y0, float(W), O.Y1 - O.Y0)
    panels = {"A": dict(clip=O.MAIN, t0=-1.0, keys=[(-1.0, full)], scale_rect=full, focus=(0.40, 0.5))}
    names = iter(NAMES)
    for (t, tgt, side, share, clip) in OPS:
        x, y, w, h = panels[tgt]["keys"][-1][1]
        if side in "LR":
            nw = w * share
            new = (x, y, nw, h) if side == "L" else (x + w - nw, y, nw, h)
            kept = (x + nw, y, w - nw, h) if side == "L" else (x, y, w - nw, h)
            start = (x, y, 0.0, h) if side == "L" else (x + w, y, 0.0, h)
        else:
            nh = h * share
            new = (x, y, w, nh) if side == "T" else (x, y + h - nh, w, nh)
            kept = (x, y + nh, w, h - nh) if side == "T" else (x, y, w, h - nh)
            start = (x, y, w, 0.0) if side == "T" else (x, y + h, w, 0.0)
        panels[tgt]["keys"].append((t, kept))
        panels[next(names)] = dict(clip=clip, t0=t, keys=[(t - 1.0, start), (t, new)], scale_rect=new, side=side)
    return panels


O.PANELS = build_layout()
START = {"g_cubes": 2.6, "g_chart": 2.4}          # where in a clip its panel starts (past an empty opening)


def clip_frame(name, p, s):
    info = media.clip_info(name)
    off = START.get(name, 0.0)
    dur = info["dur"] - 0.1 - off
    life = O.ft(O.TL1) - max(0.0, p["t0"])
    rate = min(1.0, dur / max(life, 0.1))
    ct = off + min(dur, max(0.0, (s - max(0.0, p["t0"])) * rate) + (0.3 if rate >= 1 else 0.0))
    if name not in O._READERS:
        big = name == O.MAIN
        size = (1920, 1080) if (big and O.HD) else ((1280, 720) if (big or O.HD) else (960, 540))
        O._READERS[name] = O.Reader(name, size)
    return O._READERS[name].get(int(ct * 24))


O.clip_frame = clip_frame
_STAND = {"g_wave": "o8_servers", "g_map": "19_aerial", "g_cubes": "o7_hologram", "g_chart": "o10_chip2",
          "g_net": "o1_chip", "g_floor": "o6_amr"}       # (stand-ins while a clip is still being made)


def _have(n):
    return n.startswith("#") or os.path.exists(os.path.join(media.CLIP_DIR, n + ".mp4"))


for _p in O.PANELS.values():
    if not _have(_p["clip"]):
        _p["clip"] = _STAND[_p["clip"]]

# ---------------------------------------------------------------- the AX (gothic, in letter-height units)
AX_PIECES = [  # name, polygon, facet clip, mark target
    ("AL_low", [(0.162, 0.55), (0.362, 0.55), (0.20, 1.0), (0.0, 1.0)], "o7_hologram", "s1"),
    ("AL_up", [(0.36, 0.0), (0.46, 0.0), (0.46, 0.2778), (0.362, 0.55), (0.162, 0.55)], "22_city", "s2"),
    ("AR", [(0.46, 0.0), (0.56, 0.0), (0.92, 1.0), (0.72, 1.0), (0.46, 0.2778)], "17_robot", "dia"),
    ("AB", [(0.344, 0.60), (0.576, 0.60), (0.634, 0.76), (0.286, 0.76)], "o10_chip2", "dia"),
    ("XUL", [(1.02, 0.0), (1.23, 0.0), (1.495, 0.358), (1.39, 0.5)], "g_net", "xul"),
    ("XUR", [(1.76, 0.0), (1.97, 0.0), (1.60, 0.5), (1.495, 0.358)], "10_datacenter", "xur"),
    ("XLL", [(1.39, 0.5), (1.495, 0.642), (1.23, 1.0), (1.02, 1.0)], "o5_cobots", "xll"),
    ("XLR", [(1.495, 0.642), (1.60, 0.5), (1.97, 1.0), (1.76, 1.0)], "g_map", "xlr"),
    ("XC", [(1.495, 0.358), (1.60, 0.5), (1.495, 0.642), (1.39, 0.5)], LBLUE, "xc"),
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

TXT0 = 0.50                                       # the AX comes up on the main shot
TXT_H = 130.0                                     # its letter height there (px)
ABS0, ABS_D = 4.40, 1.00                          # drawn into the AX
BIG_H = 600.0
FAC0 = 5.15                                       # each facet its own shot
SOLID0 = 5.82
SHR0, SHR_D = 6.02, 0.52                          # the solid AX comes down to the mark's size and place
MARK_H = 104.0
MORPH0, MORPH_D = 6.48, 0.50
CORE0 = 6.86
GLINT = 7.80
LOGO_W = 640.0


def ax_xf(hpx, cx=W / 2, cy=H / 2):
    return lambda u, v: (cx + (u - AX_CX) * hpx, cy + (v - AX_CY) * hpx)


def mark_xf():
    k = LOGO_W / O.LOGO_VB[0]
    x0, y0 = W / 2 - LOGO_W / 2, H / 2 - O.LOGO_VB[1] * k / 2
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


def cover(c, name, rect, s, t0):
    """A shot cover-fitted into rect (the collage's light readers, graded to the common look)."""
    img = clip_frame(name, dict(t0=t0), s)
    if img is None:
        return
    k = max(rect.width() / img.width(), rect.height() / img.height()) * (1.10 - 0.08 * e_out_cubic(prog(s, t0, 1.6)))
    iw, ih = img.width() * k, img.height() * k
    pt = skia.Paint(AntiAlias=True)
    pt.setColorFilter(O.grade(name))
    c.drawImageRect(img, R(rect.centerX() - iw / 2, rect.centerY() - ih / 2, iw, ih),
                    skia.SamplingOptions(skia.FilterMode.kLinear), pt)


AX_PIECES = [(a, b, c if _have(c) else _STAND[c], d) for (a, b, c, d) in AX_PIECES]
SQUARES = []                                      # the reference's small blue squares round the letters
_rr = np.random.default_rng(7)
for _j in range(12):
    _u = _rr.uniform(-0.55, 2.55)
    _v = _rr.uniform(-0.12, 1.12) if not (-0.05 < _u < 2.02) else (_rr.choice([-0.16, 1.16]) + _rr.uniform(-0.05, 0.05))
    SQUARES.append((_u, _v, _rr.uniform(9, 22), _rr.uniform(0, 0.5), LBLUE if _j % 3 else INDIGO))


# ---------------------------------------------------------------- frame
def render(c, t):
    s = t - TL0 / 24.0
    q = e_io_cubic(prog(s, ABS0, ABS_D))          # drawn into the AX
    hpx = lerp(TXT_H, BIG_H, q)
    sq = e_io_cubic(prog(s, SHR0, SHR_D))
    mcx, mcy = mark_xf()(247.8, 192.9)
    xf = ax_xf(math.exp(lerp(math.log(hpx), math.log(MARK_H), sq)), lerp(W / 2, mcx, sq), lerp(H / 2, mcy, sq))
    pieces = [(nm, [xf(u, v) for (u, v) in pts], clip, tgt) for (nm, pts, clip, tgt) in AX_PIECES]
    ax = union([poly(p) for _, p, _, _ in pieces])
    white = e_io_sine(prog(s, ABS0, 0.75))
    morph = prog(s, MORPH0, MORPH_D)
    c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF" if white >= 1 else "#07090F"))
    # the collage (with the main shot), contracting into the letters
    if white < 1 or (s < FAC0 + 0.45):
        push = (1.0 + 0.045 * e_io_sine(prog(s, 0.0, 6.0))) * lerp(1.0, 0.80, q)
        c.save()
        if white >= 1:
            c.clipPath(ax, skia.ClipOp.kIntersect, True)
        c.translate(W / 2, H / 2)
        c.scale(push, push)
        c.translate(-W / 2, -H / 2)
        for name in O.PANELS:
            if name != "A":
                O.draw_panel(c, name, s)
        O.draw_panel(c, "A", s)
        c.restore()
    if white > 0:                                 # outside the letters clears to white
        c.save()
        c.clipPath(ax, skia.ClipOp.kDifference, True)
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", white))
        c.restore()
    # thin guide lines and the small squares (reference vocabulary) on the white
    deco = e_io_sine(prog(s, ABS0 + 0.5, 0.5)) * (1 - e_io_sine(prog(s, SHR0 - 0.1, 0.35)))
    if deco > 0:
        for (u, v, sz, d0, colr) in SQUARES:
            a = deco * e_out_cubic(prog(s, ABS0 + 0.55 + d0, 0.3))
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
    txt_in = e_out_cubic(prog(s, TXT0, 0.45))
    fill_out = e_io_sine(prog(s, ABS0 + 0.05, 0.55))      # the indigo fill gives way to the footage inside
    fac = e_io_sine(prog(s, FAC0, 0.45))
    if morph <= 0:
        if txt_in > 0 and fill_out < 1:
            a = txt_in * (1 - fill_out)
            c.save()
            c.translate(0, 16 * (1 - txt_in))
            g = skia.Paint(AntiAlias=True, Color4f=skia.Color4f(1, 1, 1, 0.38 * a))
            g.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 22))
            c.drawPath(ax, g)                        # a soft light behind it so it reads on the shot
            c.drawPath(ax, skia.Paint(AntiAlias=True, Color4f=mixc(INDIGO, INDIGO, 0, a)))
            c.restore()
        if fac > 0:                                  # each facet takes its own shot, white seams between them
            for j, (nm, pts, clip, tgt) in enumerate(pieces):
                fa = e_io_sine(prog(s, FAC0 + 0.04 * j, 0.40))
                if fa <= 0:
                    continue
                c.save()
                c.clipPath(poly(pts), skia.ClipOp.kIntersect, True)
                c.saveLayer(None, skia.Paint(Alphaf=fa))
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                box = skia.Rect.MakeLTRB(min(xs), min(ys), max(xs), max(ys))
                if clip.startswith("#"):
                    c.drawRect(box, paint_fill(clip))
                else:
                    cover(c, clip, box, s, FAC0 - 0.3)
                c.restore()
                c.restore()
            for (nm, pts, clip, tgt) in pieces:
                c.drawPath(poly(pts), skia.Paint(AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=3.0,
                                                 Color4f=skia.Color4f(1, 1, 1, fac)))
        for j, (nm, pts, clip, tgt) in enumerate(pieces):     # solid indigo, one stroke after another
            sa = e_io_sine(prog(s, SOLID0 + 0.035 * j, 0.24))
            if sa > 0:
                c.drawPath(poly(pts), paint_fill(INDIGO, sa))
    mx = mark_xf()
    if morph > 0:                                    # the strokes become the mark
        for j, (nm, pts, clip, tgt) in enumerate(pieces):
            mq = e_io_cubic(prog(s, MORPH0 + 0.025 * j, MORPH_D - 0.2))
            A = resample(pts)
            B = resample([mx(x, y) for x, y in MARK[tgt]])
            Pm = A * (1 - mq) + B * mq
            c0 = INDIGO
            c1 = LBLUE if tgt in ("dia", "xc") else GREY
            a = 1.0 - (e_io_sine(prog(s, MORPH0 + 0.3, 0.3)) if tgt == "xc" else 0.0)
            c.drawPath(poly([tuple(p) for p in Pm]), skia.Paint(AntiAlias=True, Color4f=mixc(c0, c1, mq, a)))
    # C O R E, the E's bars and the caption (the client's SVG, own colours)
    if s >= CORE0 - 0.05:
        logo_rest(c, s)


ORDER = [("C", 0.00), ("O", 0.06), ("R", 0.12), ("bars", 0.20), ("kor", 0.36)]


def logo_rest(c, s):
    if not O.LOGO:
        O.LOGO.update(O.load_logo())
    L = O.LOGO
    k = LOGO_W / O.LOGO_VB[0]
    c.save()
    c.translate(W / 2 - LOGO_W / 2, H / 2 - O.LOGO_VB[1] * k / 2)
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
        if grp == "bars":
            c.translate(-140 * (1 - e_out_cubic(q)), 0)
        else:
            c.translate(-60 * (1 - e_out_cubic(q)), 0)
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
