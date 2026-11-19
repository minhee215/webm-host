"""Low-res sample: one clip with the reference-style light streak (light_streak) sweeping through it.

The streak follows the tracked footage (it sits in the scene), eases in and out (smooth, fast in the middle)
and its head is motion-blurred by its instantaneous speed. No grading or film finish.
Usage: python3 sample_streak.py <clip> <seconds> <out.mp4> [height=480]
"""
import subprocess
import sys

import skia

import engine as E

PATHS = {  # frame uv, lower left -> upper right, gently curved
    "r5_robot": [(-0.06, 0.93), (0.22, 0.76), (0.46, 0.60), (0.66, 0.46), (0.84, 0.33), (1.08, 0.17)],
}
T0, TRAVEL, TAIL = 0.15, 1.75, 1400.0

clip, dur, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
height = int(sys.argv[4]) if len(sys.argv) > 4 else 480
width = int(round(height * 16 / 9 / 2)) * 2

E.configure(E.SEED, E.CHAOS)
surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(E.W, E.H, skia.ColorType.kRGBA_8888_ColorType,
                                                   skia.AlphaType.kPremul_AlphaType))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", "%dx%d" % (E.W, E.H), "-r", str(E.FPS), "-i", "-",
                        "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", out], stdin=subprocess.PIPE)


def head_at(t, L):
    return (L + TAIL) * E.e_io_sine(E.prog(t, T0, TRAVEL)) - 30


for f in range(int(round(dur * E.FPS))):
    t = f / E.FPS
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    cam = E.draw_plate(c, clip, t, dur, s=(1.0, 1.0))
    pts = E.flow_pts(cam, PATHS[clip])
    L = E.path_len(pts)
    speed = abs(head_at(t + 1 / 96, L) - head_at(t - 1 / 96, L)) * 48     # px / s
    E.light_streak(c, pts, head_at(t, L), TAIL, mb_px=speed / 24)
    enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
enc.stdin.close()
enc.wait()
print(out)
