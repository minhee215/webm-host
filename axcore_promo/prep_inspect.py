"""Opening v3, the inspection station shot, fixed in post (client: the camera comes down too close, the blue light is
too narrow; no credits left for a new take). The camera is locked off, so:
  - the camera head's descent is tracked (template of the camera body), and limited: wherever it has come down more
    than DMAX, the head's column band is lifted by the excess, and the strip it uncovers is taken from a frame where
    the head was still up (the board has already stopped there, so the scene matches);
  - the blue light is widened: a soft light cone from the (lifted) lens down to the board and a wide pool of blue
    light over the whole board, both following the clip's own light (its blue measured on the board).
Usage: python3 prep_inspect.py <in.mp4> <out.mp4> [plate_frame=24] [dmax=35]
"""
import subprocess
import sys

import cv2
import numpy as np

BAND = (420, 772)                 # the head's columns (carriage plate, cables, camera, lens)
LENS = (588, 722)                 # the lens' columns
TOPROW = 26                       # below the fixed top beam
BODY = (595, 135, 715, 275)       # the camera body in the plate frame (x0, y0, x1, y1)
LENS_BOTTOM0 = 275                # its lens' lower edge there
BOARD = (620.0, 448.0, 300.0, 52.0)   # the board's top surface: centre, half width, half height (ellipse)


def read(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(f)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    pk = int(sys.argv[3]) if len(sys.argv) > 3 else 24
    dmax = float(sys.argv[4]) if len(sys.argv) > 4 else 35.0
    fr = read(src)
    plate = fr[pk].astype(np.float32)
    Hh, Ww = plate.shape[:2]
    tpl = cv2.cvtColor(fr[pk][BODY[1]:BODY[3], BODY[0]:BODY[2]], cv2.COLOR_BGR2GRAY)
    desc, light = [], []
    for f in fr:
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        win = g[60:520, BODY[0] - 40:BODY[2] + 40]
        r = cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, loc = cv2.minMaxLoc(r)
        desc.append(60 + loc[1] - BODY[1])
        roi = f[420:475, 560:780].astype(np.float32)
        light.append(float((roi[..., 0] - roi[..., 2]).mean()))
    desc = np.array(desc, float)
    desc = np.convolve(np.pad(desc, 2, mode="edge"), np.ones(5) / 5, mode="valid")    # smooth the track
    light = np.array(light) - np.max(light[pk - 4:pk + 7])      # baseline: the board stopped, light off
    light = np.clip(light / max(light.max(), 1e-3), 0, 1)
    light = np.convolve(np.pad(light, 2, mode="edge"), np.ones(5) / 5, mode="valid")
    print("descent max %.0f px, light peak at frame %d" % (desc.max(), int(np.argmax(light))))
    xs = np.arange(Ww, dtype=np.float32)
    band = np.clip(np.minimum(xs - BAND[0], BAND[1] - xs) / 18.0, 0, 1)[None, :, None]
    lens = np.clip(np.minimum(xs - LENS[0], LENS[1] - xs) / 12.0, 0, 1)[None, :, None]
    yy, xx = np.mgrid[0:Hh, 0:Ww].astype(np.float32)
    enc = None
    for i, f in enumerate(fr):
        cur = f.astype(np.float32)
        out = cur.copy()
        d = max(0.0, desc[i])
        lift = max(0.0, d - dmax)
        lb_cur = LENS_BOTTOM0 + d                       # the lens' lower edge now
        lb_new = lb_cur - lift
        if lift > 0.5:
            src_rows = np.clip(np.arange(Hh, dtype=np.float32) + np.float32(lift), 0, Hh - 1).astype(np.float32)
            shifted = cv2.remap(cur, np.tile(xs, (Hh, 1)), np.tile(src_rows[:, None], (1, Ww)),
                                cv2.INTER_LINEAR)
            rows = np.arange(Hh, dtype=np.float32)[:, None, None]
            top = np.clip((rows - TOPROW) / 8.0, 0, 1)
            up = top * np.clip((lb_new + 2 - rows) / 3.0, 0, 1)            # lifted head
            gap = np.clip((rows - lb_new) / 3.0, 0, 1) * np.clip((lb_cur + 6 - rows) / 4.0, 0, 1)
            out = out * (1 - up * band) + shifted * up * band
            out = out * (1 - gap * band) + plate * gap * band              # uncovered: as when the head was up
        L = light[i]
        if L > 0.01:                                    # the wider light: cone + pool on the board
            cx, cy, ax, ay = BOARD
            lx = (LENS[0] + LENS[1]) / 2.0
            t = np.clip((yy - lb_new) / max(cy - lb_new, 1.0), 0, 1)
            half = 40 + (ax * 0.95 - 40) * t
            cone = np.clip(1 - np.abs(xx - lx) / half, 0, 1) ** 1.5 * (yy > lb_new) * (yy < cy + ay * 0.3)
            cone = cv2.GaussianBlur(cone.astype(np.float32), (0, 0), 6) * (0.35 + 0.65 * t)
            pool = np.exp(-(((xx - cx) / ax) ** 2 + ((yy - cy) / ay) ** 2) * 1.6)
            core = np.exp(-(((xx - lx) / (ax * 0.35)) ** 2 + ((yy - cy) / (ay * 0.45)) ** 2) * 2.0)
            col = np.array([255, 120, 70], np.float32)          # BGR: blue-violet
            add = (cone[..., None] * 0.30 + pool[..., None] * 0.45 + core[..., None] * 0.40) * L
            out = out + add * col
            out = out * (1 - 0.18 * L * pool[..., None]) + 0.18 * L * pool[..., None] * \
                np.array([255, 170, 120], np.float32)           # a cool tint over the board under the light
        out = np.clip(out, 0, 255).astype(np.uint8)
        if enc is None:
            enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                    "-s", "%dx%d" % (Ww, Hh), "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "8",
                                    "-preset", "fast", "-pix_fmt", "yuv444p", dst], stdin=subprocess.PIPE)
        enc.stdin.write(out.tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, len(fr))


if __name__ == "__main__":
    main()
