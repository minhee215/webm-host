"""Segment 00:00:08:02-00:00:14:03 - "성과를 위해 어디를 바꾸고 / 어디에 AI를 적용할 것인가입니다".

Motion graphic (references: floating industry panels around a facade; a facade grid with a locked target):
  A 0.00-1.15  the inspection shot (s04) opens full frame, then pulls back and becomes one glass panel in a dark
               space while the other industry panels fly in from depth
  B 1.15-2.05  constellation of panels around a central "performance" panel (a rising KPI chart), blue
               connectors draw in, brackets hop ("성과를 위해 어디를 바꾸고")
  C 2.05-3.05  the performance panel recedes while the panels slide into the windows of a dark glass facade
  D 3.05-6.08  a blue crosshair settles on one window, then glides once to the target and locks ("어디에 AI를 적용할 것인가"); the shot
               holds on the locked grid with a slow push (no zoom into the window - the bridge to the next
               scene is designed with that scene)
Footage: the client's clips s01-s04 plus generated clips in the same bright, clean factory look. 23.976 fps, 21:9 letterbox to match the edit.
Usage: python3 seg_where.py <out.mp4> [height=480] [frames=146] [first last]
  height > 1080 renders natively at that size with full-resolution footage in every panel (e.g. 1440 = 2K);
  first/last render a frame range (for parallel chunks). Text is set in Pretendard (engine.text).
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
from engine import W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_io_sine, paint_fill, paint_stroke, col

out, height, NF, F0, F1, HD = None, 480, 146, 0, 146, False
HD_NAME = {}
width = 854


def setup(argv=None, hd=None):
    """Command-line settings (also used when another segment imports this one)."""
    global out, height, NF, F0, F1, HD, width
    if argv:
        out = argv[1]
        height = int(argv[2]) if len(argv) > 2 else 480
        NF = int(argv[3]) if len(argv) > 3 else 146
        F0, F1 = (int(argv[4]), int(argv[5])) if len(argv) > 5 else (0, NF)
        HD = height > 1080
    if hd is not None:
        HD = hd
    if HD:
        media.MAX_READERS = 24          # every panel streams its full-resolution clip
    width = int(round(height * 16 / 9 / 2)) * 2


FPS_NUM, FPS_DEN = 24000, 1001
DT = FPS_DEN / FPS_NUM
BAR = 138                      # 21:9 letterbox in 1080 logical px (276 at 4K)
F = 1100.0                     # focal length (px); a panel at Z=F is drawn 1:1
OPENER = "s04_inspect"         # the shot the scene opens on (full frame), before it becomes a panel
OPENER_T0 = 91 / 24            # its clip time at the first frame: the edit's previous cut ends on s04 frame 90
OPENER_SCALE, OPENER_DX = 1.031, 0.0155   # ...framed at 103.1 %, left edge on the frame edge (matched to that cut)
CYAN_L = "#46B4FF"
GRADE = E.grade_filter(bright=0.92, contrast=1.04, sat=0.88, tint=(-0.01, 0.0, 0.02))

# constellation slots: (X, Y, Z, w, h, yaw)
CENTER = (0, -30, 1700, 900, 500, 0.0)
SLOTS = {
    "s04_inspect": (-1250, -560, 2000, 700, 394, -0.42),
    "n1_pharma": (-1350, -30, 2050, 700, 394, -0.45),
    "s02_monitor": (-1250, 480, 2000, 660, 372, -0.42),
    "n2_warehouse": (1350, -480, 2050, 700, 394, 0.45),
    "n3_evline": (1300, 0, 2000, 700, 394, 0.42),
    "n4_office": (1350, 500, 2050, 700, 394, 0.45),
    "n5_battery": (-430, -620, 2100, 620, 350, -0.12),
    "s01_walk": (430, -620, 2100, 620, 350, 0.12),
    "n6_server": (-430, 560, 2100, 620, 350, -0.12),
    "s03_robot": (430, 560, 2100, 620, 350, 0.12),
    "n7_campus": (-2000, -150, 2700, 700, 394, -0.5),
    "17_robot": (2000, 200, 2700, 700, 394, 0.5),
}
# facade windows: 3x3 cells of 560x240 on a wall a little behind the 1:1 plane, so the facade shows around them
Z_WALL = 1270.0
CW, CH, GX, GY = 560, 240, 600, 270
CELLS = {
    "n5_battery": (0, 0), "s01_walk": (0, 1), "n2_warehouse": (0, 2),
    "n1_pharma": (1, 0), "s03_robot": (1, 1), "n3_evline": (1, 2),
    "s02_monitor": (2, 0), "n6_server": (2, 1), "n4_office": (2, 2),
}
TARGET = "s03_robot"
SCAN_FROM = (2, 0)             # the crosshair first settles on the office window...
SCAN_MOVE, SCAN_MOVE_D = 3.6, 0.8   # ...then glides once to the target
SCAN_LOCK = SCAN_MOVE + SCAN_MOVE_D
ORDER = list(SLOTS)            # fly-in order
SCENE_T = 146 * 1001 / 24000
CLIP_SPAN = {"s03_robot": (0.15, 2.2),   # usable part (s): s03 ends behind a foreground pillar
             "s01_walk": (0.0, 2.6)}    # ... and s01 with the walker gone from frame
_DUR = {}


def clip_time(n, i, t):
    """Each panel plays once through its usable part over the scene (no loop jump), offset per panel."""
    if n not in _DUR:
        _DUR[n] = json.load(open(os.path.join(media.CLIP_DIR, n + ".json")))["dur"]
    if n == OPENER:                      # carries straight on from the previous cut at normal speed
        return min(OPENER_T0 + t, _DUR[n] - 1 / 24)
    a, b = CLIP_SPAN.get(n, (0.12 * (i % 4), _DUR[n] - 0.08))
    return a + (b - a) * clamp(t / SCENE_T)


def cell_params(name):
    r, cidx = CELLS[name]
    return ((cidx - 1) * GX, (r - 1) * GY, Z_WALL, CW, CH, 0.0)


def project(p, cam):
    X, Y, Z, w, h, yaw = p
    ox, oy, oz = cam
    cs, sn = math.cos(yaw), math.sin(yaw)
    q = []
    for dx, dy in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
        x, y, z = X + dx * cs - ox, Y + dy - oy, Z + dx * sn - oz
        z = max(z, 60.0)
        q.append((W / 2 + F * x / z, H / 2 + F * y / z))
    return q


def mix(a, b, k):
    return tuple(lerp(x, y, k) for x, y in zip(a, b))


def frame_img(name, t, full=False, far=False):
    if HD and not far:
        name = HD_NAME.get(name, name)
        full = True
    if full:
        return media.frame(name, t)[0]
    img = media.proxy_frame(name, t)
    return img if img is not None else media.frame(name, t)[0]


def draw_quad(c, img, quad, alpha=1.0, grade=None):
    if alpha <= 0.003:
        return
    iw, ih = img.width(), img.height()
    qw = math.hypot(quad[1][0] - quad[0][0], quad[1][1] - quad[0][1])
    qh = math.hypot(quad[3][0] - quad[0][0], quad[3][1] - quad[0][1])
    asp = qw / max(qh, 1)
    sw = min(iw, ih * asp)
    sh = sw / asp
    sx, sy = (iw - sw) / 2, (ih - sh) / 2
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(sx, sy), skia.Point(sx + sw, sy), skia.Point(sx + sw, sy + sh), skia.Point(sx, sy + sh)],
                    [skia.Point(*p) for p in quad])
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(alpha))
    if grade is not None:
        p.setColorFilter(grade)
    c.save()
    c.clipPath(E.poly(quad, True), skia.ClipOp.kIntersect, True)
    c.concat(m)
    c.drawImage(img, 0, 0, E.SAMP, p)
    c.restore()


def glow_frame(c, quad, alpha, strength=1.0):
    if alpha <= 0.003:
        return
    path = E.poly(quad, True)
    c.drawPath(path, paint_stroke(CYAN_L, 0.55 * alpha * strength, 7, blur=10, blend=skia.BlendMode.kScreen))
    c.drawPath(path, paint_stroke("#9AD8FF", 0.9 * alpha, 1.4))


def background(c, t, wall):
    c.drawRect(R(0, 0, W, H), paint_fill("#040A14"))
    E.radial(c, W / 2, H / 2 - 20, 900, "#0E3A7A", 0.55 * (1 - wall))
    E.radial(c, W / 2, H / 2, 420, "#1E66C8", 0.25 * (1 - wall))
    # far, defocused tiles drifting slowly (depth)
    if wall < 0.99:
        lp = skia.Paint()
        lp.setImageFilter(skia.ImageFilters.Blur(5, 5, skia.TileMode.kDecal))
        lp.setAlphaf(0.32 * (1 - wall))
        c.saveLayer(None, lp)
        rng = np.random.default_rng(7)
        names = list(SLOTS) + ["06_line", "18_factory"]
        for i in range(22):
            n = names[i % len(names)]
            x, y = rng.uniform(-1.0, 1.0) * 1.15 * W / 2, rng.uniform(-1, 1) * 0.9 * H / 2
            z = rng.uniform(3200, 5200)
            sz = rng.uniform(260, 520)
            p = (x * z / F + 60 * t * z / F * 0.15, y * z / F, z, sz * 1.6, sz * 0.9, rng.uniform(-0.3, 0.3))
            q = project(p, (0, 0, 0))
            draw_quad(c, frame_img(n, t + i * 0.37, far=True), q, 0.8, GRADE)
        c.restore()


def facade_wall(c, a, cam):
    """Dark glass facade around the 3x3 windows: spandrels, mullions, faint reflections."""
    if a <= 0.003:
        return
    c.save()
    lp = skia.Paint()
    lp.setAlphaf(clamp(a))
    c.saveLayer(None, lp)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(W, H)],
                                        [col("#0A1726"), col("#10243A"), col("#081320")], [0.0, 0.55, 1.0])
    c.drawRect(R(-W, -H, 3 * W, 3 * H), skia.Paint(Shader=sh))
    # secondary small windows beyond the 3x3 block (dim, a few lit)
    rng = np.random.default_rng(3)
    for r in range(-3, 4):
        for k in range(-4, 5):
            if abs(r) <= 1 and abs(k) <= 1:
                continue
            q = project((k * GX, r * GY, Z_WALL, CW, CH, 0.0), cam)
            lit = rng.uniform() < 0.22
            c.drawPath(E.poly(q, True), paint_fill("#1B3550" if lit else "#0D1C2E", 0.9))
            if lit:
                c.drawPath(E.poly(q, True), paint_fill("#F2D7A8", 0.10))
    # mullions: verticals every quarter cell, spandrel bands between rows
    for k in range(-5, 6):
        for j in range(4):
            xw = k * GX - GX / 2 + j * GX / 4
            q1 = project((xw, 0, Z_WALL, 0.1, 9 * GY, 0.0), cam)
            c.drawLine(q1[0][0], q1[0][1], q1[3][0], q1[3][1], paint_stroke("#3B5A78", 0.55 if j == 0 else 0.25,
                                                                              3.0 if j == 0 else 1.2))
    for r in range(-4, 5):
        yw = r * GY - GY / 2
        q1 = project((0, yw, Z_WALL, 11 * GX, 0.1, 0.0), cam)
        c.drawLine(q1[0][0], q1[0][1], q1[1][0], q1[1][1], paint_stroke("#3B5A78", 0.5, 3.0))
    c.restore()
    c.restore()


def connector(c, a_pt, b_pt, k, alpha, t, seed):
    """Elbow line from the centre panel to a panel, drawn on by k, with a travelling pulse."""
    if k <= 0 or alpha <= 0.003:
        return
    mx = a_pt[0] + (b_pt[0] - a_pt[0]) * 0.55
    pts = [a_pt, (mx, a_pt[1]), (mx, b_pt[1]), b_pt]
    seg = [math.dist(pts[i], pts[i + 1]) for i in range(3)]
    L = sum(seg)
    path = skia.Path()
    path.moveTo(*pts[0])
    rem = L * k
    for i in range(3):
        if rem <= 0:
            break
        f_ = min(1.0, rem / max(seg[i], 1e-6))
        path.lineTo(lerp(pts[i][0], pts[i + 1][0], f_), lerp(pts[i][1], pts[i + 1][1], f_))
        rem -= seg[i]
    c.drawPath(path, paint_stroke(CYAN_L, 0.35 * alpha, 5, blur=6, blend=skia.BlendMode.kScreen))
    c.drawPath(path, paint_stroke("#8FD0FF", 0.85 * alpha, 1.3))
    if k >= 1:
        ph = (t * 0.9 + seed * 0.29) % 1.0
        d = ph * L
        for i in range(3):
            if d <= seg[i]:
                f_ = d / max(seg[i], 1e-6)
                x, y = lerp(pts[i][0], pts[i + 1][0], f_), lerp(pts[i][1], pts[i + 1][1], f_)
                c.drawCircle(x, y, 9, paint_fill(CYAN_L, 0.5 * alpha, blur=6, blend=skia.BlendMode.kScreen))
                c.drawCircle(x, y, 2.6, paint_fill("#FFFFFF", 0.95 * alpha))
                break
            d -= seg[i]


def brackets(c, quad, alpha, grow=0.0, ln=26, width=2.6, glow=True):
    if alpha <= 0.003:
        return
    xs, ys = [p[0] for p in quad], [p[1] for p in quad]
    r = R(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)).makeOutset(10 + grow, 10 + grow)
    if glow:
        E.corner_brackets(c, r, ln, CYAN_L, alpha * 0.6, width * 3.2)
    E.corner_brackets(c, r, ln, "#E8F6FF", alpha, width)


def performance_panel(c, quad, t, alpha):
    """Centre panel: '성과' - a dark glass KPI board whose line chart climbs as the scene opens."""
    if alpha <= 0.003:
        return
    pw, ph = 900.0, 500.0
    m = skia.Matrix()
    m.setPolyToPoly([skia.Point(0, 0), skia.Point(pw, 0), skia.Point(pw, ph), skia.Point(0, ph)],
                    [skia.Point(*p) for p in quad])
    c.save()
    lp = skia.Paint()
    lp.setAlphaf(clamp(alpha))
    c.saveLayer(None, lp)
    c.concat(m)
    sh = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, ph)],
                                        [col("#0E2440"), col("#081526")], [0.0, 1.0])
    c.drawRect(R(0, 0, pw, ph), skia.Paint(Shader=sh))
    E.radial(c, pw * 0.7, ph * 0.35, 420, "#1E6BD6", 0.35)
    E.text(c, "PERFORMANCE", 44, 70, 26, "SemiBold", "#9CC9FF", 0.9)
    k = e_io_cubic(prog(t, 0.75, 1.5))
    val = 18.4 * k
    E.text(c, "+%.1f%%" % val, 44, 138, 56, "Bold", "#FFFFFF", 1.0)
    # chart area
    x0, x1, y0, y1 = 60, pw - 50, 190, ph - 50
    for j in range(5):
        yy = lerp(y0, y1, j / 4)
        c.drawLine(x0, yy, x1, yy, paint_stroke("#2C4C72", 0.6, 1.0))
    # bars
    rng = np.random.default_rng(11)
    nb = 12
    for j in range(nb):
        hb = (0.25 + 0.55 * j / nb + rng.uniform(-0.08, 0.08)) * (y1 - y0) * e_out_cubic(prog(t, 0.6 + j * 0.05, 0.5))
        bx = lerp(x0 + 10, x1 - 40, j / (nb - 1))
        c.drawRect(R(bx, y1 - hb, 26, hb), paint_fill("#1D4E8C", 0.75))
    # rising line, drawn on
    xs = np.linspace(x0, x1, 60)
    base = np.linspace(0.18, 0.92, 60) + 0.05 * np.sin(np.linspace(0, 7, 60))
    ys = y1 - base * (y1 - y0)
    nv = max(2, int(60 * k))
    path = E.poly(list(zip(xs[:nv], ys[:nv])))
    c.drawPath(path, paint_stroke(CYAN_L, 0.45, 9, blur=8, blend=skia.BlendMode.kScreen))
    c.drawPath(path, paint_stroke("#DDF2FF", 1.0, 2.6))
    c.drawCircle(xs[nv - 1], ys[nv - 1], 14, paint_fill(CYAN_L, 0.6, blur=8, blend=skia.BlendMode.kScreen))
    c.drawCircle(xs[nv - 1], ys[nv - 1], 5, paint_fill("#FFFFFF", 1.0))
    c.restore()
    c.restore()


def render(c, t):
    # --- timeline values
    a_pull = e_io_cubic(prog(t, 0.25, 0.95))                # robot -> slot
    wall = e_io_cubic(prog(t, 2.05, 0.9))                   # constellation -> facade
    lock = e_out_cubic(prog(t, SCAN_LOCK, 0.4))
    push = 0.0                                              # no zoom into the window (next scene TBD)
    drift = math.sin(t * 0.6) * 18
    cam = (drift * (1 - wall), 0.0, -60 * prog(t, 0.0, 2.2) * (1 - wall) + 150 * e_io_sine(prog(t, 2.6, 3.5)))

    background(c, t, wall)
    # zoom into the target window for the push-in (2D, about the target centre)
    tq = project(cell_params(TARGET), cam)
    zoom = lerp(1.0, (W + 8) / (tq[1][0] - tq[0][0]), push)
    tcx, tcy = sum(p[0] for p in tq) / 4, sum(p[1] for p in tq) / 4
    c.save()
    c.translate(lerp(tcx, W / 2, push), lerp(tcy, H / 2, push))
    c.scale(zoom, zoom)
    c.translate(-tcx, -tcy)

    # centre facade panel grows into the wall
    facade_wall(c, wall, cam)
    cen = mix(CENTER, (0, -30, 2600, 900, 500, 0.0), wall)      # the performance panel recedes into the wall
    cq = project(cen, cam)
    if wall < 0.999:
        a_in = e_out_cubic(prog(t, 0.55, 0.6))
        performance_panel(c, cq, t, a_in * (1 - wall))
        glow_frame(c, cq, a_in * (1 - wall))

    centre_pts = {"l": ((cq[0][0] + cq[3][0]) / 2, (cq[0][1] + cq[3][1]) / 2),
                  "r": ((cq[1][0] + cq[2][0]) / 2, (cq[1][1] + cq[2][1]) / 2),
                  "t": ((cq[0][0] + cq[1][0]) / 2, cq[0][1]), "b": ((cq[3][0] + cq[2][0]) / 2, cq[3][1])}

    # panels (far first)
    items = []
    for i, n in enumerate(ORDER):
        slot = SLOTS[n]
        if n == OPENER:
            start = (OPENER_DX * W, 0, F, W * OPENER_SCALE, H * OPENER_SCALE, 0.0)
            p = mix(start, slot, a_pull)
            a = 1.0
        else:
            k_in = e_out_cubic(prog(t, 0.35 + 0.07 * i, 0.75))
            p = mix((slot[0] * 1.3, slot[1] * 1.3, slot[2] * 2.6, slot[3], slot[4], slot[5]), slot, k_in)
            a = k_in
        if n in CELLS:
            kk = e_io_cubic(prog(t, 2.05 + 0.05 * (i % 5), 0.85))
            p = mix(p, cell_params(n), kk)
        else:
            kk = e_io_cubic(prog(t, 1.95, 0.8))
            p = mix(p, (p[0] * 2.2, p[1] * 1.6, p[2] * 0.7, p[3], p[4], p[5]), kk)
            a *= 1 - kk
        items.append((p[2], n, p, a, i))
    items.sort(key=lambda x: -x[0])

    dim = 0.62 * lock * (1 - push)
    for z, n, p, a, i in items:
        q = project(p, cam)
        full = n == TARGET or (n == OPENER and a_pull < 0.5)
        tt = clip_time(n, i, t)
        g = None if (n == OPENER and a_pull < 0.05) else GRADE
        draw_quad(c, frame_img(n, tt, full), q, a, g)
        if n != TARGET and dim > 0:
            c.drawPath(E.poly(q, True), paint_fill("#030814", dim * a))
        border = a * (1 - 0.6 * wall) * (a_pull if n == OPENER else 1.0)
        glow_frame(c, q, border * (1 - 0.5 * dim))
        # connectors from the centre panel (constellation only)
        if wall < 0.99 and n in SLOTS and n not in ("n7_campus", "17_robot"):
            kc = e_out_cubic(prog(t, 1.0 + 0.04 * i, 0.55))
            side = "l" if p[0] < -600 else "r" if p[0] > 600 else ("t" if p[1] < 0 else "b")
            if side in "lr":
                end = ((q[1][0] + q[2][0]) / 2, (q[1][1] + q[2][1]) / 2) if side == "l" else \
                    ((q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2)
                connector(c, centre_pts[side], end, kc, a * (1 - wall), t, i)
            else:
                end = ((q[3][0] + q[2][0]) / 2, q[3][1]) if side == "t" else ((q[0][0] + q[1][0]) / 2, q[0][1])
                st = centre_pts[side]
                st = (lerp(cq[0][0], cq[1][0], 0.3 if p[0] < 0 else 0.7), st[1])
                connector(c, st, end, kc, a * (1 - wall), t, i)

    # "어디를 바꾸고": brackets hop across panels
    for j, (n, t0) in enumerate((("n1_pharma", 1.05), ("n3_evline", 1.38), ("s01_walk", 1.70), ("n6_server", 2.0))):
        av = E.vis(t, t0, 0.12, t0 + 0.30, 0.15)
        if av > 0:
            p = [x for x in items if x[1] == n][0][2]
            brackets(c, project(p, cam), av, grow=14 * (1 - clamp((t - t0) / 0.15)))

    # "어디에 AI를 적용할 것인가": the crosshair settles on one window, looks, then glides once to the target and
    # locks (two windows only - unhurried, easy to follow)
    scan_a = e_out_cubic(prog(t, 2.95, 0.3)) * (1 - push)
    if scan_a > 0:
        (r0, c0), (r1, c1) = SCAN_FROM, CELLS[TARGET]
        f_ = e_io_cubic(prog(t, SCAN_MOVE, SCAN_MOVE_D))
        rr, cc = lerp(r0, r1, f_), lerp(c0, c1, f_)
        cx_w, cy_w = (cc - 1) * GX, (rr - 1) * GY
        q = project((cx_w, cy_w, Z_WALL, CW, CH, 0.0), cam)
        x0, y0 = min(p[0] for p in q), min(p[1] for p in q)
        x1, y1 = max(p[0] for p in q), max(p[1] for p in q)
        mxc, myc = (x0 + x1) / 2, (y0 + y1) / 2
        la = scan_a * (0.55 + 0.45 * lock)
        for (xa, ya, xb, yb) in ((-W, myc, 2 * W, myc), (mxc, -H, mxc, 2 * H)):
            c.drawLine(xa, ya, xb, yb, paint_stroke(CYAN_L, 0.35 * la, 6, blur=8, blend=skia.BlendMode.kScreen))
            c.drawLine(xa, ya, xb, yb, paint_stroke("#BFE6FF", 0.75 * la, 1.2))
        # brackets tighten while it looks at the first window, open as it moves, close on the target
        look = e_io_sine(prog(t, 3.0, 0.45)) * (1 - math.sin(math.pi * f_))
        brackets(c, q, scan_a * (0.65 + 0.35 * lock), grow=lerp(10, 3, look) * (1 - lock), ln=34, width=3.0)
        if lock > 0:
            # rays from the locked bracket corners out to the frame
            for (px, py), (dx, dy) in (((x0, y0), (-1, -0.6)), ((x1, y0), (1, -0.6)), ((x0, y1), (-1, 0.6)),
                                       ((x1, y1), (1, 0.6))):
                L = 1400 * lock
                c.drawLine(px, py, px + dx * L, py + dy * L, paint_stroke(CYAN_L, 0.3 * la, 4, blur=6,
                                                                          blend=skia.BlendMode.kScreen))
                c.drawLine(px, py, px + dx * L, py + dy * L, paint_stroke("#BFE6FF", 0.55 * la, 1.0))
            c.drawPath(E.poly(q, True), paint_stroke(CYAN_L, 0.6 * lock * scan_a, 10, blur=14,
                                                     blend=skia.BlendMode.kScreen))
    c.restore()


if __name__ == "__main__":
    setup(sys.argv)
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)            # above 1080p the composite is drawn natively at the output size
    SW, SH = int(round(W * SC)), int(round(H * SC))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        t = f * DT
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, t)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
