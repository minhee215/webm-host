"""Opening 0:00-0:08 re-edit: four stock clips joined by hard cuts that ride the motion (no transitions).

Narration: "AI가 기업의 일하는 방식을 빠르게 바꾸고 있습니다. / 하지만 중요한 것은 AI 도입 자체가 아니라,"
Order and cut points come from measured motion (sparse LK flow, camera = similarity fit, subject = residual):
  1 factory  workers along the belt, camera trucks (content drifts right); cut as the front worker's hand
             reaches forward and down along the belt
  2 robot    picks up on the gripper finishing its swing down to the right, push-in; cut mid-way through the
             arm rising again
  3 engineer the rise carries on in the engineer's hand lifting the pen up to the 3D model on screen (touches
             it on "하지만"); cut screen-to-screen
  4 lab      graphic match on the monitors, the drift continues rightward: camera orbits right while a
             colleague walks left to right behind
All four are tuned to one camera language: content drifting right at the same speed with a gentle push-in
(small digital scale/pan ramps on top of each clip's own move), then matched to one look - luminance mean and
contrast, white balance and saturation pulled toward the sequence average with a cool, clean bias, skin
protected. Fade-in from black at the head only. Output: 21:9 band in 16:9 (letterbox), 23.976 fps
frame-for-frame (192 frames = 00:00:08:00).
Usage: python3 edit_open.py <factory> <robot> <engineer> <lab> <out.mp4> [height=1440]
"""
import subprocess
import sys

import cv2
import numpy as np

FPS_NUM, FPS_DEN = 24000, 1001
BAR_FRAC = 184 / 1440
FADE = 18                    # head fade-in, frames
# a = first source frame, n = timeline frames, push = added scale per frame, pan = added content drift
# (fraction of width per frame, + = right), v = vertical centre of the 21:9 band in the source (0..1)
SHOTS = [
    dict(key="factory", a=30, n=50, push=0.0016, pan=0.0000, v=0.50, zoom=1.03),
    dict(key="robot", a=96, n=42, push=0.0000, pan=0.0005, v=0.42, zoom=1.04),
    dict(key="engineer", a=30, n=47, push=0.0006, pan=0.0004, v=0.50, zoom=1.04),
    dict(key="lab", a=130, n=53, push=0.0010, pan=0.0000, v=0.40, zoom=1.03),
]
# look: targets are the shot average, pulled toward a cool, clean corporate neutral
COOL_B, COOL_A = -4.0, -0.5  # Lab b*/a* bias of the target white point
LIFT = 2.0                   # target luminance a touch above the shot average (clean, not dim)
K_L, K_AB, K_C = 0.75, 0.70, 0.55   # how far each shot moves toward the target (lum, white balance, chroma)
GRAIN = 1.2 / 255


def frames(path, a, n):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    out = []
    for _ in range(n):
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    while len(out) < n:
        out.append(out[-1])
    return out


def place(src, k, shot, W, Hb):
    """Source frame -> band (W x Hb): cover fit, base zoom, push-in and pan ramps."""
    h, w = src.shape[:2]
    s = max(W / w, Hb / h) * shot["zoom"] * (1 + shot["push"] * k)
    cx = w / 2 - shot["pan"] * k * w / shot["zoom"]
    cy = shot["v"] * h
    cy = min(max(cy, Hb / s / 2), h - Hb / s / 2)
    M = np.array([[s, 0, W / 2 - s * cx], [0, s, Hb / 2 - s * cy]], np.float32)
    return cv2.warpAffine(src, M, (W, Hb), flags=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT)


def lab(img):
    return cv2.cvtColor(img.astype(np.float32) / 255.0, cv2.COLOR_BGR2LAB)


def stats(imgs):
    L = np.stack([lab(cv2.resize(i, (480, 200), interpolation=cv2.INTER_AREA)) for i in imgs])
    c = np.hypot(L[..., 1], L[..., 2])
    return dict(Lm=L[..., 0].mean(), Ls=L[..., 0].std(), am=L[..., 1].mean(), bm=L[..., 2].mean(), cm=c.mean())


def grade(img, st, tg):
    X = lab(img)
    Lc, A, B = X[..., 0], X[..., 1], X[..., 2]
    # luminance: mean and contrast toward the target
    gain = 1 + K_L * (tg["Ls"] / st["Ls"] - 1)
    Ln = (Lc - st["Lm"]) * gain + st["Lm"] + K_L * (tg["Lm"] - st["Lm"])
    # skin (warm, moderately saturated) keeps most of its own colour
    skin = np.clip((A - 6) / 8, 0, 1) * np.clip((B - 8) / 10, 0, 1)
    w = 1 - 0.6 * cv2.GaussianBlur(skin, (0, 0), 3)
    da, db = K_AB * (tg["am"] - st["am"]), K_AB * (tg["bm"] - st["bm"])
    cs = np.clip(1 + K_C * (tg["cm"] / max(st["cm"], 1e-3) - 1), 0.85, 1.2)
    A = (A * (1 + (cs - 1) * w)) + da * w
    B = (B * (1 + (cs - 1) * w)) + db * w
    out = cv2.cvtColor(np.dstack([np.clip(Ln, 0, 100), A, B]).astype(np.float32), cv2.COLOR_LAB2BGR)
    return out


def main():
    paths = dict(zip([s["key"] for s in SHOTS], sys.argv[1:5]))
    out = sys.argv[5]
    H = int(sys.argv[6]) if len(sys.argv) > 6 else 1440
    W = int(round(H * 16 / 9 / 2)) * 2
    bar = int(round(H * BAR_FRAC / 2)) * 2
    Hb = H - 2 * bar
    plates = []
    for shot in SHOTS:
        fr = frames(paths[shot["key"]], shot["a"], shot["n"])
        plates.append([place(f, k, shot, W, Hb) for k, f in enumerate(fr)])
    sts = [stats(p[::4]) for p in plates]
    tg = {k: float(np.mean([s[k] for s in sts])) for k in sts[0]}
    tg["am"] = tg["am"] * 0.5 + COOL_A * 0.5
    tg["bm"] = tg["bm"] * 0.5 + COOL_B * 0.5
    tg["Lm"] += LIFT
    for shot, s in zip(SHOTS, sts):
        print(shot["key"], " ".join("%s=%.1f" % kv for kv in s.items()))
    print("target", " ".join("%s=%.1f" % kv for kv in tg.items()))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", "%dx%d" % (W, H), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14" if H >= 1080 else "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    t = 0
    for p, s in zip(plates, sts):
        for img in p:
            g = grade(img, s, tg)
            g += rng.normal(0, GRAIN, g.shape[:2]).astype(np.float32)[..., None]
            if t < FADE:
                x = (t + 1) / FADE
                g *= x * x * (3 - 2 * x)
            frame = np.zeros((H, W, 3), np.uint8)
            frame[bar:bar + Hb] = np.clip(g * 255 + 0.5, 0, 255).astype(np.uint8)
            enc.stdin.write(frame.tobytes())
            t += 1
    enc.stdin.close()
    enc.wait()
    print(out, t, "frames")


if __name__ == "__main__":
    main()
