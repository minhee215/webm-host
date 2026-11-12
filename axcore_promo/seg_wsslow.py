"""The connect scene of seg_wsapp, slowed (client, final cut 00:00:50:04-00:00:58:18, 207 frames): 사내 시스템 runs
over 00:50:04-00:54:07, then 외부 SaaS over 00:54:07-00:58:18.
In the final cut seg_wsapp starts at frame 1067, so its frame w sits at cut frame 1067 + w; 00:50:04 (frame 1204) is
its frame 137 (the systems panel coming in). Output frame k is seg_wsapp's own picture at a fractional frame:
  k   0 ->  99  (00:50:04-00:54:07)  w 137 -> 201  (systems panel, its rows, the counter; x0.65)
  k  99 -> 206  (00:54:07-00:58:18)  w 201 -> 290  (the SaaS panel comes in, its five cards connect; x0.83)
so the first frame is the cut's frame 1204 exactly. The rest of seg_wsapp is not used.
Usage: python3 seg_wsslow.py <out.mp4> [height=480] [first last]
"""
import subprocess
import sys

import numpy as np
import skia

import seg_axpoint as A
import seg_wsapp as WA
import seg_wsfront as WF

NF = 207
W0, WS, W1, KS = 137.0, 201.0, 290.0, 99


def wframe(k):
    if k <= KS:
        return W0 + k * (WS - W0) / KS
    return WS + (k - KS) * (W1 - WS) / (NF - 1 - KS)


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, NF)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = WF.setup(height)
    SCV = WF.SCV
    bar = int(round(A.BAR * SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k in range(F0, F1):
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        WA.render(c, (WA.TL0 + wframe(k)) / 24.0)
        c.restore()
        fr = finish.apply(surf, WA.TL0 + int(W0) + k)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
