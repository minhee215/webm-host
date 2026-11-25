"""S-WELL hero v6 - scene 2: natural cyan light graphics over a locked-off plate, camera move at the end,
logo forming in the same shot.

Input : clips/plate12.mp4 (locked-off), ../stills_v8/twin_plate.png, ../stills_v8/symbol_rgba.png
Output: tmp/v6_scene2.mp4 (1920x1080, 24 fps, silent)

Look: graphics are *added light* (additive blend) in cyan, with a thin bright core and soft bloom,
so they read as light living on the rails instead of flat UI strokes. Labels have no boxes.
"""
import os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W, H, FPS = 1920, 1080, 24
DUR = float(os.environ.get("DUR", "12.8"))
PLATE = os.environ.get("PLATE", "clips/plate12.mp4")
FD = "/usr/share/fonts/opentype/inter/"

CORE = np.array([200, 248, 255], np.float32) / 255     # near-white cyan core
GLOW = np.array([40, 200, 255], np.float32) / 255      # cyan bloom
AMBER = np.array([255, 175, 70], np.float32) / 255

RAIL_L = [(1160, 1080), (1100, 1020), (920, 930), (720, 830), (540, 730), (400, 630), (345, 570), (320, 515)]
RAIL_R = [(1920, 868), (1600, 797), (1300, 732), (1060, 682), (740, 606), (520, 552), (370, 512)]
POLES = [((222, 125), (222, 528)), ((305, 330), (305, 505))]

f_lab = ImageFont.truetype(FD + "Inter-Medium.otf", 30)
f_num = ImageFont.truetype(FD + "Inter-Medium.otf", 34)
f_axis = ImageFont.truetype(FD + "Inter-Medium.otf", 28)
f_word = ImageFont.truetype(FD + "InterDisplay-ExtraBoldItalic.otf", 112)
f_tag = ImageFont.truetype(FD + "Inter-Medium.otf", 36)
f_tag_b = ImageFont.truetype(FD + "Inter-SemiBold.otf", 36)

# twin plate (amber pole) + live-train mask
TWIN = np.asarray(Image.open(os.environ.get("TWIN_IMG", "../stills_v8/twin_plate12.png")).convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
_lum = TWIN.max(axis=2, keepdims=True)
_pole = np.zeros((H, W, 1), np.float32); _pole[0:545, 196:250] = 1
TWIN = TWIN * (1 - _pole) + np.maximum(TWIN * 0.25, _lum * AMBER * 1.2) * _pole
_yy, _xx = np.mgrid[0:H, 0:W]
TRAIN_MASK = np.zeros((H, W, 1), np.float32)   # plate is empty by the time the twin appears

# logo symbol with soft lower-left end
SYM = Image.open("../stills_v8/symbol_rgba.png")
SYM = SYM.resize((int(SYM.width * 290 / SYM.height), 290), Image.LANCZOS)
_a = np.asarray(SYM).astype(np.float32); _h, _w = _a.shape[:2]
_y, _x = np.mgrid[0:_h, 0:_w]
PROG = (_x / _w) * 0.55 + ((_h - _y) / _h) * 0.45
_f = np.clip((PROG - 0.18) / 0.32, 0, 1); _a[..., 3] *= _f * _f * (3 - 2 * _f)
SYM_A = _a


def cl(x): return max(0.0, min(1.0, x))
def ease(x): x = cl(x); return x * x * (3 - 2 * x)
def win(t, a, b): return ease((t - a) / (b - a))
def bell(t, a, b, c, d): return win(t, a, b) * (1 - win(t, c, d))


def plen(p): return [0] + list(np.cumsum([math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)]))
def pat(p, u):
    L = plen(p); d = cl(u) * L[-1]
    for i in range(len(p) - 1):
        if d <= L[i + 1]:
            k = (d - L[i]) / max(1e-6, L[i + 1] - L[i])
            return (p[i][0] + (p[i + 1][0] - p[i][0]) * k, p[i][1] + (p[i + 1][1] - p[i][1]) * k)
    return p[-1]
def ppart(p, u0, u1, n=50): return [pat(p, u0 + (u1 - u0) * i / n) for i in range(n + 1)]


def comet(d, p, head, base_level, width):
    """light travelling along polyline p up to `head` (0..1): bright head, settling glow behind it"""
    if head <= 0: return
    n = 80
    for i in range(n):
        u0, u1 = head * i / n, head * (i + 1) / n
        k = (i + 1) / n                       # 0 at start .. 1 at head
        lvl = base_level + (1 - base_level) * max(0, (k - 0.8) / 0.2) ** 1.5
        d.line([pat(p, u0), pat(p, u1)], fill=int(255 * lvl), width=width)
    if head < 1:
        x, y = pat(p, head); r = width * 2.2
        d.ellipse([x - r, y - r, x + r, y + r], fill=255)


def add_light(base, core_img, k_core=1.0, k_glow=1.0, color_core=CORE, color_glow=GLOW):
    c = np.asarray(core_img, np.float32) / 255
    g1 = np.asarray(core_img.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
    g2 = np.asarray(core_img.filter(ImageFilter.GaussianBlur(18)), np.float32) / 255
    light = (c[..., None] * color_core * 0.95 * k_core
             + g1[..., None] * color_glow * 1.3 * k_glow
             + g2[..., None] * color_glow * 0.9 * k_glow)
    return base + light


def scene_frame(t, bg):
    base = bg.astype(np.float32) / 255

    # ---- digital twin reveal ----
    scan = win(t, 8.8, 10.0)
    if scan > 0:
        sy = int(H * (1 - scan))
        twin = TWIN * (1 - TRAIN_MASK) + (base * 0.55 + TWIN * 0.45) * TRAIN_MASK
        m = np.zeros((H, 1, 1), np.float32); m[sy:] = 1
        base = base * (1 - m) + twin * m

    L = Image.new("L", (W, H), 0); d = ImageDraw.Draw(L)          # cyan light
    T = Image.new("L", (W, H), 0); dt = ImageDraw.Draw(T)         # text light (less bloom)
    A = Image.new("L", (W, H), 0); da = ImageDraw.Draw(A)         # amber light

    # A) light runs along both rails as the train passes
    head = win(t, 0.4, 2.6)
    lvl = 0.55 - 0.15 * win(t, 8.8, 10.0)
    comet(d, RAIL_L, head, lvl, 3)
    comet(d, RAIL_R, head, lvl, 3)

    # B) coordinates: small xyz at a rail point + distance counter
    b = bell(t, 2.4, 2.9, 4.5, 4.9)
    if b > 0:
        ox, oy = pat(RAIL_L, 0.42); v = int(230 * b)
        xa = pat(RAIL_L, 0.52); ya = (ox + 120, oy + 8); za = (ox, oy - 105)
        for (tx, ty), lab in [(xa, "x"), (ya, "y"), (za, "z")]:
            d.line([(ox, oy), (tx, ty)], fill=v, width=2)
            dt.text((tx + 8, ty - 20), lab, font=f_axis, fill=v)
        d.ellipse([ox - 6, oy - 6, ox + 6, oy + 6], fill=255 if b > 0.5 else v)
        r = 542.3 * win(t, 2.6, 4.2)
        lx, ly = ox + 150, oy - 150
        d.line([(ox + 8, oy - 8), (lx, ly + 26), (lx + 250, ly + 26)], fill=int(150 * b), width=2)
        dt.text((lx + 4, ly - 14), f"r = {r:5.1f} m", font=f_num, fill=v)

    # C) track-circuit boundaries light up one by one, then section TC-04
    bounds = [0.10, 0.30, 0.48, 0.63, 0.76, 0.87]
    cc = 1 - win(t, 11.0, 11.6)
    for i, u in enumerate(bounds):
        on = win(t, 4.6 + i * 0.16, 4.9 + i * 0.16) * cc
        if on <= 0: continue
        for rail in (RAIL_L, RAIL_R):
            x, y = pat(rail, u); r = (7 if u < 0.6 else 5) * (0.6 + 0.4 * on)
            d.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * on))
    hi = win(t, 5.6, 6.1) * cc
    if hi > 0:
        pulse = 0.75 + 0.25 * math.sin(t * 5)
        for rail in (RAIL_L, RAIL_R):
            d.line(ppart(rail, 0.48, 0.63), fill=int(255 * hi * pulse), width=6)
        lb = bell(t, 5.8, 6.2, 8.0, 8.4)
        if lb > 0:
            mx, my = pat(RAIL_R, 0.555)
            d.line([(mx, my - 10), (mx + 28, my - 80)], fill=int(170 * lb), width=2)
            dt.text((mx + 34, my - 116), "TC-04", font=f_lab, fill=int(240 * lb))

    # D) light runs down the catenary poles into the rail -> TCPS
    dd = win(t, 6.8, 7.8) * cc
    if dd > 0:
        for j, (top, bot) in enumerate(POLES):
            comet(d, [top, bot, pat(RAIL_L, 0.985 if j == 0 else 0.93)], dd, 0.5, 3)
            if dd >= 1:   # recurring pulses
                k = ((t - 7.8) * 0.9 + j * 0.4) % 1
                x, y = pat([top, bot], k)
                d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=255)
        tb = bell(t, 7.6, 8.0, 9.4, 9.8)
        if tb > 0:
            for rail in (RAIL_L,):
                d.line(ppart(rail, 0.0, 1.0), fill=int(110 * tb), width=5)
            x, y = pat(RAIL_L, 0.2)
            d.line([(x + 6, y - 6), (x + 40, y - 46)], fill=int(170 * tb), width=2)
            dt.text((x + 46, y - 84), "TCPS", font=f_lab, fill=int(240 * tb))

    # E) AI analysis label (amber)
    ai = bell(t, 9.6, 10.0, 10.8, 11.2)
    if ai > 0:
        da.line([(236, 300), (268, 270)], fill=int(200 * ai), width=2)
        da.text((276, 238), "AI ANALYSIS", font=f_lab, fill=int(240 * ai))

    out = add_light(base, L)
    out = add_light(out, T, k_core=1.0, k_glow=0.35)
    out = add_light(out, A, k_core=1.0, k_glow=0.5, color_core=np.array([1, .9, .75], np.float32), color_glow=AMBER)
    # bright scan line
    if 0 < scan < 1:
        sy = int(H * (1 - scan)); band = np.zeros((H, 1, 1), np.float32)
        for k in range(-24, 25):
            yy = sy + k
            if 0 <= yy < H: band[yy] = math.exp(-(k / 8) ** 2)
        out = out + band * GLOW * 0.9 + band * CORE * 0.3
    return np.clip(out, 0, 1)


def camera(img, t):
    """slow push-in + tilt toward the sky from 9.8 s on"""
    c = win(t, 9.8, DUR)
    if c <= 0: return img
    z = 1 + 0.14 * c
    cx = W / 2 + 40 * c
    cy = H / 2 - 120 * c
    w, h = W / z, H / z
    box = (cx - w / 2, max(0, cy - h / 2), cx + w / 2, max(0, cy - h / 2) + h)
    return img.resize((W, H), Image.BICUBIC, box=box)


def logo(img, t):
    pe = win(t, 10.4, 11.5)
    if pe <= 0: return img
    sw, sh = SYM_A.shape[1], SYM_A.shape[0]
    cx, cy = W // 2, 330
    # centre the whole lockup (symbol + gap + widest text line) horizontally
    _d = ImageDraw.Draw(Image.new("L", (1, 1)))
    word_w = _d.textlength("S-WELL", font=f_word) + 6
    tag_w = 6 + _d.textlength("TCPS ", font=f_tag_b) + _d.textlength("makes Rail AI possible.", font=f_tag)
    total = sw + 18 + max(word_w, tag_w)
    sx, sy = int(cx - total / 2), cy - sh // 2
    a = SYM_A.copy()
    a[..., 3] *= np.clip((pe * 1.15 - PROG) / 0.12, 0, 1)
    sym = Image.fromarray(a.astype(np.uint8), "RGBA")
    out = img.convert("RGBA")
    dim = Image.new("RGBA", (W, H), (0, 6, 20, int(60 * pe)))
    out = Image.alpha_composite(out, dim)
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gl.paste(sym, (sx, sy), sym)
    out = Image.alpha_composite(out, gl.filter(ImageFilter.GaussianBlur(16)))
    out.alpha_composite(sym, (sx, sy))
    wt = win(t, 11.3, 11.9)
    if wt > 0:
        tx, ty = sx + sw + 18, cy - 100
        wl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dw = ImageDraw.Draw(wl)
        dw.text((tx, ty), "S-WELL", font=f_word, fill=(245, 250, 255, 255))
        x = tx + 6; ly = ty + 142
        for s_, f_, c_ in [("TCPS ", f_tag_b, (130, 225, 255)), ("makes Rail AI possible.", f_tag, (225, 238, 250))]:
            dw.text((x, ly), s_, font=f_, fill=c_ + (255,)); x += dw.textlength(s_, font=f_)
        cut = int(tx - 10 + (x - tx + 40) * wt)
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle([0, 0, cut, H], fill=255)
        wl.putalpha(Image.composite(wl.split()[3], Image.new("L", (W, H), 0), m))
        glw = Image.new("RGBA", (W, H), (0, 0, 0, 0)); glw.paste((60, 200, 255, 160), (0, 0), wl.split()[3])
        out = Image.alpha_composite(out, glw.filter(ImageFilter.GaussianBlur(14)))
        out = Image.alpha_composite(out, wl)
    return out.convert("RGB")


def frame(t, bg):
    img = Image.fromarray((scene_frame(t, bg) * 255).astype(np.uint8))
    img = camera(img, t)
    img = logo(img, t)
    return np.asarray(img)


if __name__ == "__main__":
    n = int(round(DUR * FPS))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", PLATE, "-vf",
                            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
                            "tmp/v6_scene2.mp4"], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: buf = last
        last = buf
        enc.stdin.write(frame(i / FPS, np.frombuffer(buf, np.uint8).reshape(H, W, 3)).tobytes())
        if i % 48 == 0: print("frame", i, "/", n, flush=True)
    enc.stdin.close(); enc.wait(); dec.kill(); print("done")
