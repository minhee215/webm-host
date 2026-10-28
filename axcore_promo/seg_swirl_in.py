"""Replacement for the cut SC20 -> seg_ai, timeline 00:01:38:23-00:01:41:13 (63 frames).

seg_ai came in on the film's line-particle wipe (blue line bundles sweeping across, still flowing until 101:12).
Here instead seg_ai's vortex particles swoop in over the factory first (laid over it), then the deep-navy space
fades in under them; no line bundles. seg_ai's clock runs a little ahead here (so its arms arrive over the factory)
and eases back to the real time by 101:12. Before the fade the frames are seg_exec's (the same render), from 101:13 on they are seg_ai's own frames
(its bundles have left the frame by then), so the patch drops in between the delivered files.
  98.96  seg_exec's factory (the same render)
  99.35  the vortex arms swoop in over the factory, which softens and sinks back
  99.95  the navy space fades in under the vortex (slight settle)
Frame f is timeline frame 2375 + f; film time = timeline frame / 24. 23.976 fps, 21:9 letterbox.
Usage: python3 seg_swirl_in.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import engine as E
import media
import seg_ai as AI
import seg_axpoint as A
import seg_exec as X
from engine import W, H, R, prog, lerp, clamp, e_io_sine, e_out_cubic, paint_fill

FPS_NUM, FPS_DEN = 24000, 1001
BAR = 138
F_TL = 98 * 24 + 23              # 00:01:38:23
NF = 101 * 24 + 13 - F_TL + 1    # through 00:01:41:13 (63 frames): seg_ai's line bundles are gone by then
FADE0, FADE_D = 99.95, 0.60       # the navy space fades in under the vortex already there
SCV = 1.0


def ft(f):
    return (F_TL + f) / 24.0


def grain_index(f):
    """seg_exec's grain while its picture shows, seg_ai's (timeline frame) after."""
    return X.GRAIN0 + (F_TL + f - X.F_TL) if ft(f) < FADE0 + FADE_D / 2 else F_TL + f


SW0, SW_LEAD, SW_END = 99.35, 0.70, 101.50   # the vortex shows up from 99.35 (seg_ai's clock runs ahead, eases back)


def tv(t):
    """seg_ai's clock: SW_LEAD ahead at SW0 (so its vortex arms are already arriving), easing back to the real
    time by SW_END (from there on the frames are seg_ai's own). Always moving forward."""
    x = clamp((t - SW0) / (SW_END - SW0))
    return t + SW_LEAD * (1 - x * x * (3 - 2 * x))


def vortex_layer(t):
    """seg_ai's vortex alone on a transparent layer (to lay over the factory)."""
    s = A.surf_get(42)
    cc = s.getCanvas()
    cc.clear(skia.Color4f(0, 0, 0, 0))
    cc.save()
    cc.scale(A.SCV, A.SCV)
    AI.draw_vortex(cc, tv(t) - AI.U0)
    cc.restore()
    return s.makeImageSnapshot()


def render(c, t):
    k = e_io_sine(prog(t, FADE0, FADE_D))                     # the navy space fades in
    if k < 1:
        soft = e_io_sine(prog(t, SW0 + 0.2, 0.9))
        img = A.snap(40, lambda cc: X.render(cc, t))
        A.draw_img(c, img, 1.0, 8 * soft + 8 * k, 1.0 + 0.03 * k)
        c.drawRect(R(0, 0, W, H), paint_fill("#030B22", 0.30 * soft))   # the factory sinks back under the swirl
        if t >= SW0:                                           # the vortex arms swoop in over the factory
            A.draw_img(c, vortex_layer(t), 1 - k)
    if k > 0:
        img = A.snap(41, lambda cc: AI.render(cc, tv(t), sweep=False))
        A.draw_img(c, img, k, 8 * (1 - k), lerp(1.03, 1.0, e_out_cubic(k)))


def frame(f, surf, finish):
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    c.save()
    c.scale(SCV, SCV)
    render(c, ft(f))
    c.restore()
    fr = finish.apply(surf, grain_index(f))
    bar = int(round(BAR * SCV))
    fr[:bar] = 0
    fr[-bar:] = 0
    return np.ascontiguousarray(fr)


def setup(height):
    global SCV
    out = X.setup(height)
    SCV = A.SCV
    AI.HD = height > 1080
    media.MAX_READERS = 12 if height > 1080 else 4
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
