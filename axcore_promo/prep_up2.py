"""Opening v3 source prep: a clip's frame range blown up x2 (Lanczos + a light unsharp mask) so the edit works from a
sharper base; optionally the inspection shot's holographic "PASS" badge (client reference S2) drawn on at the x2
size, anchored to the scene by tracking the camera (similarity fit to LK tracks, chained from the first frame).
Usage: python3 prep_up2.py <in.mp4> <out.mp4> [first=0] [count=all] [--pass x,y,t0] [--stab y0,y1]
  --pass: badge centre as fractions of the source frame at the first frame, and its appear time (s)
  --stab: lock the camera (client: the generated "static" camera still drifts and breathes): every frame is warped
          back onto the first, tracking only the still background between rows y0..y1 (fractions), with a slight
          zoom to hide the edges; the badge then stays put. "--stab -1,0": the clip's camera is already still (measured)
          - no warp, the badge simply fixed in the frame
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
    """The PASS hologram (client reference): a glowing green check in a circle and a large "PASS", thin HUD lines
    and small read-outs beside it; no panel behind (it floats over the board)."""
    w, h = int(600 * scale), int(210 * scale)
    pad = int(50 * scale)
    im = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    G = (110, 255, 150, 255)
    cx, cy, r = pad + int(60 * scale), pad + int(84 * scale), int(52 * scale)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=G, width=max(2, int(7 * scale)))
    d.line([(cx - r * 0.45, cy + r * 0.0), (cx - r * 0.1, cy + r * 0.36), (cx + r * 0.5, cy - r * 0.36)],
           fill=G, width=max(2, int(9 * scale)), joint="curve")
    f = ImageFont.truetype(FONT, int(104 * scale))
    d.text((pad + int(132 * scale), cy + int(4 * scale)), "PASS", font=f, fill=(140, 255, 170, 255), anchor="lm")
    lw = max(1, int(2.5 * scale))
    x0, x1 = pad + int(150 * scale), pad + int(520 * scale)
    yl = pad + int(162 * scale)
    d.line([(x0, yl), (x1, yl), (x1, yl - int(34 * scale))], fill=G, width=lw)
    d.line([(x1 - int(120 * scale), pad + int(10 * scale)), (x1, pad + int(10 * scale)),
            (x1, pad + int(40 * scale))], fill=G, width=lw)
    fs = ImageFont.truetype(FONT.replace("Bold", "SemiBold"), int(26 * scale))
    d.text((x1 - int(118 * scale), pad - int(16 * scale)), "QC 0.998   ID 2417", font=fs, fill=(150, 255, 180, 220))
    d.text((x0 + int(10 * scale), yl + int(10 * scale)), "SOLDER OK   ALIGN 0.02 mm", font=fs, fill=(150, 255, 180, 220))
    gl = np.asarray(im.filter(ImageFilter.GaussianBlur(16 * scale))).copy()
    gl[..., 0], gl[..., 1], gl[..., 2] = 40, 255, 110
    gl[..., 3] = np.clip(gl[..., 3].astype(np.float32) * 1.8, 0, 255).astype(np.uint8)
    out = Image.alpha_composite(Image.fromarray(gl), im)
    return np.asarray(out).astype(np.float32) / 255.0


def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = [a for a in sys.argv[3:] if not a.startswith("--")]
    first = int(args[0]) if args else 0
    count = int(args[1]) if len(args) > 1 else 10 ** 6
    pas = None
    stab = None
    if "--stab" in sys.argv:
        stab = [float(v) for v in sys.argv[sys.argv.index("--stab") + 1].split(",")]
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
        if prev is not None and not (stab is not None and stab[0] < 0):
            mask = None
            if stab is not None:
                mask = np.zeros_like(prev)
                mask[int(stab[0] * prev.shape[0]):int(stab[1] * prev.shape[0])] = 255
            p0 = cv2.goodFeaturesToTrack(prev, 600, 0.01, 7, mask=mask)
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None)
            m, _ = cv2.estimateAffinePartial2D(p0[st == 1], p1[st == 1])
            if m is not None:
                M = np.vstack([m, [0, 0, 1]]) @ M
        prev = g
        if stab is not None and stab[0] < 0:          # (--stab -1,0: the camera is already still - badge fixed)
            M = np.eye(3)
        elif stab is not None:                        # warp back onto the first frame, zoomed a little
            hh, ww = f.shape[:2]
            Z = np.array([[1.04, 0, -0.02 * ww], [0, 1.04, -0.02 * hh], [0, 0, 1]])
            f = cv2.warpAffine(f, (Z @ np.linalg.inv(M))[:2], (ww, hh), flags=cv2.INTER_LANCZOS4,
                               borderMode=cv2.BORDER_REFLECT)
        up = cv2.resize(f, (f.shape[1] * 2, f.shape[0] * 2), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        up = cv2.addWeighted(up, 1.45, cv2.GaussianBlur(up, (0, 0), 2.2), -0.45, 0)
        if pas is not None:
            t = i / 24.0
            a = np.clip((t - pas[2]) / 0.25, 0, 1)
            if a > 0:
                flick = 0.75 + 0.25 * np.sin(t * 40) if a < 1 else 0.96 + 0.04 * np.sin(t * 5)
                s = (1.0 if stab[0] < 0 else 1.04) if stab is not None else np.hypot(M[0, 0], M[1, 0])
                if bimg is None or abs(bimg[1] - s) > 0.02:
                    bimg = (badge(float(2 * s * (0.9 + 0.1 * a))), s)
                b = bimg[0]
                x0, y0 = pas[0] * f.shape[1], pas[1] * f.shape[0]
                Mb = M if stab is None or stab[0] < 0 else \
                    np.array([[1.04, 0, -0.02 * f.shape[1]], [0, 1.04, -0.02 * f.shape[0]], [0, 0, 1]])
                x, y = (Mb @ np.array([x0, y0, 1.0]))[:2] * 2
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
