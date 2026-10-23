"""A still photo brought to life with the reference light streak (the client's silo shot, remade cleanly).

The photo (AI-upscaled to 4K) gets a slow camera move - a gentle push-in with a slight clockwise roll - and the
engine's light streak (white-hot core, cyan glow, star flare with an anamorphic streak at the head) crosses the
sky from lower left to upper right, locked to the photo so it moves with the camera. Framed for the film's 21:9
letterbox (picture band only), frame-for-frame 23.976 fps like the other deliverables.
Usage: python3 still_streak.py <image> <out.mp4> [frames=97] [height=1440]
"""
import subprocess
import sys

import numpy as np
import skia

import engine as E
from engine import W, H, R, clamp, lerp, prog, e_io_sine, paint_fill

BAR = 138
FPS_NUM, FPS_DEN = 24000, 1001
# streak path in photo uv (same course as the client's clip: up out of the lower left, across the sky between
# the silos, out over the top right)
PATH = [(-0.06, 0.80), (0.12, 0.68), (0.28, 0.58), (0.44, 0.48), (0.62, 0.37), (0.80, 0.25), (1.04, 0.10)]
T_IN, T_OUT, TAIL = 0.30, 3.20, 1100.0   # the head crosses the frame between these times (steady, like the clip)
ZOOM = (1.0, 1.07)
ROLL = (0.0, 3.0)            # degrees, clockwise
FOCUS = (0.5, 0.5)           # photo uv kept at the frame centre


def cam_matrix(img, t, dur):
    """Photo -> screen: cover the 21:9 picture band, then push in and roll about the band centre."""
    iw, ih = img.width(), img.height()
    bh = H - 2 * BAR
    k = max(W / iw, bh / ih) * 1.04            # small margin so the roll never shows an edge
    p = e_io_sine(clamp(t / dur)) * 0.35 + 0.65 * clamp(t / dur)
    z = lerp(ZOOM[0], ZOOM[1], p)
    rot = lerp(ROLL[0], ROLL[1], p)
    m = skia.Matrix()
    m.setTranslate(W / 2, H / 2)
    m.preRotate(rot)
    m.preScale(k * z, k * z)
    m.preTranslate(-FOCUS[0] * iw, -FOCUS[1] * ih)
    return m


def main():
    src, out = sys.argv[1], sys.argv[2]
    nf = int(sys.argv[3]) if len(sys.argv) > 3 else 97
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 1440
    width = int(round(height * 16 / 9 / 2)) * 2
    SC = height / H
    SW, SH = int(round(W * SC)), int(round(H * SC))
    img = skia.Image.open(src)
    E.configure(E.SEED, E.CHAOS)
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    dur = nf / 24
    samp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
    for f in range(nf):
        t = f / 24
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        m = cam_matrix(img, t, dur)
        c.save()
        c.concat(m)
        c.drawImage(img, 0, 0, samp, skia.Paint(AntiAlias=True))
        c.restore()
        pts = []
        for u, v in PATH:
            p = m.mapXY(u * img.width(), v * img.height())
            pts.append((p.x(), p.y()))
        L = E.path_len(pts)

        def head(tt):
            # steady glide (the path starts and ends off-frame): head at the path start at T_IN, at its end at
            # T_OUT, the tail following on out
            return L * (tt - T_IN) / (T_OUT - T_IN)

        speed = abs(head(t + 1 / 96) - head(t - 1 / 96)) * 48
        E.light_streak(c, pts, head(t), TAIL, mb_px=speed / 24)
        c.drawRect(R(0, 0, W, BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - BAR, W, BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray()[..., :3].tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)


if __name__ == "__main__":
    main()
