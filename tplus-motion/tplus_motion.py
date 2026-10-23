#!/usr/bin/env python3
"""T PLUS logo motion (hero background) — 1920x1080, 6s, 30fps.

Shot list
  0.00-0.55  anamorphic light line ignites
  0.42-1.55  macro chrome edge (Nano Banana Pro still, virtual camera move)
  1.45-2.55  whip pan -> 3/4 chrome symbol (Nano Banana Pro still)
  2.45-2.70  white flash
  2.56-4.60  real 3D: exact SVG extruded, chrome env-reflection shading,
             symbol spins in, wordmark letters flip in
  4.60-5.40  light sweep, extrusion flattens, chrome -> flat white 2D
  5.40-6.00  hold (logo parked on the right third, away from centre UI)

usage: python tplus_motion.py [--frames a:b] [--only 10,40] [--workers N]
"""
import argparse
import math
import os
import re
from multiprocessing import Pool

import cairosvg
import cv2
import numpy as np

W, H, FPS, DUR = 1920, 1080, 30, 6.0
NF = int(round(DUR * FPS))
ROOT = os.path.dirname(os.path.abspath(__file__))
AS = os.path.join(ROOT, "assets")
OUT = os.path.join(ROOT, "frames")
cv2.setNumThreads(1)

# final logo placement (screen px) — right third, clear of the centred hero copy
FINAL_CX, FINAL_CY, FINAL_H = 1490.0, 545.0, 330.0
FOCAL = 1600.0


# ---------------------------------------------------------------- easing
def seg(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


def smooth(x):
    return x * x * (3 - 2 * x)


def out_cubic(x):
    return 1 - (1 - x) ** 3


def out_quint(x):
    return 1 - (1 - x) ** 5


def in_cubic(x):
    return x ** 3


def lerp(a, b, x):
    return a + (b - a) * x


def pulse(t, c, w):
    return math.exp(-((t - c) / w) ** 2)


# ---------------------------------------------------------------- assets
def load(name, size=None):
    im = cv2.imread(os.path.join(AS, name), cv2.IMREAD_COLOR)
    if size:
        im = cv2.resize(im, size, interpolation=cv2.INTER_AREA)
    im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return im ** 2.2  # work in linear light


ENV = cv2.GaussianBlur(load("env.png", (2048, 869)), (0, 0), 1.5)
ENV = ENV * 1.6 + 0.012
BG = load("bg.png", (2304, 1296))
MACRO = load("macro.png", (2752, 1536))
ANGLE = load("angle.png", (2752, 1536))
FLARE = load("flare.png", (1920, 1072))
GLINT = load("glint.png", (640, 640))
STREAK = load("streaks.png", (2304, 1296))
HERO = load("hero_full.png", (2752, 1536))

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


def align_hero():
    """Affine map svg-units -> HERO pixels, fitted with ECC on silhouettes."""
    ds = 4
    hl = cv2.resize(HERO, (HERO.shape[1] // ds, HERO.shape[0] // ds), interpolation=cv2.INTER_AREA)
    hm = (hl.mean(-1) ** (1 / 2.2) > 0.18).astype(np.float32)
    sm = raster(range(len(PATHS)), scale=1.0)
    ys, xs = np.nonzero(hm > 0.5)
    yv, xv = np.nonzero(sm > 0.5)
    s = (ys.max() - ys.min()) / (yv.max() - yv.min())
    A0 = np.array([[s, 0, xs.min() - s * xv.min()], [0, s, ys.min() - s * yv.min()], [0, 0, 1]])
    src = cv2.warpAffine(sm, A0[:2].astype(np.float32), (hm.shape[1], hm.shape[0]))
    tpl = cv2.GaussianBlur(hm, (0, 0), 1.5)
    src = cv2.GaussianBlur(src, (0, 0), 1.5)
    Wc = np.eye(2, 3, dtype=np.float32)
    try:
        crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7)
        cc, Wc = cv2.findTransformECC(tpl, src, Wc, cv2.MOTION_AFFINE, crit, None, 5)
    except cv2.error:
        cc = -1.0
    # ECC: src(Wc x) ~ hero(x)  ->  hero = inv(Wc) . A0 . svg
    A = np.linalg.inv(np.vstack([Wc, [0, 0, 1]])) @ A0
    return A[:2] * ds, cc


HERO_A, HERO_CC = align_hero()


class Obj:
    """Extruded, bevelled slab built from a subset of the SVG paths."""

    def __init__(self, idx, depth, bevel):
        full = raster(idx)
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
        hgt = 0.45 * x + 0.55 * np.sqrt(1 - (1 - x) ** 2)
        hgt = cv2.GaussianBlur(hgt, (0, 0), 1.0)
        gy, gx = np.gradient(hgt)
        k = bevel * TS * 0.8
        n = np.stack([-gx * k, -gy * k, -np.ones_like(gx)], -1)
        self.nface = (n / np.linalg.norm(n, axis=-1, keepdims=True)).astype(np.float32)
        gy2, gx2 = np.gradient(cv2.GaussianBlur(sd, (0, 0), 2.5))
        wn = np.stack([-gx2, -gy2, np.zeros_like(gx2)], -1)
        self.nwall = (wn / (np.linalg.norm(wn, axis=-1, keepdims=True) + 1e-6)).astype(np.float32)
        u = (np.arange(self.w) / TS + self.ox - self.cx).astype(np.float32)
        v = (np.arange(self.h) / TS + self.oy - self.cy).astype(np.float32)
        self.X, self.Y = np.meshgrid(u, v)
        # AI chrome render resampled onto this object's texels (front view only)
        su = np.arange(self.w, dtype=np.float32)[None, :] / TS + self.ox
        sv = np.arange(self.h, dtype=np.float32)[:, None] / TS + self.oy
        su, sv = np.broadcast_to(su, m.shape), np.broadcast_to(sv, m.shape)
        mx = HERO_A[0, 0] * su + HERO_A[0, 1] * sv + HERO_A[0, 2]
        my = HERO_A[1, 0] * su + HERO_A[1, 1] * sv + HERO_A[1, 2]
        self.ai = cv2.remap(HERO, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT)
        self.corners = np.array([[self.ox - self.cx, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / TS, self.oy - self.cy],
                                 [self.ox - self.cx + self.w / TS, self.oy - self.cy + self.h / TS],
                                 [self.ox - self.cx, self.oy - self.cy + self.h / TS]], np.float64)


SYM = Obj([0], depth=70, bevel=7)
# wordmark letters left->right: T P L U S ( + )
LETTERS = [Obj(i, depth=18, bevel=2.2) for i in ([4], [2], [3], [8, 9, 10], [1], [6], [5], [7])]

# final scale: px per svg unit; full logo spans y 47..836 in svg units
FINAL_S = FINAL_H / (835.6 - 47.1)
LOGO_CX, LOGO_CY = (82.7 + 1103.8) / 2, (47.1 + 835.6) / 2
FINAL_Z = FOCAL / FINAL_S


def final_screen(o):
    return (FINAL_CX + (o.cx - LOGO_CX) * FINAL_S, FINAL_CY + (o.cy - LOGO_CY) * FINAL_S)


def rot(rx, ry, rz):
    rx, ry, rz = map(math.radians, (rx, ry, rz))
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


K = np.array([[FOCAL, 0, W / 2], [0, FOCAL, H / 2], [0, 0, 1]])


def pose_T(sx, sy, Z):
    return np.array([(sx - W / 2) * Z / FOCAL, (sy - H / 2) * Z / FOCAL, Z])


def homog(o, R, T, z):
    A = np.array([[1 / TS, 0, o.ox - o.cx], [0, 1 / TS, o.oy - o.cy], [0, 0, 1]])
    M = np.column_stack([R[:, 0], R[:, 1], R @ np.array([0, 0, z]) + T])
    return K @ M @ A


def project(R, T, pts):
    P = pts @ R.T + T
    return np.stack([FOCAL * P[:, 0] / P[:, 2] + W / 2, FOCAL * P[:, 1] / P[:, 2] + H / 2], -1)


def shade(o, n, R, T, z, yaw):
    nc = n @ R.T.astype(np.float32)
    P = np.stack([o.X, o.Y, np.full_like(o.X, z)], -1) @ R.T.astype(np.float32) + T.astype(np.float32)
    v = P * np.array([3.2, 3.2, 1.0], np.float32)  # exaggerate view spread -> richer reflections
    v /= np.linalg.norm(v, axis=-1, keepdims=True)
    d = np.sum(v * nc, -1, keepdims=True)
    r = v - 2 * d * nc
    u = 0.5 + (np.arctan2(r[..., 0], -r[..., 2]) + yaw) / (2 * np.pi) * 1.6
    vv = 0.5 + np.arcsin(np.clip(r[..., 1], -1, 1)) / np.pi * 1.4
    mx = (u % 1.0) * (ENV.shape[1] - 1)
    my = np.clip(vv, 0, 1) * (ENV.shape[0] - 1)
    col = cv2.remap(ENV, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR)
    fres = 0.75 + 0.25 * (1 - np.abs(d)) ** 2
    fill = np.clip(0.35 - 1.2 * r[..., 1:2], 0, 1) * 0.07  # soft overhead fill
    return (col + fill) * fres * np.array([0.92, 0.97, 1.06], np.float32)


def draw_obj(layer, o, R, T, depth_k, yaw, white, ai_w, alpha=1.0):
    """Painter's-algorithm render: extrusion slices back->front, then bevelled face."""
    rgb, a = layer
    depth = o.depth * depth_k
    c3 = np.column_stack([o.corners, np.zeros(4)])
    pts = np.vstack([project(R, T, c3), project(R, T, c3 + [0, 0, depth])])
    x0, y0 = np.floor(pts.min(0)).astype(int) - 2
    x1, y1 = np.ceil(pts.max(0)).astype(int) + 2
    x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if x1 <= x0 or y1 <= y0:
        return
    rw, rh = x1 - x0, y1 - y0
    Tr = np.array([[1, 0, -x0], [0, 1, -y0], [0, 0, 1]])
    m4 = o.mask[..., None]
    seq = []  # (z, premultiplied rgba texture, brightness)
    if depth > 0.5:
        plen = np.abs(project(R, T, c3 + [0, 0, depth]) - project(R, T, c3)).max()
        ns = int(np.clip(plen * 2.0 + 2, 2, 170))
        wall = shade(o, o.nwall, R, T, depth * 0.5, yaw)
        wall = wall * (1 - white) + white * 0.55
        src = np.concatenate([wall * m4, m4], -1).astype(np.float32)
        for i in range(ns, 0, -1):
            f = i / ns
            seq.append((f * depth, src, lerp(1.0, 0.28, f)))
    face = shade(o, o.nface, R, T, 0.0, yaw)
    if ai_w > 0:
        face = face * (1 - ai_w) + o.ai * 1.15 * ai_w
    face = face * (1 - white) + white * 1.12
    seq.append((0.0, np.concatenate([face * m4, m4], -1).astype(np.float32), 1.0))
    lr, la = rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]
    for z, src, k in seq:
        wp = cv2.warpPerspective(src, Tr @ homog(o, R, T, z), (rw, rh), flags=cv2.INTER_LINEAR)
        sa = wp[..., 3:4] * alpha
        lr *= 1 - sa
        lr += wp[..., :3] * (alpha * k)
        la *= 1 - sa[..., 0]
        la += sa[..., 0]


def card(img, zoom, yaw=0.0, pitch=0.0, roll=0.0, dx=0.0, dy=0.0):
    """Virtual camera move over a still: rotation homography + zoom (cover-fit)."""
    h, w = img.shape[:2]
    s0 = max(W / w, H / h)
    fi = FOCAL / (s0 * zoom)
    Kin = np.array([[fi, 0, w / 2], [0, fi, h / 2], [0, 0, 1]])
    Ko = np.array([[FOCAL, 0, W / 2 + dx], [0, FOCAL, H / 2 + dy], [0, 0, 1]])
    Hm = Ko @ rot(pitch, yaw, roll) @ np.linalg.inv(Kin)
    return cv2.warpPerspective(img, Hm, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), Hm


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
XN, YN = XX / W, YY / H


def hblur(img, length):
    """Horizontal motion blur (camera whip)."""
    n = int(abs(length))
    if n < 3:
        return img
    out = img
    for _ in range(3):  # 3 box passes ~ smooth gaussian-ish streak
        out = cv2.blur(out, (max(3, n // 2 | 1), 1))
    return out


def sweep(img, p, ang=-0.55, width=0.07, gain=2.2):
    """Moving specular band, only where the still already has metal highlights."""
    lum = img.mean(-1)
    metal = np.clip((lum ** (1 / 2.2) - 0.18) / 0.5, 0, 1)
    coord = XN * math.cos(ang) + YN * math.sin(ang)
    band = np.exp(-((coord - p) / width) ** 2)
    return img + (band * metal)[..., None] * gain * np.array([0.85, 0.93, 1.0], np.float32)


def add_sprite(dst, spr, cx, cy, scale, gain, sx=1.0, sy=1.0, angle=0.0):
    h, w = spr.shape[:2]
    ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    M2 = np.array([[ca, -sa], [sa, ca]]) @ np.diag([scale * sx, scale * sy])
    M = np.column_stack([M2, np.array([cx, cy]) - M2 @ np.array([w / 2, h / 2])])
    dst += cv2.warpAffine(spr, M, (W, H), flags=cv2.INTER_LINEAR) * gain


def drift(img, t, zoom0, zoom1, vx, vy):
    z = lerp(zoom0, zoom1, t / DUR)
    out, _ = card(img, z, dx=vx * t, dy=vy * t)
    return out


# ---------------------------------------------------------------- shots
def shot_3d(t, frame):
    pr = out_cubic(seg(t, 2.56, 4.35))
    p = smooth(seg(t, 2.6, 4.3))
    R = rot(lerp(-20, 0, pr), lerp(70, 0, pr), lerp(-14, 0, pr))
    fx, fy = final_screen(SYM)
    Z = math.exp(lerp(math.log(1000), math.log(FINAL_Z), p))
    sx, sy = lerp(820, fx, p), lerp(640, fy, p)
    depth_k = 1 - smooth(seg(t, 4.75, 5.15))
    white = smooth(seg(t, 4.85, 5.3))
    ai_w = 0.75 * smooth(seg(t, 3.9, 4.5)) * (1 - white)
    yaw = lerp(1.4, 0.0, out_cubic(seg(t, 2.56, 4.3))) + 0.9 * smooth(seg(t, 4.3, 4.85)) - 0.45
    layer = (np.zeros((H, W, 3), np.float32), np.zeros((H, W), np.float32))
    objs = []
    for i, o in enumerate(LETTERS):
        st = 3.25 + 0.06 * i
        q = out_cubic(seg(t, st, st + 0.75))
        if t < st:
            continue
        lx, ly = final_screen(o)
        Rl = rot(lerp(25, 0, q), lerp(-84, 0, q), 0)
        Tl = pose_T(lx + lerp(70, 0, q), ly, FINAL_Z * lerp(1.25, 1.0, q))
        objs.append((Tl[2], o, Rl, Tl, min(1.0, seg(t, st, st + 0.12))))
    objs.append((pose_T(sx, sy, Z)[2], SYM, R, pose_T(sx, sy, Z), 1.0))
    for _, o, Ro, To, al in sorted(objs, key=lambda e: -e[0]):
        draw_obj(layer, o, Ro, To, depth_k, yaw, white, ai_w, al)
    rgb, a = layer
    # vector swap at the very end keeps the 2D logo pixel-crisp
    v = smooth(seg(t, 5.2, 5.45))
    if v > 0:
        vec = VEC_FINAL
        rgb[:] = rgb * (1 - v) + vec[..., None] * 1.12 * v
        a[:] = a * (1 - v) + vec * v
    bgk = lerp(0.85, 0.42, smooth(seg(t, 2.56, 4.6)))
    bg = drift(BG, t, 1.12, 1.02, -6, 0) * bgk
    frame[:] = bg * (1 - a[..., None]) + rgb
    # glint on the symbol's top-right tip during the settle
    tip = project(R, pose_T(sx, sy, Z), np.array([[872.0 - SYM.cx, 48.5 - SYM.cy, 0]]))[0]
    g = pulse(t, 4.62, 0.09)
    if g > 0.01:
        add_sprite(frame, GLINT, tip[0], tip[1], 0.55 + 0.35 * g, 1.6 * g, angle=12 * g)
    # speed streak riding through right after the flash
    s = seg(t, 2.56, 3.05)
    if 0 < s < 1:
        out, _ = card(STREAK, 1.15, dx=lerp(900, -1400, out_cubic(s)), roll=-4)
        frame += out * 0.9 * math.sin(math.pi * s)


def render(t):
    f = np.zeros((H, W, 3), np.float32)
    # macro chrome edge
    if 0.40 < t < 1.62:
        q = seg(t, 0.42, 1.55)
        dxw = -2600 * in_cubic(seg(t, 1.45, 1.58))
        vel = 2600 * 3 * seg(t, 1.45, 1.58) ** 2 / 0.13 / FPS
        img, _ = card(MACRO, lerp(1.5, 1.16, out_cubic(q)), yaw=lerp(-5, 3, q), roll=lerp(7, 0, out_cubic(q)),
                      dx=lerp(90, -60, q) + dxw, dy=lerp(-40, 20, q))
        img = hblur(sweep(img, lerp(-0.25, 1.35, smooth(seg(t, 0.55, 1.45)))), vel * 0.8)
        f += img * smooth(seg(t, 0.40, 0.56))
    # 3/4 chrome symbol
    if 1.48 < t < 2.62:
        q = seg(t, 1.5, 2.6)
        dxw = 2600 * (1 - out_cubic(seg(t, 1.48, 1.68)))
        vel = 2600 * 3 * (1 - seg(t, 1.48, 1.68)) ** 2 / 0.2 / FPS if t < 1.68 else 0
        img, Hm = card(ANGLE, lerp(1.05, 1.24, q), yaw=lerp(6, -5, q), pitch=lerp(2, -1, q),
                       dx=dxw + lerp(-40, 40, q))
        img = sweep(img, lerp(-0.2, 1.3, smooth(seg(t, 1.75, 2.4))), ang=-0.9)
        tip = Hm @ np.array([0.654 * ANGLE.shape[1], 0.262 * ANGLE.shape[0], 1])
        g = pulse(t, 2.18, 0.07)
        if g > 0.01:
            add_sprite(img, GLINT, tip[0] / tip[2], tip[1] / tip[2], 0.6 + 0.4 * g, 1.8 * g, angle=20 * g)
        f += hblur(img, vel * 0.8) * smooth(seg(t, 1.48, 1.56))
    if t >= 2.56:
        shot_3d(t, f)
    # anamorphic line ignite
    li = smooth(seg(t, 0.0, 0.32)) * (1 - smooth(seg(t, 0.5, 0.75)))
    if li > 0:
        add_sprite(f, FLARE, W / 2, H / 2, 1.0, 1.6 * li, sx=lerp(0.25, 1.6, out_cubic(seg(t, 0, 0.55))), sy=0.7)
    # flashes: into macro, and into the 3D shot
    fl = 0.8 * pulse(t, 0.47, 0.045) + 1.1 * pulse(t, 2.56, 0.045)
    if fl > 0.005:
        add_sprite(f, FLARE, W / 2, H / 2, 1.0, 1.4 * fl, sx=2.2, sy=1.4)
        f += fl * 0.55 * np.array([0.8, 0.9, 1.0], np.float32)
    return f


def finish(img, t):
    lum = img.mean(-1)
    br = img * np.clip((lum - 0.5) / 0.6, 0, 1)[..., None]
    small = cv2.resize(br, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    bloom = cv2.GaussianBlur(small, (0, 0), 3) * 0.5 + cv2.GaussianBlur(small, (0, 0), 14) * 0.6
    streak = cv2.GaussianBlur(small, (0, 0), sigmaX=90, sigmaY=0.8) * np.array([0.5, 0.72, 1.0], np.float32)
    end = 1 - 0.6 * smooth(seg(t, 5.0, 5.6))
    img = img + cv2.resize(bloom, (W, H)) * 0.55 * end + cv2.resize(streak, (W, H)) * 0.7 * end ** 2
    img = img * VIG
    img = np.where(img < 0.82, img, 0.82 + 0.18 * np.tanh((img - 0.82) / 0.18))
    img = np.clip(img, 0, 1) ** (1 / 2.2)
    rng = np.random.default_rng(int(t * 1000))
    img = img + rng.normal(0, 0.006, (H, W, 1)).astype(np.float32)
    return (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)


r2 = ((XN - 0.5) * 1.1) ** 2 + (YN - 0.5) ** 2
VIG = (1 - 0.55 * np.clip(r2 / 0.5, 0, 1) ** 1.4)[..., None].astype(np.float32)

# exact vector logo at its final screen position
_fw, _fh = int(round(VBW * FINAL_S * 4)), int(round(VBH * FINAL_S * 4))
_v = raster(range(len(PATHS)), w=_fw, h=_fh)
_M = np.array([[0.25, 0, FINAL_CX - LOGO_CX * FINAL_S], [0, 0.25, FINAL_CY - LOGO_CY * FINAL_S]], np.float32)
VEC_FINAL = cv2.warpAffine(_v, _M, (W, H), flags=cv2.INTER_AREA)


def nsub(t):
    if 2.45 < t < 2.70:
        return 5
    if t < 4.4:
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
    print("hero ECC", HERO_CC, flush=True)
    if a.only:
        ids = [int(x) for x in a.only.split(",")]
    else:
        s, e = map(int, a.frames.split(":"))
        ids = list(range(s, e))
    with Pool(a.workers) as pool:
        for i in pool.imap_unordered(do_frame, ids):
            print("done", i, flush=True)
