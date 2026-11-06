"""Opening v3, the inspection monitor shot: the generated monitor clip (at double speed) blown up x2 like prep_up2, with
the REJECT the client asked for drawn on the screen: the board is found per frame from its green (bounding box), a
small IC near its lower edge is the faulty part; once the screen's scan line has passed it, a red box with a REJECT
tag sits on it (moving with the board) and a red frame flashes round the board.
Usage: python3 prep_monitor.py <in.mp4> <out.mp4> [defect_rel_x=0.382] [defect_rel_up=0.088]
  defect position: x as a fraction of the board's width from its left edge, height above its lower edge as a fraction
  of its width
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/home/user/webm-host/axcore_promo/fonts/Pretendard-Bold.otf"
RED = (255, 64, 80)


def board_box(f):
    b, g, r = [f[..., i].astype(np.int16) for i in range(3)]
    m = ((g > 90) & (g > r + 35) & (g > b + 5)).astype(np.uint8)
    m[:, int(f.shape[1] * 0.83):] = 0                 # (the panel on the screen's right)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))   # across the chip and the scan line
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    if st[i, cv2.CC_STAT_AREA] < 3000:
        return None
    x, y, w, h = st[i, :4]
    return x, y, x + w, y + h


def scan_row(f, box):
    b, g, r = [f[..., i].astype(np.float32) for i in range(3)]
    cyan = (g + b) / 2 - r
    x0, x1 = int(f.shape[1] * 0.08), int(f.shape[1] * 0.78)
    prof = (cyan[:, x0:x1] * (g[:, x0:x1] > 170)).mean(1)
    return int(np.argmax(prof))


def main():
    src, dst = sys.argv[1], sys.argv[2]
    rx = float(sys.argv[3]) if len(sys.argv) > 3 else 0.382
    ru = float(sys.argv[4]) if len(sys.argv) > 4 else 0.088
    cap = cv2.VideoCapture(src)
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    # the board's left and lower edges move smoothly (belt + slow push in): fit them over the frames where they are
    # clean, so the box rides steady and carries on once the lower edge leaves the screen
    raw = [(board_box(f), scan_row(f, None)) for f in frames]
    H0 = frames[0].shape[0]
    ok = [(i, bx) for i, (bx, _) in enumerate(raw) if bx is not None and bx[3] < H0 * 0.92 and bx[3] - bx[1] > 60]
    ii = np.array([i for i, _ in ok], float)
    px0 = np.polyfit(ii, [bx[0] for _, bx in ok], 1)
    py1 = np.polyfit(ii, [bx[3] for _, bx in ok], 1)
    wid = float(np.median([bx[2] - bx[0] for _, bx in ok if 0.4 < (bx[2] - bx[0]) / frames[0].shape[1] < 0.5] or
                          [bx[2] - bx[0] for _, bx in ok]))
    info, hit = [], None
    for i, (bx, sy) in enumerate(raw):
        x0, y1 = np.polyval(px0, i), np.polyval(py1, i)
        d = (x0 + rx * wid, y1 - ru * wid, wid)
        box = (x0, y1 - wid * 0.45, x0 + wid, y1)
        if hit is None and bx is not None and d[1] >= sy:      # the line has passed the faulty part
            hit = i
        info.append((box, sy, d))
    print("REJECT from frame", hit)
    H0 = frames[0].shape[0]
    font = ImageFont.truetype(FONT, 40)
    enc = None
    for i, f in enumerate(frames):
        up = cv2.resize(f, (f.shape[1] * 2, f.shape[0] * 2), interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        up = cv2.addWeighted(up, 1.45, cv2.GaussianBlur(up, (0, 0), 2.2), -0.45, 0)
        img = Image.fromarray(np.clip(up, 0, 255).astype(np.uint8)[..., ::-1])
        bx, sy, d = info[i]
        if hit is not None and i >= hit and d is not None and d[1] < H0 * 0.90:
            a = min(1.0, (i - hit + 1) / 3.0)
            ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(ov)
            cx, cy, w = d[0] * 2, d[1] * 2, d[2] * 2
            s = w * 0.085 * (1 + 0.6 * (1 - a))
            dr.rectangle((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), fill=RED + (int(50 * a),),
                         outline=RED + (int(255 * a),), width=5)
            tx, ty = cx + s / 2 + 10, cy - s / 2
            dr.rounded_rectangle((tx, ty, tx + 196, ty + 58), radius=10, fill=RED + (int(240 * a),))
            dr.text((tx + 98, ty + 29), "REJECT", font=font, fill=(255, 255, 255, int(255 * a)), anchor="mm")
            fl = i - hit
            if fl < 12 and bx is not None:                # red frame flash round the board
                fa = (1 - fl / 12.0) * min(1.0, (fl + 1) / 2.0)
                x0, y0, x1, y1 = [v * 2 for v in bx]
                y0 = max(y0, H0 * 2 * 0.10)
                dr.rectangle((x0 - 8, y0 - 8, x1 + 8, y1 + 8), outline=RED + (int(230 * fa),), width=7)
            img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        out = np.asarray(img)[..., ::-1]
        if enc is None:
            enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                    "-s", "%dx%d" % (out.shape[1], out.shape[0]), "-r", "24", "-i", "-",
                                    "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv444p", dst],
                                   stdin=subprocess.PIPE)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, len(frames))


if __name__ == "__main__":
    main()
