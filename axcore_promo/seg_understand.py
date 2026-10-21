"""Segment 00:00:14:04-00:00:18:10 - "기업의 AI 전환은 업무를 이해하는 것부터 시작됩니다".

Graphic bridge between the locked facade grid (end of seg_where) and SC05 (isometric glass tiles around a
layered core):
  0.00-0.30  continues the locked grid exactly, then dissolves into this scene
  0.25-1.40  "기업의 AI 전환은": the windows drain to glass cards and glide (top view) into a ring - the eight
             business areas of SC05 at their SC05 positions; the locked window becomes the central core
  1.45-3.20  "업무를 이해하는": one smooth blue line runs the whole workflow around the ring, each area lights
             up and gets its label as the line passes; spokes link the areas to the core
  2.95-3.90  "것부터 시작됩니다": the camera tilts from the top view into SC05's isometric view; the core's
             glass layers separate
  last 0.42  dissolves into SC05's own opening frames, so the cut to SC05 at 18:11 is continuous
23.976 fps, 21:9 letterbox. Labels in English (Pretendard, same pill style as SC05).
Usage: python3 seg_understand.py <out.mp4> [height=480] [frames=102] [first last]
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
    return 1.42 * e_io_sine(prog(t, 1.45, 1.75)) - 0.02


def render(c, t, f, nf):
    t_last = (nf - 1) * DT
    T_iso = T_SC05_LAST
    k = e_io_cubic(prog(t, 2.95, 0.95))                     # top view -> SC05 iso view
    P = make_P(k, T_iso)
    tw = where_t(t)
    cam = where_cam(tw)
    b = e_io_cubic(prog(t, 0.1, 0.9))                       # facade wall -> SC05 stage

    c.clear(col("#040A14"))
    stage(c, P, b)
    SW.facade_wall(c, 1 - b, cam)

    # windows -> glass cards (top view), locked window -> core
    head = head_at(t)
    labels = []
    for i, ((r, cc), lab) in enumerate(CELL_AREA.items()):
        u = e_io_cubic(prog(t, 0.25 + 0.035 * i, 1.0))
        wq = SW.project(SW.cell_params(CELL_CLIP[(r, cc)]), cam)
        x, z = TILES[lab]
        q = qmix(wq, card_quad(P, x, z), u)
        foot = 1 - e_io_cubic(prog(t, 0.2, 0.75))
        lit = e_out_cubic(clamp((head - RING_AT[lab]) / 0.05)) if head > 0 else 0.0
        fade = 1 - e_io_sine(prog(t, t_last - 0.42, 0.42))  # hand over to SC05's own tiles
        if foot > 0:
            SW.draw_quad(c, SW.frame_img(CELL_CLIP[(r, cc)], tw + 0.31 * SW.ORDER.index(CELL_CLIP[(r, cc)])),
                         q, foot, SW.GRADE)
            c.drawPath(E.poly(q, True), paint_fill("#030814", 0.62 * foot))
        glass_card(c, q, fade, lit)
        card_glyph(c, P, x, z, fade * u * (1 - foot), lit)
        # spokes to the core (same links SC05 draws)
        g = e_out_expo(prog(t, 2.75 + 0.04 * i, 0.6))
        if g > 0:
            p0, p1 = P(x * 0.62, 0.02, z * 0.62), P(x * 0.3, 0.02, z * 0.3)
            E.line(c, E.poly([p0, p1]), S.CYAN, 0.8 * fade, 1.4, (0, g), glow=0.5)
        lx, ly = P(x - 1.25, 0.25, z + 0.8)
        la = clamp(u * 1.4 - 0.4) * (0.45 + 0.55 * lit) * fade
        labels.append((lx + 6, ly + 22, lab, la))

    # core: the locked window shrinks into the centre and becomes SC05's layered glass core
    tq = SW.project(SW.cell_params(SW.TARGET), cam)
    u = e_io_cubic(prog(t, 0.25, 1.0))
    core_q = qmix(tq, card_quad(P, 0, 0, 0.0, 1.9, 1.9), u)
    core_a = e_out_cubic(prog(t, 0.75, 0.6))
    foot = 1 - e_io_cubic(prog(t, 0.2, 0.75))
    if foot > 0:
        SW.draw_quad(c, SW.frame_img(SW.TARGET, tw, True), core_q, foot, None)
        SW.brackets(c, core_q, foot)
    glass_card(c, core_q, (1 - core_a), 1.0)
    S.s5_core(c, P, T_iso, core_a, pulse_=0.3 * e_out_cubic(prog(t, 3.0, 0.5)))

    # the workflow: one smooth blue line around every business area
    if head > 0:
        pts = [P(*p) for p in RING_W]
        mb = abs(head_at(t + DT / 2) - head_at(t - DT / 2)) * 2
        E.light_ribbon(c, pts, head, 0.42, width=3.0, alpha=1 - e_io_sine(prog(t, t_last - 0.5, 0.45)), mb=mb)

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
    a_s = e_io_sine(prog(t, t_last - 0.42, 0.42))
    if a_s > 0.003:
        lp = skia.Paint()
        lp.setAlphaf(a_s)
        c.saveLayer(None, lp)
        Tn = T_SC05_LAST - (nf - 1 - f) / 24.0
        S.sc05(c, Tn, Tn - S.SC05_T0, 9.75)
        c.restore()


e_out_expo = E.e_out_expo

if __name__ == "__main__":
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
    for f in range(F0, F1):
        t = f * DT
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        render(c, t, f, NF)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
