#!/usr/bin/env python3
"""T PLUS logo motion v2 — light-driven reveal in one continuous 3D space.

1920x1080, 30fps, 6.8s. Every transition is motivated by light:
  0.00-1.30  macro: an ice-blue point light glides along the chrome top edge
  1.30-2.45  macro: a champagne-gold light climbs the curved stem tip
  2.45-3.55  pull back: both lights race along the contour and collide
  3.55-4.10  white bloom -> contracts to a star
  4.05-5.30  the symbol is drawn out of the star (glowing growth front)
             while rotating to front; wordmark letters swing in
  5.30-6.80  centred chrome logo, light sweep + glint, flattens to 2D white

usage: python tplus_motion_v2.py [--frames a:b] [--only 10,40] [--workers N]
"""
import argparse
import math
import os
import re
from multiprocessing import Pool

import cairosvg
import cv2
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

W, H, FPS, DUR = 1920, 1080, 30, 6.8
NF = int(round(DUR * FPS))
ROOT = os.path.dirname(os.path.abspath(__file__))
AS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "frames")
cv2.setNumThreads(1)

ICE = np.array([0.35, 0.78, 1.0], np.float32)
GOLD = np.array([1.0, 0.74, 0.38], np.float32)
WHITE = np.array([0.9, 0.95, 1.0], np.float32)
FINAL_H = 400.0  # final logo height on screen (px), centred


# ---------------------------------------------------------------- easing
def seg(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def smooth(x):
    return x * x * (3 - 2 * x)


def smoother(x):
    return x * x * x * (x * (6 * x - 15) + 10)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def in_cubic(x):
    return x ** 3


def in_out_cubic(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def lerp(a, b, x):
    return a + (b - a) * x


def lerpv(a, b, x):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * x


def pulse(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


# ---------------------------------------------------------------- assets
def load(name, size=None):
    im = cv2.imread(os.path.join(AS, name), cv2.IMREAD_COLOR)
    if size:
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return im ** 2.2  # linear light


ENV = cv2.GaussianBlur(load("env2.png", (2048, 869)), (0, 0), 1.2) * 1.8
HAZE = load("haze.png", (2304, 1296))
BURST = load("burst.png", (1920, 1072))
STAR = load("star.png", (900, 900))
GLINT = load("glint.png", (640, 640))
FLARE = load("flare.png", (1920, 1072))

# ---------------------------------------------------------------- logo geometry
SVG = open(os.path.join(ROOT, "logo.svg")).read()
PATHS = re.findall(r"<path[^>]*/>", SVG)
HEAD = SVG[: SVG.index("<path")]
VBW, VBH = 1186.43, 882.78
TS = 2.0  # texels per svg unit


def raster(idx, scale=TS, w=None, h=None):
    s = HEAD + "".join(PATHS[i] for i in idx) + "</svg>"
    png = cairosvg.svg2png(bytestring=s.encode(),
                           output_width=w or int(round(VBW * scale)),
                           output_height=h or int(round(VBH * scale)))
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_UNCHANGED)[..., 3].astype(np.float32) / 255.0


def geodesic(mask, seed, ds=4):
    """Normalised geodesic distance inside the shape from a seed texel (drawing order)."""
    h, w = mask.shape
    m = cv2.resize(mask, (w // ds, h // ds), interpolation=cv2.INTER_AREA) > 0.25
    m = cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    hs, ws = m.shape
    idx = -np.ones((hs, ws), np.int64)
    ys, xs = np.nonzero(m)
    idx[ys, xs] = np.arange(len(ys))
    rows, cols, wts = [], [], []
    for dy, dx, c in ((0, 1, 1.0), (1, 0, 1.0), (1, 1, 1.4142), (1, -1, 1.4142)):
        y2, x2 = ys + dy, xs + dx
        ok = (y2 < hs) & (x2 >= 0) & (x2 < ws)
        ok[ok] &= m[y2[ok], x2[ok]]
        rows.append(idx[ys[ok], xs[ok]])
        cols.append(idx[y2[ok], x2[ok]])
        wts.append(np.full(ok.sum(), c))
    g = csr_matrix((np.concatenate(wts), (np.concatenate(rows), np.concatenate(cols))), shape=(len(ys),) * 2)
    sy, sx = seed[1] / ds, seed[0] / ds
    s = int(np.argmin((ys - sy) ** 2 + (xs - sx) ** 2))
    d = dijkstra(g, directed=False, indices=s)
    f = np.full((hs, ws), np.nan, np.float32)
    f[ys, xs] = d / np.nanmax(d[np.isfinite(d)])
    valid = np.isfinite(f)
    for _ in range(12):  # grow values outward so upsampling has no holes
        fz = np.where(valid, f, 0).astype(np.float32)
        s1 = cv2.blur(fz, (3, 3))
        c1 = cv2.blur(valid.astype(np.float32), (3, 3))
        fill = (~valid) & (c1 > 0)
        f[fill] = s1[fill] / c1[fill]
        valid |= fill
    f[~valid] = 1.0
    return cv2.resize(f, (w, h), interpolation=cv2.INTER_LINEAR)


class Obj:
    """Extruded, bevelled slab built from a subset of the SVG paths."""

    def __init__(self, idx, depth, bevel, seed_svg=None, ts=TS):
        self.ts = TS = ts
        full = raster(idx, scale=ts)
        ys, xs = np.nonzero(full > 0.01)
        pad = int(bevel * TS) + 6
        x0, x1 = xs.min() - pad, xs.max() + pad + 1
        y0, y1 = ys.min() - pad, ys.max() + pad + 1
        m = full[y0:y1, x0:x1].copy()
        self.mask = m
        self.h, self.w = m.shape
        self.ox, self.oy = x0 / TS, y0 / TS
        self.cx, self.cy = (x0 + x1) / 2 / TS, (y0 + y1) / 2 / TS
        self.depth = depth
        mb = (m > 0.5).astype(np.uint8)
        sd = cv2.distanceTransform(mb, cv2.DIST_L2, 5) - cv2.distanceTransform(1 - mb, cv2.DIST_L2, 5)
        x = np.clip(sd / (bevel * TS), 0, 1)
        hgt = cv2.GaussianBlur(0.45 * x + 0.55 * np.sqrt(1 - (1 - x) ** 2), (0, 0), 1.0)
        gy, gx = np.gradient(hgt)
        k = bevel * TS * 0.8
        n = np.stack([-gx * k, -gy * k, -np.ones_like(gx)], -1)
        self.nface = (n / np.linalg.norm(n, axis=-1, keepdims=True)).astype(np.float32)
        gy2, gx2 = np.gradient(cv2.GaussianBlur(sd, (0, 0), 1.3 * ts))
        wn = np.stack([-gx2, -gy2, np.zeros_like(gx2)], -1)
        self.nwall = (wn / (np.linalg.norm(wn, axis=-1, keepdims=True) + 1e-6)).astype(np.float32)
        u = (np.arange(self.w) / TS + self.ox - self.cx).astype(np.float32)
        v = (np.arange(self.h) / TS + self.oy - self.cy).astype(np.float32)
        self.X, self.Y = np.meshgrid(u, v)
        self.corners = np.array([[self.ox - self.cx, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / TS, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / TS, self.oy - self.cy + self.h / TS],
                                 [self.ox - self.cx, self.oy - self.cy + self.h / TS]], np.float64)
        # outer contour, resampled uniformly, in object units (for lights to travel on)
        cs, _ = cv2.findContours(mb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=len)[:, 0, :].astype(np.float64)
        seglen = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([c, c[:1]]), axis=0), axis=1))]
        s = np.linspace(0, seglen[-1], 2400, endpoint=False)
        cc = np.vstack([c, c[:1]])
        px = np.interp(s, seglen, cc[:, 0])
        py = np.interp(s, seglen, cc[:, 1])
        self.contour = np.stack([px / TS + self.ox - self.cx, py / TS + self.oy - self.cy], -1)
        self.arrival = None
        if seed_svg is not None:
            self.arrival = geodesic(m, ((seed_svg[0] - self.ox) * TS, (seed_svg[1] - self.oy) * TS))

    def cidx(self, svg_xy):
        p = np.array([svg_xy[0] - self.cx, svg_xy[1] - self.cy])
        return int(np.argmin(((self.contour - p) ** 2).sum(1)))

    def cpoint(self, i):
        n = len(self.contour)
        i0 = int(math.floor(i)) % n
        f = i - math.floor(i)
        p = self.contour[i0] * (1 - f) + self.contour[(i0 + 1) % n] * f
        return np.array([p[0], p[1], 0.0])


TIP_TL = (276.0, 49.0)    # symbol top-left blade tip (svg units)
TIP_TR = (872.0, 48.5)    # top-right tip
TIP_BOT = (562.0, 562.0)  # bottom of the stem
SYM = Obj([0], depth=80, bevel=7, seed_svg=TIP_TL, ts=3.5)
# wordmark letters left->right: T P L U S ( + )
LETTERS = [Obj(i, depth=18, bevel=2.2, ts=2.5) for i in ([4], [2], [3], [8, 9, 10], [1], [6], [5], [7])]
LOGO_C = np.array([(82.7 + 1103.8) / 2 - SYM.cx, (47.1 + 835.6) / 2 - SYM.cy, 0.0])  # world
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
    def __init__(self, eye, target, focal, roll=0.0):
        eye, target = np.asarray(eye, float), np.asarray(target, float)
        f = target - eye
        f /= np.linalg.norm(f)
        x = np.cross(f, [0, -1, 0])
        x /= np.linalg.norm(x)
        y = np.cross(f, x)
        cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
        x, y = cr * x + sr * y, -sr * x + cr * y
        self.Rv = np.stack([x, y, f])
        self.eye = eye
        self.f = focal
        self.K = np.array([[focal, 0, W / 2], [0, focal, H / 2], [0, 0, 1]])

    def pose(self, Ro, To):
        return self.Rv @ Ro, self.Rv @ (np.asarray(To, float) - self.eye)

    def proj(self, pw):
        p = self.Rv @ (np.asarray(pw, float) - self.eye)
        return np.array([self.f * p[0] / p[2] + W / 2, self.f * p[1] / p[2] + H / 2]), p[2]


def homog(cam, o, R, T, z):
    A = np.array([[1 / o.ts, 0, o.ox - o.cx], [0, 1 / o.ts, o.oy - o.cy], [0, 0, 1]])
    M = np.column_stack([R[:, 0], R[:, 1], R @ np.array([0, 0, z]) + T])
    return cam.K @ M @ A


def project(cam, R, T, pts):
    P = pts @ R.T + T
    return np.stack([cam.f * P[:, 0] / P[:, 2] + W / 2, cam.f * P[:, 1] / P[:, 2] + H / 2], -1), P[:, 2]


def shade(o, n, R, T, z, yaw, env_k, lights):
    Rf = R.astype(np.float32)
    nc = n @ Rf.T
    Po = np.stack([o.X, o.Y, np.full_like(o.X, z)], -1)
    P = Po @ Rf.T + T.astype(np.float32)
    v = P * np.array([2.6, 2.6, 1.0], np.float32)  # exaggerated view spread -> richer reflections
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    d = np.sum(v * nc, -1, keepdims=True)
    r = v - 2 * d * nc
    u = 0.5 + (np.arctan2(r[..., 0], -r[..., 2]) + yaw) / (2 * np.pi) * 1.6
    vv = 0.5 + np.arcsin(np.clip(r[..., 1], -1, 1)) / np.pi * 1.4
    mx = (u % 1.0) * (ENV.shape[1] - 1)
    my = np.clip(vv, 0, 1) * (ENV.shape[0] - 1)
    col = cv2.remap(ENV, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
    fres = 0.7 + 0.3 * (1 - np.abs(d)) ** 2
    ry = r[..., 1:2]
    col = col + (np.exp(-((ry + 0.04) / 0.05) ** 2) * 0.9 + np.clip(-ry, 0, 1) * 0.22) * WHITE  # horizon + sky
    col = col * fres * env_k
    for lp, lc, rad, pw in lights:  # point lights glancing over the metal
        dd = ((Po - np.asarray(lp, np.float32)) ** 2).sum(-1, keepdims=True)
        col = col + lc * (pw * np.exp(-dd / (rad * rad)))
    return col


def draw_obj(layer, cam, o, R, T, depth_k=1.0, yaw=0.0, env_k=1.0, white=0.0, lights=(),
             front=None, alpha=1.0, glow_col=WHITE):
    """Painter's-algorithm render: extrusion slices back->front, then bevelled face."""
    rgb, a = layer
    depth = o.depth * depth_k
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
    m = o.mask
    emis = 0.0
    if front is not None:  # drawing reveal along the geodesic field + glowing front
        m = m * np.clip((front - o.arrival) / 0.025 + 0.5, 0, 1)
        emis = np.exp(-((o.arrival - front + 0.02) / 0.035) ** 2)[..., None] * glow_col * 2.4 * (front < 1.04)
    m4 = m[..., None]
    seq = []
    if depth > 0.5:
        plen = np.abs(p1 - p0).max()
        ns = int(np.clip(plen * 1.6 + 2, 2, 420))
        wall = shade(o, o.nwall, R, T, depth * 0.5, yaw, env_k * 0.85, lights)
        wall = wall * (1 - white) + white * 0.55 + emis * 0.6
        src = np.concatenate([wall * m4, m4], -1).astype(np.float32)
        for i in range(ns, 0, -1):
            f = i / ns
            seq.append((f * depth, src, lerp(1.0, 0.3, f)))
    face = shade(o, o.nface, R, T, 0.0, yaw, env_k, lights)
    face = face * (1 - white) + white * 1.12 + emis
    seq.append((0.0, np.concatenate([face * m4, m4], -1).astype(np.float32), 1.0))
    lr, la = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
    for z, src, k in seq:
        wp = cv2.warpPerspective(src, Tr @ homog(cam, o, R, T, z), (rw, rh), flags=cv2.INTER_LINEAR)
        sa = wp[..., 3:4] * alpha
        lr *= 1 - sa
        lr += wp[..., :3] * (alpha * k)
        la *= 1 - sa[..., 0]
        la += sa[..., 0]


# ---------------------------------------------------------------- 2D helpers
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
XN, YN = XX / W, YY / H


def card(img, zoom, dx=0.0, dy=0.0, roll=0.0):
    h, w = img.shape[:2]
    s = max(W / w, H / h) * zoom
    M = cv2.getRotationMatrix2D((w / 2, h / 2), roll, s)
    M[:, 2] += [W / 2 - w / 2 + dx, H / 2 - h / 2 + dy]
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def add_sprite(dst, spr, cx, cy, scale, gain, sx=1.0, sy=1.0, angle=0.0):
    if gain <= 1e-3 or scale <= 1e-3:
        return
    h, w = spr.shape[:2]
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    M2 = np.array([[ca, -sa], [sa, ca]]) @ np.diag([scale * sx, scale * sy])
    M = np.column_stack([M2, np.array([cx, cy]) - M2 @ np.array([w / 2, h / 2])])
    dst += cv2.warpAffine(spr, M, (W, H), flags=cv2.INTER_LINEAR) * gain


def glow(dst, x, y, col, inten, core=2.5, halo=26.0, streak=1.0):
    """Procedural point light: hot core + coloured halo + thin anamorphic streak."""
    r = int(halo * 8)
    xa, xb = int(max(x - r * 2, 0)), int(min(x + r * 2, W))
    ya, yb = int(max(y - r, 0)), int(min(y + r, H))
    if xa >= xb or ya >= yb:
        return
    gx = XX[ya:yb, xa:xb] - x
    gy = YY[ya:yb, xa:xb] - y
    d2 = gx * gx + gy * gy
    core_v = np.exp(-d2 / (2 * core * core)) * 4.0
    halo_v = np.exp(-d2 / (2 * halo * halo)) * 0.55 + np.exp(-d2 / (2 * (halo * 3.5) ** 2)) * 0.12
    st = np.exp(-gy * gy / 3.0) * np.exp(-np.abs(gx) / (halo * 5)) * 0.5 * streak
    dst[ya:yb, xa:xb] += (core_v[..., None] * WHITE + (halo_v + st)[..., None] * col) * inten


def trail(dst, pts, col, inten):
    """Fading light trail through recent screen positions (newest last)."""
    if len(pts) < 2:
        return
    lay = np.zeros((H, W, 3), np.float32)
    n = len(pts)
    for i in range(n - 1):
        k = (i + 1) / n
        p, q = pts[i], pts[i + 1]
        cv2.line(lay, (int(p[0] * 4), int(p[1] * 4)), (int(q[0] * 4), int(q[1] * 4)),
                 tuple(float(c) * k * k for c in col), thickness=max(1, int(3 * k)), lineType=cv2.LINE_AA, shift=2)
    dst += (cv2.GaussianBlur(lay, (0, 0), 1.2) * 1.4 + cv2.GaussianBlur(lay, (0, 0), 9) * 2.2) * inten


# ---------------------------------------------------------------- choreography
I_TL, I_TR, I_BOT = SYM.cidx(TIP_TL), SYM.cidx(TIP_TR), SYM.cidx(TIP_BOT)
I_CRV = SYM.cidx((600.1, 456.6))  # top of the curved cut on the stem
NC = len(SYM.contour)


def cwalk(i0, i1, x):
    """Walk along the contour from i0 to i1 (shorter way round)."""
    d = (i1 - i0) % NC
    if d > NC / 2:
        d -= NC
    return i0 + d * x


def light_states(t):
    """Point lights (object-space position, colour, trail positions fn) active at time t."""
    out = []
    if t < 1.32:  # ice light glides along the top edge
        out.append(("ice", lambda tt: cwalk(I_TL, I_TR, lerp(0.04, 0.62, smooth(seg(tt, -0.1, 1.4)))), ICE,
                    smooth(seg(t, 0.0, 0.25))))
    elif t < 2.47:  # gold light climbs the curved stem tip
        out.append(("gold", lambda tt: cwalk(I_BOT, I_CRV, lerp(-0.3, 1.6, smooth(seg(tt, 1.25, 2.55)))), GOLD,
                    smooth(seg(t, 1.3, 1.45))))
    elif t < 3.56:  # both race to the top-right tip and collide
        out.append(("ice", lambda tt: cwalk(I_TL, I_TR, lerp(0.2, 1.0, in_cubic(seg(tt, 2.45, 3.56)))), ICE, 1.0))
        out.append(("gold", lambda tt: cwalk(I_BOT, I_TR, lerp(0.15, 1.0, in_cubic(seg(tt, 2.45, 3.56)))), GOLD, 1.0))
    return out


def camera(t):
    tl = np.array([TIP_TL[0] - SYM.cx, TIP_TL[1] - SYM.cy, 0.0])
    tr = np.array([TIP_TR[0] - SYM.cx, TIP_TR[1] - SYM.cy, 0.0])
    bot = np.array([TIP_BOT[0] - SYM.cx, TIP_BOT[1] - SYM.cy, 0.0])
    if t < 1.30:  # macro A: grazing view over the top edge, telephoto
        q = seg(t, 0.0, 1.3)
        tgt = lerpv(tl + [110, 4, 20], tl + [230, 4, 20], q)
        d = np.array([-0.30, -0.62, -1.0])
        return Cam(tgt + d / np.linalg.norm(d) * 560, tgt, 3300, roll=lerp(-14, -8, q))
    if t < 2.45:  # macro B: low, looking up the curved stem tip
        q = seg(t, 1.3, 2.45)
        tgt = lerpv(bot + [25, -20, 30], bot + [30, -110, 30], q)
        d = np.array([0.55, 0.42, -1.0])
        return Cam(tgt + d / np.linalg.norm(d) * 540, tgt, 3000, roll=lerp(10, 4, q))
    if t < 3.56:  # pull back, chase the collision point
        q = smooth(seg(t, 2.45, 3.56))
        tgt = lerpv([0, -60, 0], tr, q)
        d = lerpv([0.55, -0.30, -1.0], [0.25, -0.15, -1.0], q)
        return Cam(tgt + d / np.linalg.norm(d) * lerp(2100, 1300, q), tgt, 1700, roll=lerp(-6, 0, q))
    # build + final: frontal, drifting from the seed tip to the logo centre
    q1 = smoother(seg(t, 4.0, 4.7))
    q2 = smoother(seg(t, 4.75, 5.6))
    tgt = lerpv(lerpv(tl * 0.55, [0, 0, 0], q1), LOGO_C, q2)
    dist = lerp(lerp(1050, 1250, q1), 1600 / FINAL_S, q2)
    eye = tgt + np.array([lerp(-160, 0, q2), lerp(-90, 0, q2), -dist])
    return Cam(eye, tgt, 1600, roll=lerp(lerp(-10, -3, q1), 0, q2))


VEC_FINAL = None


def vec_final():
    global VEC_FINAL
    if VEC_FINAL is None:
        cx, cy = W / 2, H / 2
        lw, lh = int(round(VBW * FINAL_S * 4)), int(round(VBH * FINAL_S * 4))
        v = raster(range(len(PATHS)), w=lw, h=lh)
        lcx, lcy = (82.7 + 1103.8) / 2, (47.1 + 835.6) / 2
        M = np.array([[0.25, 0, cx - lcx * FINAL_S], [0, 0.25, cy - lcy * FINAL_S]], np.float32)
        VEC_FINAL = cv2.warpAffine(v, M, (W, H), flags=cv2.INTER_AREA)
    return VEC_FINAL


def render(t):
    cam = camera(t)
    f = np.zeros((H, W, 3), np.float32)
    # atmosphere
    hk = 0.55 if t < 3.6 else lerp(0.6, 0.38, smooth(seg(t, 4.0, 6.0)))
    hz = card(HAZE, 1.12 - 0.03 * t / DUR, dx=-10 * t, roll=0.0)
    if t < 1.3:
        hz = hz[:, ::-1]  # vary the glow side per shot
    f += hz * hk
    layer = (np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32))
    lights = light_states(t)
    lt = []
    for name, walk, col, k in lights:
        p = SYM.cpoint(walk(t))
        lt.append((p + [0, 0, -2], col, 34.0, 1.6 * k))
    if t < 3.56:
        env_k = 0.55 if t < 2.45 else 0.42
        R, T = cam.pose(np.eye(3), [0, 0, 0])
        draw_obj(layer, cam, SYM, R, T, env_k=env_k, yaw=0.6 * t, lights=lt)
    elif t >= 3.95:
        pr = out_cubic(seg(t, 3.95, 5.25))
        Ro = rot(lerp(58, 0, pr), lerp(-38, 0, pr), lerp(24, 0, pr))
        front = lerp(-0.02, 1.08, in_out_cubic(seg(t, 4.02, 4.95)))
        depth_k = 1 - smooth(seg(t, 6.0, 6.4))
        white = smooth(seg(t, 6.05, 6.45))
        yaw = lerp(1.1, 0.0, out_cubic(seg(t, 4.0, 5.3))) + 0.95 * smooth(seg(t, 5.35, 6.0)) - 0.4
        objs = []
        for i, o in enumerate(LETTERS):
            st = 4.62 + 0.055 * i
            if t < st:
                continue
            q = out_cubic(seg(t, st, st + 0.6))
            Rl = rot(lerp(-20, 0, q), lerp(-80, 0, q), lerp(-8, 0, q))
            To = world_off(o) + [lerp(420, 0, q), lerp(-40, 0, q), lerp(260, 0, q)]
            R, T = cam.pose(Rl, To)
            objs.append((T[2], o, R, T, min(1.0, seg(t, st, st + 0.1)), None))
        R, T = cam.pose(Ro, [0, 0, 0])
        objs.append((T[2], SYM, R, T, 1.0, front))
        for _, o, R, T, al, fr in sorted(objs, key=lambda e: -e[0]):
            draw_obj(layer, cam, o, R, T, depth_k=depth_k, yaw=yaw, env_k=1.0, white=white, front=fr, alpha=al)
    rgb, a = layer
    v = smooth(seg(t, 6.3, 6.55))
    if v > 0:
        vec = vec_final()
        rgb[:] = rgb * (1 - v) + vec[..., None] * 1.12 * v
        a[:] = a * (1 - v) + vec * v
    f = f * (1 - a[..., None]) + rgb
    # light points + trails
    for name, walk, col, k in lights:
        pts = []
        for j in range(10, -1, -1):
            pw = SYM.cpoint(walk(t - j * 0.016)) + [0, 0, -2]
            sp, z = cam.proj(pw)
            if z > 15:
                pts.append(sp)
        if pts:
            trail(f, pts, col, 0.9 * k)
            glow(f, pts[-1][0], pts[-1][1], col, 1.3 * k, halo=30 if t < 2.45 else 22)
    # collision -> bloom -> star
    if 3.40 < t < 4.35:
        cx, cy = W / 2, H / 2
        if t < 3.56:
            sp, _ = cam.proj([TIP_TR[0] - SYM.cx, TIP_TR[1] - SYM.cy, -2])
            cx, cy = sp
        b_in = smooth(seg(t, 3.50, 3.62))
        b_out = smooth(seg(t, 3.72, 4.05))
        add_sprite(f, BURST, cx, cy, lerp(0.4, 1.7, b_in) * lerp(1, 0.12, b_out), 2.2 * b_in * (1 - b_out ** 2))
        wo = b_in * (1 - smooth(seg(t, 3.66, 3.95)))
        f += wo * 1.5 * WHITE
        s_k = smooth(seg(t, 3.78, 3.92)) * (1 - smooth(seg(t, 4.08, 4.3)))
        add_sprite(f, STAR, cx, cy, lerp(1.2, 0.35, smooth(seg(t, 3.8, 4.3))), 2.4 * s_k, angle=lerp(0, 18, seg(t, 3.8, 4.3)))
    # final glint on the top-right tip
    g = pulse(t, 5.82, 0.08)
    if g > 0.01:
        sp, _ = cam.proj([TIP_TR[0] - SYM.cx, TIP_TR[1] - SYM.cy, -2])
        add_sprite(f, GLINT, sp[0], sp[1], 0.45 + 0.3 * g, 1.5 * g, angle=15 * g)
    # opening: fade from black
    f *= smooth(seg(t, 0.0, 0.3))
    return f


def finish(img, t):
    lum = img.mean(-1)
    br = img * np.clip((lum - 0.45) / 0.6, 0, 1)[..., None]
    small = cv2.resize(br, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 3) * 0.5 + cv2.GaussianBlur(small, (0, 0), 14) * 0.7
    streak = cv2.GaussianBlur(small, (0, 0), sigmaX=70, sigmaY=0.7) * np.array([0.55, 0.78, 1.0], np.float32)
    end = 1 - 0.65 * smooth(seg(t, 6.0, 6.6))
    img = img + cv2.resize(bloom, (W, H)) * 0.6 * end + cv2.resize(streak, (W, H)) * 0.55 * end ** 3
    img = img * VIG
    img = np.where(img < 0.8, img, 0.8 + 0.2 * np.tanh((img - 0.8) / 0.2))
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    lum = img.mean(-1, keepdims=True)
    img = lum + (img - lum) * 1.18  # a touch more colour
    img = img + (img - 0.5) * 0.06  # and contrast
    rng = np.random.default_rng(int(t * 1000))
    img = img + rng.normal(0, 0.004, (H, W, 1)).astype(np.float32)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


r2 = ((XN - 0.5) * 1.1) ** 2 + (YN - 0.5) ** 2
VIG = (1 - 0.5 * np.clip(r2 / 0.5, 0, 1) ** 1.5)[..., None].astype(np.float32)


def nsub(t):
    if 3.45 < t < 3.75:
        return 5
    if t < 5.4:
        return 3
    return 1


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
