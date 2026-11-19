"""Opening v3, the logistics shot: a holographic wifi icon floating over the lift robot's tote (client reference: the
robot's connection shown as a glowing blue wifi sign). The icon follows the tote: a patch of the tote under the icon is
tracked by template matching from frame to frame (re-anchored on the first frame's patch, smoothed).
Usage: python3 prep_wifi.py <in.mp4> <out.mp4> x,y [t0=0.3] [size=0.09]
  x,y: the icon's centre at the first frame (fractions of the frame); the tote patch is taken just below it
"""
import subprocess
import sys

import cv2
import numpy as np


def icon(px):
    """Three arcs and a dot, glowing blue, RGBA float."""
    s = int(px * 1.6)
    im = np.zeros((s, s, 4), np.float32)
    c = (s // 2, int(s * 0.72))
    col = (255, 205, 90)                    # BGR: light blue
    lw = max(2, int(px * 0.085))
    for r in (0.20, 0.36, 0.52):
        cv2.ellipse(im, c, (int(px * r), int(px * r)), 0, 225, 315, col + (255,), lw, cv2.LINE_AA)
    cv2.circle(im, c, max(2, int(px * 0.07)), col + (255,), -1, cv2.LINE_AA)
    a = im[..., 3] / 255.0
    glow = cv2.GaussianBlur(a, (0, 0), px * 0.06) * 1.6 + cv2.GaussianBlur(a, (0, 0), px * 0.18) * 0.9
    out = np.zeros_like(im)
    out[..., :3] = np.array([255, 190, 70], np.float32)
    out[..., :3] = out[..., :3] * (1 - a[..., None]) + np.array(col, np.float32) * a[..., None]
    out[..., 3] = np.clip(np.maximum(a, glow), 0, 1)
    return out


def main():
    src, dst = sys.argv[1], sys.argv[2]
    x0, y0 = [float(v) for v in sys.argv[3].split(",")]
    t0 = float(sys.argv[4]) if len(sys.argv) > 4 else 0.3
    size = float(sys.argv[5]) if len(sys.argv) > 5 else 0.09
    cap = cv2.VideoCapture(src)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    h, w = frames[0].shape[:2]
    px = size * w
    ic = icon(px)
    # the tote patch below the icon
    pw, ph = int(px * 1.2), int(px * 0.6)
    cx, cy = x0 * w, y0 * h + px * 0.95
    g0 = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    tpl = g0[int(cy - ph / 2):int(cy + ph / 2), int(cx - pw / 2):int(cx + pw / 2)]
    pos = [(cx, cy)]
    for f in frames[1:]:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        px_, py_ = pos[-1]
        R = int(px * 0.6)
        xa, ya = int(max(0, px_ - pw / 2 - R)), int(max(0, py_ - ph / 2 - R))
        win = g[ya:int(min(h, py_ + ph / 2 + R)), xa:int(min(w, px_ + pw / 2 + R))]
        r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
        _, mv, _, loc = cv2.minMaxLoc(r)
        nxt = (xa + loc[0] + pw / 2, ya + loc[1] + ph / 2) if mv > 0.4 else pos[-1]
        pos.append(nxt)
        tpl = g[int(nxt[1] - ph / 2):int(nxt[1] + ph / 2), int(nxt[0] - pw / 2):int(nxt[0] + pw / 2)] \
            if mv > 0.4 and tpl.shape == (ph, pw) else tpl
    pos = np.array(pos)
    k = 7
    pos = np.stack([np.convolve(np.pad(pos[:, i], k // 2, mode="edge"), np.ones(k) / k, mode="valid")
                    for i in range(2)], 1)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s",
                            "%dx%d" % (w, h), "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "8", "-preset", "fast",
                            "-pix_fmt", "yuv444p", dst], stdin=subprocess.PIPE)
    ih, iw = ic.shape[:2]
    for i, f in enumerate(frames):
        t = i / 24.0
        a = float(np.clip((t - t0) / 0.3, 0, 1))
        img = f.astype(np.float32)
        if a > 0:
            flick = (0.7 + 0.3 * np.sin(t * 45)) if a < 1 else 0.92 + 0.08 * np.sin(t * 4)
            bob = np.sin(t * 2.4) * px * 0.03 + (1 - a) * px * 0.15
            X = int(pos[i, 0] - iw / 2)
            Y = int(pos[i, 1] - px * 0.95 - ih * 0.62 + bob)
            ys, xs = slice(max(0, Y), min(h, Y + ih)), slice(max(0, X), min(w, X + iw))
            b = ic[ys.start - Y:ys.stop - Y, xs.start - X:xs.stop - X]
            al = b[..., 3:4] * a * flick
            img[ys, xs] = img[ys, xs] * (1 - al * 0.55) + b[..., :3] * al * 0.55 + b[..., :3] * al * 0.35
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, len(frames), "track dx %.0f dy %.0f" % tuple(pos[-1] - pos[0]))


if __name__ == "__main__":
    main()
