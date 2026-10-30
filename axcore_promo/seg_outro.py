"""Outro 00:01:49:01-00:01:58:13 (229 frames) - "더 빠른 판단, / 더 효율적인 실행. / 더 높은 업무 생산성으로. /
AI 전환의 가장 쉬운 시작. / AXCORE" - after the client's reference: one live-action shot full frame, then the frame
splits again and again (each new panel pushes in from its side) into a collage of the film's own footage round the
main shot in the centre, on which the AXCORE logo (the client's SVG; grey parts white, the blue kept) builds up.
  0.00  seg_sphere's last frame (plain white); the white clears onto the main shot
  0.90  the first split; then a new panel about every 0.45 s
  3.50  the AXCORE logo builds on the main shot, piece by piece
  7.75  the logo draws back, the collage (the main shot with it) narrows to the left and a column comes in on the right
  8.90  "AXCORE": a light runs over the logo
Local clock s = (timeline frame - 2617) / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_outro.py <out.mp4> [height=480] [first last]
"""
import math
import os
import re
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import seg_ai as AI
from engine import W, H, R, WHITE, lerp, prog, clamp, e_io_cubic, e_io_sine, e_out_cubic, paint_fill, colint


def e_out_back(x, k=1.70158):
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2

TL0, TL1 = 109 * 24 + 1, 118 * 24 + 13          # timeline 01:49:01 .. 01:58:13
NF = TL1 - TL0 + 1
SHIFT = 2.0                                      # the old FIN passage sat 2 s earlier (seg_sphere hands over from it)
BAR = 138
Y0, Y1 = BAR, H - BAR
FPS_NUM, FPS_DEN = 24000, 1001
SCV = 1.0
HD = False

MAIN = "o0_present"                              # a presenter at a data wall (after the client's sample)
SPLIT_D = 0.55
# (time, panel split, side the new panel comes in from, its share, the new panel's clip)
OPS = [(0.90, "A", "L", 0.30, "o1_chip"), (1.45, "B", "B", 0.50, "17_robot"), (2.00, "A", "R", 0.40, "o2_warehouse"),
       (2.50, "D", "B", 0.42, "o4_wafer"), (2.95, "B", "R", 0.50, "10_datacenter"), (3.40, "C", "R", 0.45, "o3_drones"),
       (3.85, "D", "R", 0.45, "18_factory"), (4.25, "E", "R", 0.50, "o5_cobots"), (4.65, "F", "B", 0.50, "r5_robot"),
       (5.05, "H", "B", 0.55, "05_warehouse"), (5.45, "G", "T", 0.45, "22_city"), (5.85, "I", "T", 0.50, "s03_robot"),
       (6.25, "B", "T", 0.50, "n6_server"), (6.65, "K", "R", 0.45, "19_aerial"), (7.05, "C", "B", 0.45, "06_line"),
       (7.45, "E", "T", 0.45, "q3_silos")]
END0, END_D = 7.75, 0.75                         # the collage draws back to the left, a column comes in on the right
END_K = 0.80
END_COL = [(END0 + 0.05, 0.0, 0.36, "o1_chip"), (END0 + 0.17, 0.36, 0.30, "o3_drones"), (END0 + 0.29, 0.66, 0.34, "q1_refinery")]
LOGO0 = 3.50
GLINT = 8.90


def ft(tl):
    return (tl - TL0) / 24.0


# ---------------------------------------------------------------- the layout over time
def build_layout():
    """Each panel: its clip, when it appears, and its rect keyframes [(time, rect)]."""
    full = (0.0, Y0, float(W), Y1 - Y0)
    panels = {"A": dict(clip=MAIN, t0=-1.0, keys=[(-1.0, full)], scale_rect=full)}
    names = iter("BCDEFGHIJKLMNOPQRSTU")
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
        n = next(names)
        panels[n] = dict(clip=clip, t0=t, keys=[(t - 1.0, start), (t, new)], scale_rect=new, side=side)
    x0 = W * END_K
    for j, (t, fy, fh, clip) in enumerate(END_COL):
        y, h = Y0 + (Y1 - Y0) * fy, (Y1 - Y0) * fh
        new = (x0, y, W - x0, h)
        panels["Z%d" % j] = dict(clip=clip, t0=t, keys=[(t - 1.0, (W, y, 0.0, h)), (t, new)], scale_rect=new,
                                 side="R", end=True, loop=True)
    return panels


PANELS = build_layout()


def squeeze(s):
    return lerp(1.0, END_K, e_io_cubic(prog(s, END0, END_D)))


def rect_at(p, s):
    r = _rect_at(p, s)
    if p.get("end"):
        return r
    k = squeeze(s)
    return (r[0] * k, r[1], r[2] * k, r[3])


def _rect_at(p, s):
    keys = p["keys"]
    cur = keys[0][1]
    for (t, r) in keys[1:]:
        if s <= t:
            break
        q = e_io_cubic(clamp((s - t) / SPLIT_D))
        cur = tuple(lerp(a, b, q) for a, b in zip(cur, r)) if q < 1 else r
        if q < 1:
            return cur
    return cur


# ---------------------------------------------------------------- footage (own light readers: scaled-down tiles)
class Reader:
    def __init__(self, name, size):
        self.path = os.path.join(media.CLIP_DIR, name + ".mp4")
        self.w, self.h = size
        self.proc, self.cur, self.img = None, -1, None

    def _open(self, fi):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
        self.proc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-threads", "1", "-ss", "%.4f" % (fi / 24.0),
                                      "-i", self.path, "-vf", "scale=%d:%d" % (self.w, self.h), "-f", "rawvideo",
                                      "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE)
        self.cur = fi - 1

    def get(self, fi):
        if self.img is not None and fi == self.cur:
            return self.img
        if self.proc is None or fi < self.cur or fi > self.cur + 30:
            self._open(fi)
        n = self.w * self.h * 4
        while self.cur < fi:
            buf = self.proc.stdout.read(n)
            if len(buf) < n:
                break
            self.img = skia.Image.fromarray(np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 4).copy(),
                                            colorType=skia.ColorType.kRGBA_8888_ColorType)
            self.cur += 1
        return self.img


_READERS = {}


def clip_frame(name, p, s):
    """The panel's frame: it plays from its start, slowed when needed so it never runs out (holds) before the end."""
    info = media.clip_info(name)
    dur = info["dur"] - 0.1
    life = ft(TL1) - max(0.0, p["t0"])
    rate = min(1.0, dur / max(life, 0.1))
    ct = min(dur, max(0.0, (s - max(0.0, p["t0"])) * rate) + (0.3 if rate >= 1 else 0.0))
    if name not in _READERS:
        big = name == MAIN
        size = (1920, 1080) if (big and HD) else ((1280, 720) if (big or HD) else (960, 540))
        _READERS[name] = Reader(name, size)
    return _READERS[name].get(int(ct * 24))


GRADE = E.grade_filter(bright=1.04, contrast=1.03, sat=0.92, tint=(-0.004, 0.0, 0.010))


def draw_panel(c, name, s):
    p = PANELS[name]
    x, y, w, h = rect_at(p, s)
    if w < 1 or h < 1:
        return
    img = clip_frame(p["clip"], p, s)
    if img is None:
        return
    sx, sy, sw, sh = p["scale_rect"]
    k = max(sw / img.width(), sh / img.height()) * 1.02       # cover the panel's settled size; crop as it narrows
    iw, ih = img.width() * k, img.height() * k
    side = p.get("side")
    # the picture rides with the edge it comes in from (it is pushed in), otherwise stays centred on the panel
    if side == "L":
        cx = x + w - sw / 2
    elif side == "R":
        cx = x + sw / 2
    else:
        cx = x + w / 2
    if side == "T":
        cy = y + h - sh / 2
    elif side == "B":
        cy = y + sh / 2
    else:
        cy = y + h / 2
    c.save()
    c.clipRect(R(x + 1.5, y + 1.5, w - 3, h - 3))
    pt = skia.Paint(AntiAlias=True)
    pt.setColorFilter(GRADE)
    c.drawImageRect(img, R(cx - iw / 2, cy - ih / 2, iw, ih), skia.SamplingOptions(skia.FilterMode.kLinear), pt)
    c.restore()


# ---------------------------------------------------------------- the AXCORE logo (the client's SVG)
SVG = os.path.join(E.HERE, "assets", "axcore_logo.svg")
LOGO_VB = (1246.15, 311.1)
BLUE = "#0053FC"


def _bounds(tag, a):
    if tag == "rect":
        x, y = float(a["x"]), float(a["y"])
        return x, y, x + float(a["width"]), y + float(a["height"])
    v = [float(x) for x in re.findall(r"-?\d*\.?\d+", a.get("points") or a.get("d"))]
    if tag == "polygon":
        xs, ys = v[0::2], v[1::2]
    else:                                             # the Korean caption paths: their first point is enough
        xs, ys = [v[0]], [v[1]]
    return min(xs), min(ys), max(xs), max(ys)


LOGO_RES = 3.0                                        # the logo is rasterised at 3x its viewBox


def load_logo():
    """{group: (image, colour)} - each piece group of the client's SVG rendered on its own (grey parts white,
    the blue kept), so the pieces can come in one after another."""
    txt = open(SVG).read()
    groups = {}
    for m in re.finditer(r"<(rect|polygon|path)\s+class=\"(st\d)\"([^>]*)/>", txt):
        tag, cls, attrs = m.groups()
        a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        x0, y0, x1, y1 = _bounds(tag, a)
        if y1 < 80:
            grp = "kor"
        elif cls == "st0" and x0 > 1000:
            grp = "bars"
        elif cls == "st0":
            grp = "dia"
        elif x1 < 140:
            grp = "s1"
        elif x1 < 260:
            grp = "s2"
        elif x1 < 470:
            grp = "X"
        elif x1 < 640:
            grp = "C"
        elif x1 < 840:
            grp = "O"
        else:
            grp = "R"
        col = BLUE if cls == "st0" else "#FFFFFF"
        attrs = re.sub(r'class="st\d"', "", attrs)
        groups.setdefault(grp, []).append('<%s fill="%s" %s/>' % (tag, col, attrs))
    out = {}
    vw, vh = LOGO_VB
    for grp, els in groups.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%d" height="%d">%s</svg>'
               % (vw, vh, int(vw * LOGO_RES), int(vh * LOGO_RES), "".join(els)))
        dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg.encode(), True))
        sf = skia.Surface.MakeRaster(skia.ImageInfo.Make(int(vw * LOGO_RES), int(vh * LOGO_RES),
                                                         skia.ColorType.kRGBA_8888_ColorType,
                                                         skia.AlphaType.kPremul_AlphaType))
        cc = sf.getCanvas()
        cc.clear(skia.Color4f(0, 0, 0, 0))
        dom.setContainerSize(skia.Size(vw * LOGO_RES, vh * LOGO_RES))
        dom.render(cc)
        img = sf.makeImageSnapshot()
        al = img.toarray()[..., 3]
        ys, xs = np.where(al > 0)
        b = R(xs.min() / LOGO_RES, ys.min() / LOGO_RES, (xs.max() - xs.min()) / LOGO_RES, (ys.max() - ys.min()) / LOGO_RES)
        out[grp] = (img, b)
    return out


LOGO = []
ORDER = [("s1", 0.00), ("s2", 0.07), ("X", 0.14), ("C", 0.21), ("O", 0.28), ("R", 0.35), ("bars", 0.45),
         ("dia", 0.70), ("kor", 0.80)]


LOGO = {}


def logo(c, s, cx, cy, width):
    if not LOGO:
        LOGO.update(load_logo())
    k = width / LOGO_VB[0]
    c.save()
    c.translate(cx - width / 2, cy - LOGO_VB[1] * k / 2)
    c.scale(k, k)
    full = R(0, 0, LOGO_VB[0], LOGO_VB[1])
    smp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
    for grp, t0 in ORDER:
        q = prog(s, LOGO0 + t0, 0.5)
        if q <= 0 or grp not in LOGO:
            continue
        img, b = LOGO[grp]
        a = e_io_sine(clamp(q * 1.6))
        c.save()
        if grp == "bars":                             # the E's bars slide in from the left
            c.translate(-120 * (1 - e_out_cubic(q)), 0)
        elif grp == "dia":                            # the diamond pops (and glows)
            sc = e_out_back(clamp(q))
            c.translate(b.centerX(), b.centerY())
            c.scale(sc, sc)
            c.translate(-b.centerX(), -b.centerY())
        else:                                         # the glyphs rise in out of a blur
            c.translate(0, 28 * (1 - e_out_cubic(q)))
        gp = skia.Paint(AntiAlias=True)
        gp.setAlphaf(0.55 * a)
        gp.setImageFilter(skia.ImageFilters.Blur(10 + 6 * (1 - q), 10 + 6 * (1 - q)))
        c.drawImageRect(img, full, smp, gp)           # soft glow round the pieces
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(a)
        if q < 1:
            p.setImageFilter(skia.ImageFilters.Blur(6 * (1 - q), 6 * (1 - q)))
        c.drawImageRect(img, full, smp, p)
        c.restore()
    glint = prog(s, GLINT, 0.9)
    if 0 < glint < 1:                                 # "AXCORE": a light runs over it
        gx = lerp(-200, LOGO_VB[0] + 200, e_io_sine(glint))
        sh = skia.GradientShader.MakeLinear([skia.Point(gx - 140, 0), skia.Point(gx + 140, LOGO_VB[1])],
                                            [colint(WHITE, 0), colint(WHITE, 0.85), colint(WHITE, 0)])
        c.saveLayer(None, None)
        for grp in LOGO:
            c.drawImageRect(LOGO[grp][0], full, smp, skia.Paint(AntiAlias=True))
        c.drawPaint(skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kSrcIn))
        c.restore()
    c.restore()


# ---------------------------------------------------------------- frame
def render(c, t):
    s = t - TL0 / 24.0
    c.drawRect(R(0, 0, W, H), paint_fill("#07090F"))
    push = 1.0 + 0.045 * e_io_sine(prog(s, 0.0, ft(TL1)))
    c.save()
    c.translate(W / 2, H / 2)
    c.scale(push, push)
    c.translate(-W / 2, -H / 2)
    for name in PANELS:
        if name != "A":
            draw_panel(c, name, s)
    draw_panel(c, "A", s)
    ax, ay, aw, ah = rect_at(PANELS["A"], s)
    la = e_io_sine(prog(s, LOGO0 - 0.2, 0.6))
    if la > 0:                                        # the main shot dims a little under the logo
        c.save()
        c.clipRect(R(ax + 1.5, ay + 1.5, aw - 3, ah - 3))
        c.drawRect(R(ax, ay, aw, ah), paint_fill("#061026", 0.32 * la))
        E.radial(c, ax + aw / 2, ay + ah / 2, aw * 0.6, "#061026", 0.35 * la, blend=skia.BlendMode.kSrcOver)
        c.restore()
    logo(c, s, ax + aw / 2, ay + ah / 2, min(620.0, aw * 0.78) * lerp(1.0, 0.92, e_io_cubic(prog(s, END0, END_D))))
    c.restore()
    # in: from seg_sphere's last frame (FIN under the fading white) to the main shot
    m = e_io_sine(prog(s, 0.0, 0.55))
    if m < 1:                                         # in: seg_sphere's white flash clears onto the main shot
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", 1 - m))


_FS = []


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    HD = height > 1080
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
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
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
        render(c, tl / 24.0)
        c.restore()
        fr = finish.apply(surf, tl - 48)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
