"""Quick low-res sample of one opening shot: a clip with the light line swept over it (no film finish).

Usage: python3 sample_shot.py <clip> <path key> <seconds> <out.mp4> [height=480] [line start s=0.3]
e.g.   python3 sample_shot.py p5_robot op6 2.0 out/sample_robot.mp4
"""
import subprocess
import sys

import skia

import engine as E
import scenes as S

clip, key, dur, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
height = int(sys.argv[5]) if len(sys.argv) > 5 else 480
t_in = float(sys.argv[6]) if len(sys.argv) > 6 else 0.3
width = int(round(height * 16 / 9 / 2)) * 2

E.configure(E.SEED, E.CHAOS)
pts = [(u * E.W, v * E.H) for (u, v) in S.OPEN_PATHS[key]]
surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(E.W, E.H, skia.ColorType.kRGBA_8888_ColorType,
                                                   skia.AlphaType.kPremul_AlphaType))
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                        "-s", "%dx%d" % (E.W, E.H), "-r", str(E.FPS), "-i", "-",
                        "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", out], stdin=subprocess.PIPE)
for f in range(int(round(dur * E.FPS))):
    t = f / E.FPS
    c = surf.getCanvas()
    c.clear(skia.Color4f(0, 0, 0, 1))
    if key in S.OPEN_STAB:
        E.draw_plate(c, clip, t, dur, s=(1.04, 1.04), stab=True)
    else:
        E.draw_plate(c, clip, t, dur, s=(1.0, 1.0))
    E.light_beam(c, pts, S.OPEN_V * (t - t_in), S.OPEN_TAIL, mb_px=S.OPEN_MB)
    enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
enc.stdin.close()
enc.wait()
print(out)
