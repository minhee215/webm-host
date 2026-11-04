"""Opening v3 source prep: a clip's frame range blown up x2 (Lanczos + a light unsharp mask) so the edit works from a
sharper base; optionally the inspection shot's holographic "PASS" badge (client reference S2) drawn on at the x2
size, anchored to the scene by tracking the camera (similarity fit to LK tracks, chained from the first frame).
Usage: python3 prep_up2.py <in.mp4> <out.mp4> [first=0] [count=all] [--pass x,y,t0]
  --pass: badge centre as fractions of the source frame at the first frame, and its appear time (s)
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/home/user/webm-host/axcore_promo/fonts/Pretendard-Bold.otf"
CYAN = (25, 200, 255)
GREEN = (60, 235, 170)


def badge(scale):
    """The PASS badge as an RGBA image: a glowing rounded frame, a check in a circle, 'PASS'."""
    w, h = int(330 * scale), int(110 * scale)
    pad = int(30 * scale)
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = (pad, pad, pad + w, pad + h)
    d.rounded_rectangle(box, radius=int(22 * scale), fill=(20, 180, 150, 70), outline=GREEN + (255,),
                        width=max(2, int(4 * scale)))
    cx, cy, r = pad + int(62 * scale), pad + h // 2, int(32 * scale)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=GREEN + (255,), width=max(2, int(5 * scale)))
    d.line([(cx - r * 0.45, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.38), (cx + r * 0.5, cy - r * 0.35)],
           fill=GREEN + (255,), width=max(2, int(6 * scale)), joint="curve")
    f = ImageFont.truetype(FONT, int(64 * scale))
    d.text((pad + int(115 * scale), cy), "PASS", font=f, fill=(225, 255, 240, 255), anchor="lm")
    glow = im.filter(ImageFilter.GaussianBlur(10 * scale))
    out = Image.alpha_composite(glow, im)
    return np.asarray(out).astype(np.float32) / 255.0


def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    first = int(args[0]) if args else 0
    count = int(args[1]) if len(args) > 1 else 10 ** 6
    pas = None
    if "--pass" in sys.argv:
        pas = [float(v) for v in sys.argv[sys.argv.index("--pass") + 1].split(",")]
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    enc = None
    prev = None
    M = np.eye(3)
    bimg = None
    for i in range(count):
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        if prev is not None:
            p0 = cv2.goodFeaturesToTrack(prev, 600, 0.01, 7)
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None)
            m, _ = cv2.estimateAffinePartial2D(p0[st == 1], p1[st == 1])
            if m is not None:
                M = np.vstack([m, [0, 0, 1]]) @ M
        prev = g
        up = cv2.resize(f, (f.shape[1] * 2, f.shape[0] * 2), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        up = cv2.addWeighted(up, 1.45, cv2.GaussianBlur(up, (0, 0), 2.2), -0.45, 0)
        if pas is not None:
            t = i / 24.0
            a = np.clip((t - pas[2]) / 0.25, 0, 1)
            if a > 0:
                flick = 0.75 + 0.25 * np.sin(t * 40) if a < 1 else 0.92 + 0.08 * np.sin(t * 9)
                s = np.hypot(M[0, 0], M[1, 0])
                if bimg is None or abs(bimg[1] - s) > 0.02:
                    bimg = (badge(float(2 * s * (0.9 + 0.1 * a))), s)
                b = bimg[0]
                x0, y0 = pas[0] * f.shape[1], pas[1] * f.shape[0]
                x, y = (M @ np.array([x0, y0, 1.0]))[:2] * 2
                y -= 26 * (1 - a) * 2
                hh, ww = b.shape[:2]
                X, Y = int(x - ww / 2), int(y - hh / 2)
                ys, xs = slice(max(0, Y), min(up.shape[0], Y + hh)), slice(max(0, X), min(up.shape[1], X + ww))
                bb = b[ys.start - Y:ys.stop - Y, xs.start - X:xs.stop - X]
                al = bb[..., 3:4] * a * flick
                rgb = bb[..., [2, 1, 0]] * 255
                region = up[ys, xs]
                up[ys, xs] = region * (1 - al) + (region + rgb * 0.9) * al * 0.5 + rgb * al * 0.5
        up = np.clip(up, 0, 255).astype(np.uint8)
        if enc is None:
            enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                    "-s", "%dx%d" % (up.shape[1], up.shape[0]), "-r", "24", "-i", "-",
                                    "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv444p", dst],
                                   stdin=subprocess.PIPE)
        enc.stdin.write(up.tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, i + 1)


if __name__ == "__main__":
    main()
