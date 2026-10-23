"""Segment 00:01:39:10-00:01:47:12 - "업무와 데이터가 연결될수록 / AI는 더 빠르게 이해하고 더 정확하게 판단합니다".
Replaces SC21 (aerial city). AI given a shape: a living network that grows solid and smart, then floods the lens.

  0.00-2.40  deep-navy space of drifting network nodes; lines flicker on and off as nodes pass each other,
             data tags (values, icons, code) float through ("업무와 데이터가 연결될수록")
  1.45-4.00  the nearby nodes leave together and swirl in on one smooth vortex into a geodesic structure
             (no straight-line darts, no tangle of links while they travel); signals race along its edges
             faster and faster ("AI는 더 빠르게 이해하고")
  3.60-5.80  the structure tightens: jitter dies, lattice edges sharpen, facets fill, precision rings lock and
             the core condenses to a bright point ("더 정확하게 판단합니다")
  5.30-7.05  light bursts from the core and the camera rushes into it; the frame floods white
Hand-overs: SC20 -> this shot with the film's line-particle wipe (99.43-100.38, as before), but the line bundles
keep flowing on and out of frame instead of vanishing; this shot -> FIN through the white flash (peak 106.95,
FIN's warm white is revealed by 107.40). From the first frame the camera flies in through the field, data streams
curve into the structure and links fire across the network.
Shot clock u = film time - 99.90 (SC21's start). Frame f is film time (2386 + f) / 24. Film finish; 21:9 letterbox.
Usage: python3 seg_ai.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import scenes as S
from engine import W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_in_cubic, e_io_sine, paint_fill, paint_stroke, colint

SEG0 = 99 * 24 + 10            # first frame delivered: 00:01:39:10 (SC20 still pure)
NF = 107 * 24 + 12 - SEG0 + 1  # through 00:01:47:12 (FIN pure again)
U0 = 99.9                      # shot clock zero (SC21's original start)
BAR = 138
FPS_NUM, FPS_DEN = 24000, 1001
F = 1100.0
CX, CY = W / 2, H / 2 + 10
C3 = np.array([0.0, -60.0, 3600.0])     # the structure's centre (world)
RAD = 560.0
SC20 = [sc for sc in S.SCENES if sc[0] == "sc20"][0]
FIN = [sc for sc in S.SCENES if sc[0] == "fin"][0]
TR_TYPE, TR_D, TR_KW = S.TRANS["sc21"]
TR0 = U0 - TR_D / 2
FLASH_PEAK, FLASH_OUT = 106.95, 0.45
HD = False

LINE = "#4A8DFF"
LINE_HI = "#9CCBFF"
GLOW = "#4FA3FF"


# ------------------------------------------------------------------ the network
def icosphere(level=2):
    t = (1 + 5 ** 0.5) / 2
    V = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    V = [np.array(v, float) / np.linalg.norm(v) for v in V]
    Fc = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
          (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
          (8, 6, 7), (9, 8, 1)]
    for _ in range(level):
        cache, nf = {}, []

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in cache:
                m = V[a] + V[b]
                V.append(m / np.linalg.norm(m))
                cache[k] = len(V) - 1
            return cache[k]
        for a, b, c in Fc:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        Fc = nf
    edges = sorted({(min(a, b), max(a, b)) for f in Fc for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))})
    return np.array(V), Fc, edges


SPH_V, SPH_F, SPH_E = icosphere(2)          # 162 vertices, 320 faces, 480 edges
IN_V, IN_F, IN_E = icosphere(1)             # inner shell (42 vertices), counter-rotating
NO = len(SPH_V)
NC = NO + len(IN_V)
# spokes between the shells: each inner vertex to its 3 nearest outer vertices
SPOKES = [(NO + i, int(j)) for i in range(len(IN_V)) for j in np.argsort(-(SPH_V @ IN_V[i]))[:3]]
CL_E = SPH_E + [(NO + a, NO + b) for a, b in IN_E] + SPOKES
IN_R = 0.55
r = np.random.default_rng(2110)
N_VOL, N_GND = 520, 330
N = N_VOL + N_GND
BASE = np.zeros((N, 3))
BASE[:N_VOL] = np.c_[r.uniform(-2500, 2500, N_VOL), r.uniform(-950, 380, N_VOL), r.uniform(500, 6600, N_VOL)]
BASE[N_VOL:] = np.c_[r.uniform(-3200, 3200, N_GND), r.uniform(410, 470, N_GND), r.uniform(400, 7000, N_GND)]
FREQ = r.uniform(0.25, 0.75, (N, 3, 2))
PHASE = r.uniform(0, 2 * np.pi, (N, 3, 2))
AMP = np.where(np.arange(N)[:, None] < N_VOL, 170.0, 60.0) * np.array([1.0, 0.6, 1.0])
# the first NC volume nodes become the structure; pick the ones nearest the centre so the gathering reads
_order = np.argsort(np.linalg.norm((BASE[:N_VOL] - C3) * [1, 1.6, 0.7], axis=1))
CL = _order[:NC]
# the structure's nodes start as a loose cloud around it (part of the field), so gathering reads as the cloud
# condensing - a short, slow inward swirl - rather than nodes darting in from across the frame
_dirs = r.normal(size=(NC, 3))
_dirs /= np.linalg.norm(_dirs, axis=1)[:, None]
BASE[CL] = C3 + _dirs * r.uniform(820, 1500, NC)[:, None] * np.array([1.25, 0.75, 1.0])
AMP[CL] = np.array([90.0, 60.0, 90.0])
# nodes leave for the structure almost together (a short ripple from the nearest outward), not one by one
_dist = np.linalg.norm(BASE[CL] - C3, axis=1)
GATHER_D = 1.45 + 0.55 * (_dist - _dist.min()) / (np.ptp(_dist) + 1e-9) + r.uniform(0, 0.12, NC)
GATHER_LEN = 1.9
SWIRL = 1.1                                   # radians of orbit the nodes sweep through on the way in
SIZE = r.uniform(0.7, 1.5, N)

TAGS = []                                     # floating data tags: (kind, payload, base world pos, phase)
_tr = np.random.default_rng(77)
_icons = ["doc", "db", "chart", "cube", "link", "gear", "user", "mail", "search", "flow", "report", "scan"]
for i in range(22):
    pos = np.array([_tr.uniform(-1900, 1900), _tr.uniform(-760, 360), _tr.uniform(900, 4200)])
    if i % 3 == 0:
        TAGS.append(("code", int(_tr.integers(4, 7)), pos, _tr.uniform(0, 6)))
    elif i % 3 == 1:
        TAGS.append(("num", float(_tr.uniform(1, 99)), pos, _tr.uniform(0, 6)))
    else:
        TAGS.append(("icon", _icons[i % len(_icons)], pos, _tr.uniform(0, 6)))


def camz(u):
    # flies in through the field from the first frame (decelerating), drifts, then rushes into the core
    return 110 * u + 950 * e_out_cubic(prog(u, -0.6, 2.8)) + 2900 * e_in_cubic(prog(u, 5.45, 1.6))


def camx(u):
    return lerp(-220, 160, e_io_sine(clamp(u / 6.0)))      # slow lateral drift: parallax through the field


def spin(u):
    return 0.22 * u + 0.5 * e_io_cubic(prog(u, 2.2, 3.0))


def tight(u):
    return e_io_cubic(prog(u, 3.6, 1.7))


def world(u):
    """Node positions at shot time u."""
    w = np.sin(FREQ[..., 0] * u + PHASE[..., 0]) * 0.6 + np.sin(FREQ[..., 1] * u * 1.7 + PHASE[..., 1]) * 0.4
    P = BASE + w * AMP
    # structure: rotated sphere vertices, a little breathing jitter that dies away as it tightens
    a = spin(u)
    tilt = 0.32
    ct, st = math.cos(tilt), math.sin(tilt)
    def rot(V, a):
        ca, sa = math.cos(a), math.sin(a)
        x, z = V[:, 0] * ca + V[:, 2] * sa, -V[:, 0] * sa + V[:, 2] * ca
        y = V[:, 1] * ct - z * st
        return np.c_[x, y, V[:, 1] * st + z * ct]
    V = np.r_[rot(SPH_V, a), rot(IN_V, 1.5 * a) * IN_R]
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    jit = (1 - tight(u)) * 0.06
    nz = np.sin(FREQ[CL, 0, 0] * u * 2 + PHASE[CL, 0, 0]) * jit
    d1 = np.c_[x, y, z] * RAD * (1 + nz)[:, None]
    g = np.array([e_io_cubic(prog(u, d, GATHER_LEN)) for d in GATHER_D])
    # the way in: a smooth vortex around the structure's axis - direction and distance ease from where each
    # node was to its place on the shell while the whole cloud orbits the same way (no straight-line darts)
    d0 = P[CL] - C3
    r0, r1 = np.linalg.norm(d0, axis=1), np.linalg.norm(d1, axis=1)
    n0, n1 = d0 / r0[:, None], d1 / r1[:, None]
    dirv = n0 * (1 - g)[:, None] + n1 * g[:, None]
    dirv /= np.linalg.norm(dirv, axis=1)[:, None] + 1e-9
    ang = SWIRL * (1 - g)
    ca_, sa_ = np.cos(ang), np.sin(ang)
    dx, dz = dirv[:, 0] * ca_ + dirv[:, 2] * sa_, -dirv[:, 0] * sa_ + dirv[:, 2] * ca_
    rr = r0 * (1 - g) + r1 * g
    P[CL] = C3 + np.c_[dx, dirv[:, 1], dz] * rr[:, None]
    return P, g


def project(P, u):
    z = P[:, 2] - camz(u)
    ok = z > 40
    zz = np.maximum(z, 40)
    return np.c_[CX + F * (P[:, 0] - camx(u)) / zz, CY + F * P[:, 1] / zz], zz, ok


def fog(z):
    return np.clip(1.15 - z / 5200, 0, 1) ** 1.2


# ------------------------------------------------------------------ drawing
def background(c, u):
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, H)],
                                        [E.col("#01050F"), E.col("#030B22"), E.col("#06205A")], [0.0, 0.55, 1.0])
    c.drawPaint(skia.Paint(Shader=sh))
    E.radial(c, CX, H * 0.86, 1100, "#1E56FF", 0.4, skia.BlendMode.kScreen)
    # the glowing ground the network rests on (a flat ellipse of light at the horizon)
    c.save()
    c.translate(CX, H * 0.79)
    c.scale(1.0, 0.16)
    E.radial(c, 0, 0, 1300, "#5C9CFF", 0.55, skia.BlendMode.kScreen)
    E.radial(c, 0, 0, 520, "#DCEBFF", 0.45, skia.BlendMode.kScreen)
    c.restore()


def bucket_paths(segs, nb=8):
    """segs: list of (x0, y0, x1, y1, alpha) -> per-alpha-bucket paths (one draw call each)."""
    out = [skia.Path() for _ in range(nb)]
    for x0, y0, x1, y1, a in segs:
        k = min(nb - 1, int(a * nb))
        out[k].moveTo(x0, y0)
        out[k].lineTo(x1, y1)
    return [((k + 0.5) / nb, p) for k, p in enumerate(out) if not p.isEmpty()]


def draw_network(c, u):
    P, g = world(u)
    S2, Z, ok = project(P, u)
    fg = fog(Z)
    fieldm = np.ones(N, bool)
    fieldm[CL] = False
    fg = np.where(fieldm, fg * (1 - 0.88 * clean(u)), fg)       # the field clears away before the push-in
    tg = tight(u)
    k_near = np.clip((Z - 60) / 300, 0, 1)
    # proximity links (all nodes): flicker on and off as nodes pass each other
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=2)
    thr = 470.0
    ii, jj = np.where(np.triu(D < thr, 1))
    segs = []
    clmask = np.zeros(N, bool)
    clmask[CL] = True
    ci = np.zeros(N)
    ci[CL] = np.clip(g * 4, 0, 1)
    for i, j in zip(ii, jj):
        if not (ok[i] and ok[j]):
            continue
        a = (1 - D[i, j] / thr) ** 1.6 * min(fg[i], fg[j]) * min(k_near[i], k_near[j])
        # nodes on their way into the structure drop their loose links (no tangle while they travel);
        # the lattice takes over once they arrive
        if clmask[i]:
            a *= 1 - ci[i]
        if clmask[j]:
            a *= 1 - ci[j]
        if a > 0.02:
            segs.append((S2[i, 0], S2[i, 1], S2[j, 0], S2[j, 1], min(a, 0.999)))
    for a, pth in bucket_paths(segs):
        c.drawPath(pth, paint_stroke(LINE, a, 1.1, blend=skia.BlendMode.kScreen))
    # the structure's lattice edges
    lat = e_io_cubic(prog(u, 2.4, 1.6))
    if lat > 0:
        segs = []
        for a_, b_ in CL_E:
            i, j = CL[a_], CL[b_]
            if not (ok[i] and ok[j]):
                continue
            a = lat * (g[a_] * g[b_]) ** 1.5 * min(fg[i], fg[j]) * min(k_near[i], k_near[j])
            if a > 0.02:
                segs.append((S2[i, 0], S2[i, 1], S2[j, 0], S2[j, 1], min(a, 0.999)))
        for a, pth in bucket_paths(segs):
            c.drawPath(pth, paint_stroke(GLOW, 0.35 * a, 4.0, blur=4, blend=skia.BlendMode.kScreen))
            c.drawPath(pth, paint_stroke(LINE_HI, (0.45 + 0.45 * tg) * a, 1.0 + 0.5 * tg))
    # facets fill in as it tightens: a faceted crystal
    fac = e_io_sine(prog(u, 4.3, 1.4)) * (1 - e_io_sine(prog(u, 6.2, 0.6)))
    if fac > 0:
        faces = []
        for f in SPH_F:
            idx = [CL[k] for k in f]          # outer shell facets
            if not all(ok[k] for k in idx):
                continue
            pz = np.mean([Z[k] for k in idx])
            n = np.cross(P[idx[1]] - P[idx[0]], P[idx[2]] - P[idx[0]])
            n /= np.linalg.norm(n) + 1e-9
            lit = abs(n @ np.array([-0.4, -0.7, -0.6]))
            faces.append((pz, idx, lit))
        faces.sort(key=lambda q: -q[0])
        for pz, idx, lit in faces:
            pts = [(S2[k, 0], S2[k, 1]) for k in idx]
            c.drawPath(E.poly(pts, True), paint_fill("#5A9BFF", fac * (0.03 + 0.13 * lit)))
    # nodes (and motion streaks while the camera rushes)
    rush = u > 5.4
    zprev = project(world(u - 1 / 48)[0], u - 1 / 48)[0] if rush else None
    for i in range(N):
        if not ok[i]:
            continue
        a = fg[i] * k_near[i]
        if a < 0.03:
            continue
        rad = max(0.8, SIZE[i] * 2.0 * F / Z[i] * (1 + 0.4 * tg if clmask[i] else 1))
        x, y = S2[i]
        if rush and math.hypot(x - zprev[i, 0], y - zprev[i, 1]) > 4:
            px, py = zprev[i]
            c.drawLine(px, py, x, y, paint_stroke("#DCEBFF", a * 0.8, min(rad * 1.4, 6)))
        else:
            c.drawCircle(x, y, min(rad, 9), paint_fill("#EAF3FF", a))
        if Z[i] < 2800 or (clmask[i] and tg > 0.5):
            E.glow_dot(c, x, y, min(rad * 6, 40), GLOW, 0.45 * a)
        if Z[i] < 700 and not rush:                           # out-of-focus foreground bokeh
            c.drawCircle(x, y, 26 * 700 / Z[i], paint_fill("#7FB6FF", 0.10 * a, blur=10))
    # nodes on their way in: bright heads with soft comet trails that trace the swirl
    moving = [k for k in range(NC) if 0.01 < g[k] < 0.995]
    if moving:
        tr = [project(world(u - d)[0][CL], u - d)[0] for d in (0.04, 0.08, 0.12)]
        for k in moving:
            i = CL[k]
            if not ok[i]:
                continue
            w = math.sin(math.pi * g[k]) * fg[i]
            pts = [(S2[i, 0], S2[i, 1])] + [(q[k, 0], q[k, 1]) for q in tr]
            for m in range(3):
                c.drawLine(pts[m][0], pts[m][1], pts[m + 1][0], pts[m + 1][1],
                           paint_stroke("#CFE6FF", 0.55 * w * (1 - m / 3), 1.6 - 0.4 * m))
            E.glow_dot(c, S2[i, 0], S2[i, 1], 14, "#DDEEFF", 0.8 * w)
    return P, S2, Z, ok, g


def _pulse_schedule():
    """Launch times of the lattice signals: the launch rate climbs from 8/s to 70/s as it learns."""
    out, acc, u = [], 0.0, 2.2
    while u < 8.0:
        acc += lerp(8, 70, e_io_cubic(prog(u, 2.2, 2.6))) * 0.005
        while acc >= 1:
            out.append(u)
            acc -= 1
        u += 0.005
    rp = np.random.default_rng(5)
    return np.array(out), rp.integers(0, len(CL_E), len(out)), rp.random(len(out)) < 0.5


PULSE_T, PULSE_E, PULSE_REV = _pulse_schedule()


def draw_pulses(c, u, S2, ok, g):
    """Signals racing along the lattice, faster and more of them as it learns."""
    if u < 2.2:
        return
    speed = lerp(1.4, 4.0, e_io_cubic(prog(u, 2.2, 2.6)))
    lat = e_io_cubic(prog(u, 2.6, 1.8))
    live = np.where((PULSE_T < u) & (PULSE_T > u - 1 / 1.4))[0]
    for k in live:
        q = (u - PULSE_T[k]) * speed
        if not 0 < q < 1:
            continue
        a_, b_ = CL_E[PULSE_E[k]]
        if g[a_] * g[b_] < 0.95:                                # only along links that are already built
            continue
        i, j = (CL[b_], CL[a_]) if PULSE_REV[k] else (CL[a_], CL[b_])
        if not (ok[i] and ok[j]):
            continue
        x, y = lerp(S2[i, 0], S2[j, 0], q), lerp(S2[i, 1], S2[j, 1], q)
        x0, y0 = lerp(S2[i, 0], S2[j, 0], max(0, q - 0.35)), lerp(S2[i, 1], S2[j, 1], max(0, q - 0.35))
        c.drawLine(x0, y0, x, y, paint_stroke("#FFFFFF", 0.9 * lat, 1.8))
        E.glow_dot(c, x, y, 12, "#BFE2FF", 0.8 * lat)


_sr = np.random.default_rng(31)
STREAMS = []                                  # data streams flying through the field into the structure
for k in range(16):
    side = -1 if k % 2 == 0 else 1
    S0 = np.array([side * _sr.uniform(2600, 3400), _sr.uniform(-900, 420), _sr.uniform(900, 3600)])
    off = np.array([_sr.uniform(-500, 500), _sr.uniform(-600, 300), _sr.uniform(-800, 800)])
    STREAMS.append((-0.1 + k * 0.27 + _sr.uniform(-0.08, 0.08), S0, off, k))


def draw_streams(c, u):
    """Bright data streams (bundles of light lines) curving through the field into the structure."""
    for t0, S0, off, k in STREAMS:
        hd = 1.45 * e_io_sine(prog(u, t0, 1.6))
        if hd <= 0 or hd >= 1.45:
            continue
        M = (S0 + C3) / 2 + off
        pts = []
        for j in range(9):
            q = j / 8
            P = (1 - q) ** 2 * S0 + 2 * (1 - q) * q * M + q * q * C3
            z = max(P[2] - camz(u), 60)
            pts.append((CX + F * (P[0] - camx(u)) / z, CY + F * P[1] / z))
        E.line_flow(c, pts, hd, 0.5, n=16, spread=24, twist=1.4, width=2.1, color="#46B4FF", alpha=1.0,
                    key="st%d" % k, glow=1.0, sparks=16, tsec=u, blend="screen", core=E.WHITE)
        if 0.95 < hd < 1.3:                                   # arrival: the structure flares where it lands
            z = max(C3[2] - camz(u), 60)
            x, y = CX + F * (C3[0] - camx(u)) / z, CY + F * C3[1] / z
            k_ = math.sin(math.pi * (hd - 0.95) / 0.35)
            E.radial(c, x, y, 260 * F / z * 3, "#7FB6FF", 0.35 * k_, skia.BlendMode.kScreen)


# ------------------------------------------------------------------ the vortex (data flowing into the AI)
# Instead of light bundles darting in from the sides: a galaxy-like vortex of glowing particles around the
# structure. Three soft spiral arms turn and drift inward all the time, faster as it learns, tighter as it
# becomes precise, and fling outward toward the lens in the burst.
_vr = np.random.default_rng(404)
VM = 4200
V_ARM = _vr.integers(0, 3, VM)
V_Q0 = _vr.random(VM)                         # position along the inflow (1 = outer rim, 0 = at the core)
V_J = _vr.normal(0, 0.2, VM)                 # spread around the arm
V_H = _vr.normal(0, 1, VM)                    # thickness of the disk
V_COL = np.where(_vr.random(VM) < 0.06, 2, np.where(_vr.random(VM) < 0.3, 1, 0))
V_SZ = _vr.uniform(0.6, 1.6, VM)
_tilt, _roll = 0.62, 0.25                     # disk turned toward the lens (a galaxy seen at an angle), rolled
E1 = np.array([math.cos(_roll), math.sin(_roll), 0.0])
E2 = np.array([-math.sin(_roll) * math.cos(_tilt), math.cos(_roll) * math.cos(_tilt), math.sin(_tilt)])
NRM = np.cross(E1, E2)
V_COLS = ["#3D86FF", "#9FD0FF", "#FFFFFF"]


def _ramp(u, t0, k=1.6):
    return clamp(u - t0, 0, 4) ** k


def absorb(u):
    """The vortex drains into the structure (3.80-5.40): no new particles enter at the rim, the inflow speeds up
    gently and the arms empty from the outside in, so the frame is clean before the push-in."""
    return e_io_sine(prog(u, 3.8, 1.6))


def clean(u):
    return e_io_sine(prog(u, 4.3, 1.1))


ARR_T0, ARR_LAG, ARR_D, ARR_FAR = 0.15, 1.0, 1.5, 3.2


def vortex_pts(u):
    """World positions of the vortex particles at shot time u."""
    flow = 0.085 * u + 0.035 * _ramp(u, 2.2) + 0.12 * _ramp(u, 3.8, 2.0)   # inflow speeds up as it learns
    q = (V_Q0 - flow) % 1.0
    shrink = lerp(1.0, 0.78, tight(u))
    ab = absorb(u)
    # arrival: the three arms are not there at first - each swoops in from beyond the frame along its own
    # spiral (head first, the rest of the arm following), wrapping around the structure as it comes in
    arr = np.clip((u - (ARR_T0 + ARR_LAG * q)) / ARR_D, 0, 1)
    arr = 1 - (1 - arr) ** 3
    reach = 1 + ARR_FAR * (1 - arr) ** 2
    r0 = RAD * (1.12 + 3.4 * q ** 1.5) * reach
    r = r0 * shrink
    # the arm angle follows the unscaled radius, so tightening/bursting never turns the pattern backwards:
    # the vortex only ever turns one way (clockwise on screen), and only speeds up
    th = V_ARM * (2 * math.pi / 3) + 2.3 * np.log(r0 / RAD) + V_J + 0.45 * u + 0.22 * _ramp(u, 2.2)
    h = V_H * 26 * (r / RAD) ** 0.8
    P = C3 + (np.cos(th)[:, None] * E1 + np.sin(th)[:, None] * E2) * r[:, None] + NRM * h[:, None]
    edge = np.clip(q / 0.06, 0, 1) * np.clip((1 - q) / 0.12, 0, 1) * (arr > 0)
    if ab > 0:                                    # the rim empties first, the rest flows on into the core
        edge = edge * np.clip(((1 - ab) - q) / 0.15, 0, 1)
    return P, edge, q


def draw_vortex(c, u):
    vis = 1 - e_io_sine(prog(u, 6.35, 0.5))
    if u < ARR_T0:
        return
    if vis <= 0:
        return
    P, edge, q = vortex_pts(u)
    dt = 0.03
    Pp, _, _ = vortex_pts(u - dt)
    S2, Z, ok = project(P, u)
    Sp, _, okp = project(Pp, u - dt)
    ok &= okp
    bright = vis * (0.55 + 0.25 * e_io_sine(prog(u, 0.6, 2.4)) + 0.2 * tight(u) + 0.1 * absorb(u))
    a = edge * fog(Z) * np.clip((Z - 80) / 300, 0, 1) * (0.45 + 0.55 * (1 - q)) * bright
    # soft haze of the disk
    zc = max(C3[2] - camz(u), 60)
    xc, yc = CX + F * (C3[0] - camx(u)) / zc, CY + F * C3[1] / zc
    E.radial(c, xc, yc, F * RAD * 3.0 / zc, "#1F5EFF", 0.22 * vis * e_io_sine(prog(u, ARR_T0 + 0.6, 1.6)),
             skia.BlendMode.kScreen)
    groups = {}
    for i in np.where(ok & (a > 0.02))[0]:
        k = (int(V_COL[i]), min(4, int(a[i] * 5)))
        groups.setdefault(k, []).extend([skia.Point(Sp[i, 0], Sp[i, 1]), skia.Point(S2[i, 0], S2[i, 1])])
    # glow pass (blurred), then crisp streaks
    c.saveLayer(None, skia.Paint(ImageFilter=skia.ImageFilters.Blur(5, 5, skia.TileMode.kDecal)))
    for (ci, ak), pts in groups.items():
        p = paint_stroke(V_COLS[ci], min(1, (ak + 0.5) / 5 * 0.9), 6.0, blend=skia.BlendMode.kScreen)
        c.drawPoints(skia.Canvas.kLines_PointMode, pts, p)
    c.restore()
    for (ci, ak), pts in groups.items():
        p = paint_stroke(V_COLS[ci], (ak + 0.5) / 5, 1.6 if ci else 1.2, blend=skia.BlendMode.kScreen)
        c.drawPoints(skia.Canvas.kLines_PointMode, pts, p)


def draw_arcs(c, u):
    """Energy arcs wrapping the structure once it is solid (reference: a glowing orb with light ribbons)."""
    a = e_io_sine(prog(u, 3.9, 0.8)) * (1 - e_io_sine(prog(u, 6.1, 0.5)))
    if a <= 0:
        return
    rr = np.random.default_rng(88)
    for k in range(4):
        n = rr.normal(size=3)
        n /= np.linalg.norm(n)
        b1 = np.cross(n, [0, 0, 1.0])
        b1 /= np.linalg.norm(b1)
        b2 = np.cross(n, b1)
        ph = rr.uniform(0, 2 * math.pi) + (1.4 + 0.5 * k) * u                # all arcs turn the same way
        span = rr.uniform(2.2, 3.2)
        rad = RAD * rr.uniform(1.06, 1.2) * lerp(1, 0.92, tight(u))
        t = np.linspace(ph, ph + span, 70)
        P = C3 + (np.cos(t)[:, None] * b1 + np.sin(t)[:, None] * b2) * rad
        S2, Z, ok = project(P, u)
        w = np.sin(np.linspace(0, math.pi, 70)) ** 1.5
        front = (P[:, 2] < C3[2]).astype(float) * 0.6 + 0.4          # the near side glows brighter
        for i in range(69):
            if not (ok[i] and ok[i + 1]):
                continue
            al = a * w[i] * front[i]
            c.drawLine(S2[i, 0], S2[i, 1], S2[i + 1, 0], S2[i + 1, 1],
                       paint_stroke("#4FA3FF", 0.35 * al, 10, blur=8, blend=skia.BlendMode.kScreen))
            c.drawLine(S2[i, 0], S2[i, 1], S2[i + 1, 0], S2[i + 1, 1],
                       paint_stroke("#DDEEFF", 0.9 * al, 2.2, blend=skia.BlendMode.kScreen))


def draw_sparks(c, u, S2, Z, ok):
    """Connections firing: nodes flash as links form across the field."""
    rp = np.random.default_rng(13)
    ph = rp.random(N)
    per = rp.uniform(1.6, 3.2, N)
    act = clamp(u / 0.6) * (1 - clean(u))
    for i in range(0, N_VOL):
        if not ok[i] or Z[i] > 4800:
            continue
        f = ((u / per[i]) + ph[i]) % 1.0
        if f < 0.08:
            k = math.sin(math.pi * f / 0.08) * act * float(fog(np.array([Z[i]]))[0])
            x, y = S2[i]
            E.glow_dot(c, x, y, 16 * k + 4, "#DDEEFF", 0.95 * k)
            c.drawCircle(x, y, 4 + 20 * f / 0.08, paint_stroke("#9CCBFF", 0.5 * k, 1.0))


def draw_tags(c, u):
    for kind, pay, pos, ph in TAGS:
        p = pos + np.array([math.sin(u * 0.4 + ph) * 60, math.sin(u * 0.33 + ph * 1.3) * 30, 0])
        z = p[2] - camz(u)
        if z < 200:
            continue
        x, y = CX + F * (p[0] - camx(u)) / z, CY + F * p[1] / z
        s = clamp(F / z, 0.35, 1.6)
        a = float(fog(np.array([z]))[0]) * E.e_io_sine(prog(u, 0.2 + ph * 0.3, 0.8)) * \
            (1 - clean(u)) * clamp((z - 200) / 400)
        if a <= 0.02:
            continue
        if kind == "num":
            v = pay + 7.31 * math.floor(u * 6 + ph)
            txt = "%.4f" % (v % 100)
            w_ = E.text_w(txt, 13 * s, "Medium") + 12 * s
            E.rrect_stroke(c, R(x - w_ / 2, y - 11 * s, w_, 22 * s), 3 * s, "#6FB2FF", 0.8 * a, 1.0)
            E.rrect(c, R(x - w_ / 2, y - 11 * s, w_, 22 * s), 3 * s, "#0A2A6A", 0.55 * a)
            E.text(c, txt, x, y + 4.5 * s, 13 * s, "Medium", "#CFE6FF", a, "center")
        elif kind == "icon":
            E.icon(c, pay, x, y, 26 * s, "#EAF3FF", 0.9 * a)
        else:
            rr = np.random.default_rng(int(ph * 1000))
            for li in range(pay):
                w_ = rr.uniform(60, 200) * s
                E.rrect(c, R(x, y + li * 9 * s, w_, 2.4 * s), 1.2 * s, "#6FA8FF", 0.35 * a)


def _coast(u, t0, d, n=40):
    """Integral of (1 - lock) dt: an angle that turns at unit speed and eases to a stop over [t0, t0 + d]."""
    if u <= t0:
        return u
    x = np.linspace(t0, min(u, t0 + d), n)
    v = 1 - np.array([e_io_cubic(prog(t, t0, d)) for t in x])
    return t0 + float(np.sum((v[1:] + v[:-1]) * np.diff(x)) / 2)


def draw_core(c, u, S2, Z, ok):
    """The structure's core condenses to a bright point, precision rings lock, then light bursts out."""
    z = C3[2] - camz(u)
    if z < 30:
        return
    x, y = CX + F * (C3[0] - camx(u)) / z, CY + F * C3[1] / z
    k = e_io_sine(prog(u, 3.9, 1.8))
    burst = e_in_cubic(prog(u, 5.3, 1.75))
    R_ = RAD * F / z
    if k > 0:
        E.radial(c, x, y, R_ * (0.9 + 0.6 * burst), "#2F7BFF", 0.35 * k, skia.BlendMode.kScreen)
        E.radial(c, x, y, R_ * 0.35 * (1 + 2.5 * burst), "#CFE8FF", 0.55 * k + 0.4 * burst, skia.BlendMode.kScreen)
        E.glow_dot(c, x, y, 16 + 30 * k + 200 * burst, "#FFFFFF", 0.9 * k)
    # precision rings: two tilted rings with ticks, spinning in, then locked level
    ring = e_io_sine(prog(u, 4.25, 0.9)) * (1 - e_io_sine(prog(u, 5.9, 0.5)))
    if ring > 0:
        lock = e_io_cubic(prog(u, 4.4, 1.0))
        for j, (rr, tilt0) in enumerate(((1.28, 0.9), (1.45, -0.7))):
            tilt = lerp(tilt0, 0.0, lock)
            # spins the same way as the vortex and coasts to a stop as it locks (never unwinds backwards)
            rot = (1.6 if j else 1.2) * _coast(u, 4.4, 1.0)
            c.save()
            c.translate(x, y)
            c.rotate(math.degrees(tilt) * 0.3)
            c.scale(1.0, lerp(0.35, 1.0, lock) if j == 0 else lerp(0.5, 1.0, lock))
            c.rotate(math.degrees(rot))
            rad = R_ * rr
            c.drawCircle(0, 0, rad, paint_stroke("#9CCBFF", 0.55 * ring, 1.2))
            for t_ in range(72):
                ang = 2 * math.pi * t_ / 72
                L = 10 if t_ % 6 == 0 else 4
                c.drawLine(rad * math.cos(ang), rad * math.sin(ang), (rad + L) * math.cos(ang), (rad + L) * math.sin(ang),
                           paint_stroke("#9CCBFF", 0.5 * ring, 1.0))
            c.restore()
        # lock brackets
        b = e_out_cubic(prog(u, 5.0, 0.4)) * ring
        if b > 0:
            s_ = R_ * lerp(2.0, 1.62, b)
            E.corner_brackets(c, R(x - s_, y - s_, 2 * s_, 2 * s_), 34, "#CFE6FF", b * 0.9, 2.0)
    # light rays bursting toward the lens
    if burst > 0:
        rr = np.random.default_rng(9)
        for j in range(70):
            ang = rr.uniform(0, 2 * math.pi)
            L = (150 + 2200 * burst) * rr.uniform(0.4, 1.0)
            wdt = rr.uniform(1.0, 4.0) * (1 + 3 * burst)
            x1, y1 = x + math.cos(ang) * L, y + math.sin(ang) * L
            sh = skia.GradientShader.MakeLinear([skia.Point(x, y), skia.Point(x1, y1)],
                                                [colint("#FFFFFF", min(1, 0.9 * burst + 0.1)), colint("#6FB2FF", 0.0)])
            p = skia.Paint(AntiAlias=True, Shader=sh, Style=skia.Paint.kStroke_Style, StrokeWidth=wdt,
                           BlendMode=skia.BlendMode.kScreen)
            c.drawLine(x, y, x1, y1, p)


SWEEP_ANG = 16.0


def sweep_front(T):
    """Front of the wipe in from SC20 (px along the sweep direction); keeps moving after the wipe completes."""
    p = (T - TR0) / TR_D
    ang = math.radians(SWEEP_ANG)
    span = abs(math.cos(ang)) * W + abs(math.sin(ang)) * H
    q = 2 * p * p if p < 0.25 else p - 0.125               # eases in, then constant speed (never stops)
    return -span / 2 - 260 + (span + 520) * q / 0.875, span, p


def draw_sweep(c, T):
    """The line-particle bundles that carry the cut in from SC20; they keep flowing on and out of frame."""
    front, span, p = sweep_front(T)
    if p <= 0 or p > 2.2:
        return
    ang = math.radians(SWEEP_ANG)
    dx, dy = math.cos(ang), math.sin(ang)
    nx, ny = -dy, dx
    perp = abs(nx) * W + abs(ny) * H
    rr = E.rng("t21")
    L = span * 0.95
    fade = 1 - clamp((p - 1.3) / 0.9)
    for b in range(5):
        o = lerp(-0.5, 0.5, (b + 0.5) / 5) * perp + rr.uniform(-0.06, 0.06) * perp
        phs = rr.uniform(0, 2 * math.pi)
        amp = 0.10 * perp * rr.uniform(0.6, 1.2)
        pts = []
        for i in range(7):
            uu = lerp(-1, 1, i / 6)
            w = o + amp * math.sin(math.pi * uu + phs)
            pts.append((W / 2 + dx * uu * L + nx * w, H / 2 + dy * uu * L + ny * w))
        hd = (front + L) / (2 * L) + rr.uniform(-0.03, 0.02)
        E.line_flow(c, pts, hd, 0.42, n=12, spread=rr.uniform(16, 46), twist=1.2, width=1.9, color=E.CYAN,
                    alpha=fade, key="t21%d" % b, glow=0.9, sparks=14, tsec=p * 3, blend="screen", core=E.WHITE)


def wipe_in(c, A, B, T):
    """SC20 -> this shot: B is carried in behind the bundle heads (as the film's line transition)."""
    front, span, p = sweep_front(T)
    ang = math.radians(SWEEP_ANG)
    dx, dy = math.cos(ang), math.sin(ang)
    E.blit(c, A)
    fx, fy = W / 2 + dx * front, H / 2 + dy * front
    c.saveLayer(None, None)
    E.draw_scaled(c, B, lerp(1.05, 1.0, e_out_cubic(clamp(p))))
    sh = skia.GradientShader.MakeLinear([skia.Point(fx - dx * 220, fy - dy * 220), skia.Point(fx + dx * 30, fy + dy * 30)],
                                        [colint("#FFFFFF", 1.0), colint("#FFFFFF", 0.0)])
    c.drawPaint(skia.Paint(Shader=sh, BlendMode=skia.BlendMode.kDstIn))
    c.restore()
    a = math.sin(math.pi * clamp(p))
    band = skia.GradientShader.MakeLinear([skia.Point(fx - dx * 260, fy - dy * 260), skia.Point(fx + dx * 120, fy + dy * 120)],
                                          [colint(E.CYAN, 0), colint(E.CYAN, 0.22 * a), colint(E.CYAN, 0)], [0.0, 0.68, 1.0])
    c.drawPaint(skia.Paint(Shader=band, BlendMode=skia.BlendMode.kScreen))


def render(c, T, sweep=True):
    u = T - U0
    background(c, u)
    P, S2, Z, ok, g = draw_network(c, u)
    draw_tags(c, u)
    draw_vortex(c, u)
    draw_sparks(c, u, S2, Z, ok)
    draw_pulses(c, u, S2, ok, g)
    draw_core(c, u, S2, Z, ok)
    draw_arcs(c, u)
    if sweep:
        draw_sweep(c, T)
    # flood to white into FIN
    wf = e_in_cubic(prog(T, FLASH_PEAK - 0.6, 0.6))
    if wf > 0:
        c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", wf))


def make_surface(sw, sh):
    return skia.Surface.MakeRaster(skia.ImageInfo.Make(sw, sh, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    HD = height > 1080
    media.MAX_READERS = 12 if HD else 4
    width = int(round(height * 16 / 9 / 2)) * 2
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)
    SW, SH = int(round(W * SC)), int(round(H * SC))
    surf, sa, sb = make_surface(SW, SH), make_surface(SW, SH), make_surface(SW, SH)
    finish = E.Finish(size=(SW, SH))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)

    def draw_new(sf, T, sweep=True):
        c = sf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, T, sweep)
        c.restore()

    def draw_scene(sf, sc, T):
        _, t0, t1, fn = sc
        c = sf.getCanvas()
        c.save()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.scale(SC, SC)
        fn(c, T, T - t0, t1 - t0)
        c.restore()

    def shot(T):
        if T < TR0 + TR_D:
            draw_scene(sa, SC20, T)
            draw_new(sb, T, sweep=False)
            A, B = sa.makeImageSnapshot(), sb.makeImageSnapshot()
            c = surf.getCanvas()
            c.save()
            c.clear(skia.Color4f(0, 0, 0, 1))
            c.scale(SC, SC)
            wipe_in(c, A, B, T)
            draw_sweep(c, T)
            c.restore()
        elif T < FLASH_PEAK:
            draw_new(surf, T)
        else:
            draw_scene(surf, FIN, T)
            wf = 1 - e_out_cubic(prog(T, FLASH_PEAK, FLASH_OUT))
            if wf > 0:
                c = surf.getCanvas()
                c.save()
                c.scale(SC, SC)
                c.drawRect(R(0, 0, W, H), paint_fill("#FFFFFF", wf))
                c.restore()
        return surf.makeImageSnapshot().toarray()[..., :3]

    bar = int(round(BAR * SC))
    for f in range(F0, F1):
        T = (SEG0 + f) / 24
        u = T - U0
        if 5.45 < u < FLASH_PEAK - U0:
            # the rush into the core: 180-degree shutter
            acc = np.zeros((SH, SW, 3), np.float32)
            n = 5
            for j in range(n):
                acc += shot(T + (j / (n - 1) - 0.5) / 48)
            fr = np.clip(acc / n + 0.5, 0, 255).astype(np.uint8)
            rgba = np.dstack([fr, np.full((SH, SW), 255, np.uint8)])
            surf.getCanvas().drawImage(skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType), 0, 0)
        else:
            shot(T)
        fr = finish.apply(surf, SEG0 + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
