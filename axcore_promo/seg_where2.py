"""Segment 00:00:08:02-00:00:14:03, second version (client: the facade grid first, the performance panel after; the
opening's first three shots are cut, so the scene no longer opens on the logistics shot):
  G 0.00-1.10  a dark glass facade; the industry footage slides into its 3x3 windows from depth, staggered, the
               camera easing in
  H 1.00-2.00  brackets hop across windows ("어디를 바꾸고")
  L 1.85-3.55  a blue crosshair settles on one window, then glides once to the target (the AI inspection) and locks
  P 3.55-4.65  the lock lets go: the windows come off the facade and float out into a constellation, the facade
               fades into the dark space, the performance panel ("성과", a rising KPI chart) rises from depth in the
               middle, the extra panels (logistics, campus, robot) fly in, blue connectors draw in
  E 5.05-6.08  the brackets close on the inspection panel in the constellation again (the hand-over target)
Panels, footage, look, letterbox and helpers are seg_where's (same clips: the client keeps the inspection / monitor /
factory / logistics panels).
10 s version (client): G 0-1.9, H 1.95-3.6, L 3.65-5.05 (lock), the camera closes in and a scan beam runs down the
target 5.05-6.4, P 6.45-7.75, connectors / count-up to 9.1, the constellation drifts sideways, E 8.95-10.0.
Usage: python3 seg_where2.py <out.mp4> [height=480] [frames=240] [first last]
"""
import math
import subprocess
import sys

import skia

import engine as E
import seg_where as SW
from engine import W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_io_sine, paint_fill, paint_stroke

# 10 s version (client: about 10 s, with more action) - 240 frames
GRID_IN, GRID_STAG = 0.1, 0.11        # windows fill one by one
HOPS = (("n1_pharma", 1.95), ("n3_evline", 2.40), ("op3_factory", 2.85), ("10_datacenter", 3.30))
SCAN_IN, SCAN_MOVE, SCAN_MOVE_D = 3.65, 4.20, 0.85
SCAN_LOCK = SCAN_MOVE + SCAN_MOVE_D   # 5.05
SWEEP_T, SWEEP_D = 5.35, 0.75         # after the lock: the camera closes in, a scan beam runs down the target window
OPEN_T, OPEN_D = 6.45, 1.3            # facade -> constellation
PERF_T = 6.85                         # the performance panel's own clock starts here (its count-up runs 0.75-2.25)
END_LOCK = 8.95
EXTRA = [n for n in SW.SLOTS if n not in SW.CELLS]      # constellation-only panels
# the target plays the inspection take from the start: the light and PASS are on as the crosshair locks (source
# 2.3 s at the lock), then it runs on slower so it never stops (also through seg_insight's hand-over frames)
TGT_R1, TGT_R2, TGT_AT_LOCK = 0.45, 0.26, 2.3


def clip_time(n, i, t):
    if n == SW.TARGET:
        src = TGT_AT_LOCK + (t - SCAN_LOCK) * (TGT_R1 if t < SCAN_LOCK else TGT_R2)
        return min(max(0.0, src), SW._dur(n) - 1 / 24) - 0.5
    a, b = SW.CLIP_SPAN.get(n, (0.12 * (i % 4), SW._dur(n) - 0.08))
    if n == SW.OPENER:                 # (now an ordinary panel: plays through its usable part)
        a, b = -0.5, SW._dur(n) - 0.08
    return a + (b - a) * max(0.0, t / SW.SCENE_T)


def panel_pose(n, i, t, det):
    """World pose and opacity of panel n: in its facade window, then (det) out at its constellation slot."""
    slot = SW.SLOTS[n]
    if n in SW.CELLS:
        cell = SW.cell_params(n)
        j = list(SW.CELLS).index(n)
        k_in = e_out_cubic(prog(t, GRID_IN + GRID_STAG * j, 0.9))
        p = SW.mix((cell[0] * 1.15, cell[1] * 1.15, cell[2] + 2600, cell[3], cell[4], 0.0), cell, k_in)
        kk = e_io_cubic(prog(t, OPEN_T + 0.06 * (j % 5), OPEN_D - 0.2))
        return SW.mix(p, slot, kk), k_in
    j = EXTRA.index(n)
    k_in = e_out_cubic(prog(t, OPEN_T + 0.45 + 0.12 * j, 0.9))
    p = SW.mix((slot[0] * 1.3, slot[1] * 1.3, slot[2] * 2.6, slot[3], slot[4], slot[5]), slot, k_in)
    return p, k_in


def render(c, t):
    det = e_io_cubic(prog(t, OPEN_T, OPEN_D))
    wall = 1.0 - det
    lock = e_out_cubic(prog(t, SCAN_LOCK, 0.4)) * (1 - e_io_cubic(prog(t, OPEN_T - 0.1, 0.45)))
    end = e_out_cubic(prog(t, END_LOCK, 0.45))
    # camera: eases in on the facade, closes in on the locked window, pulls back as it opens up, then drifts
    # across the constellation with a slow push
    z_grid = lerp(-260.0, 110.0, e_io_sine(prog(t, 0.0, SCAN_LOCK))) + 230.0 * e_io_sine(prog(t, SCAN_LOCK, 1.3))
    k_c = e_io_sine(prog(t, OPEN_T + OPEN_D - 0.3, SW.SCENE_T - OPEN_T - OPEN_D + 0.3))
    z_cons = lerp(-90.0, 40.0, k_c)
    x_cons = lerp(-110.0, 110.0, k_c) + math.sin(t * 0.6) * 12
    y_cons = lerp(25.0, -15.0, k_c)
    cam = (x_cons * det, y_cons * det, lerp(z_grid, z_cons, det))

    SW.background(c, t, wall)
    SW.facade_wall(c, wall, cam)
    cq = SW.project(SW.mix((0, -30, 2900, 900, 500, 0.0), SW.CENTER, e_out_cubic(prog(t, PERF_T, 0.8))), cam)
    a_perf = e_out_cubic(prog(t, PERF_T, 0.6))
    if a_perf > 0:
        SW.performance_panel(c, cq, t - PERF_T, a_perf)
        SW.glow_frame(c, cq, a_perf)
    centre_pts = {"l": ((cq[0][0] + cq[3][0]) / 2, (cq[0][1] + cq[3][1]) / 2),
                  "r": ((cq[1][0] + cq[2][0]) / 2, (cq[1][1] + cq[2][1]) / 2),
                  "t": ((cq[0][0] + cq[1][0]) / 2, cq[0][1]), "b": ((cq[3][0] + cq[2][0]) / 2, cq[3][1])}

    items = []
    for i, n in enumerate(SW.ORDER):
        p, a = panel_pose(n, i, t, det)
        items.append((p[2], n, p, a, i))
    items.sort(key=lambda x: -x[0])
    dim = 0.62 * lock + 0.35 * end
    tq = None
    for z, n, p, a, i in items:
        q = SW.project(p, cam)
        if n == SW.TARGET:
            tq = q
        SW.draw_quad(c, SW.frame_img(n, clip_time(n, i, t), n == SW.TARGET), q, a, SW.GRADE)
        if n != SW.TARGET and dim > 0:
            c.drawPath(E.poly(q, True), paint_fill("#030814", dim * a))
        SW.glow_frame(c, q, a * (1 - 0.6 * wall) * (1 - 0.5 * dim))
        if det > 0.01 and n not in ("n7_campus", "17_robot"):
            kc = e_out_cubic(prog(t, PERF_T + 0.45 + 0.04 * i, 0.55))
            side = "l" if p[0] < -600 else "r" if p[0] > 600 else ("t" if p[1] < 0 else "b")
            if side in "lr":
                e_ = ((q[1][0] + q[2][0]) / 2, (q[1][1] + q[2][1]) / 2) if side == "l" else \
                    ((q[0][0] + q[3][0]) / 2, (q[0][1] + q[3][1]) / 2)
                SW.connector(c, centre_pts[side], e_, kc, a * det * a_perf, t, i)
            else:
                e_ = ((q[3][0] + q[2][0]) / 2, q[3][1]) if side == "t" else ((q[0][0] + q[1][0]) / 2, q[0][1])
                st = (lerp(cq[0][0], cq[1][0], 0.3 if p[0] < 0 else 0.7), centre_pts[side][1])
                SW.connector(c, st, e_, kc, a * det * a_perf, t, i)

    # "어디를 바꾸고": brackets hop across windows
    for n, t0 in HOPS:
        av = E.vis(t, t0, 0.12, t0 + 0.30, 0.15)
        if av > 0:
            p = [x for x in items if x[1] == n][0][2]
            SW.brackets(c, SW.project(p, cam), av, grow=14 * (1 - clamp((t - t0) / 0.15)))

    # "어디에 AI를": the crosshair settles on one window, glides once to the target and locks; it lets go as the
    # facade opens
    scan_a = e_out_cubic(prog(t, SCAN_IN, 0.3)) * (1 - e_io_cubic(prog(t, OPEN_T - 0.1, 0.4)))
    if scan_a > 0:
        (r0, c0), (r1, c1) = SW.SCAN_FROM, SW.CELLS[SW.TARGET]
        f_ = e_io_cubic(prog(t, SCAN_MOVE, SCAN_MOVE_D))
        rr, cc = lerp(r0, r1, f_), lerp(c0, c1, f_)
        q = SW.project(((cc - 1) * SW.GX, (rr - 1) * SW.GY, SW.Z_WALL, SW.CW, SW.CH, 0.0), cam)
        x0, y0 = min(p[0] for p in q), min(p[1] for p in q)
        x1, y1 = max(p[0] for p in q), max(p[1] for p in q)
        mxc, myc = (x0 + x1) / 2, (y0 + y1) / 2
        lk = e_out_cubic(prog(t, SCAN_LOCK, 0.4))
        la = scan_a * (0.55 + 0.45 * lk)
        for (xa, ya, xb, yb) in ((-W, myc, 2 * W, myc), (mxc, -H, mxc, 2 * H)):
            c.drawLine(xa, ya, xb, yb, paint_stroke(SW.CYAN_L, 0.35 * la, 6, blur=8, blend=skia.BlendMode.kScreen))
            c.drawLine(xa, ya, xb, yb, paint_stroke("#BFE6FF", 0.75 * la, 1.2))
        look = e_io_sine(prog(t, SCAN_IN + 0.05, 0.4)) * (1 - math.sin(math.pi * f_))
        SW.brackets(c, q, scan_a * (0.65 + 0.35 * lk), grow=lerp(10, 3, look) * (1 - lk), ln=34, width=3.0)
        sw = prog(t, SWEEP_T, SWEEP_D)                   # the scan beam runs down the locked window
        if 0 < sw < 1:
            ys = lerp(y0, y1, e_io_sine(sw))
            fade = math.sin(math.pi * sw)
            c.drawRect(R(x0, ys - 26, x1 - x0, 26), paint_fill(SW.CYAN_L, 0.18 * fade * scan_a,
                                                               blend=skia.BlendMode.kScreen))
            c.drawLine(x0 - 30, ys, x1 + 30, ys, paint_stroke(SW.CYAN_L, 0.5 * fade * scan_a, 8, blur=8,
                                                              blend=skia.BlendMode.kScreen))
            c.drawLine(x0 - 30, ys, x1 + 30, ys, paint_stroke("#E8F6FF", 0.95 * fade * scan_a, 1.6))
        if lk > 0:
            for (px, py), (dx, dy) in (((x0, y0), (-1, -0.6)), ((x1, y0), (1, -0.6)), ((x0, y1), (-1, 0.6)),
                                       ((x1, y1), (1, 0.6))):
                L = 1400 * lk
                c.drawLine(px, py, px + dx * L, py + dy * L, paint_stroke(SW.CYAN_L, 0.3 * la, 4, blur=6,
                                                                          blend=skia.BlendMode.kScreen))
                c.drawLine(px, py, px + dx * L, py + dy * L, paint_stroke("#BFE6FF", 0.55 * la, 1.0))
            c.drawPath(E.poly(q, True), paint_stroke(SW.CYAN_L, 0.6 * lk * scan_a, 10, blur=14,
                                                     blend=skia.BlendMode.kScreen))

    # the hand-over target: brackets close on the inspection panel in the constellation
    if end > 0 and tq is not None:
        SW.brackets(c, tq, end, grow=16 * (1 - end), ln=30, width=3.0)
        c.drawPath(E.poly(tq, True), paint_stroke(SW.CYAN_L, 0.45 * end, 9, blur=12, blend=skia.BlendMode.kScreen))


def _dur(n):
    import json
    import os
    if n not in SW._DUR:
        SW._DUR[n] = json.load(open(os.path.join(SW.media.CLIP_DIR, n + ".json")))["dur"]
    return SW._DUR[n]


SW._dur = _dur

if __name__ == "__main__":
    argv = list(sys.argv)
    if len(argv) < 4:
        argv += ["480", "240"][len(argv) - 2:]
    SW.setup(argv)
    SW.SCENE_T = SW.NF * SW.DT
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, SW.height / H)
    SWD, SHD = int(round(W * SC)), int(round(H * SC))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SWD, SHD, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (SW.FPS_NUM, SW.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (SW.width, SW.height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if not SW.HD else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", SW.out], stdin=subprocess.PIPE)
    for f in range(SW.F0, SW.F1):
        t = f * SW.DT
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, t)
        c.drawRect(R(0, 0, W, SW.BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - SW.BAR, W, SW.BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
    enc.stdin.close()
    enc.wait()
    print(SW.out)
