"""Segment 00:01:35:01-00:01:39:05 (101 frames) - "AI는 분석에서 실행으로 확장됩니다."

The original SC20 (the factory, the 분석 | 실행 switch), unchanged except for its way in: it carries on from the
end of seg_ops (the robot shot gone soft, the factory already out of focus and punched in, the switch risen to the
centre), so the frames it shares with seg_ops are identical.
  95.04  seg_ops' last frames (the same render: the robot shot goes soft at 95.20, the switch rises)
  95.85  the network grows over the soft factory
  96.22  "실행": the switch flips hard to 실행 and the shot snaps open (motion-blurred), the switch glides to its corner
Frame f is timeline frame 2281 + f; film time = timeline frame / 24 (narration: "실행" at 96.26).
23.976 fps, 21:9 letterbox.
Usage: python3 seg_exec.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_axpoint as A
import seg_ops as O
from engine import (W, H, R, WHITE, NAVY_950, CYAN, lerp, prog, clamp, e_io_sine, e_out_cubic, e_out_expo,
                    paint_fill, paint_stroke, rrect, text, poly)

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 95 * 24 + 1               # 00:01:35:01 (from before the robot shot goes soft)
NF = 99 * 24 + 5 - F_TL + 1      # through 00:01:39:05 (101 frames)
GRAIN0 = O.GRAIN0 + (F_TL - O.F_TL)   # the same grain as seg_ops on the frames they share
OPS_END = O.T0 + (O.NF - 1) / 24.0
SCV = 1.0

OUT, OUT_D = 96.22, 1.0          # "실행" (voice 96.26): the shot snaps open
NET0 = 95.85                     # the network grows (after seg_ops' last frame)


def ft(f):
    return (F_TL + f) / 24.0


def zoom(t):
    """0 = punched in, 1 = open (the original SC20 easing)."""
    return S.bezier_ease(prog(t, OUT, OUT_D), 0.5, 0.0, 0.12, 1.0)


def network_dist():
    dist = {0: 0}
    frontier = [0]
    while frontier:
        nxt = []
        for n in frontier:
            for (a_, b_) in S.SC20_EDGES:
                for (x_, y_) in ((a_, b_), (b_, a_)):
                    if x_ == n and y_ not in dist:
                        dist[y_] = dist[n] + 1
                        nxt.append(y_)
        frontier = nxt
    return dist


DIST = network_dist()


def factory(c, t):
    zo = zoom(t)
    creep = e_io_sine(prog(t, O.SC20_OUT - 1.15, 1.15))          # as seg_ops, so the frames join
    Z = lerp(1.85 + 0.06 * creep, 1.0, zo)
    c.save()
    c.translate(W / 2, H / 2 - 24 * (1 - zo))
    c.scale(Z, Z)
    c.translate(-W / 2, -H / 2)
    bl = 11.0 * (1 - zo) ** 1.4
    if bl > 0.05:
        lp = skia.Paint()
        lp.setImageFilter(skia.ImageFilters.Blur(bl, bl, skia.TileMode.kClamp))
        c.saveLayer(None, lp)
    cam = E.draw_plate(c, "18_factory", t - O.FAC0, O.FAC_D, s=(1.05, 1.16), y=(20, -10), grade=S.GRADE_COOL)
    if bl > 0.05:
        c.drawRect(R(-W, -H, 3 * W, 3 * H), paint_fill(NAVY_950, 0.18 * (1 - zo)))
        c.restore()
    pts = [cam.map(u, v) for (u, v) in S.SC20_NODES]
    for (a_, b_) in S.SC20_EDGES:
        lv = min(DIST[a_], DIST[b_])
        g = e_out_expo(prog(t, NET0 + lv * 0.45, 0.6))
        src, dst = (a_, b_) if DIST[a_] <= DIST[b_] else (b_, a_)
        E.line(c, poly([pts[src], pts[dst]]), CYAN, 0.85, 1.8 / Z, (0, g), glow=0.8)
    for i, (x, y) in enumerate(pts):
        k = E.enter(t, NET0 + DIST[i] * 0.45 + 0.3, 0.4)
        if k <= 0:
            continue
        a = clamp(k)
        ph = ((t - NET0) * 0.8 + i * 0.13) % 1.0
        c.drawCircle(x, y, 16 + 26 * ph, paint_stroke(CYAN, a * (1 - ph) * 0.7, 1.4))
        E.square(c, x, y, 12, CYAN if i == 0 else WHITE, a)
    c.restore()
    # the switch: large in the centre (where seg_ops left it), flips hard on "실행", then glides to its corner
    fin = R(110, 176, 470, 100)
    sc = lerp(1.8, 1.0, zo)
    cx = lerp(W / 2, fin.centerX(), zo)
    cy = lerp(H / 2 - 30, fin.centerY(), zo)
    sw = e_out_expo(prog(t, OUT - 0.04, 0.42))
    hit = e_out_cubic(prog(t, OUT - 0.02, 0.16)) * math.exp(-max(0.0, t - (OUT + 0.14)) * 3.0)
    c.save()
    c.translate(cx, cy)
    c.scale(sc, sc)
    c.translate(-fin.centerX(), -fin.centerY())
    r = fin
    E.glass(c, r, 50, 1.0, tint=S.NAVY_800, tint_a=0.5, blur=20, border=0.5, shadow=0.3,
            glow=0.15 + 0.85 * hit, glow_col=CYAN)
    knob = R(r.left() + 10 + sw * 225, r.top() + 10, 225, 80)
    if hit > 0.01:
        c.drawRRect(skia.RRect.MakeRectXY(knob.makeOutset(6 * hit, 6 * hit), 46, 46),
                    paint_fill(CYAN, 0.35 * hit, blur=14))
    rrect(c, knob, 40, CYAN, 1.0)
    on = sw >= 0.5
    text(c, "분석", r.left() + 122, r.centerY() + 8, 22, "SemiBold", WHITE if on else S.NAVY_900, 0.7 if on else 1.0,
         "center")
    ex = 1.0 + 0.12 * hit
    c.save()
    c.translate(r.left() + 348, r.centerY())
    c.scale(ex, ex)
    text(c, "실행", 0, 8, 22, "Bold" if on else "SemiBold", S.NAVY_900 if on else WHITE, 1.0, "center")
    c.restore()
    c.restore()


def render(c, t):
    if t <= OPS_END + 1e-6:
        O.render(c, t)
        return
    # while the shot snaps open, average sub-frames over a 180-degree shutter (as the original)
    v = abs(zoom(t + 1 / 96) - zoom(t - 1 / 96))
    n = 1 if v < 0.003 else int(clamp(v / 0.0045, 4, 16))
    if n == 1:
        factory(c, t)
        return
    for i in range(n):
        dt = (i / (n - 1) - 0.5) / 48
        if i:
            p = skia.Paint()
            p.setAlphaf(1.0 / (i + 1))
            c.saveLayer(None, p)
        factory(c, t + dt)
        if i:
            c.restore()


def frame(f, surf, finish):
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    c.save()
    c.scale(SCV, SCV)
    render(c, ft(f))
    c.restore()
    fr = finish.apply(surf, GRAIN0 + f)
    bar = int(round(BAR * SCV))
    fr[:bar] = 0
    fr[-bar:] = 0
    return np.ascontiguousarray(fr)


def setup(height):
    global SCV
    out = O.setup(height)
    SCV = A.SCV
    return out


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = setup(height)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(F0, F1):
        enc.stdin.write(frame(f, surf, finish).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
