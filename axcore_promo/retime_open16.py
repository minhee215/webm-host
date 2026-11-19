"""00:00:00:00-00:00:16:09 re-timed (client): the hand-over 09:23-12:00 (into the inspection panel, the pill, the press)
a little slower, the frames around it a little fewer, the total length unchanged (394 frames):
  out   0-199  seg_where2 frames 0-199 as they were
  out 200-235  seg_where2 frames 200-239 (40 -> 36 frames: the constellation's last moments a touch quicker)
  out 236-291  seg_insight frames 0-47 (48 -> 56 frames, x0.86: the hand-over slower)
  out 292-393  seg_insight frames 48-153 (106 -> 102 frames: the zoom-through and the map's start a touch quicker)
Every frame is rendered at its re-timed scene time (no frame interpolation); the live-action touch footage, read
between its frames, is blended from its two neighbours.
Usage: python3 retime_open16.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import skia

import engine as E
import media
import seg_insight as SI
import seg_where2 as W2
from engine import W, H, R, paint_fill

N_OUT = 394
_frame = media.frame


def frame_blend(name, t):
    """Clip frame at time t, blended between its two neighbours when t falls between frames."""
    x = t * media.FPS
    f0 = math.floor(x + 1e-6)
    a = x - f0
    img0, fi = _frame(name, f0 / media.FPS)
    if a < 0.02 or a > 0.98:
        return (img0 if a < 0.5 else _frame(name, (f0 + 1) / media.FPS)[0]), fi
    img1, _ = _frame(name, (f0 + 1) / media.FPS)
    s = skia.Surface.MakeRaster(skia.ImageInfo.Make(img0.width(), img0.height(), skia.ColorType.kRGBA_8888_ColorType,
                                                    skia.AlphaType.kPremul_AlphaType))
    c = s.getCanvas()
    c.drawImage(img0, 0, 0)
    p = skia.Paint()
    p.setAlphaf(a)
    c.drawImage(img1, 0, 0, E.SAMP, p)
    return s.makeImageSnapshot(), fi


media.frame = frame_blend


def source(k):
    """(scene, scene frame) of output frame k."""
    if k < 200:
        return "where", float(k)
    if k < 236:
        return "where", 200 + (k - 200) * 39 / 35
    if k < 292:
        return "insight", (k - 236) * 47 / 55
    return "insight", 48 + (k - 292) * 105 / 101


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, N_OUT)
    width = int(round(height * 16 / 9 / 2)) * 2
    W2.SW.setup(["x", "/dev/null", str(height), "240"])
    if height > 1080:
        media.MAX_READERS = 24
    E.configure(E.SEED, E.CHAOS)
    SC = max(1.0, height / H)
    SI.SCV = SC
    SWD, SHD = int(round(W * SC)), int(round(H * SC))
    info = skia.ImageInfo.Make(SWD, SHD, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    surf = skia.Surface.MakeRaster(info)
    buf = skia.Surface.MakeRaster(info)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "24000/1001", "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k in range(F0, F1):
        scene, f = source(k)
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SC, SC)
        if scene == "where":
            W2.render(c, f * W2.SW.DT)
        else:
            SI.render(c, f, buf)
        c.drawRect(R(0, 0, W, SI.BAR), paint_fill("#000000"))
        c.drawRect(R(0, H - SI.BAR, W, SI.BAR), paint_fill("#000000"))
        c.restore()
        enc.stdin.write(surf.makeImageSnapshot().toarray().tobytes())
    enc.stdin.close()
    enc.wait()
    print(out, F1 - F0)
