"""S-WELL hero v7 - scene 2 with a rich light-dot coordinate lattice + floating data network
(look of the early storyboard plates), digital twin, camera move, centred logo. No fades: every
element is *drawn on* (grows / lights up), never cross-dissolved.

Reuses look/assets from composite_v6 (cyan additive light, twin plate, symbol, fonts).
Output: tmp/v7_scene2.mp4
"""
import os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import composite_v6 as v6

W, H, FPS = v6.W, v6.H, v6.FPS
DUR = float(os.environ.get("DUR", "11.0"))
PLATE = os.environ.get("PLATE", "clips/plate12.mp4")
L_, R_ = v6.RAIL_L, v6.RAIL_R
pat, win, cl = v6.pat, v6.win, v6.cl

T_TWIN0, T_TWIN1 = 6.4, 7.4       # scan
T_CAM0 = 7.2                      # camera push/tilt starts
T_SYM0, T_SYM1 = 7.8, 8.9         # symbol draws on
T_TXT0, T_TXT1 = 8.7, 9.3         # wordmark wipe

# depth samples: compress toward the horizon like real sleepers
US = [1 - 0.88 ** k for k in range(1, 34)]


def gp(u, s):
    """ground point at depth u, lateral s (0 = left rail, 1 = right rail)"""
    a, b = pat(L_, u), pat(R_, u)
    return (a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s)


def gauge(u):
    a, b = pat(L_, u), pat(R_, u)
    return math.dist(a, b)


LANES = [-0.9, 0.0, 1.0, 1.9, 2.8]

# floating network nodes: rows above the track at a few depths
rng = np.random.default_rng(7)
NODES = []
for i, u in enumerate([0.18, 0.30, 0.42, 0.53, 0.63, 0.72, 0.80, 0.87]):
    g = gauge(u)
    for s, hgt in [(-0.6, 0.55), (0.5, 0.95), (1.6, 0.6), (2.6, 0.85)]:
        x, y = gp(u, s + rng.uniform(-0.15, 0.15))
        NODES.append((x, y - min(g * hgt, 230) * rng.uniform(0.8, 1.15), u))
NODES += [(222, 125, 0.95), (305, 330, 0.97)]               # pole tops join the web
EDGES = []
pts = np.array([(n[0], n[1]) for n in NODES])
for i in range(len(NODES)):
    d = np.hypot(*(pts - pts[i]).T)
    for j in np.argsort(d)[1:4]:
        if (j, i) not in EDGES and d[j] < 520:
            EDGES.append((i, int(j)))
# drop lines from each node to the rail lattice
DROPS = [(i, gp(NODES[i][2], round(min(max((pts[i][0] - pat(L_, NODES[i][2])[0]) /
          max(1, pat(R_, NODES[i][2])[0] - pat(L_, NODES[i][2])[0]), 0), 1)))) for i in range(len(NODES) - 2)]


def dot(d, x, y, r, v):
    d.ellipse([x - r, y - r, x + r, y + r], fill=int(255 * cl(v)))


def scene(t, bg):
    base = bg.astype(np.float32) / 255
    scan = win(t, T_TWIN0, T_TWIN1)
    if scan > 0:
        sy = int(H * (1 - scan))
        m = np.zeros((H, 1, 1), np.float32); m[sy:] = 1
        base = base * (1 - m) + v6.TWIN * m

    Lc = Image.new("L", (W, H), 0); d = ImageDraw.Draw(Lc)
    Tx = Image.new("L", (W, H), 0); dt = ImageDraw.Draw(Tx)

    # 1) coordinate lattice: dots wave outward with the train, ladder rungs, side lanes
    wave = win(t, 0.2, 2.6) * 1.15
    for k, u in enumerate(US):
        on = cl((wave - u) / 0.08 + 1) if wave > 0 else 0
        if on <= 0: continue
        g = gauge(u)
        r = max(1.6, g / 95)
        for s in LANES:
            if s not in (0.0, 1.0):
                if t < 1.6 + abs(s) * 0.25: continue
            lv = on * (1.0 if s in (0.0, 1.0) else 0.65)
            x, y = gp(u, s); dot(d, x, y, r, lv)
        if k % 2 == 0 and t > 1.0:                                   # rungs = coordinate grid
            grow = win(t, 1.0 + u * 1.2, 1.5 + u * 1.2)
            a, b = gp(u, -0.9), gp(u, -0.9 + 3.7 * grow)
            d.line([a, b], fill=int(70 * on), width=max(1, int(r * 0.5)))
    # rails + lanes as faint continuous light
    for s in LANES:
        rail = (s in (0.0, 1.0))
        reach = cl(wave) if rail else win(t, 1.6 + abs(s) * 0.25, 3.0 + abs(s) * 0.25)
        if reach <= 0: continue
        seg = [gp(u, s) for u in np.linspace(0, reach * 0.98, 60)]
        d.line(seg, fill=110 if rail else 55, width=3 if rail else 2)

    # 2) track-circuit section: dots between two boundaries pulse brighter
    tc = win(t, 2.6, 3.0) * (1 - win(t, T_TWIN0 + 0.4, T_TWIN0 + 0.8))
    if tc > 0:
        pulse = 0.75 + 0.25 * math.sin(t * 6)
        for u in US:
            if 0.45 < u < 0.62:
                for s in (0.0, 1.0):
                    x, y = gp(u, s); dot(d, x, y, max(3, gauge(u) / 55), tc * pulse)
        mx, my = gp(0.535, 1.0)
        d.line([(mx, my - 6), (mx + 26, my - 70)], fill=int(170 * tc), width=2)
        dt.text((mx + 32, my - 104), "TC-04", font=v6.f_lab, fill=int(235 * tc))

    # 3) floating data network: nodes rise from the rails, edges draw on, pulses flow
    nt = t - 3.0
    if nt > 0:
        for i, (x, y, u) in enumerate(NODES):
            ap = cl((nt - u * 1.6) / 0.35)
            if ap <= 0: continue
            gx, gy = (x, y) if i >= len(NODES) - 2 else DROPS[i][1]
            cx, cy = gx + (x - gx) * v6.ease(ap), gy + (y - gy) * v6.ease(ap)
            if i < len(NODES) - 2:
                d.line([DROPS[i][1], (cx, cy)], fill=int(60 * ap), width=1)
            dot(d, cx, cy, max(3, 9 - u * 6), ap)
        for (i, j) in EDGES:
            ui, uj = NODES[i][2], NODES[j][2]
            g = cl((nt - max(ui, uj) * 1.6 - 0.35) / 0.4)
            if g <= 0: continue
            a, b = NODES[i][:2], NODES[j][:2]
            e = (a[0] + (b[0] - a[0]) * g, a[1] + (b[1] - a[1]) * g)
            d.line([a, e], fill=150, width=2)
            if g >= 1:
                k = ((t * 0.8) + (i * 0.37)) % 1
                px, py = a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k
                dot(d, px, py, 3, 0.9)
        lb = win(t, 4.6, 5.0) * (1 - win(t, T_TWIN0, T_TWIN0 + 0.3))
        if lb > 0:
            x, y = NODES[13][:2]
            d.line([(x + 6, y - 6), (x + 36, y - 40)], fill=int(170 * lb), width=2)
            dt.text((x + 42, y - 78), "TCPS", font=v6.f_lab, fill=int(235 * lb))

    calm = 1 - 0.55 * win(t, T_SYM0 - 0.4, T_SYM1)        # graphics settle back while the logo draws
    if calm < 1:
        Lc = Lc.point(lambda v: int(v * calm))
    out = v6.add_light(base, Lc)
    out = v6.add_light(out, Tx, k_core=1.0, k_glow=0.35)
    if 0 < scan < 1:
        sy = int(H * (1 - scan)); band = np.zeros((H, 1, 1), np.float32)
        for k in range(-24, 25):
            if 0 <= sy + k < H: band[sy + k] = math.exp(-(k / 8) ** 2)
        out = out + band * v6.GLOW * 0.9 + band * v6.CORE * 0.3
    return np.clip(out, 0, 1)


def camera(img, t):
    c = win(t, T_CAM0, DUR)
    if c <= 0: return img
    z = 1 + 0.16 * c; cx = W / 2 + 40 * c; cy = H / 2 - 130 * c
    w, h = W / z, H / z
    y0 = max(0, cy - h / 2)
    return img.resize((W, H), Image.BICUBIC, box=(cx - w / 2, y0, cx + w / 2, y0 + h))


def logo(img, t):
    # same lockup as v6 (centred), retimed
    s = t + (10.4 - T_SYM0)
    return v6.logo(img, s)


def frame(t, bg):
    img = Image.fromarray((scene(t, bg) * 255).astype(np.uint8))
    return np.asarray(logo(camera(img, t), t))


if __name__ == "__main__":
    n = int(round(DUR * FPS))
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", PLATE, "-vf",
                            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p",
                            "tmp/v7_scene2.mp4"], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        buf = dec.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: buf = last
        last = buf
        enc.stdin.write(frame(i / FPS, np.frombuffer(buf, np.uint8).reshape(H, W, 3)).tobytes())
        if i % 48 == 0: print("frame", i, "/", n, flush=True)
    enc.stdin.close(); enc.wait(); dec.kill(); print("done")
