#!/usr/bin/env python3
"""T PLUS logo motion v7 — minimal monochrome reveal (AHOF-style), 6s.

Pure black, white light, graphite; every motion overlaps the next (sine easing,
no dead stops). TPLUS_SCALE=0.5 renders a 960x540 sample.
  0.00-0.95  a point of light stretches into a vertical sliver
  0.75-1.55  the sliver lays down to near-horizontal (a thin plate seen edge-on)
  1.40-2.05  the plate opens along its long axis: a crisp glowing T
  1.40-4.70  the lying T turns gently on its own axis (no flips)
  2.10-3.40  the light drains across the plate like a switch-off, revealing graphite
  3.30-4.60  one broad soft reflection glides across the graphite, a faint rim glint follows
  4.20-5.20  stands up to face front along one smooth arc (slerp) and rises; wordmark fades in
  5.00-5.45  settles to flat white 2D, hold

usage: TPLUS_SCALE=0.5 python tplus_motion_v7.py [--frames a:b] [--only 10,40] [--workers N]
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
W, H, FPS, DUR = int(1920 * SC), int(1080 * SC), 30, 6.0
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


def ease(x):
    """Sine in-out: gentle start and landing."""
    return 0.5 - 0.5 * math.cos(math.pi * x)


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
ENV_SOFT = cv2.GaussianBlur(ENV, (0, 0), 45.0)  # satin graphite: broad, smooth reflections

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
        # arc-length position (0..1) of the nearest outer-contour point, for rim lights
        cs, _ = cv2.findContours(mb, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        c = max(cs, key=len)[:, 0, :]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
        zero = np.ones_like(mb)
        zero[c[:, 1], c[:, 0]] = 0
        _, lab = cv2.distanceTransformWithLabels(zero, cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
        par = np.zeros(mb.shape, np.float32)
        par[c[:, 1], c[:, 0]] = arc / arc[-1]
        zy, zx = np.nonzero(zero == 0)
        self.edge_param = par[zy, zx][lab - 1]
        self.edge_band = (np.exp(-(np.clip(sd, 0, None) / (bevel * ts * 0.9)) ** 2) * (sd > -1.5)).astype(np.float32)
        dg = self.X * 0.82 + self.Y * 0.57
        inside = m > 0.5
        self.diag = ((dg - dg[inside].min()) / (dg[inside].max() - dg[inside].min())).astype(np.float32)
        self.corners = np.array([[self.ox - self.cx, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / ts, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / ts, self.oy - self.cy + self.h / ts],
                                 [self.ox - self.cx, self.oy - self.cy + self.h / ts]], np.float64)


SYM = Obj([0], depth=16, bevel=4, ts=max(1.6, 3.2 * SC))
SYM_W = 600.0  # symbol width in svg units
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


def shade(o, n, R, T, z, yaw, env_k, soft=0.0, spread=2.2):
    Rf = R.astype(np.float32)
    nc = n @ Rf.T
    P = np.stack([o.X, o.Y, np.full_like(o.X, z)], -1) @ Rf.T + T.astype(np.float32)
    v = P * np.array([spread, spread, 1.0], np.float32)
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    d = np.sum(v * nc, -1, keepdims=True)
    r = v - 2 * d * nc
    u = 0.5 + (np.arctan2(r[..., 0], -r[..., 2]) + yaw) / (2 * np.pi) * 1.3
    vv = 0.5 + np.arcsin(np.clip(r[..., 1], -1, 1)) / np.pi * 1.2
    mx = (u % 1.0) * (ENV.shape[1] - 1)
    my = np.clip(vv, 0, 1) * (ENV.shape[0] - 1)
    mx, my = mx.astype(np.float32), my.astype(np.float32)
    col = cv2.remap(ENV, mx, my, cv2.INTER_LINEAR)
    if soft > 0:
        col = col * (1 - soft) + cv2.remap(ENV_SOFT, mx, my, cv2.INTER_LINEAR) * soft
    fres = 0.55 + 0.45 * (1 - np.abs(d)) ** 3
    return (col * fres + 0.018) * env_k  # graphite base + glossy reflections


def draw_obj(layer, cam, o, R, T, depth_k=1.0, yaw=0.0, env_k=1.0, white=0.0, emit=1.12, alpha=1.0,
             rim=0.0, rim_p=0.0, drain=None):
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
    wfront = 0.0
    if drain is not None:  # light switches off from one side to the other
        wmap = np.clip((o.diag - drain) / 0.16 + 0.5, 0, 1)
        wmap = wmap * wmap * (3 - 2 * wmap)
        white = np.maximum(wmap, white)[..., None]
        wfront = (np.exp(-((o.diag - drain) / 0.06) ** 2) * 0.55)[..., None] * (drain < 1.1) * (drain > -0.1)
    front_visible = float(np.dot(R @ np.array([0, 0, -1.0]), T + R @ np.array([0, 0, 0.0]))) < 0
    seq = []
    if depth > 0.3:
        plen = np.abs(p1 - p0).max()
        ns = int(np.clip(plen * 1.6 + 2, 2, 300))
        wall = shade(o, o.nwall, R, T, depth * 0.5, yaw, env_k * 0.9)
        wall = wall * (1 - white) + white * emit * 0.7 + wfront * 0.5
        src = np.concatenate([wall * m4, m4], -1).astype(np.float32)
        zs = [i / ns * depth for i in range(ns, 0, -1)] if front_visible else [i / ns * depth for i in range(0, ns)]
        for z in zs:
            seq.append((z, src, lerp(1.0, 0.55, z / max(depth, 1e-6)) if front_visible else lerp(0.55, 1.0, z / max(depth, 1e-6))))
    if front_visible:
        face = shade(o, o.nface, R, T, 0.0, yaw, env_k, soft=0.8, spread=1.5)
        zf = 0.0
        if rim > 0:  # one faint glint gliding along the bevel
            dd = np.abs(((o.edge_param - rim_p) + 0.5) % 1.0 - 0.5)
            g = np.exp(-(dd / 0.09) ** 2)
            face = face + (o.edge_band * g * 1.1)[..., None] * rim
    else:
        face = shade(o, o.nback, R, T, depth, yaw, env_k, soft=0.8, spread=1.5)
        zf = depth
    face = face * (1 - white) + white * emit + wfront
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
    """Lens-shaped line of light from p to q (thick in the middle, tapering to points).
    Short lines collapse to a round dot; the halo is isotropic so nothing reads as a cross."""
    p, q = np.asarray(p, np.float32), np.asarray(q, np.float32)
    dv = q - p
    L = float(np.linalg.norm(dv))
    hs = 10 * SC + width * 4  # halo sigma
    pad = hs * 4 + width * 4
    xa, xb = int(max(min(p[0], q[0]) - pad, 0)), int(min(max(p[0], q[0]) + pad, W))
    ya, yb = int(max(min(p[1], q[1]) - pad, 0)), int(min(max(p[1], q[1]) + pad, H))
    if xa >= xb or ya >= yb:
        return
    gx, gy = XX[ya:yb, xa:xb] - p[0], YY[ya:yb, xa:xb] - p[1]
    if L < 1e-3:
        d2 = gx * gx + gy * gy
        prof = np.ones_like(d2)
    else:
        u = dv / L
        s = (gx * u[0] + gy * u[1]) / L
        perp = gx * (-u[1]) + gy * u[0]
        sc = np.clip(s, 0, 1)
        along = (s - sc) * L
        d2 = perp * perp + along * along
        prof = np.sqrt(np.clip(1 - (2 * sc - 1) ** 2, 0, 1))
    k = min(L / (12 * width + 1e-6), 1.0)  # 0 -> round dot, 1 -> tapered sliver
    wd = width * ((1 - k) + k * (0.2 + 0.8 * prof))
    core = np.exp(-d2 / (2 * wd * wd + 1e-6)) * 3.0
    halo = np.exp(-d2 / (2 * hs * hs)) * 0.3
    dst[ya:yb, xa:xb] += ((core + halo) * inten)[..., None] * WHITE


# ---------------------------------------------------------------- choreography
def mat2quat(R):
    w = math.sqrt(max(0.0, 1 + R[0, 0] + R[1, 1] + R[2, 2])) / 2
    x = math.copysign(math.sqrt(max(0.0, 1 + R[0, 0] - R[1, 1] - R[2, 2])) / 2, R[2, 1] - R[1, 2])
    y = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] + R[1, 1] - R[2, 2])) / 2, R[0, 2] - R[2, 0])
    z = math.copysign(math.sqrt(max(0.0, 1 - R[0, 0] - R[1, 1] + R[2, 2])) / 2, R[1, 0] - R[0, 1])
    q = np.array([w, x, y, z])
    return q / np.linalg.norm(q)


def quat2mat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def slerp_to_identity(R, f):
    q = mat2quat(R)
    if q[0] < 0:
        q = -q
    ang = math.acos(min(1.0, q[0]))
    if ang < 1e-6 or f <= 0:
        return R
    s0 = math.sin((1 - f) * ang) / math.sin(ang)
    s1 = math.sin(f * ang) / math.sin(ang)
    return quat2mat(q * s0 + np.array([1, 0, 0, 0]) * s1)


def sym_pose(t):
    """Symbol rotation matrix — overlapping sine-eased moves, no flips."""
    # sliver: plate edge-on (rx~90), long axis turning from vertical to a shallow tilt
    rz = lerp(90, 14, ease(seg(t, 0.75, 1.55)))
    rx = 89.5
    # opens along its long axis like a lid, lying back
    o = ease(seg(t, 1.40, 2.10))
    rx = lerp(rx, 54, o)
    rz = lerp(rz, 6, o)
    ry = lerp(0, -8, o)
    # gentle turn about the plate's own normal
    spin = lerp(0, -18, ease(seg(t, 1.45, 4.8)))
    c, s_ = math.cos(math.radians(spin)), math.sin(math.radians(spin))
    R = rot(rx, ry, rz) @ np.array([[c, -s_, 0], [s_, c, 0], [0, 0, 1]])
    # stand up to face front along the shortest arc
    return slerp_to_identity(R, ease(seg(t, 4.20, 5.20)))


def camera(t):
    f = ease(seg(t, 4.20, 5.20))
    tgt = lerpv([0, 0, 0], LOGO_C, f)
    d0 = lerp(1950, 1700, ease(seg(t, 0.0, 4.4)))  # continuous slow push-in
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
    R = sym_pose(t)
    _, T = cam.pose(R, [0, 0, 0])

    plate_on = ease(seg(t, 1.38, 1.62))
    drain = lerp(-0.25, 1.25, ease(seg(t, 2.10, 3.40)))  # light switches off across the plate
    flat = ease(seg(t, 5.00, 5.45))
    white = flat
    emit = 1.3
    depth_k = lerp(0.0, 1.0, ease(seg(t, 2.3, 3.5))) * (1 - ease(seg(t, 4.9, 5.3)))
    yaw = lerp(-1.1, 0.7, ease(seg(t, 2.9, 4.9)))    # one broad soft reflection gliding across
    env_k = lerp(1.0, 0.85, ease(seg(t, 4.4, 5.0)))
    rim = math.sin(math.pi * seg(t, 3.4, 4.7)) ** 2 * (1 - flat)
    rim_p = lerp(0.0, 0.42, ease(seg(t, 3.4, 4.7)))
    if plate_on > 0:
        draw_obj(layer, cam, SYM, R, T, depth_k=depth_k, yaw=yaw, env_k=env_k, white=white, emit=emit,
                 alpha=plate_on, rim=rim, rim_p=rim_p, drain=drain if t < 3.6 else None)
    wa = ease(seg(t, 4.55, 5.20))
    if wa > 0:
        _, Tw = cam.pose(np.eye(3), world_off(WORD))
        draw_obj(layer, cam, WORD, np.eye(3), Tw, depth_k=0.6 * (1 - flat), yaw=yaw, env_k=lerp(0.4, 0.9, wa),
                 white=flat, alpha=wa)
    rgb, a = layer
    v = ease(seg(t, 5.30, 5.55))
    if v > 0:
        vec = vec_final()
        rgb[:] = rgb * (1 - v) + vec[..., None] * 1.12 * v
        a[:] = a * (1 - v) + vec * v
    f = f * (1 - a[..., None]) + rgb

    # point -> sliver: the plate seen exactly edge-on, crossfading into the opening plate
    lk = 1 - ease(seg(t, 1.40, 1.60))
    if lk > 0:
        grow = ease(seg(t, 0.30, 0.95))
        half = SYM_W / 2 * grow
        R0 = rot(89.5, 0, lerp(90, 14, ease(seg(t, 0.75, 1.55))))
        ends, _ = project(cam, R0, cam.pose(R0, [0, 0, 0])[1], np.array([[-half, 0, 0], [half, 0, 0]]))
        inten = ease(seg(t, 0.0, 0.40)) * lk
        sliver(f, ends[0], ends[1], width=lerp(1.6, 1.25, grow) * SC * 2, inten=inten)
    return f


def finish(img, t):
    lum = img.mean(-1)
    br = img * np.clip((lum - 0.55) / 0.6, 0, 1)[..., None]
    small = cv2.resize(br, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 2.5 * SC) * 0.5 + cv2.GaussianBlur(small, (0, 0), 12 * SC) * 0.6
    bk = lerp(0.5, 0.12, ease(seg(t, 2.1, 3.3)))  # the halo fades together with the light
    bk = lerp(bk, 0.35, ease(seg(t, 5.0, 5.45)))
    img = img + cv2.resize(bloom, (W, H)) * bk
    img = np.where(img < 0.85, img, 0.85 + 0.15 * np.tanh((img - 0.85) / 0.15))
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    rng = np.random.default_rng(int(t * 1000))
    img = img + rng.normal(0, 0.003, (H, W, 1)).astype(np.float32)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


def nsub(t):
    if 2.0 < t < 3.5:
        return 4
    if 0.7 < t < 2.2:
        return 4
    return 3


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
