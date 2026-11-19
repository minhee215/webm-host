"""00:00:34:02-00:00:41:09 of the client's edit (176 frames) re-timed (client): 39:11-41:09 (the workspace app going up
and out, the AXCORE node, 사내 시스템 spreading) a little slower, the frames before it a little fewer, the total
length and both ends unchanged.
The client's edit was matched frame by frame against the scenes' renders (the speeds it set):
  edit   0- 36  seg_diagmon   0- 40      (the diagnosis -> the browser over the man -> the ceiling)
  edit  37- 89  seg_axpoint 376-452      (the ceiling, AXunion toggles, the workspace cards)
  edit  90-136  seg_wsapp     0-137      (the workspace page, the app goes up and out)
  edit 137-175  seg_wsapp   138-162      (the node, 사내 시스템)
Re-timed: edit 0-128 (129 frames) -> 122 frames, edit 129-175 (47 frames) -> 54 frames (x0.87); every frame is
rendered at its scene time (no frame interpolation).
Usage: python3 retime_34.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import seg_axpoint as A
import seg_diagmon as DM
import seg_wsapp as WS
import seg_wsfront as WF

N_OUT = 176
SEGS = [("dm", 0, 36, 0, 40), ("ax", 37, 89, 376, 452), ("ws", 90, 136, 0, 137), ("ws", 137, 175, 138, 162)]


def edit_pos(k):
    """Position in the client's edit (fractional edit frame) of output frame k."""
    if k < 122:
        return k * 128 / 121
    return 129 + (k - 122) * 46 / 53


def source(u):
    """(scene, scene frame) at edit position u."""
    for i, (sc, u0, u1, f0, f1) in enumerate(SEGS):
        if u <= u1 or i == len(SEGS) - 1:
            uu = max(u, u0)
            return sc, f0 + (min(uu, u1) - u0) * (f1 - f0) / (u1 - u0)
        nsc, nu0, _, nf0, _ = SEGS[i + 1]
        if u < nu0:                                  # between two segments
            if nsc == sc:                            # the same scene runs on: carry straight across
                return sc, f1 + (u - u1) * (nf0 - f1) / (nu0 - u1)
            return (sc, f1) if u - u1 < 0.5 else (nsc, nf0)
    raise ValueError(u)


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, N_OUT)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = WF.setup(height)
    _apply = finish.apply
    finish.apply = lambda s, idx, *a, **kw: _apply(s, int(round(idx)), *a, **kw)   # (scene frames are fractional)
    SCV = A.SCV
    bar = int(round(A.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k in range(F0, F1):
        sc, f = source(edit_pos(k))
        if sc == "ax":
            fr = A.frame(f, surf, finish)
        else:
            c = surf.getCanvas()
            c.clear(skia.Color4f(0, 0, 0, 1))
            c.save()
            c.scale(SCV, SCV)
            if sc == "dm":
                DM.render(c, f)
                grain = DM.F_TL + f
            else:
                tl = WS.TL0 + f
                WS.render(c, tl / 24.0)
                grain = tl
            c.restore()
            fr = finish.apply(surf, int(round(grain)))
            fr[:bar] = 0
            fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out, F1 - F0)
