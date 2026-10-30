"""Outro 00:01:49:01-00:01:59:13 (253 frames) - "더 빠른 판단, / 더 효율적인 실행. / 더 높은 업무 생산성으로. /
AI 전환의 가장 쉬운 시작. / AXCORE" - after the client's reference: one live-action shot full frame, then the frame
splits again and again (each new panel pushes in from its side) into a collage of the film's own footage round the
main shot in the centre, on which the AXCORE logo (the client's SVG; grey parts white, the blue kept) builds up.
  0.00  seg_sphere's last frame (plain white); the white clears onto the main shot
  0.90  the first split; then a new panel about every 0.45 s
  3.50  the AXCORE logo builds on the main shot, piece by piece
  8.00  all built: the collage fades out to white, the logo stays and settles in the centre in its own colours
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

TL0, TL1 = 109 * 24 + 1, 119 * 24 + 13          # timeline 01:49:01 .. 01:59:13 (1 s longer: the logo's light finishes)
NF = TL1 - TL0 + 1
SHIFT = 2.0                                      # the old FIN passage sat 2 s earlier (seg_sphere hands over from it)
BAR = 138
Y0, Y1 = BAR, H - BAR
FPS_NUM, FPS_DEN = 24000, 1001
SCV = 1.0
HD = False

MAIN = "o0_present"                              # a presenter at a data wall (after the client's sample)
SPLIT_D = 0.55
SNAP_D, DRIFT_D = 0.24, 1.40
# (time, panel split, side the new panel comes in from, its share, the new panel's clip)
OPS = [(0.90, "A", "L", 0.30, "o1_chip"), (1.45, "B", "B", 0.50, "17_robot"), (2.00, "A", "R", 0.40, "o2_warehouse"),
       (2.50, "D", "B", 0.42, "o4_wafer"), (2.95, "B", "R", 0.50, "10_datacenter"), (3.40, "C", "R", 0.45, "o3_drones"),
       (3.85, "D", "R", 0.45, "18_factory"), (4.25, "E", "R", 0.50, "o5_cobots"), (4.65, "F", "B", 0.50, "o6_amr"),
       (5.05, "H", "B", 0.55, "05_warehouse"), (5.45, "G", "T", 0.45, "22_city"), (5.85, "I", "T", 0.50, "s03_robot"),
       (6.25, "B", "T", 0.50, "n6_server"), (6.65, "K", "R", 0.45, "19_aerial"), (7.05, "C", "B", 0.45, "06_line"),
       (7.45, "E", "T", 0.45, "o5_cobots")]
END0, END_D = 7.75, 0.75                         # the collage draws back to the left, a column comes in on the right
END_K = 0.80
END_COL = []                                     # (the closing column on the right: taken out again)
FADE0, FADE_D = 8.00, 0.70                       # all built: the collage fades to white, the logo stays (own colours)
LOGO0 = 3.50
GLINT = 8.90


def ft(tl):
    return (tl - TL0) / 24.0


# ---------------------------------------------------------------- the layout over time
def build_layout():
    """Each panel: its clip, when it appears, and its rect keyframes [(time, rect)]."""
    full = (0.0, Y0, float(W), Y1 - Y0)
    panels = {"A": dict(clip=MAIN, t0=-1.0, keys=[(-1.0, full)], scale_rect=full, focus=(0.40, 0.5))}
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
CUTS2 = {"B": (2.25, "o10_chip2"), "C": (3.05, "o8_servers"), "D": (3.30, "o7_hologram"), "E": (4.95, "17_robot"),
         "F": (4.10, "o2_warehouse"), "G": (5.15, "o9_weld"), "H": (6.05, "o1_chip"), "I": (6.45, "10_datacenter"),
         "J": (6.85, "o3_drones"), "K": (7.25, "o4_wafer")}
for _n, (_t, _c) in CUTS2.items():
    PANELS[_n]["cut"], PANELS[_n]["clip2"] = _t, _c


def squeeze(s):
    return 1.0


def rect_at(p, s):
    r = _rect_at(p, s)
    if p.get("end"):
        return r
    k = squeeze(s)
    return (r[0] * k, r[1], r[2] * k, r[3])


def snap(dt):
    """A split's move (reference): most of the way in a few frames, the rest a slow drift after it."""
    if dt <= 0:
        return 0.0
    return 0.84 * (1 - (1 - clamp(dt / SNAP_D)) ** 4) + 0.16 * e_io_sine(clamp(dt / DRIFT_D))


def _rect_at(p, s):
    """The rect as the sum of each split's move, so a move still drifting when the next one comes stays smooth."""
    keys = p["keys"]
    cur = list(keys[0][1])
    prev = keys[0][1]
    for (t, r) in keys[1:]:
        q = snap(s - t)
        for i in range(4):
            cur[i] += (r[i] - prev[i]) * q
        prev = r
    return tuple(cur)


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


TARGET, TARGET_SD = np.array([0.50, 0.56, 0.65]), 0.22     # one cool blue-white look for every panel
_GRADES = {}


def grade(name):
    """Per-clip match to the common look: each clip's mean colour and contrast (from its proxy) are pulled most
    of the way to the target, with a little less saturation, so the collage reads as one film."""
    if name not in _GRADES:
        a = np.load(os.path.join(media.CLIP_DIR, name + "_proxy.npy"), mmap_mode="r")
        sm = np.asarray(a[::12, ::4, ::4]).astype(np.float32) / 255.0
        m = sm.reshape(-1, 3).mean(0)
        sd = float((sm @ np.array([0.2126, 0.7152, 0.0722], np.float32)).std())
        k = lerp(1.0, float(np.clip(TARGET_SD / max(sd, 1e-3), 0.85, 1.25)), 0.6)
        tgt = m + (TARGET - m) * 0.70
        sat = 0.88
        lr, lg, lb = 0.2126, 0.7152, 0.0722
        S = np.array([[lr * (1 - sat) + sat, lg * (1 - sat), lb * (1 - sat)],
                      [lr * (1 - sat), lg * (1 - sat) + sat, lb * (1 - sat)],
                      [lr * (1 - sat), lg * (1 - sat), lb * (1 - sat) + sat]]) * k
        off = tgt - S @ m
        rows = []
        for i in range(3):
            rows += list(S[i]) + [0.0, float(off[i])]
        rows += [0, 0, 0, 1, 0]
        _GRADES[name] = skia.ColorFilters.Matrix([float(v) for v in rows])
    return _GRADES[name]


def draw_panel(c, name, s):
    p = PANELS[name]
    x, y, w, h = rect_at(p, s)
    if w < 1 or h < 1:
        return
    clip, cut_t = p["clip"], p.get("cut")
    if cut_t is not None and s >= cut_t:
        clip = p["clip2"]
    img = clip_frame(clip, dict(p, t0=cut_t) if clip != p["clip"] else p, s)
    if img is None:
        return
    sx, sy, sw, sh = p["scale_rect"]
    k = max(sw / img.width(), sh / img.height()) * 1.02       # cover the panel's settled size; crop as it narrows
    k *= 1.0 + 0.06 * prog(s, max(0.0, p["t0"]), 6.0)    # every panel keeps pushing in a little
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
    if name == "A":                                  # the main shot: always just covers its panel, so as the
        k = max(w / img.width(), h / img.height()) * 1.04   # panel narrows the shot draws back (the presenter
        iw, ih = img.width() * k, img.height() * k          # gets smaller instead of being cropped to his face)
        fx_ = p.get("focus", (0.5, 0.5))[0]
        cx = x + w / 2 + clamp((0.5 - fx_) * iw, -(iw - w) / 2, (iw - w) / 2)
        cy = y + h / 2
    else:
        fx_, fy_ = p.get("focus", (0.5, 0.5))       # keep the subject of the shot in the panel
        cx += (0.5 - fx_) * iw * clamp((sw - w) / max(sw * 0.4, 1.0))
    c.save()
    c.clipRect(R(x + 1.5, y + 1.5, w - 3, h - 3))
    pt = skia.Paint(AntiAlias=True)
    pt.setColorFilter(grade(clip))
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
        orig = {"st0": "#0053fc", "st1": "#77787b", "st2": "#5e5f64"}[cls]
        attrs = re.sub(r'class="st\d"', "", attrs)
        groups.setdefault(grp, []).append('<%s fill="%s" %s/>' % (tag, col, attrs))
        groups.setdefault(grp + "@o", []).append('<%s fill="%s" %s/>' % (tag, orig, attrs))
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
ORDER = [("s1", 0.00), ("s2", 0.05), ("X", 0.10), ("C", 0.15), ("O", 0.20), ("R", 0.25), ("bars", 0.33),
         ("dia", 0.48), ("kor", 0.56)]


LOGO = {}
ORIG = 0.0


def logo(c, s, cx, cy, width):
    if not LOGO:
        LOGO.update(load_logo())
    k = width / LOGO_VB[0]
    c.save()
    c.translate(cx - width / 2, cy - LOGO_VB[1] * k / 2)
    c.scale(k, k)
    full = R(0, 0, LOGO_VB[0], LOGO_VB[1])
    smp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
    global ORIG
    ORIG = e_io_sine(prog(s, FADE0 + 0.15, FADE_D))
    for grp, t0 in ORDER:
        q = prog(s, LOGO0 + t0, 0.28)
        if q <= 0 or grp not in LOGO:
            continue
        img, b = LOGO[grp]
        img_o = LOGO[grp + "@o"][0]
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
            c.translate(0, 18 * (1 - e_out_cubic(q)))
        gp = skia.Paint(AntiAlias=True)
        gp.setAlphaf(0.55 * a * (1 - ORIG))
        gp.setImageFilter(skia.ImageFilters.Blur(10 + 6 * (1 - q), 10 + 6 * (1 - q)))
        c.drawImageRect(img, full, smp, gp)           # soft glow round the pieces
        p = skia.Paint(AntiAlias=True)
        p.setAlphaf(a * (1 - ORIG))
        if q < 1:
            p.setImageFilter(skia.ImageFilters.Blur(6 * (1 - q), 6 * (1 - q)))
        if ORIG < 1:
            c.drawImageRect(img, full, smp, p)
        if ORIG > 0:                                  # its own colours on the white end card
            po = skia.Paint(AntiAlias=True)
            po.setAlphaf(a * ORIG)
            c.drawImageRect(img_o, full, smp, po)
        c.restore()
    glint = prog(s, GLINT, 0.9)
    if 0 < glint < 1:                                 # "AXCORE": a light runs over it
        gx = lerp(-200, LOGO_VB[0] + 200, e_io_sine(glint))
        sh = skia.GradientShader.MakeLinear([skia.Point(gx - 140, 0), skia.Point(gx + 140, LOGO_VB[1])],
                                            [colint("#9FD2FF", 0), colint("#CFE8FF" if ORIG > 0.5 else WHITE, 0.85),
                                             colint("#9FD2FF", 0)])
        c.saveLayer(None, None)
        for grp in LOGO:
            if not grp.endswith("@o"):
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
    c.restore()
    f = e_io_sine(prog(s, FADE0, FADE_D))            # everything fades out to white ...
    if f > 0:
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", f))
    mv = e_io_cubic(prog(s, FADE0, FADE_D + 0.2))     # ... the logo stays, settles in the centre in its own colours
    lx = lerp(W / 2 + (ax + aw / 2 - W / 2) * push, W / 2, mv)
    ly = lerp(H / 2 + (ay + ah / 2 - H / 2) * push, H / 2, mv)
    logo(c, s, lx, ly, lerp(min(620.0, aw * 0.78) * push, 640.0, mv))
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
