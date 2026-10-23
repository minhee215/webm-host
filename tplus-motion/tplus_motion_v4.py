#!/usr/bin/env python3
"""T PLUS logo motion v4 — minimal monochrome reveal (AHOF-style structure).

10s, 30fps. Pure black, white light, graphite. TPLUS_SCALE=0.5 -> 960x540 sample.
  0.0-1.2  a single point of light
  1.2-2.0  it stretches into a thin vertical sliver
  2.0-2.8  the sliver tilts — it is the symbol plate seen edge-on
  2.8-3.1  the plate swings open: a glowing white T-shaped plane
  3.1-4.6  glowing hold, slow drift
  4.6-5.0  glow fades, graphite surface and thickness appear
  5.0-5.8  one full tumble in 3D
  5.8-6.4  lands in a tilted perspective, white highlight sweeps across
  6.4-7.6  slow drift, glossy graphite
  7.6-8.6  turns to face front, rises and shrinks; wordmark fades in below
  8.6-9.3  everything settles to flat white 2D
  9.3-10   hold

usage: TPLUS_SCALE=0.5 python tplus_motion_v4.py [--frames a:b] [--only 10,40] [--workers N]
"""
import argparse
import math
import os
import re
from multiprocessing import Pool

import cairosvg
import cv2
import numpy as np

SC = float(os.environ.get("TPLUS_SCALE", "1"))
W, H, FPS, DUR = int(1920 * SC), int(1080 * SC), 30, 10.0
NF = int(round(DUR * FPS))
ROOT = os.path.dirname(os.path.abspath(__file__))
AS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "frames")
cv2.setNumThreads(1)

WHITE = np.array([1.0, 1.0, 1.0], np.float32)
FINAL_H = 400.0  # final logo height on screen at full res (px), centred
FOCAL = 1600.0


# ---------------------------------------------------------------- easing
def seg(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def smooth(x):
    return x * x * (3 - 2 * x)


def smoother(x):
    return x * x * x * (x * (6 * x - 15) + 10)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def in_out_quint(x):
    return 16 * x ** 5 if x < 0.5 else 1 - (-2 * x + 2) ** 5 / 2


def lerp(a, b, x):
    return a + (b - a) * x


def lerpv(a, b, x):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * x


# ---------------------------------------------------------------- assets
def load(name, size=None):
    im = cv2.imread(os.path.join(AS, name), cv2.IMREAD_COLOR)
    if size:
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    im = im ** 2.2
    return im.mean(-1, keepdims=True).repeat(3, -1)  # strictly neutral


ENV = cv2.GaussianBlur(load("env_mono.png", (2048, 869)), (0, 0), 3.0) * 1.5

# ---------------------------------------------------------------- logo geometry
SVG = open(os.path.join(ROOT, "logo.svg")).read()
PATHS = re.findall(r"<path[^>]*/>", SVG)
HEAD = SVG[: SVG.index("<path")]
VBW, VBH = 1186.43, 882.78


def raster(idx, scale, w=None, h=None):
    s = HEAD + "".join(PATHS[i] for i in idx) + "</svg>"
    png = cairosvg.svg2png(bytestring=s.encode(),
                           output_width=w or int(round(VBW * scale)),
                           output_height=h or int(round(VBH * scale)))
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255.0


class Obj:
    """Extruded, bevelled slab built from a subset of the SVG paths."""

    def __init__(self, idx, depth, bevel, ts):
        self.ts = ts
        full = raster(idx, ts)
        ys, xs = np.nonzero(full > 0.01)
        pad = int(bevel * ts) + 6
        x0, x1 = xs.min() - pad, xs.max() + pad + 1
        y0, y1 = ys.min() - pad, ys.max() + pad + 1
        m = full[y0:y1, x0:x1].copy()
        self.mask = m
        self.h, self.w = m.shape
        self.ox, self.oy = x0 / ts, y0 / ts
        self.cx, self.cy = (x0 + x1) / 2 / ts, (y0 + y1) / 2 / ts
        self.depth = depth
        mb = (m > 0.5).astype(np.uint8)
        sd = cv2.distanceTransform(mb, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - mb, cv2.DIST_L2, 5)
        x = np.clip(sd / (bevel * ts), 0, 1)
        hgt = cv2.GaussianBlur(0.45 * x + 0.55 * np.sqrt(1 - (1 - x) ** 2), (0, 0), 1.0)
        gy, gx = np.gradient(hgt)
        k = bevel * ts * 0.8
        n = np.stack([-gx * k, -gy * k, -np.ones_like(gx)], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        self.nface = n.astype(np.float32)
        self.nback = (n * np.array([1, 1, -1])).astype(np.float32)
        gy2, gx2 = np.gradient(cv2.GaussianBlur(sd, (0, 0), 1.3 * ts))
        wn = np.stack([-gx2, -gy2, np.zeros_like(gx2)], -1)
        self.nwall = (wn / (np.linalg.norm(wn, axis=-1, keepdims=True) + 1e-6)).astype(np.float32)
        u = (np.arange(self.w) / ts + self.ox - self.cx).astype(np.float32)
        v = (np.arange(self.h) / ts + self.oy - self.cy).astype(np.float32)
        self.X, self.Y = np.meshgrid(u, v)
        self.corners = np.array([[self.ox - self.cx, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / ts, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / ts, self.oy - self.cy + self.h / ts],
                                 [self.ox - self.cx, self.oy - self.cy + self.h / ts]], np.float64)


SYM = Obj([0], depth=60, bevel=6, ts=max(1.6, 3.2 * SC))
WORD = Obj(list(range(1, len(PATHS))), depth=10, bevel=1.6, ts=max(1.6, 2.5 * SC))
SYM_H = 518.0  # symbol height in svg units
LOGO_C = np.array([(82.7 + 1103.8) / 2 - SYM.cx, (47.1 + 835.6) / 2 - SYM.cy, 0.0])
FINAL_S = FINAL_H / (835.6 - 47.1)


def world_off(o):
    return np.array([o.cx - SYM.cx, o.cy - SYM.cy, 0.0])


# ---------------------------------------------------------------- camera / projection
def rot(rx, ry, rz):
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Cam:
    def __init__(self, target, dist):
        self.eye = np.asarray(target, float) + [0, 0, -dist]
        self.f = FOCAL * SC
        self.K = np.array([[self.f, 0, W / 2], [0, self.f, H / 2], [0, 0, 1]])

    def pose(self, Ro, To):
        return Ro, np.asarray(To, float) - self.eye


def homog(cam, o, R, T, z):
    A = np.array([[1 / o.ts, 0, o.ox - o.cx], [0, 1 / o.ts, o.oy - o.cy], [0, 0, 1]])
    M = np.column_stack([R[:, 0], R[:, 1], R @ np.array([0, 0, z]) + T])
    return cam.K @ M @ A


def project(cam, R, T, pts):
    P = pts @ R.T + T
    return np.stack([cam.f * P[:, 0] / P[:, 2] + W / 2, cam.f * P[:, 1] / P[:, 2] + H / 2], -1), P[:, 2]


def shade(o, n, R, T, z, yaw, env_k):
    Rf = R.astype(np.float32)
    nc = n @ Rf.T
    P = np.stack([o.X, o.Y, np.full_like(o.X, z)], -1) @ Rf.T + T.astype(np.float32)
    v = P * np.array([2.2, 2.2, 1.0], np.float32)
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    d = np.sum(v * nc, -1, keepdims=True)
    r = v - 2 * d * nc
    u = 0.5 + (np.arctan2(r[..., 0], -r[..., 2]) + yaw) / (2 * np.pi) * 1.3
    vv = 0.5 + np.arcsin(np.clip(r[..., 1], -1, 1)) / np.pi * 1.2
    mx = (u % 1.0) * (ENV.shape[1] - 1)
    my = np.clip(vv, 0, 1) * (ENV.shape[0] - 1)
    col = cv2.remap(ENV, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
    fres = 0.55 + 0.45 * (1 - np.abs(d)) ** 3
    return (col * fres + 0.018) * env_k  # graphite base + glossy reflections


def draw_obj(layer, cam, o, R, T, depth_k=1.0, yaw=0.0, env_k=1.0, white=0.0, emit=1.12, alpha=1.0):
    """Painter's-algorithm render of an extruded slab; handles either side facing the camera."""
    rgb, a = layer
    depth = max(o.depth * depth_k, 0.0)
    c3 = np.column_stack([o.corners, np.zeros(4)])
    p0, z0 = project(cam, R, T, c3)
    p1, z1 = project(cam, R, T, c3 + [0, 0, depth])
    if min(z0.min(), z1.min()) < 15:
        return
    pts = np.vstack([p0, p1])
    x0, y0 = np.floor(pts.min(0)).astype(int) - 2
    x1, y1 = np.ceil(pts.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    rw, rh = x1 - x0, y1 - y0
    Tr = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])
    m4 = o.mask[..., None]
    front_visible = float(np.dot(R @ np.array([0, 0, -1.0]), T + R @ np.array([0, 0, 0.0]))) < 0
    seq = []
    if depth > 0.3:
        plen = np.abs(p1 - p0).max()
        ns = int(np.clip(plen * 1.6 + 2, 2, 300))
        wall = shade(o, o.nwall, R, T, depth * 0.5, yaw, env_k * 0.9)
        wall = wall * (1 - white) + white * emit * 0.7
        src = np.concatenate([wall * m4, m4], -1).astype(np.float32)
        zs = [i / ns * depth for i in range(ns, 0, -1)] if front_visible else [i / ns * depth for i in range(0, ns)]
        for z in zs:
            seq.append((z, src, lerp(1.0, 0.55, z / max(depth, 1e-6)) if front_visible else lerp(0.55, 1.0, z / max(depth, 1e-6))))
    if front_visible:
        face = shade(o, o.nface, R, T, 0.0, yaw, env_k)
        zf = 0.0
    else:
        face = shade(o, o.nback, R, T, depth, yaw, env_k)
        zf = depth
    face = face * (1 - white) + white * emit
    seq.append((zf, np.concatenate([face * m4, m4], -1).astype(np.float32), 1.0))
    lr, la = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
    for z, src, k in seq:
        wp = cv2.warpPerspective(src, Tr @ homog(cam, o, R, T, z), (rw, rh), flags=cv2.INTER_LINEAR)
        sa = wp[..., 3:4] * alpha
        lr *= 1 - sa
        lr += wp[..., :3] * (alpha * k)
        la *= 1 - sa[..., 0]
        la += sa[..., 0]


# ---------------------------------------------------------------- light sliver
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
XN, YN = XX / W, YY / H


def sliver(dst, p, q, width, inten):
    """Lens-shaped line of light from p to q (thick in the middle, tapering to points)."""
    p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
    dv = q - p
    L = float(np.linalg.norm(dv))
    pad = 60 * SC + width * 6
    xa, xb = int(max(min(p[0], q[0]) - pad, 0)), int(min(max(p[0], q[0]) + pad, W))
    ya, yb = int(max(min(p[1], q[1]) - pad, 0)), int(min(max(p[1], q[1]) + pad, H))
    if xa >= xb or ya >= yb:
        return
    gx, gy = XX[ya:yb, xa:xb] - p[0], YY[ya:yb, xa:xb] - p[1]
    if L < 1e-3:
        d2 = gx * gx + gy * gy
        s_mid = np.ones_like(d2)
    else:
        u = dv / L
        s = (gx * u[0] + gy * u[1]) / L
        perp = gx * (-u[1]) + gy * u[0]
        sc = np.clip(s, 0, 1)
        along = (s - sc) * L
        d2 = perp * perp + along * along
        s_mid = np.sqrt(np.clip(1 - (2 * sc - 1) ** 2, 0, 1)) * 0.85 + 0.15
    wd = width * s_mid
    core = np.exp(-d2 / (2 * wd * wd + 1e-6)) * 3.0
    halo = np.exp(-d2 / (2 * (wd * 7 + 4 * SC) ** 2)) * 0.35
    dst[ya:yb, xa:xb] += ((core + halo) * inten)[..., None] * WHITE


# ---------------------------------------------------------------- choreography
def sym_pose(t):
    """Symbol rotation (rx, ry, rz in degrees)."""
    # edge-on sliver (ry~89) -> tilt (rz) -> swing open (ry) -> drift
    rz_line = lerp(0, -62, in_out_cubic(seg(t, 2.0, 2.8)))
    ry_open = lerp(89.5, 32, out_cubic(seg(t, 2.8, 3.15)))
    ry = lerp(ry_open, 24, smooth(seg(t, 3.15, 5.0)))
    rx = lerp(0, 38, out_cubic(seg(t, 2.8, 3.3)))
    rz = rz_line + lerp(0, 50, out_cubic(seg(t, 2.8, 3.3))) + lerp(0, 4, smooth(seg(t, 3.3, 5.0)))
    # tumble: one full roll around X with a twist
    k = in_out_quint(seg(t, 5.0, 5.8))
    rx += 360 * k - (360 if k >= 1 else 0)  # keep the angle unwrapped for the final turn
    ry += lerp(0, -46, k)
    rz += lerp(0, 12, k)
    # slow drift after landing, then face front
    ry += lerp(0, 8, smooth(seg(t, 5.8, 7.6)))
    f = smoother(seg(t, 7.6, 8.6))
    return lerp(rx, 0, f), lerp(ry, 0, f), lerp(rz, 0, f)


def camera(t):
    f = smoother(seg(t, 7.6, 8.6))
    tgt = lerpv([0, 0, 0], LOGO_C, f)
    d0 = lerp(1900, 1650, smooth(seg(t, 3.0, 7.6)))  # slow push-in
    return Cam(tgt, lerp(d0, FOCAL / FINAL_S, f))


VEC_FINAL = None


def vec_final():
    global VEC_FINAL
    if VEC_FINAL is None:
        fs = FINAL_S * SC
        lw, lh = int(round(VBW * fs * 4)), int(round(VBH * fs * 4))
        v = raster(range(len(PATHS)), 1, w=lw, h=lh)
        lcx, lcy = (82.7 + 1103.8) / 2, (47.1 + 835.6) / 2
        M = np.array([[0.25, 0, W / 2 - lcx * fs], [0, 0.25, H / 2 - lcy * fs]], np.float32)
        VEC_FINAL = cv2.warpAffine(v, M, (W, H), flags=cv2.INTER_AREA)
    return VEC_FINAL


def render(t):
    cam = camera(t)
    f = np.zeros((H, W, 3), np.float32)
    layer = (np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32))
    R = rot(*sym_pose(t))
    _, T = cam.pose(R, [0, 0, 0])

    # glowing plate -> graphite
    glow_k = 1 - smooth(seg(t, 4.6, 5.0))
    plate_on = smooth(seg(t, 2.78, 2.95))
    depth_k = lerp(0.04, 1.0, smooth(seg(t, 4.6, 5.1))) * (1 - smooth(seg(t, 8.6, 9.0)))
    sweep = math.sin(math.pi * seg(t, 5.75, 6.5)) ** 2  # white highlight as it lands
    yaw = lerp(-0.9, 0.9, smooth(seg(t, 5.7, 6.6))) + lerp(0, 0.35, smooth(seg(t, 6.6, 8.6)))
    env_k = lerp(0.55, 1.25, sweep)
    flat = smooth(seg(t, 8.6, 9.3))
    white = max(glow_k, flat)
    emit = lerp(1.12, 2.6, glow_k * (1 - flat))
    if plate_on > 0:
        draw_obj(layer, cam, SYM, R, T, depth_k=depth_k, yaw=yaw, env_k=env_k, white=white, emit=emit, alpha=plate_on)
    # wordmark fades in under the symbol
    wa = smooth(seg(t, 7.9, 8.7))
    if wa > 0:
        _, Tw = cam.pose(np.eye(3), world_off(WORD))
        draw_obj(layer, cam, WORD, np.eye(3), Tw, depth_k=depth_k, yaw=yaw, env_k=lerp(0.35, 0.8, wa),
                 white=flat, alpha=wa)
    rgb, a = layer
    v = smooth(seg(t, 9.1, 9.4))
    if v > 0:
        vec = vec_final()
        rgb[:] = rgb * (1 - v) + vec[..., None] * 1.12 * v
        a[:] = a * (1 - v) + vec * v
    f = f * (1 - a[..., None]) + rgb

    # point -> sliver (the plate seen edge-on), fades as the plate opens
    lk = 1 - smooth(seg(t, 2.8, 3.05))
    if lk > 0:
        grow = smooth(seg(t, 1.2, 2.0))
        half = SYM_H / 2 * grow
        R0 = rot(0, 89.5, lerp(0, -62, in_out_cubic(seg(t, 2.0, 2.8))))
        ends, _ = project(cam, R0, cam.pose(R0, [0, 0, 0])[1], np.array([[0, -half, 0], [0, half, 0]]))
        twinkle = 0.85 + 0.15 * math.sin(t * 9.0)
        inten = smooth(seg(t, 0.15, 0.6)) * (twinkle if t < 1.2 else 1.0) * lk
        sliver(f, ends[0], ends[1], width=lerp(1.6, 1.2, grow) * SC * 2, inten=inten)
    return f


def finish(img, t):
    lum = img.mean(-1)
    br = img * np.clip((lum - 0.55) / 0.6, 0, 1)[..., None]
    small = cv2.resize(br, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 2.5 * SC) * 0.5 + cv2.GaussianBlur(small, (0, 0), 12 * SC) * 0.6
    img = img + cv2.resize(bloom, (W, H)) * 0.55
    img = np.where(img < 0.85, img, 0.85 + 0.15 * np.tanh((img - 0.85) / 0.15))
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    rng = np.random.default_rng(int(t * 1000))
    img = img + rng.normal(0, 0.003, (H, W, 1)).astype(np.float32)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def nsub(t):
    if 4.95 < t < 5.85:
        return 6
    if 2.75 < t < 3.2:
        return 4
    return 2


def do_frame(i):
    t = i / FPS
    n = nsub(t)
    acc = np.zeros((H, W, 3), np.float32)
    for k in range(n):
        acc += render(t + (k - (n - 1) / 2) / (n * FPS))
    out = finish(acc / n, t)
    cv2.imwrite(os.path.join(OUT, f"f{i:04d}.png"), cv2.cvtColor(out, cv2.COLOR_RGB2BGR),
                [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return i


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default=f"0:{NF}")
    ap.add_argument("--only", default="")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.only:
        ids = [int(x) for x in a.only.split(",")]
    else:
        s, e = map(int, a.frames.split(":"))
        ids = list(range(s, e))
    with Pool(a.workers) as pool:
        for i in pool.imap_unordered(do_frame, ids):
            print("done", i, flush=True)
