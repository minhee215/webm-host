"""Opening v3, the inspection monitor shot, re-timed (client): the board comes down onto the screen, the conveyor
stops, the scan line runs over the still board, REJECT. Built from the generated monitor clip itself, so the monitor
stays the real one: one frame (the board fully on screen) is taken apart -
  - the clip's own scan line is removed (on the board: patched from an earlier frame aligned onto it, where the line
    was elsewhere; on the empty screen: filled from the rows above and below),
  - the board is lifted out as a sprite, and the screen under it filled smoothly (plane fit to the screen round it),
then put back together per frame: the board slides in from the screen's top edge and settles (ease-out), holds; a
cyan scan line (the clip's look) sweeps down over it; once it has passed the faulty IC, a red box + REJECT and a red
frame flash. Output x2 with the same Lanczos + unsharp as prep_up2.
Usage: python3 prep_monitor2.py <monitor.mp4> <out.mp4> [frame=58] [patch_from=42] [frames=42]
"""
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/home/user/webm-host/axcore_promo/fonts/Pretendard-Bold.otf"
RED = (255, 64, 80)
T_STOP, T_SCAN0, T_SCAN1 = 11, 13, 30           # frames: board settles, scan starts, scan reaches the screen bottom
DEF_RX, DEF_RU = 0.382, 0.088


def read(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        out.append(f)


def line_rows(f):
    f = f.astype(np.float32)
    cy = (f[..., 1] + f[..., 0]) / 2 - f[..., 2]
    prof = (cy[:, 100:1100] * (f[:, 100:1100, 1] > 170)).mean(1)
    r = int(np.argmax(prof))
    return r - 12, r + 13


def board_box(f):
    """The board's rectangle from row / column profiles of its green (robust to the chip and the scan line)."""
    b, g, r = [f[..., i].astype(np.int16) for i in range(3)]
    m = (g > 90) & (g > r + 35) & (g > b + 5)
    Ww = f.shape[1]
    rows = m[:, int(Ww * 0.2):int(Ww * 0.68)].mean(1)
    rr = np.where(rows > 0.25)[0]
    gold = (r > 150) & (g > 100) & (b < 120) & (r > b + 60)        # (the edge connector)
    cols = (m | gold)[rr.min():rr.max() + 1, :int(Ww * 0.79)].mean(0)
    cc = np.where(cols > 0.12)[0]
    return int(cc.min()), int(rr.min()), int(cc.max()) + 1, int(rr.max()) + 1


def board_box_old(f):
    b, g, r = [f[..., i].astype(np.int16) for i in range(3)]
    m = ((g > 90) & (g > r + 35) & (g > b + 5)).astype(np.uint8)
    m[:, int(f.shape[1] * 0.79):] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    x, y, w, h = st[i, :4]
    return int(x), int(y), int(x + w), int(y + h)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    k0 = int(sys.argv[3]) if len(sys.argv) > 3 else 58
    k1 = int(sys.argv[4]) if len(sys.argv) > 4 else 42
    NF = int(sys.argv[5]) if len(sys.argv) > 5 else 42
    fr = read(src)
    F = fr[k0].copy()
    Hh, Ww = F.shape[:2]
    y0, y1 = line_rows(F)
    bx0, by0, bx1, by1 = board_box(F)
    # 1) the line on the board: patch from frame k1 aligned onto F (ECC, affine, on the board minus the line)
    A = cv2.cvtColor(F, cv2.COLOR_BGR2GRAY).astype(np.float32)
    B = cv2.cvtColor(fr[k1], cv2.COLOR_BGR2GRAY).astype(np.float32)
    mask = np.zeros_like(A, np.uint8)
    mask[by0:by1, bx0:bx1] = 255
    mask[max(0, y0 - 46):y1 + 32] = 0
    # board features (SIFT) matched between frame k1 and F; a homography (the screen is seen at a slight angle, so
    # the board grows as it comes down) maps k1 onto F
    mb = np.zeros_like(B, np.uint8)
    mb[int(Hh * 0.18):, int(Ww * 0.18):int(Ww * 0.69)] = 255
    sift = cv2.SIFT_create(3000)
    ka, da = sift.detectAndCompute(A.astype(np.uint8), mask)
    kb, db = sift.detectAndCompute(B.astype(np.uint8), mb)
    good = [m for m, n in cv2.BFMatcher().knnMatch(db, da, k=2) if m.distance < 0.7 * n.distance]
    src_p = np.float32([kb[m.queryIdx].pt for m in good])
    dst_p = np.float32([ka[m.trainIdx].pt for m in good])
    Hm, inl = cv2.findHomography(src_p, dst_p, cv2.RANSAC, 1.5)
    print("patch homography inliers", int(inl.sum()), "of", len(good))
    Bw = cv2.warpPerspective(fr[k1], Hm, (Ww, Hh), flags=cv2.INTER_LINEAR)
    ramp = np.clip(np.minimum(np.arange(Hh) - (y0 - 42), (y1 + 26) - np.arange(Hh)) / 6.0, 0, 1)[:, None, None]
    cols = np.zeros((1, Ww, 1))
    cols[0, bx0:bx1] = 1
    F = (F * (1 - ramp * cols) + Bw * ramp * cols).astype(np.uint8)
    # 2) the board sprite; the screen behind it rebuilt from the clip's own empty-screen frames (before the board
    # arrives), aligned onto F on the still machine round the screen, each used where it has neither its scan line
    # nor the board
    sprite = F[by0:by1, bx0:bx1].copy()
    orb = cv2.ORB_create(4000)
    gF = cv2.cvtColor(F, cv2.COLOR_BGR2GRAY)
    still = np.full(gF.shape, 255, np.uint8)
    still[int(Hh * 0.15):int(Hh * 0.93), int(Ww * 0.06):int(Ww * 0.78)] = 0   # (not the screen's moving content)
    kF, dF = orb.detectAndCompute(gF, still)
    acc = np.zeros(F.shape, np.float64)
    wsum = np.zeros(F.shape[:2], np.float64)
    for e in (0, 6):
        E = fr[e]
        gE = cv2.cvtColor(E, cv2.COLOR_BGR2GRAY)
        kE, dE = orb.detectAndCompute(gE, still)
        mt = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(dE, dF)
        src_p = np.float32([kE[m.queryIdx].pt for m in mt])
        dst_p = np.float32([kF[m.trainIdx].pt for m in mt])
        M, _ = cv2.estimateAffinePartial2D(src_p, dst_p, ransacReprojThreshold=2.0)
        Ew = cv2.warpAffine(E, M, (Ww, Hh), flags=cv2.INTER_LINEAR)
        bad = np.zeros((Hh, Ww), np.uint8)
        ly0, ly1 = line_rows(E)
        bad[max(0, ly0 - 12):ly1 + 12] = 1
        f16 = E.astype(np.int16)
        bad |= ((f16[..., 1] > 90) & (f16[..., 1] > f16[..., 2] + 35)).astype(np.uint8)
        bad = cv2.dilate(bad, np.ones((15, 15), np.uint8))
        good = 1.0 - cv2.warpAffine(bad.astype(np.float32), M, (Ww, Hh), borderValue=1.0)
        good = cv2.GaussianBlur(np.clip(good, 0, 1), (0, 0), 3)
        acc += Ew * good[..., None]
        wsum += good
    empty = (acc / np.maximum(wsum, 1e-3)[..., None])
    # use it inside the screen's content area (feathered), keep F elsewhere (bezel, side panel, machine)
    zone = np.zeros((Hh, Ww), np.float32)
    zone[int(Hh * 0.17):int(Hh * 0.92), int(Ww * 0.065):int(Ww * 0.795)] = 1
    zone = cv2.GaussianBlur(zone * (wsum > 0.5), (0, 0), 4)[..., None]
    base = (F * (1 - zone) + empty * zone)
    base = np.clip(base, 0, 255).astype(np.uint8)
    # the screen area (where the board may show): bright, within the screen's columns, below its top edge
    L = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
    scr = (L > 120).astype(np.uint8)
    scr[:, int(Ww * 0.79):] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(scr)
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    scr = (lab == i).astype(np.uint8)
    scr = cv2.morphologyEx(scr, cv2.MORPH_CLOSE, np.ones((31, 31), np.uint8))
    scr_top = int(np.median([np.argmax(scr[:, x] > 0) for x in range(bx0 + 20, bx1 - 20, 10)]))
    scr_bot = int(np.median([Hh - 1 - np.argmax(scr[::-1, x] > 0) for x in range(bx0 + 20, bx1 - 20, 10)]))
    soft = cv2.GaussianBlur(scr.astype(np.float32), (0, 0), 1.2)[..., None]
    print("line", y0, y1, "board", (bx0, by0, bx1, by1), "screen rows", scr_top, scr_bot)
    bw = bx1 - bx0
    font = ImageFont.truetype(FONT, 40)
    enc = None
    for k in range(NF):
        q = min(1.0, k / T_STOP)
        dy = -(by1 - scr_top) * (1 - (1 - (1 - q) ** 3)) if k < T_STOP else 0.0     # slides in, settles
        frame = base.astype(np.float32).copy()
        layer = np.zeros_like(frame)
        alpha = np.zeros((Hh, Ww, 1), np.float32)
        ty = int(round(by0 + dy))
        ys, ye = max(0, ty), min(Hh, ty + sprite.shape[0])
        if ye > ys:
            layer[ys:ye, bx0:bx1] = sprite[ys - ty:ye - ty]
            alpha[ys:ye, bx0:bx1] = 1.0
        alpha *= soft
        frame = frame * (1 - alpha) + layer * alpha
        up = cv2.resize(frame, (Ww * 2, Hh * 2), interpolation=cv2.INTER_LANCZOS4)
        up = cv2.addWeighted(up, 1.45, cv2.GaussianBlur(up, (0, 0), 2.2), -0.45, 0)
        img = Image.fromarray(np.clip(up, 0, 255).astype(np.uint8)[..., ::-1]).convert("RGBA")
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        s = (k - T_SCAN0) / float(T_SCAN1 - T_SCAN0)
        sy = None
        if 0 <= s <= 1:                                   # the scan line (cyan core, soft glow), across the screen
            e = s * s * (3 - 2 * s)
            sy = scr_top + (scr_bot - scr_top) * e
            x0, x1 = int(Ww * 0.075) * 2, int(Ww * 0.79) * 2
            for wdt, a in ((26, 40), (14, 70), (6, 140), (2, 255)):
                dr.rectangle((x0, sy * 2 - wdt, x1, sy * 2 + wdt), fill=(70, 230, 255, a) if wdt > 2 else
                             (215, 250, 255, 255))
        dfy = by1 - DEF_RU * bw
        hit = T_SCAN0 + (T_SCAN1 - T_SCAN0) * 0.5 if False else None
        # the defect is found once the line has passed it
        e_hit = None
        for kk in range(T_SCAN0, T_SCAN1 + 1):
            ss = (kk - T_SCAN0) / float(T_SCAN1 - T_SCAN0)
            if scr_top + (scr_bot - scr_top) * ss * ss * (3 - 2 * ss) >= dfy:
                e_hit = kk
                break
        if e_hit is not None and k >= e_hit:
            a = min(1.0, (k - e_hit + 1) / 3.0)
            cx, cy = (bx0 + DEF_RX * bw) * 2, dfy * 2
            sz = bw * 2 * 0.085 * (1 + 0.6 * (1 - a))
            dr.rectangle((cx - sz / 2, cy - sz / 2, cx + sz / 2, cy + sz / 2), fill=RED + (int(50 * a),),
                         outline=RED + (int(255 * a),), width=5)
            tx, ty2 = cx + sz / 2 + 10, cy - sz / 2
            dr.rounded_rectangle((tx, ty2, tx + 196, ty2 + 58), radius=10, fill=RED + (int(240 * a),))
            dr.text((tx + 98, ty2 + 29), "REJECT", font=font, fill=(255, 255, 255, int(255 * a)), anchor="mm")
            fl = k - e_hit
            if fl < 12:
                fa = (1 - fl / 12.0) * min(1.0, (fl + 1) / 2.0)
                dr.rectangle(((bx0 - 4) * 2, (by0 - 4) * 2, (bx1 + 4) * 2, (by1 + 4) * 2),
                             outline=RED + (int(230 * fa),), width=7)
        img = Image.alpha_composite(img, ov).convert("RGB")
        out = np.asarray(img)[..., ::-1]
        if enc is None:
            enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                    "-s", "%dx%d" % (out.shape[1], out.shape[0]), "-r", "24", "-i", "-",
                                    "-c:v", "libx264", "-crf", "10", "-preset", "fast", "-pix_fmt", "yuv444p", dst],
                                   stdin=subprocess.PIPE)
        enc.stdin.write(np.ascontiguousarray(out).tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, NF, "REJECT at frame", e_hit)


if __name__ == "__main__":
    main()
