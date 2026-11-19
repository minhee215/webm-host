"""Opening 0:00-0:08 re-edit: four stock clips joined by hard cuts carried by motion (no transitions).

Narration: "AI가 기업의 일하는 방식을 빠르게 바꾸고 있습니다. / 하지만 중요한 것은 AI 도입 자체가 아니라,"
Edit grammar taken from the two references: the camera never stops at a cut - the outgoing shot accelerates
into the cut and the incoming shot leaves it at the same speed in the same direction, then settles; the cut
lands on the fastest frame of a subject action that the next shot continues. Cut points come from tracked
subject paths (LK point tracks) and the measured camera flow of each clip:
  1 factory  workers along the belt, camera trucks (content drifts right). The front worker reaches right,
             then plunges his hand down onto the belt (src 92-96, the hand at x~0.45) -> CUT on the plunge
  2 robot    the gripper is already dropping straight down at the same place in frame (x~0.41, src 88-104,
             started fast and eased: match on action); it settles, then the arm rises -> CUT on the rise
  3 engineer the rise continues in the engineer's hand lifting the pen up to the 3D model (src 24-40); the pen
             touches the model on "하지만"; the camera speeds up rightward -> CUT on the move
  4 lab      leaves the cut at the same rightward speed and settles into the clip's own orbit to the right,
             a colleague walking left to right behind carries the flow out of the sequence
One virtual camera ties them: every shot gets the same forward push and the same rightward drift (small
digital ramps on top of each clip's own move, sized to make up the difference), and around each cut an
exponential pan bump whose velocity is continuous across the cut. Time remapping (speed ramps) shortens the
idle beats and sharpens the actions; frames are rendered with a 180-degree shutter (sub-frame samples of both
the speed ramp and the camera move), so fast frames carry real motion blur.
Look: luminance mean and contrast, white balance and saturation pulled toward the sequence average with a
cool, clean bias, skin protected; a little shared grain. Fade-in from black at the head only.
Output: 21:9 band in 16:9 (letterbox), 23.976 fps frame-for-frame, 192 frames = 00:00:08:00.
Usage: python3 edit_open.py <factory> <robot> <engineer> <lab> <out.mp4> [height=1440]
"""
import subprocess
import sys

import cv2
import numpy as np

FPS_NUM, FPS_DEN = 24000, 1001
BAR_FRAC = 184 / 1440
FADE = 18                    # head fade-in, frames
PUSH = 0.0010                # common forward push (scale per frame)
DRIFT = 0.0018               # common rightward travel (fraction of width per frame)
TAU = 3.5                    # pan bump time constant around a cut (frames)
SHUTTER, SUB = 0.5, 5        # 180-degree shutter, sub-frame samples
# a: first source frame; n: timeline frames; speed: [(k, speed)] keys (ramped up into a cut and out of it);
# push/drift: the clip's own measured move (subtracted from the common one); v: band centre in the source;
# the overscan zoom is derived from the travel each shot needs
SHOTS = [
    dict(key="factory", a=34, n=56, speed=[(0, 1.0), (46, 1.0), (56, 2.2)],
         push=-0.0010, drift=0.0009, v=0.52),
    dict(key="robot", a=85, n=37, speed=[(0, 2.2), (6, 1.0), (12, 1.4), (26, 1.4), (31, 1.8), (37, 1.8)],
         push=0.0017, drift=0.0002, v=0.46),
    dict(key="engineer", a=26, n=50, speed=[(0, 2.0), (6, 1.0), (40, 1.0), (50, 2.0)],
         push=0.0005, drift=0.0003, v=0.50),
    dict(key="lab", a=139, n=49, speed=[(0, 1.6), (6, 1.0), (49, 1.0)],
         push=-0.0006, drift=0.0008, v=0.40),
]
BUMPS = [0.040, 0.040, 0.045]   # pan bump size at cut 1, 2, 3 (fraction of width; peak speed = size / TAU)
# look: targets are the shot average, pulled toward a cool, clean corporate neutral
COOL_B, COOL_A = -4.0, -0.5
LIFT = 2.0
K_L, K_AB, K_C = 0.75, 0.70, 0.55
GRAIN = 1.2 / 255


def src_time(shot, k):
    """Source frame position at timeline frame k (fractional), integrating the speed keys."""
    ks = np.array([p[0] for p in shot["speed"]], float)
    sp = np.array([p[1] for p in shot["speed"]], float)
    if k <= 0:
        return float(shot["a"])
    grid = np.linspace(0, k, int(k * 4) + 2)
    v = np.interp(grid, ks, sp)
    return shot["a"] + float(((v[1:] + v[:-1]) / 2 * np.diff(grid)).sum())


def travel(i, shot, k):
    n = shot["n"]
    x = (DRIFT - shot["drift"]) * (k - n / 2)
    if i > 0:
        x -= BUMPS[i - 1] * np.exp(-k / TAU)               # leaves the cut fast, eases out
    if i < len(SHOTS) - 1:
        x += BUMPS[i] * np.exp((k - n) / TAU)              # accelerates into the cut
    return x


def overscan(i, shot):
    reach = max(abs(travel(i, shot, k)) for k in np.linspace(0, shot["n"], 200))
    return 1.01 / (1 - 2 * reach)


def cam(i, shot, k):
    """Virtual camera for shot i at (fractional) frame k: (scale, x offset as fraction of width)."""
    return overscan(i, shot) * (1 + (PUSH - shot["push"]) * k), travel(i, shot, k)


class Clip:
    def __init__(self, path, width):
        self.cap = cv2.VideoCapture(path)
        self.width = width
        self.cache = {}
        self.pos = -1

    def frame(self, j):
        j = int(max(0, j))
        if j not in self.cache:
            if j != self.pos + 1:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, j)
            ok, f = self.cap.read()
            if not ok:
                return self.frame(j - 1)
            self.pos = j
            if f.shape[1] > self.width:
                h = int(round(f.shape[0] * self.width / f.shape[1]))
                f = cv2.resize(f, (self.width, h), interpolation=cv2.INTER_AREA)
            self.cache[j] = f.astype(np.float32)
            for old in [q for q in self.cache if q < j - 6]:
                del self.cache[old]
        return self.cache[j]

    def at(self, t):
        j = int(np.floor(t))
        w = t - j
        a = self.frame(j)
        return a if w < 1e-3 else a * (1 - w) + self.frame(j + 1) * w


def place(src, s, x, shot, W, Hb):
    h, w = src.shape[:2]
    s = max(W / w, Hb / h) * s
    cx = w / 2 - x * W / s
    cy = min(max(shot["v"] * h, Hb / s / 2), h - Hb / s / 2)
    cx = min(max(cx, W / s / 2), w - W / s / 2)
    M = np.array([[s, 0, W / 2 - s * cx], [0, s, Hb / 2 - s * cy]], np.float32)
    return cv2.warpAffine(src, M, (W, Hb), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def render_frame(clip, i, shot, k, W, Hb):
    acc = None
    for q in range(SUB):
        kk = k + (q / (SUB - 1) - 0.5) * SHUTTER
        kk = min(max(kk, 0), shot["n"] - 1e-3)
        s, x = cam(i, shot, kk)
        img = place(clip.at(src_time(shot, kk)), s, x, shot, W, Hb)
        acc = img if acc is None else acc + img
    return acc / SUB


def lab(img):
    return cv2.cvtColor(np.clip(img / 255.0, 0, 1).astype(np.float32), cv2.COLOR_BGR2LAB)


def stats(imgs):
    L = np.stack([lab(cv2.resize(i, (480, 200), interpolation=cv2.INTER_AREA)) for i in imgs])
    c = np.hypot(L[..., 1], L[..., 2])
    return dict(Lm=L[..., 0].mean(), Ls=L[..., 0].std(), am=L[..., 1].mean(), bm=L[..., 2].mean(), cm=c.mean())


def grade(img, st, tg):
    X = lab(img)
    Lc, A, B = X[..., 0], X[..., 1], X[..., 2]
    gain = 1 + K_L * (tg["Ls"] / st["Ls"] - 1)
    Ln = (Lc - st["Lm"]) * gain + st["Lm"] + K_L * (tg["Lm"] - st["Lm"])
    skin = np.clip((A - 6) / 8, 0, 1) * np.clip((B - 8) / 10, 0, 1)
    w = 1 - 0.6 * cv2.GaussianBlur(skin, (0, 0), 3)
    da, db = K_AB * (tg["am"] - st["am"]), K_AB * (tg["bm"] - st["bm"])
    cs = np.clip(1 + K_C * (tg["cm"] / max(st["cm"], 1e-3) - 1), 0.85, 1.2)
    A = (A * (1 + (cs - 1) * w)) + da * w
    B = (B * (1 + (cs - 1) * w)) + db * w
    return cv2.cvtColor(np.dstack([np.clip(Ln, 0, 100), A, B]).astype(np.float32), cv2.COLOR_LAB2BGR)


def main():
    paths = dict(zip([s["key"] for s in SHOTS], sys.argv[1:5]))
    out = sys.argv[5]
    H = int(sys.argv[6]) if len(sys.argv) > 6 else 1440
    W = int(round(H * 16 / 9 / 2)) * 2
    bar = int(round(H * BAR_FRAC / 2)) * 2
    Hb = H - 2 * bar
    work = int(W * 1.35)
    for s in SHOTS:
        i = SHOTS.index(s)
        print("%-9s src %.1f -> %.1f  (%d frames) overscan %.3f" % (s["key"], s["a"], src_time(s, s["n"] - 1),
                                                                   s["n"], overscan(i, s)))
    # look statistics from plain (sharp) samples of each shot
    sts = []
    for i, s in enumerate(SHOTS):
        c = Clip(paths[s["key"]], work)
        smp = []
        for k in range(0, s["n"], 6):
            sc, x = cam(i, s, k)
            smp.append(place(c.at(src_time(s, k)), sc, x, s, W, Hb))
        sts.append(stats(smp))
    tg = {k: float(np.mean([s[k] for s in sts])) for k in sts[0]}
    tg["am"] = tg["am"] * 0.5 + COOL_A * 0.5
    tg["bm"] = tg["bm"] * 0.5 + COOL_B * 0.5
    tg["Lm"] += LIFT
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", "%dx%d" % (W, H), "-r", "%d/%d" % (FPS_NUM, FPS_DEN), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14" if H >= 1080 else "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    t = 0
    for i, (s, st) in enumerate(zip(SHOTS, sts)):
        c = Clip(paths[s["key"]], work)
        for k in range(s["n"]):
            g = grade(render_frame(c, i, s, k, W, Hb), st, tg)
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
