"""The ceiling UI standing up to face the lens (client edit 2026-11-19, 00:00:36:14) was too sudden: in the edit the
scene jumped from x1.45 (the ceiling cards) to x3 (seg_wsapp) right as the UI comes down. This re-times the stretch
00:00:35:15-00:00:37:17 of that edit (51 frames, same length and same frames at both ends; the edit's held page at
37:05-37:17 is used up) over the film's own clock: the cards gather a little quicker (x2.0), the UI comes down to face
the lens at about x1.45 (it was x3: its 1.1 s move took ~9 frames, the flip itself 1-2), then the app page settles
faster and the speed eases down to the x1 the edit runs at from 37:18 - no speed jumps. The lower-left caption stays off (seg_axpoint.CAPTION_WS).
Usage: python3 retime_34b.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import seg_axpoint as A
import seg_wsapp as WS
import seg_wsfront as WF

E0, E1 = 855, 905                 # the edit's frames re-timed (inclusive)
P0, P1 = 1117.0, 1232.0           # film frames at them in the edit (matched frame by frame); the edit holds the
                                  # page at 1232 from 893 to 905, then runs on at x1
AX_END = 1137                     # film frame where seg_wsapp takes over from seg_axpoint
# speed keys (film frame, film frames per frame); "vh" is solved so the 51 frames come out exactly
KEYS = [(1117, 1.5), (1126, 2.0), (1133, 2.0), (1141, 1.45), (1160, 1.45), (1180, "vh"), (1210, "vh"),
        (1232, 1.0)]


def smooth(x, a, b):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def speed(p, vh):
    ks = [(a, vh if b == "vh" else b) for a, b in KEYS]
    v = np.full_like(p, ks[0][1], dtype=float)
    for (a0, v0), (a1, v1) in zip(ks, ks[1:]):
        v = v + (v1 - v0) * smooth(p, a0, a1)
    return v


def build_map():
    """Film frame for each output frame (E0..E1): integrate dk = dp / v(p), v's top speed solved so it fits."""
    ps = np.linspace(P0, P1, 4001)
    lo, hi = 1.0, 15.0
    for _ in range(60):
        vh = (lo + hi) / 2
        k = np.concatenate([[0], np.cumsum(np.diff(ps) / speed(ps[:-1], vh))])
        if k[-1] > E1 - E0:
            lo = vh
        else:
            hi = vh
    k = k * (E1 - E0) / k[-1]
    return np.interp(np.arange(E1 - E0 + 1), k, ps), vh


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, E1 - E0 + 1)
    width = int(round(height * 16 / 9 / 2)) * 2
    pmap, vh = build_map()
    print("top speed x%.2f" % vh)
    surf, finish, SWD, SHD = WF.setup(height)
    _apply = finish.apply
    finish.apply = lambda s, idx, *a, **kw: _apply(s, int(round(idx)), *a, **kw)
    SCV = A.SCV
    bar = int(round(A.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for i in range(F0, F1):
        p = pmap[i]
        if p <= AX_END:
            fr = A.frame(p - A.F_TL, surf, finish)
        else:
            c = surf.getCanvas()
            c.clear(skia.Color4f(0, 0, 0, 1))
            c.save()
            c.scale(SCV, SCV)
            WS.render(c, p / 24.0)
            c.restore()
            fr = finish.apply(surf, p)
            fr[:bar] = 0
            fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out, F1 - F0)
