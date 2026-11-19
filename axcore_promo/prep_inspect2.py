"""Opening v3, the inspection station shot, second fix (client: the lifted head showed a seam and shook). No warping
now: the camera is locked off and the board has stopped, so the shot is re-timed from the clip's own frames - the
board comes in (x1.5), the head starts down and the picture holds on the frame where it has come down only a little;
on that held frame the blue light is laid (a cone from the lens, a wide pool over the board, the lens ring and a
violet sheen on the beam, as the clip's own light did), then the head goes back up (the descent played backwards).
The output is already on the edit's clock (56 frames).
Usage: python3 prep_inspect2.py <in.mp4> <out.mp4> [hold_frame=31]
"""
import subprocess
import sys

import cv2
import numpy as np

import prep_inspect as P

N_IN = 16          # board in: source 8..30 at x1.5
N_HOLD = 32        # held: light up 5, on 17, down 10
N_OUT = 8          # head back up


def light_layer(hh, ww, lb, L):
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    cx, cy, ax, ay = P.BOARD
    lx = (P.LENS[0] + P.LENS[1]) / 2.0
    t = np.clip((yy - lb) / max(cy - lb, 1.0), 0, 1)
    half = 36 + (ax * 0.95 - 36) * t
    cone = np.clip(1 - np.abs(xx - lx) / half, 0, 1) ** 1.5 * (yy > lb) * (yy < cy + ay * 0.3)
    cone = cv2.GaussianBlur(cone.astype(np.float32), (0, 0), 6) * (0.30 + 0.70 * t)
    pool = np.exp(-(((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2) * 1.6)
    core = np.exp(-(((xx - lx) / (ax * 0.35)) ** 2 + ((yy - cy) / (ay * 0.45)) ** 2) * 2.0)
    ring = np.exp(-(((xx - lx) / 60.0) ** 2 + ((yy - lb) / 9.0) ** 2))
    beam = ((yy > 28) & (yy < 160) & (xx < 440)).astype(np.float32)
    beam = cv2.GaussianBlur(beam, (0, 0), 12) * np.clip(1 - xx / 900.0, 0, 1)
    blue = np.array([255, 120, 70], np.float32)
    violet = np.array([255, 110, 150], np.float32)
    add = (cone * 0.28 + pool * 0.45 + core * 0.40 + ring * 0.9)[..., None] * blue + (beam * 0.22)[..., None] * violet
    return add * L, pool


def main():
    src, dst = sys.argv[1], sys.argv[2]
    hk = int(sys.argv[3]) if len(sys.argv) > 3 else 31
    fr = P.read(src)
    hh, ww = fr[0].shape[:2]
    # where the lens is in the held frame
    tpl = cv2.cvtColor(fr[24][P.BODY[1]:P.BODY[3], P.BODY[0]:P.BODY[2]], cv2.COLOR_BGR2GRAY)
    g = cv2.cvtColor(fr[hk], cv2.COLOR_BGR2GRAY)
    r = cv2.matchTemplate(g[60:520, P.BODY[0] - 40:P.BODY[2] + 40], tpl, cv2.TM_CCOEFF_NORMED)
    d = 60 + cv2.minMaxLoc(r)[3][1] - P.BODY[1]
    lb = P.LENS_BOTTOM0 + d
    print("held frame", hk, "descent", d, "lens bottom", lb)
    seq = [int(round(8 + i * (hk - 8) / (N_IN - 1))) for i in range(N_IN)]
    out = []
    for k in seq:
        out.append((fr[k], 0.0))
    for j in range(N_HOLD):
        L = min(1.0, (j + 1) / 5.0) if j < 22 else max(0.0, 1 - (j - 21) / 10.0)
        L = L * L * (3 - 2 * L)
        out.append((fr[hk], L))
    back = [int(round(hk - (i + 1) * (hk - 22) / N_OUT)) for i in range(N_OUT)]
    for k in back:
        out.append((fr[k], 0.0))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", "%dx%d" % (ww, hh), "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "8",
                            "-preset", "fast", "-pix_fmt", "yuv444p", dst], stdin=subprocess.PIPE)
    cache = {}
    for f, L in out:
        img = f.astype(np.float32)
        if L > 0.005:
            if "lay" not in cache:
                cache["lay"] = light_layer(hh, ww, lb, 1.0)
            add, pool = cache["lay"]
            img = img + add * L
            img = img * (1 - 0.16 * L * pool[..., None]) + 0.16 * L * pool[..., None] * \
                np.array([255, 170, 120], np.float32)
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, len(out), "frames; PASS from about frame", N_IN + 6)


if __name__ == "__main__":
    main()
