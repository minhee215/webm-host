"""Segment 00:00:14:04-00:00:18:10 - "기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다".

Graphic bridge between the locked facade grid (end of seg_where) and SC05 (isometric glass tiles around a
layered core):
  0.00-0.30  continues the locked grid exactly, then dissolves into this scene
  0.30-1.80  "기업의 AI 전환은": the facade lies down - each window travels straight into its SC05 tile in
             the isometric view, its footage turning into that business area's footage; the locked window
             drops into the centre and rises as SC05's layered glass core (no flat top view, no empty cards)
  1.25-3.30  "업무를 이해하는": one smooth blue line runs through every business area; each tile lights, a scan
             band reads across it and its label comes up as the line passes
  2.90-3.60  "것부터 시작됩니다": spokes link every area to the core, the core pulses
  last 0.42  the glass cards fill with SC05's footage tiles (SC05 with its opening build already complete)
--sc05-head renders the matching replacement for SC05's opening, timeline 18:11-20:08 (from 20:09 on it is
identical to the original SC05), so the map never disappears and rebuilds at the cut.
23.976 fps, 21:9 letterbox. Labels in English (Pretendard, same pill style as SC05).
Usage: python3 seg_understand.py [--sc05-head] <out.mp4> [height=480] [frames=102] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_where as SW
from engine import W, H, R, clamp, lerp, prog, e_io_cubic, e_out_cubic, e_io_sine, paint_fill, paint_stroke, col

FPS_NUM, FPS_DEN = 24000, 1001
DT = FPS_DEN / FPS_NUM
BAR = 138
NF_DEFAULT = 102
T_SC05_LAST = 17.4167          # SC05 scene time of this segment's last frame (SC05 continues at 18:11)
TOP_S = 78.0                   # top-view scale (px per world unit)

# seg_where grid cell -> SC05 business area (same angular position around the centre)
CELL_AREA = {(0, 0): "Planning", (0, 1): "Production", (0, 2): "Logistics", (1, 2): "Sales", (2, 2): "Quality",
             (2, 1): "Office", (2, 0): "IT Systems", (1, 0): "Finance"}
RING = ["Planning", "Production", "Logistics", "Sales", "Quality", "Office", "IT Systems", "Finance"]
TILES = {lab: (x, z) for (_, (x, z), lab, _, _) in S.S5_TILES}
CELL_CLIP = {rc: n for n, rc in SW.CELLS.items()}


def where_t(t):
    return SW.NF * DT + t          # seg_where time that continues its last frame


def where_cam(tw):
    return (0.0, 0.0, 150 * e_io_sine(prog(tw, 2.6, 3.5)))


def make_P(k, T_iso):
    Pi, _ = S.s5_iso(T_iso)

    def P(x, y, z):
        tx, ty = W / 2 + x * TOP_S, 540 + z * TOP_S
        ix, iy = Pi(x, y, z)
        return lerp(tx, ix, k), lerp(ty, iy, k)
    return P


def card_quad(P, x, z, y=0.25, w=2.5, d=1.6):
    return [P(x - w / 2, y, z - d / 2), P(x + w / 2, y, z - d / 2), P(x + w / 2, y, z + d / 2), P(x - w / 2, y, z + d / 2)]


def qmix(a, b, k):
    return [(lerp(p[0], q[0], k), lerp(p[1], q[1], k)) for p, q in zip(a, b)]


def glass_card(c, quad, a, lit):
    if a <= 0.003:
        return
    path = E.poly(quad, True)
    c.drawPath(path, paint_fill("#CFE0FF", (0.06 + 0.10 * lit) * a))
    if lit > 0:
        c.drawPath(path, paint_stroke(S.BLUE, 0.6 * lit * a, 8, blur=10, blend=skia.BlendMode.kScreen))
    c.drawPath(path, paint_stroke(S.CYAN if lit > 0.5 else "#7FA6FF", 0.85 * a, 1.4))


def card_glyph(c, P, x, z, a, lit):
    """A tiny process inside each card: three nodes joined by a line, lit by the passing workflow."""
    if a <= 0.003:
        return
    pts = [P(x - 0.7 + 0.7 * j, 0.26, z) for j in range(3)]
    c.drawPath(E.poly(pts), paint_stroke("#9CC9FF", (0.35 + 0.5 * lit) * a, 1.4))
    for j, p in enumerate(pts):
        on = clamp(lit * 3 - j)
        c.drawCircle(*p, 4.5, paint_fill(S.CYAN if on > 0.5 else "#5D7BC4", a))
        if on > 0:
            c.drawCircle(*p, 12, paint_fill(S.CYAN, 0.45 * on * a, blur=6, blend=skia.BlendMode.kScreen))


def stage(c, P, a):
    if a <= 0.003:
        return
    lp = skia.Paint()
    lp.setAlphaf(clamp(a))
    c.saveLayer(None, lp)
    E.vgrad(c, R(0, 0, W, H), "#0B1A3D", "#050B1C", 1.0, 1.0)
    E.radial(c, *P(0, 0, 0), 900, "#1C46B8", 0.35)
    for i in range(-8, 9):
        c.drawLine(*P(i, 0, -8), *P(i, 0, 8), paint_stroke("#3A63C9", 0.10, 1.0))
        c.drawLine(*P(-8, 0, i), *P(8, 0, i), paint_stroke("#3A63C9", 0.10, 1.0))
    c.restore()


def ring_path(n=700):
    ctrl = [(TILES[lab][0], 0.3, TILES[lab][1]) for lab in RING] + [(TILES[RING[0]][0], 0.3, TILES[RING[0]][1])]
    ctrl = [(-6.5, 0.3, -1.2)] + ctrl                    # the line arrives from off the left edge
    return E.bspline(ctrl, n)


RING_W = ring_path()
_d = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(RING_W, axis=0), axis=1))])
RING_S = _d / _d[-1]
_FIRST = RING_S < 0.93                                  # first pass (the loop closes back on Planning)
RING_AT = {lab: float(RING_S[_FIRST][np.argmin(np.linalg.norm(RING_W[_FIRST] - np.array([TILES[lab][0], 0.3,
                                                                                          TILES[lab][1]]), axis=1))])
           for lab in RING}


def head_at(t):
    return 1.40 * e_io_sine(prog(t, 1.25, 2.05)) - 0.02


def scan_sweep(c, quad, k, a):
    """A bright band sweeping across a tile (k 0..1) - the area being read."""
    if a <= 0.003 or not 0 < k < 1:
        return
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = quad
    u0, u1 = max(0.0, k - 0.12), min(1.0, k)
    band = [(lerp(x0, x1, u0), lerp(y0, y1, u0)), (lerp(x0, x1, u1), lerp(y0, y1, u1)),
            (lerp(x3, x2, u1), lerp(y3, y2, u1)), (lerp(x3, x2, u0), lerp(y3, y2, u0))]
    c.save()
    c.clipPath(E.poly(quad, True), skia.ClipOp.kIntersect, True)
    c.drawPath(E.poly(band, True), paint_fill(S.CYAN, 0.28 * a, blur=6, blend=skia.BlendMode.kScreen))
    lead = [(lerp(x0, x1, u1), lerp(y0, y1, u1)), (lerp(x3, x2, u1), lerp(y3, y2, u1))]
    c.drawPath(E.poly(lead), paint_stroke("#E6F7FF", 0.9 * a, 2.0))
    c.restore()


def render(c, t, f, nf):
    t_last = (nf - 1) * DT
    T_iso = T_SC05_LAST
    Pi, _ = S.s5_iso(T_iso)
    tw = where_t(t)
    cam = where_cam(tw)
    b = e_io_cubic(prog(t, 0.15, 1.1))                      # facade wall -> SC05 stage

    c.clear(col("#040A14"))
    stage(c, Pi, b)
    SW.facade_wall(c, 1 - b, cam)

    head = head_at(t)
    labels, tiles = [], []
    clip_of = {lab: (name, foc) for (name, _, lab, _, foc) in S.S5_TILES}
    for i, ((r, cc), lab) in enumerate(CELL_AREA.items()):
        # the facade lies down: each window travels straight into its SC05 tile (no flat top view)
        u = e_io_cubic(prog(t, 0.3 + 0.045 * i, 1.35))
        x, z = TILES[lab]
        y = 0.25 + 0.06 * math.sin(T_iso * 1.1 + [l for (_, _, l, _, _) in S.S5_TILES].index(lab))
        wq = SW.project(SW.cell_params(CELL_CLIP[(r, cc)]), cam)
        tq = card_quad(Pi, x, z, y)
        q = qmix(wq, tq, u)
        tiles.append((q, tq, x, y, z, lab, u, i))
    tiles.sort(key=lambda it: it[1][0][1])                 # far (upper) tiles first
    for (q, tq, x, y, z, lab, u, i) in tiles:
        name, foc = clip_of[lab]
        swap = e_io_sine(prog(t, 0.55 + 0.04 * i, 0.9))       # window footage -> this area's footage
        lit = e_out_cubic(clamp((head - RING_AT[lab]) / 0.04)) if head > 0 else 0.0
        if swap < 1:
            SW.draw_quad(c, SW.frame_img(CELL_CLIP[(r_c := [k_ for k_, v in CELL_AREA.items() if v == lab][0])],
                                         tw + 0.31 * SW.ORDER.index(CELL_CLIP[r_c])), q, 1 - swap, SW.GRADE)
        if swap > 0:
            S.s5_video(c, name, q, T_iso + list(clip_of).index(lab) * 0.7, swap, foc)
        # glass edge: SC05's slab once the tile has landed, lit cyan as the workflow passes it
        edge_a = clamp(u * 1.3 - 0.3)
        if edge_a > 0:
            S.s5_slab(c, Pi, x, z, 2.5, 1.6, y, edge_a, top=0.0, edge=S.CYAN if lit > 0.5 else "#7FA6FF",
                      glow=0.9 * lit * (1 - 0.6 * e_io_sine(prog(t, 3.4, 0.6))))
        c.drawPath(E.poly(q, True), paint_stroke("#9AD8FF", 0.6 * (1 - edge_a), 1.4))
        scan_sweep(c, tq, clamp((head - RING_AT[lab]) / 0.10), 1.0)
        # spokes to the core (the links SC05 draws)
        g = e_out_expo(prog(t, 2.9 + 0.04 * i, 0.6))
        if g > 0:
            p0, p1 = Pi(x * 0.62, 0.02, z * 0.62), Pi(x * 0.3, 0.02, z * 0.3)
            E.line(c, E.poly([p0, p1]), S.CYAN, 0.8, 1.4, (0, g), glow=0.5)
        lx, ly = Pi(x - 1.25, y, z + 0.8)
        labels.append((lx + 6, ly + 22, lab, clamp(u * 1.6 - 0.6) * (0.55 + 0.45 * max(lit, prog(t, 3.4, 0.5)))))

    # core: the locked window drops into the centre and rises as SC05's layered glass core
    tq = SW.project(SW.cell_params(SW.TARGET), cam)
    u = e_io_cubic(prog(t, 0.3, 1.2))
    core_q = qmix(tq, card_quad(Pi, 0, 0, 0.0, 1.9, 1.9), u)
    foot = 1 - e_io_cubic(prog(t, 0.45, 0.9))
    if foot > 0:
        SW.draw_quad(c, SW.frame_img(SW.TARGET, tw, True), core_q, foot, None)
        SW.brackets(c, core_q, foot)
    core_a = e_out_cubic(prog(t, 0.9, 0.7))
    S.s5_core(c, Pi, T_iso, core_a, pulse_=0.35 * e_out_cubic(prog(t, 3.0, 0.5)))

    # the workflow: one smooth blue line through every business area
    if head > 0:
        pts = [Pi(*p) for p in RING_W]
        mb = abs(head_at(t + DT / 2) - head_at(t - DT / 2)) * 2
        E.light_ribbon(c, pts, head, 0.38, width=3.2, alpha=1 - e_io_sine(prog(t, 3.35, 0.55)), mb=mb)

    for (lx, ly, lab, la) in labels:
        S.s5_label(c, lx, ly, lab, la)

    # continuity: first frames are seg_where's own, last frames are SC05's own
    a_w = 1 - e_io_sine(prog(t, 0.0, 0.3))
    if a_w > 0.003:
        lp = skia.Paint()
        lp.setAlphaf(a_w)
        c.saveLayer(None, lp)
        SW.render(c, tw)
        c.restore()
    a_s = e_io_sine(prog(t, t_last - 0.35, 0.35))
    if a_s > 0.003:
        lp = skia.Paint()
        lp.setAlphaf(a_s)
        c.saveLayer(None, lp)
        Tn = T_SC05_LAST - (nf - 1 - f) / 24.0
        sc05_formed(c, Tn)
        c.restore()


e_out_expo = E.e_out_expo

_ENTER, _PROG = S.enter, S.prog


def _formed_enter(t, t0, d=0.6, *a, **kw):
    return 1.0 if 17.29 < t0 < 18.2 else _ENTER(t, t0, d, *a, **kw)


def _formed_prog(t, t0, d):
    if (abs(t0 - 17.3) < 1e-6 and abs(d - 1.2) < 1e-6) or (17.6 <= t0 <= 18.45 and abs(d - 0.9) < 1e-6):
        return 1.0
    return _PROG(t, t0, d)


def sc05_formed(c, T):
    """SC05 with its opening build already complete (tiles, links, grid and core in place): the map built in
    this segment simply becomes SC05. From T >= 19.32 it is identical to the original SC05."""
    S.enter, S.prog = _formed_enter, _formed_prog
    try:
        S.sc05(c, T, T - S.SC05_T0, 9.75)
    finally:
        S.enter, S.prog = _ENTER, _PROG


SC05_HEAD = (443, 489)           # timeline frames 18:11 .. 20:08 replace SC05's opening build

if __name__ == "__main__":
    HEAD = sys.argv[1] == "--sc05-head"
    if HEAD:
        sys.argv.pop(1)
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    NF = int(sys.argv[3]) if len(sys.argv) > 3 else NF_DEFAULT
    F0, F1 = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    SW.setup(hd=height > 1080)
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)
    SWD, SHD = int(round(W * SC)), int(round(H * SC))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SWD, SHD, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if SC == 1 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    frames = range(*SC05_HEAD) if HEAD else range(F0, F1)
    for f in frames:
        t = f * DT
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        if HEAD:
            sc05_formed(c, f / 24.0 - 1.0)       # timeline frame -> SC05 scene time
        else:
            render(c, t, f, NF)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
