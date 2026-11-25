"""Frame-by-frame motion graphics over a locked-off plate (S-WELL hero, scene 2 + logo).

Input : clips/plate.mp4  (locked-off camera, train receding)  -- graphics stay glued to the ground
Output: tmp/v5_scene2.mp4 (1920x1080, 24 fps, silent)

Timeline (seconds within the scene):
  0.0-1.5  neon traces both rails from the foreground to the horizon; xyz marker + r counter (0 -> 542.3 m)
  1.5-3.0  track-circuit boundary dots along the rails, section highlight + "TC-04"
  3.0-4.4  data lines run down two catenary poles into the rail -> "TCPS"
  4.4-5.6  scan line sweeps bottom->top, scene turns into a neon digital twin; left pole amber + "AI ANALYSIS"
  5.6-7.8  neon S symbol draws itself in the sky, "S-WELL" + "TCPS makes Rail AI possible." appear
All text is rendered with Inter, so it stays crisp.
"""
import os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
W, H, FPS = 1920, 1080, 24
DUR = float(os.environ.get("DUR", "7.8"))
FD = "/usr/share/fonts/opentype/inter/"
NEON = (70, 175, 255)
CYAN = (120, 225, 255)
WHITE = (240, 248, 255)
AMBER = (255, 170, 60)

# ---- geometry measured on the plate (1920x1080) ----
RAIL_L = [(1160, 1080), (1100, 1020), (920, 930), (720, 830), (540, 730), (400, 630), (345, 570), (320, 515)]
RAIL_R = [(1920, 868), (1600, 797), (1300, 732), (1060, 682), (740, 606), (520, 552), (370, 512)]
POLES = [((222, 125), (222, 530)), ((305, 330), (305, 505))]
LOGO_CX, LOGO_CY = 1010, 300

f_lab = ImageFont.truetype(FD + "Inter-SemiBold.otf", 40)
f_lab_s = ImageFont.truetype(FD + "Inter-SemiBold.otf", 26)
f_axis = ImageFont.truetype(FD + "Inter-SemiBold.otf", 36)
f_word = ImageFont.truetype(FD + "InterDisplay-ExtraBoldItalic.otf", 118)
f_tag = ImageFont.truetype(FD + "Inter-Medium.otf", 38)
f_tag_b = ImageFont.truetype(FD + "Inter-SemiBold.otf", 38)

TWIN = np.asarray(Image.open("../stills_v8/twin_plate.png").convert("RGB").resize((W, H), Image.LANCZOS)).astype(np.float32)
_lum = TWIN.max(axis=2, keepdims=True)
_pole = np.zeros((H, W, 1), np.float32); _pole[0:545, 196:250] = 1
_amber = np.clip(_lum / 255.0, 0, 1) * np.array(AMBER, np.float32) * 1.25
TWIN = TWIN * (1 - _pole) + np.maximum(TWIN * 0.25, _amber) * _pole
_yy, _xx = np.mgrid[0:H, 0:W]
TRAIN_MASK = np.clip(1 - np.maximum(np.abs(_xx - 300) / 260.0, np.abs(_yy - 235) / 70.0), 0, 1)[..., None]
TRAIN_MASK = np.clip(TRAIN_MASK * 2.5, 0, 1)
SYM = Image.open("../stills_v8/symbol_rgba.png")
s = 300 / SYM.height
SYM = SYM.resize((int(SYM.width * s), 300), Image.LANCZOS)
# extra fade on the lower-left end of the symbol so the track dissolves naturally
_a = np.asarray(SYM).astype(float)
_h, _w = _a.shape[:2]
_yy, _xx = np.mgrid[0:_h, 0:_w]
_t = (_xx / _w) * 0.55 + ((_h - _yy) / _h) * 0.45
_f = np.clip((_t - 0.18) / 0.32, 0, 1); _f = _f * _f * (3 - 2 * _f)
_a[..., 3] *= _f
SYM = Image.fromarray(_a.astype(np.uint8), "RGBA")


def clamp01(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp01(x); return x * x * (3 - 2 * x)
def win(t, a, b): return ease((t - a) / (b - a))


def poly_len(pts):
    return [0] + list(np.cumsum([math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]))


def poly_at(pts, u):
    L = poly_len(pts); d = u * L[-1]
    for i in range(len(pts) - 1):
        if d <= L[i + 1]:
            k = (d - L[i]) / max(1e-6, L[i + 1] - L[i])
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * k, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * k)
    return pts[-1]


def poly_part(pts, u0, u1, n=60):
    return [poly_at(pts, u0 + (u1 - u0) * i / n) for i in range(n + 1)]


def glow_line(d, pts, col, w):
    d.line(pts, fill=col + (255,), width=w, joint="curve")


def sobel_edges(rgb):
    # smooth first so only structural edges survive (no ballast noise)
    small = Image.fromarray(rgb).resize((W // 2, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.2))
    g = np.asarray(small).astype(np.float32).mean(axis=2)
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    m = np.sqrt(gx * gx + gy * gy)
    e = np.clip((m - 8) / 22, 0, 1)
    e = np.asarray(Image.fromarray((e * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
    return e


def frame(t, bg):
    """bg: HxWx3 uint8 plate frame -> composited uint8 frame"""
    base = bg.astype(np.float32)
    # ---------- digital twin (phase D onward): reveal the AI twin plate behind a scan line ----------
    scan = win(t, 4.4, 5.4)
    if scan > 0:
        sy = int(H * (1 - scan))
        twin = TWIN.copy()
        # keep the receding train alive: blend the live plate inside a soft box around its path
        twin = twin * (1 - TRAIN_MASK) + (base * 0.55 + twin * 0.45) * TRAIN_MASK
        mask = np.zeros((H, 1, 1), np.float32); mask[sy:] = 1
        base = base * (1 - mask) + twin * mask
        # bright scan line
        if scan < 1:
            y0 = max(0, sy - 3); y1 = min(H, sy + 3)
            base[y0:y1] = base[y0:y1] * 0.3 + np.array(CYAN, np.float32) * 0.9
    out = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")

    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    txt = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dt = ImageDraw.Draw(txt)

    # ---------- phase A: rails + xyz + r counter ----------
    pa = win(t, 0.0, 1.0)
    if pa > 0:
        glow_line(d, poly_part(RAIL_L, 0, pa), NEON, 7)
        glow_line(d, poly_part(RAIL_R, 0, pa), NEON, 7)
    ax_on = win(t, 0.35, 0.7) * (1 - win(t, 1.45, 1.65))
    if ax_on > 0:
        ox, oy = poly_at(RAIL_L, 0.42)
        a = int(255 * ax_on)
        tip_x = poly_at(RAIL_L, 0.60); tip_y = poly_at(RAIL_R, 0.30)
        for (tx, ty), lab in [(tip_x, "x"), ((ox, oy - 120), "z"), ((tip_y[0] * 0.25 + ox * 0.75 + 80, oy - 15), "y")]:
            d.line([(ox, oy), (tx, ty)], fill=WHITE + (a,), width=5)
            dt.text((tx + 10, ty - 22), lab, font=f_axis, fill=WHITE + (a,))
        d.ellipse([ox - 8, oy - 8, ox + 8, oy + 8], fill=WHITE + (a,))
        r = 542.3 * win(t, 0.35, 1.3)
        lx, ly = 1180, 690
        d.line([(ox + 30, oy - 30), (lx - 20, ly + 20), (lx + 300, ly + 20)], fill=CYAN + (a,), width=3)
        dt.text((lx, ly - 30), f"r = {r:6.1f} m", font=f_lab, fill=WHITE + (a,))

    # ---------- phase B: track-circuit boundaries + TC-04 ----------
    pb = win(t, 1.5, 2.2)
    if pb > 0:
        bounds = [0.10, 0.30, 0.48, 0.63, 0.76, 0.87]
        for i, u in enumerate(bounds):
            if pb < (i + 1) / len(bounds) * 0.999 and pb < 1:
                if pb < i / len(bounds): continue
            for rail in (RAIL_L, RAIL_R):
                x, y = poly_at(rail, u)
                rr = 7 if u < 0.6 else 5
                d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, 255))
        hi = win(t, 2.0, 2.4)
        if hi > 0:
            glow_line(d, poly_part(RAIL_L, 0.48, 0.63), CYAN, 12)
            glow_line(d, poly_part(RAIL_R, 0.48, 0.63), CYAN, 12)
            mx, my = poly_at(RAIL_R, 0.55)
            a = int(255 * hi * (1 - win(t, 4.3, 4.5)))
            d.line([(mx, my), (mx + 40, my - 90)], fill=CYAN + (a,), width=3)
            bx, by = mx + 40, my - 140
            dt.rounded_rectangle([bx - 4, by - 4, bx + 130, by + 46], radius=8, fill=(10, 30, 60, int(a * 0.8)),
                                 outline=CYAN + (a,), width=2)
            dt.text((bx + 14, by + 4), "TC-04", font=f_lab_s, fill=WHITE + (a,))

    # ---------- phase C: data lines down the poles -> TCPS ----------
    pc = win(t, 3.0, 3.8)
    if pc > 0:
        for (top, bot) in POLES:
            yb = top[1] + (bot[1] - top[1]) * pc
            d.line([top, (bot[0], yb)], fill=NEON + (255,), width=4)
            if pc >= 1:
                jx, jy = poly_at(RAIL_L, 0.92 if bot[0] > 260 else 0.97)
                d.line([bot, (jx, jy)], fill=NEON + (255,), width=4)
            # travelling pulse
            k = (t * 1.6) % 1
            py = top[1] + (bot[1] - top[1]) * k * pc
            d.ellipse([top[0] - 7, py - 7, top[0] + 7, py + 7], fill=(255, 255, 255, 255))
        ta = win(t, 3.5, 3.9) * (1 - win(t, 5.5, 5.7))
        if ta > 0:
            glow_line(d, poly_part(RAIL_L, 0, 1), CYAN, 9)
            x, y = poly_at(RAIL_L, 0.2)
            a = int(255 * ta)
            dt.rounded_rectangle([x + 40, y - 70, x + 175, y - 24], radius=8, fill=(10, 30, 60, int(a * 0.8)),
                                 outline=CYAN + (a,), width=2)
            dt.text((x + 56, y - 66), "TCPS", font=f_lab_s, fill=WHITE + (a,))
            d.line([(x, y), (x + 40, y - 47)], fill=CYAN + (a,), width=3)

    # ---------- phase D label ----------
    ai = win(t, 5.0, 5.3) * (1 - win(t, 5.9, 6.1))
    if ai > 0:
        a = int(255 * ai)
        dt.rounded_rectangle([262, 250, 470, 296], radius=8, fill=(40, 20, 0, int(a * 0.7)), outline=AMBER + (a,), width=2)
        dt.text((276, 254), "AI ANALYSIS", font=f_lab_s, fill=(255, 235, 210, a))
        d.line([(232, 300), (262, 273)], fill=AMBER + (a,), width=3)

    # glow for line layer
    g1 = lay.filter(ImageFilter.GaussianBlur(12)); g2 = lay.filter(ImageFilter.GaussianBlur(4))
    out = Image.alpha_composite(out, g1); out = Image.alpha_composite(out, g1); out = Image.alpha_composite(out, g2); out = Image.alpha_composite(out, lay)

    # ---------- phase E: logo in the sky of the same shot ----------
    pe = win(t, 5.6, 6.4)
    if pe > 0:
        sw, sh = SYM.size
        sx = LOGO_CX - 330 - sw // 2; sy_ = LOGO_CY - sh // 2
        # reveal along the stroke: from the faded rail end (lower-left) toward the swoosh tip (upper-right)
        m = np.zeros((sh, sw), np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        prog = (xx / sw) * 0.55 + ((sh - yy) / sh) * 0.45
        m = np.clip((pe * 1.15 - prog) / 0.12, 0, 1)
        sa = np.asarray(SYM).astype(np.float32)
        sa[..., 3] *= m
        sym = Image.fromarray(sa.astype(np.uint8), "RGBA")
        dim = Image.new("RGBA", (W, H), (0, 8, 24, int(70 * pe)))     # slight sky dim behind the logo
        out = Image.alpha_composite(out, dim)
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gl.paste(sym, (sx, sy_), sym)
        out = Image.alpha_composite(out, gl.filter(ImageFilter.GaussianBlur(14)))
        out.alpha_composite(sym, (sx, sy_))
        wt = win(t, 6.2, 6.6)
        if wt > 0:
            tx = sx + sw + 20; ty = LOGO_CY - 105
            wl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dw = ImageDraw.Draw(wl)
            dw.text((tx, ty), "S-WELL", font=f_word, fill=WHITE + (255,))
            x = tx + 6; ly2 = ty + 150
            for tt, ff, cc in [("TCPS ", f_tag_b, (120, 200, 255)), ("makes Rail AI possible.", f_tag, (225, 235, 248))]:
                dw.text((x, ly2), tt, font=ff, fill=cc + (255,)); x += dw.textlength(tt, font=ff)
            # left-to-right wipe reveal (no fade)
            cut = int(tx - 10 + (x - tx + 40) * wt)
            mask = Image.new("L", (W, H), 0); ImageDraw.Draw(mask).rectangle([0, 0, cut, H], fill=255)
            wl.putalpha(Image.composite(wl.split()[3], Image.new("L", (W, H), 0), mask))
            glw = Image.new("RGBA", (W, H), (0, 0, 0, 0)); glw.paste((90, 170, 255, 255), (0, 0), wl.split()[3])
            out = Image.alpha_composite(out, glw.filter(ImageFilter.GaussianBlur(12)).point(lambda v: v) )
            out = Image.alpha_composite(out, wl)

    out = Image.alpha_composite(out, txt)
    return np.asarray(out.convert("RGB"))


if __name__ == "__main__":
    n = int(round(DUR * FPS))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", "clips/plate.mp4", "-t", str(DUR), "-vf",
                            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
                            "tmp/v5_scene2.mp4"], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            buf = last           # hold last plate frame if the clip is shorter
        last = buf
        bg = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
        enc.stdin.write(frame(i / FPS, bg).tobytes())
        if i % 24 == 0: print("frame", i, flush=True)
    enc.stdin.close(); enc.wait(); dec.kill()
    print("done")
