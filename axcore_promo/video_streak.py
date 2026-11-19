"""The reference light streak over a moving background clip (the client's silo shot, with real camera motion).

The background is an image-to-video take generated from the clean, upscaled silo photo (the camera walks
slowly beneath the silos). The plate is tracked (global homography, track.py) so the streak - laid out in
frame-0 coordinates - stays locked to the sky as the camera moves. Framed for the film's 21:9 letterbox,
frame-for-frame 23.976 fps like the other deliverables.
Usage: python3 video_streak.py <bg.mp4> <out.mp4> [first=0] [frames=97] [height=1440]
Env AXS_PATH (JSON list of [u, v]) overrides the streak course for tuning.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
import skia

import engine as E
import track as T
from engine import W, H, R, paint_fill

BAR = 138
FPS_NUM, FPS_DEN = 24000, 1001
# streak course in frame-0 uv (full 16:9 frame; the picture band is v 0.128..0.872): up out of the lower left,
# across the sky between the silos, out over the top right - the client's clip
PATH = [(-0.06, 0.86), (0.12, 0.72), (0.28, 0.61), (0.44, 0.50), (0.62, 0.38), (0.80, 0.25), (1.06, 0.07)]
T_IN, T_OUT, TAIL = 0.30, 3.20, 1100.0   # the head crosses between these times (steady, like the clip)


def homographies(path, first, nf):
    frames = T.read_frames(path)[first:first + nf]
    grays = [T.to_gray(f) for f in frames]
    return [np.array(h).reshape(3, 3) for h in T.track_region(grays, [0.0, 0.0, 1.0, 1.0])]


def apply(Hm, u, v):
    p = Hm @ np.array([u, v, 1.0])
    return p[0] / p[2], p[1] / p[2]


def main():
    src, out = sys.argv[1], sys.argv[2]
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    nf = int(sys.argv[4]) if len(sys.argv) > 4 else 97
    height = int(sys.argv[5]) if len(sys.argv) > 5 else 1440
    course = [tuple(p) for p in json.loads(os.environ["AXS_PATH"])] if os.environ.get("AXS_PATH") else PATH
    width = int(round(height * 16 / 9 / 2)) * 2
    SC = height / H
    SW, SH = int(round(W * SC)), int(round(H * SC))
    Hs = homographies(src, first, nf)
    E.configure(E.SEED, E.CHAOS)
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p",
                            "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    samp = skia.SamplingOptions(skia.CubicResampler.Mitchell())
    for f in range(nf):
        ok, bgr = cap.read()
        if not ok:
            break
        rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGBA)
        img = skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType)
        t = f / 24
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        k = max(W / img.width(), H / img.height())
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(k, k)
        c.translate(-img.width() / 2, -img.height() / 2)
        c.drawImage(img, 0, 0, samp, skia.Paint(AntiAlias=True))
        c.restore()
        pts = []
        for u, v in course:
            uu, vv = apply(Hs[f], u, v)
            pts.append((uu * W, vv * H))
        L = E.path_len(pts)

        def head(tt):
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
