"""Segment 00:01:40:22-00:01:49:01 (196 frames) - "업무와 데이터가 연결될수록 / AI는 더 빠르게 이해하고 더 정확하게
판단합니다" - after the client's reference (a logo button is clicked, a wireframe sphere opens round it, partner
marks fly out and orbit it in depth), with the film's own content.
  0.00  seg_exec2's last frame (the factory, the switch in the centre)
  0.20  the AXCORE logo comes in over it on a glass button (fade + scale up); the switch fades, the shot sinks back
  0.85  the cursor glides in and clicks the logo (1.55)
  1.60  the wireframe sphere opens round the logo, which fades away, and the background fades into the navy space
  3.10  the core flares, the network spreads out, and the connected systems and SaaS (the connect scene's items)
        burst out of the centre and orbit it in depth, in various sizes; slow push in
  7.20  the camera rushes into the core, white flood; from the flash peak the frames are seg_ai's (FIN under the
        white), so the next file carries on
Local clock s = film time - 100.917 (01:40:22); the old seg_ai passage sat 2 s earlier. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_sphere.py <out.mp4> [height=480] [first last]
"""
import math
import os
import subprocess
import sys

import numpy as np
import skia

import engine as E
import seg_axpoint as A
import seg_ai as AI
import seg_exec as X
import seg_exec2 as Q
import seg_ops as O
import seg_ops2 as P
from engine import (W, H, R, WHITE, CYAN, lerp, prog, clamp, e_io_cubic, e_io_sine, e_out_cubic, e_in_cubic,
                    paint_fill, paint_stroke, text, text_w, colint)

TL0, TL1 = 100 * 24 + 22, 109 * 24 + 1          # timeline 01:40:22 .. 01:49:01
NF = TL1 - TL0 + 1
T0 = TL0 / 24.0
SHIFT = 2.0
PEAK = AI.FLASH_PEAK + SHIFT                     # seg_ai's flash peak, moved with it
LOGO0, LOGO_D = 0.20, 0.70
CUR0, CLICK = 0.85, 1.55
SPH0, SPH_D = 1.60, 0.80
BG0, BG_D = 1.60, 0.70
BURST = 3.10
RUSH0 = 7.20
FAC_RATE = 0.55                                  # the factory clip runs on a little slower so it never stops (freezes)
CX, CY = W / 2, H / 2 - 10
FOC, DIST = 1400.0, 1400.0
RS = 250.0
SCV = 1.0


# ---------------------------------------------------------------- geometry
def geodesic():
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
         (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    mid = {}

    def m(a, b):
        k = (min(a, b), max(a, b))
        if k not in mid:
            p = v[a] + v[b]
            v.append(p / np.linalg.norm(p))
            mid[k] = len(v) - 1
        return mid[k]
    edges = set()
    for a, b, c in f:
        ab, bc, ca = m(a, b), m(b, c), m(c, a)
        for x, y in ((a, ab), (ab, b), (b, bc), (bc, c), (c, ca), (ca, a), (ab, bc), (bc, ca), (ca, ab)):
            edges.add((min(x, y), max(x, y)))
    return np.array(v), sorted(edges)


SV, SE = geodesic()
_rng = np.random.default_rng(1406)
NET = []                                          # the spreading network: points in a shell round the sphere
while len(NET) < 64:
    d = _rng.normal(size=3)
    d /= np.linalg.norm(d)
    NET.append(d * _rng.uniform(430, 1800) * np.array([1.0, 0.55, 1.0]))
NET = np.array(NET)
NET_E = set()
for i, p in enumerate(NET):
    dd = np.linalg.norm(NET - p, axis=1)
    for j in np.argsort(dd)[1:3]:
        NET_E.add((min(i, j), max(i, j)))
    if np.linalg.norm(p) < 900:
        k = int(np.argmin(np.linalg.norm(SV * RS - p, axis=1)))
        NET_E.add((i, -1 - k))                    # joined to the sphere
NET_E = sorted(NET_E)


def rot(p, s, k=1.0):
    a = 0.30 * s * k + 0.6
    ca, sa = math.cos(a), math.sin(a)
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    x, z = x * ca + z * sa, -x * sa + z * ca
    b = 0.22
    cb, sb = math.cos(b), math.sin(b)
    y, z = y * cb - z * sb, y * sb + z * cb
    return np.stack([x, y, z], -1)


def zoom(s):
    push = 1.0 + 0.14 * e_io_sine(prog(s, SPH0, RUSH0 - SPH0))
    return push * (1.0 + 7.0 * e_in_cubic(prog(s, RUSH0, PEAK - T0 - RUSH0)))


def project(p, s):
    """World -> screen (x, y, scale); the camera pushes in by scaling about the centre."""
    z = zoom(s)
    d = p[..., 2] + DIST
    k = FOC / np.maximum(d, 60.0) * z
    return CX + p[..., 0] * k, CY + p[..., 1] * k, k


# ---------------------------------------------------------------- the items (the connect scene's systems and SaaS)
SAAS = {"Gmail": "gmail", "Slack": "slack", "Notion": "notion", "Microsoft Teams": "teams", "Google Drive": "gdrive"}
ITEMS = [("SAP", 66), ("Oracle", 60), ("Microsoft Dynamics", 46), ("Workday", 54), ("Slack", 54), ("Notion", 50),
         ("더존", 50), ("Siemens Teamcenter", 38), ("Gmail", 44), ("Microsoft Teams", 42), ("Google Drive", 42),
         ("flex", 46), ("네이버웍스", 40), ("영림원", 36), ("하이웍스", 34), ("3DEXPERIENCE", 34)]
_r2 = np.random.default_rng(77)
ORB = []
ROWS = np.linspace(-470, 470, 9)                  # height rows, so the marks keep clear of each other
order = sorted(range(len(ITEMS)), key=lambda i: -ITEMS[i][1])
per_row = {}
for n, i in enumerate(order):
    row = (n * 4) % len(ROWS)                     # big ones spread over the rows first
    per_row.setdefault(row, []).append(i)
for row, idx in per_row.items():
    off = _r2.uniform(0, 2 * math.pi)
    for j, i in enumerate(idx):
        name, size = ITEMS[i]
        big = size >= 44
        ORB.append(dict(name=name, size=size * 1.35, r=_r2.uniform(620, 900) if big else _r2.uniform(700, 1100),
                        y=ROWS[row] + _r2.uniform(-20, 20), ph=off + 2 * math.pi * j / len(idx),
                        w=1.0, t0=BURST + 0.05 + _r2.uniform(0, 0.5), weight="ExtraBold" if big else "Bold"))
_LOGOS = {}


def saas_mark(c, name, x, y, s, a):
    if name not in _LOGOS:
        _LOGOS[name] = skia.Image.open(os.path.join(E.HERE, "assets", "logos", SAAS[name] + ".png"))
    img = _LOGOS[name]
    k = s * 0.78 / max(img.width(), img.height())
    w, h = img.width() * k, img.height() * k
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    c.drawImageRect(img, R(x - w / 2, y - h / 2, w, h), skia.SamplingOptions(skia.CubicResampler.Mitchell()), p)


def glow_text(c, s_, x, y, size, w, align):
    """White text with a soft blue-white glow round it (the marks light up the space)."""
    f = E.font(size, w)
    tw = f.measureText(s_)
    x0 = x - tw / 2 if align == "center" else x
    for col, bl, al in (("#6FB8FF", size * 0.45, 0.55), ("#FFFFFF", size * 0.12, 0.55)):
        p = skia.Paint(AntiAlias=True, Color4f=E.col(col, al))
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, bl))
        c.drawString(s_, x0, y, f, p)
    c.drawString(s_, x0, y, f, skia.Paint(AntiAlias=True, Color4f=E.col("#FFFFFF", 1.0)))


def item_pos(o, s):
    b = e_out_cubic(prog(s, o["t0"], 1.1))
    a = o["ph"] + 0.65 * o["w"] * (s - BURST)
    p = np.array([o["r"] * math.cos(a), o["y"], o["r"] * math.sin(a)]) * b
    return rot(p, 0.0, 0.0), b


def draw_items(c, s, front):
    if s < BURST:
        return
    rows = []
    for o in ORB:
        p, b = item_pos(o, s)
        if b <= 0:
            continue
        if (p[2] < 0) != front:
            continue
        x, y, k = project(p, s)
        rows.append((p[2], o, x, y, k, b))
    for z, o, x, y, k, b in sorted(rows, key=lambda r_: -r_[0]):
        sz = o["size"] * k
        if sz < 6 or sz > 900:
            continue
        a = clamp(b * 1.6) * (0.85 if z > 0 else 1.0) * clamp((1.6 - k) / 0.3 + 1) if k < 3 else 0.0
        if a <= 0.01:
            continue
        bl = 1.5 * clamp((0.75 - k) / 0.35) + 6 * clamp((k - 1.5) / 0.8) + 4 * (1 - clamp(b * 1.5))
        A.blur_layer(c, bl, a)
        name = o["name"]
        if name in SAAS:
            tw = text_w(name, sz, "Bold")
            x0 = x - (tw + sz * 1.5) / 2
            glow_text(c, name, x0 + sz * 1.5, y, sz, "Bold", "left")
            saas_mark(c, name, x0 + sz * 0.6, y - sz * 0.33, sz * 1.15, 1.0)
        else:
            glow_text(c, name, x, y, sz, o["weight"], "center")
        c.restore()


# ---------------------------------------------------------------- the scene
def space(c, s):
    c.drawRect(R(0, 0, W, H), paint_fill("#0A1A3C"))
    E.radial(c, CX, CY, 1150, "#1F4C9E", 0.62, blend=skia.BlendMode.kSrcOver)
    E.radial(c, CX, CY + 380, 900, "#14336E", 0.35, blend=skia.BlendMode.kSrcOver)
    sh = skia.GradientShader.MakeRadial(skia.Point(CX, CY), 1250, [colint("#020814", 0.0), colint("#020814", 0.55)],
                                        [0.45, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))


TRIS = []                                         # membranes: faint films between neighbouring nodes
for i, p in enumerate(NET):
    nb = np.argsort(np.linalg.norm(NET - p, axis=1))[1:3]
    t_ = tuple(sorted((i, int(nb[0]), int(nb[1]))))
    if t_ not in TRIS:
        TRIS.append(t_)


def network(c, s):
    g = prog(s, BURST - 0.1, 1.6)
    if g <= 0:
        return
    pts = rot(NET, s, 0.5)
    sp = rot(SV * RS, s)
    x, y, k = project(pts, s)
    sx, sy, sk = project(sp, s)
    qn = [clamp((g * 2000 - np.linalg.norm(NET[i]) * 0.8) / 400) for i in range(len(NET))]
    for (i, j, l) in TRIS:
        q = min(qn[i], qn[j], qn[l])
        if q <= 0 or max(k[i], k[j], k[l]) > 3:
            continue
        pth = E.poly([(x[i], y[i]), (x[j], y[j]), (x[l], y[l])], True)
        sh = skia.GradientShader.MakeLinear([skia.Point(x[i], y[i]), skia.Point((x[j] + x[l]) / 2, (y[j] + y[l]) / 2)],
                                            [colint("#6B98FF", 0.26 * q), colint("#2A4FB0", 0.05 * q)])
        c.drawPath(pth, skia.Paint(AntiAlias=True, Shader=sh))
    for i, j in NET_E:
        pa = (x[i], y[i])
        pb = (x[j], y[j]) if j >= 0 else (sx[-1 - j], sy[-1 - j])
        q = qn[i]
        if q <= 0 or k[i] > 3:
            continue
        kk = clamp(min(k[i], 2.2))
        xb, yb = lerp(pa[0], pb[0], q), lerp(pa[1], pb[1], q)
        c.drawLine(pa[0], pa[1], xb, yb, paint_stroke("#4F86FF", 0.35 * q * kk, 4.0, blur=4,
                                                      blend=skia.BlendMode.kScreen))
        c.drawLine(pa[0], pa[1], xb, yb, paint_stroke("#8CB6FF", 0.55 * q * kk, 1.2))
    for i in range(len(NET)):
        q = qn[i]
        if q <= 0 or k[i] > 3:
            continue
        c.drawCircle(x[i], y[i], 12 * k[i], paint_fill("#4FA8FF", 0.25 * q, blur=6))
        c.drawCircle(x[i], y[i], 7 * k[i], paint_stroke("#8FD0FF", 0.8 * q, 1.4))
        c.drawCircle(x[i], y[i], 2.4 * k[i], paint_fill("#DFF2FF", 0.95 * q))


def sphere(c, s):
    q = prog(s, SPH0, SPH_D)
    g = e_io_sine(clamp(q * 3))
    if g <= 0.003:
        return
    sc = 0.30 + 0.70 * (1 + 2.2 * (q - 1) ** 3 + 1.2 * (q - 1) ** 2) if q < 1 else 1.0   # overshoot (back-out)
    hot = math.exp(-max(0.0, s - SPH0) * 2.6)          # it arrives glowing, then calms
    p = rot(SV * RS * sc, s)
    x, y, k = project(p, s)
    zf = (p[:, 2] / RS + 1) / 2                     # 0 front .. 1 back
    A.blur_layer(c, 0, g)
    if hot > 0.02:
        E.radial(c, CX, CY, RS * sc * 1.5 * zoom(s), "#3CC8FF", 0.45 * hot, blend=skia.BlendMode.kScreen)
    for a_, b_ in SE:
        fr = 1 - (zf[a_] + zf[b_]) / 2
        if hot > 0.02:
            c.drawLine(x[a_], y[a_], x[b_], y[b_], paint_stroke("#7FE8FF", 0.6 * hot * fr, 5, blur=4,
                                                                 blend=skia.BlendMode.kScreen))
        c.drawLine(x[a_], y[a_], x[b_], y[b_], paint_stroke(A.colint_mix("#38B8FF", "#BDF4FF", hot),
                                                             0.25 + 0.5 * fr, 1.3 + 0.5 * fr))
    for i in range(len(SV)):
        fr = 1 - zf[i]
        r = (2.4 + 2.2 * fr) * k[i] / (FOC / DIST)
        c.drawCircle(x[i], y[i], r * 2.4, paint_fill("#3CC8FF", 0.18 * fr, blur=4))
        c.drawCircle(x[i], y[i], r, paint_fill("#8FE3FF", 0.45 + 0.55 * fr))
    c.restore()


def core(c, s):
    kb = e_io_sine(prog(s, BURST - 0.15, 0.8))
    kr = e_in_cubic(prog(s, RUSH0, PEAK - T0 - RUSH0))
    if kb <= 0:
        return
    z = zoom(s)
    E.radial(c, CX, CY, (300 + 900 * kr) * min(z, 3), "#FF8A3D", 0.42 * kb * (1 - 0.4 * kr), blend=skia.BlendMode.kScreen)
    E.radial(c, CX, CY, (130 + 1400 * kr) * min(z, 3), "#FFD9AE", (0.55 + 0.45 * kr) * kb, blend=skia.BlendMode.kScreen)


_LOGO_IMG = {}


def logo_images():
    """The AXCORE logo (light, for the dark) as one image, and a mosaic (pixelated) copy of it."""
    if not _LOGO_IMG:
        import cv2
        L = E.logo()
        w = 500
        h = int(round(L.h * w / L.w))
        sf = skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType,
                                                         skia.AlphaType.kPremul_AlphaType))
        cc = sf.getCanvas()
        cc.clear(skia.Color4f(0, 0, 0, 0))
        L.draw(cc, w / 2, h / 2, w, 1.0, 1.0, (1.0, 1.0, 1.0), True, 1.0)
        img = sf.makeImageSnapshot()
        a = img.toarray()
        n = 16                                    # bright pixel blocks wherever the logo has ink (reference)
        gh, gw = max(1, h // n), max(1, w // n)
        cov = cv2.resize((a[..., 3] > 20).astype(np.float32), (gw, gh), interpolation=cv2.INTER_AREA)
        rr = np.random.default_rng(5)
        blk = np.zeros((gh, gw, 4), np.float32)
        on = cov > 0.08
        lum = rr.uniform(0.55, 1.0, (gh, gw))
        for ch, v in enumerate((205, 225, 250)):
            blk[..., ch] = v * lum
        blk[..., 3] = 255 * np.clip(cov * 2.2, 0, 1) * on
        blk[..., :3] *= blk[..., 3:4] / 255.0         # premultiplied
        mos = cv2.resize(blk, (w, h), interpolation=cv2.INTER_NEAREST).astype(np.uint8)
        _LOGO_IMG["img"] = img
        _LOGO_IMG["mos"] = skia.Image.fromarray(np.ascontiguousarray(mos), colorType=skia.ColorType.kRGBA_8888_ColorType)
        _LOGO_IMG["w"], _LOGO_IMG["h"] = w, h
    return _LOGO_IMG


def logo_button(c, s, on_sphere):
    """Reference entrance: a thin outline box comes in, then the logo fills it with a mosaic wipe (left to right)
    while the box turns to glass; clicked, it presses and gives way to the sphere."""
    k = e_out_cubic(prog(s, LOGO0, 0.45))
    a = e_io_sine(prog(s, LOGO0, 0.35)) * (1 - e_io_sine(prog(s, CLICK + 0.10, 0.55)))
    if a <= 0.003:
        return
    press = math.sin(math.pi * clamp(prog(s, CLICK, 0.22)))
    sc = lerp(0.92, 1.0, k) * (1 - 0.05 * press) * zoom(s)
    bw, bh = 360, 96
    c.save()
    c.translate(CX, CY)
    c.scale(sc, sc)
    A.blur_layer(c, 0, a)
    r = R(-bw / 2, -bh / 2, bw, bh)
    fill = e_io_sine(prog(s, LOGO0 + 0.30, 0.45))
    if fill > 0:
        E.glass(c, r, 10, fill, tint="#0A1A3C", tint_a=0.6, blur=18, border=0.0, shadow=0.3)
        E.rrect(c, r, 10, "#1D4FB0", 0.75 * fill * e_io_sine(prog(s, CLICK, 0.4)))
    E.rrect_stroke(c, r, 10, "#BFE4FF", 0.9, 1.4)
    li = logo_images()
    lw = 270
    lh = lw * li["h"] / li["w"]
    dst = R(-lw / 2, -lh / 2 + 2, lw, lh)
    wipe = e_io_sine(prog(s, LOGO0 + 0.35, 0.60))      # mosaic front sweeps left to right, the crisp logo after it
    if wipe > 0:
        band = 0.30
        xe = lerp(dst.left() - band * lw, dst.right(), wipe)
        smp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
        c.save()
        c.clipRect(R(dst.left() - 4, dst.top() - 20, max(0.0, xe - dst.left() + 4), lh + 40))
        c.drawImageRect(li["img"], dst, smp, skia.Paint(AntiAlias=True))
        c.restore()
        c.save()
        c.clipRect(R(xe, dst.top() - 20, band * lw, lh + 40))
        c.drawImageRect(li["mos"], dst, skia.SamplingOptions(skia.FilterMode.kNearest), skia.Paint(AntiAlias=True))
        c.restore()
    c.restore()
    c.restore()


def cursor(c, s):
    if s < CUR0 or s > 3.0:
        return
    m = e_io_cubic(prog(s, CUR0, CLICK - 0.1 - CUR0))
    out = e_io_cubic(prog(s, 2.15, 0.7))
    x = lerp(lerp(W * 0.70, CX + 60, m), W * 0.66, out)
    y = lerp(lerp(H * 0.74, CY + 18, m), H * 0.70, out)
    a = clamp(prog(s, CUR0, 0.2)) * (1 - out)
    A.ripple(c, CX + 60, CY + 18, s, CLICK, "#9FD2FF", 80)
    A.cursor(c, x, y, a, math.sin(math.pi * clamp(prog(s, CLICK, 0.22))))


def render(c, t):
    s = t - T0
    if t >= PEAK:                                     # seg_ai's own frames from the flash peak on (FIN under white)
        to = t - SHIFT
        _, t0, t1, fn = AI.FIN
        fn(c, to, to - t0, t1 - t0)
        wf = 1 - e_out_cubic(prog(to, AI.FLASH_PEAK, AI.FLASH_OUT))
        if wf > 0:
            c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", wf))
        return
    bgx = e_io_sine(prog(s, BG0, BG_D))
    if bgx > 0:
        space(c, s)
    if bgx < 1:                                       # the previous shot under the logo, sinking back
        X.SWITCH_ALPHA = 1 - e_io_sine(prog(s, LOGO0 - 0.05, 0.45))
        img = A.snap(32, lambda cc: Q.render(cc, T0 + s * FAC_RATE))
        sink = e_io_sine(prog(s, LOGO0, 0.8))
        A.draw_img(c, img, 1 - bgx, 6 * sink, 1.0 + 0.03 * sink)
        c.drawRect(R(0, 0, W, H), paint_fill("#050B1C", 0.30 * sink * (1 - bgx)))
    network(c, s)
    draw_items(c, s, front=False)
    core(c, s)
    sphere(c, s)
    logo_button(c, s, s > CLICK)
    draw_items(c, s, front=True)
    cursor(c, s)
    wf = e_in_cubic(prog(t, PEAK - 0.6, 0.6))         # flood to white (as seg_ai)
    if wf > 0:
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", wf))


def setup(height):
    global SCV
    out = Q.setup(height)
    SCV = A.SCV
    AI.HD = height > 1080
    return out


if __name__ == "__main__":
    X.SWITCH_CENTER = True
    O.FAC0 = Q.FAC0
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    bar = int(round(O.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (O.FPS_NUM, O.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        tl = TL0 + f
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        render(c, tl / 24.0)
        c.restore()
        fr = finish.apply(surf, P.grain(tl) if tl / 24.0 < PEAK else tl - 48)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
