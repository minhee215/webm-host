"""Patch 00:00:20:20-00:00:28:12 (185 frames) of seg_insight (the frontal SC05 map): DX / AX shown large over the
footage of their cards (instead of a small pill by the name); the tagged cards grow and their footage goes
translucent like the others, the untagged cards shrink - all eased. The flow has no rail or arrows (they popped on at
23:05): once the first flow card is in, a light runs behind the cards from the first to the last, leaving the lit cyan
line (no line particles). The shot with all four cards holds longer (the cards coming in and the line end run a little
quicker). As the cards go and the line runs right the camera eases in on its head, then back out to the original
framing once the line is drawn. Everything else is seg_insight's own render,
so the first and the last frame join the delivered file.
Usage: python3 seg_dxax.py <out.mp4> [height=480]
"""
import math
import runpy
import sys

import numpy as np

import scenes as S

F0, F1 = 160, 345                # seg_insight frames = timeline 20:20 .. 28:12



def _win(t, a, b):
    x = np.clip((t - a) / (b - a), 0, 1)
    return np.where((t > a) & (t < b), 0.5 - 0.5 * np.cos(2 * math.pi * x), 0.0)


def _hold_map():
    """Scene clock for the flow part: a little quicker through the cards coming in (22.75-25.05) and the line end
    (26.40-27.30), so the shot with all four cards holds longer (about 1.0 s instead of 0.4 s); identical to the
    original clock before 22.75 and after 27.30, and smooth throughout (no jolts in the camera)."""
    t = np.arange(22.75, 27.30, 1e-4)
    up = 0.45 * _win(t, 22.75, 25.05) + 0.25 * _win(t, 26.40, 27.30)
    sl = _win(t, 24.80, 26.40)
    v = 1 + up - np.trapezoid(up, t) / np.trapezoid(sl, t) * sl
    g = 22.75 + np.concatenate([[0.0], np.cumsum((v[1:] + v[:-1]) / 2 * np.diff(t))])
    return t, g


_HT, _HG = _hold_map()
_sc05 = S.sc05


ZIN0, ZIN_D = 26.18, 0.65       # (patch clock) as the cards go and the line runs right, the camera eases in on its head
ZOUT0, ZOUT_D = 26.95, 0.50     # once the line is drawn, back out to the original framing (identical from 27.45)
ZIN_K, ZIN_FOLLOW = 1.15, 0.5


def line_head(T):
    """Screen point of the head of the line the last card's diamond draws (as scenes.s5_line_end)."""
    P, _ = S.s5_iso(T)
    px, py = P(*S.s5_port(3))
    u = S.e_io_cubic(S.prog(T, S.S5_LINE_T0 + 0.08, S.S5_LINE_D - 0.08))
    return S.lerp(px, S.BAR_LINE[0], u), py


def sc05_held(c, T, t, *a):
    T0 = T
    if 22.75 < T < 27.30:
        T2 = float(np.interp(T, _HT, _HG))
        t, T = t + (T2 - T), T2
    k = S.e_io_sine(S.prog(T0, ZIN0, ZIN_D)) * (1 - S.e_io_sine(S.prog(T0, ZOUT0, ZOUT_D)))
    if k <= 1e-4:
        return _sc05(c, T, t, *a)
    hx, hy = line_head(T)
    z = S.lerp(1.0, ZIN_K, k)
    fx, fy = S.W / 2 + ZIN_FOLLOW * k * (hx - S.W / 2), S.H / 2 + ZIN_FOLLOW * k * (hy - S.H / 2)
    mx, my = S.W / 2 / z, S.H / 2 / z                 # keep the scene's own background covering the frame
    fx, fy = S.clamp(fx, mx, S.W - mx), S.clamp(fy, my, S.H - my)
    c.save()
    c.translate(S.W / 2, S.H / 2)
    c.scale(z, z)
    c.translate(-fx, -fy)
    r = _sc05(c, T, t, *a)
    c.restore()
    return r


if __name__ == "__main__":
    S.S5_BIG_TAGS = True
    S.S5_FLOW_LIGHT = True
    S.sc05 = sc05_held
    out = sys.argv[1]
    height = sys.argv[2] if len(sys.argv) > 2 else "480"
    a, b = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else (str(F0), str(F1))
    sys.argv = ["seg_insight.py", out, height, a, b]
    runpy.run_path("seg_insight.py", run_name="__main__")
