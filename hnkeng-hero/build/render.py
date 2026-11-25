#!/usr/bin/env python3
"""
HNKENG hero background video renderer.

Image-based cinematic camera motion (sub-pixel pan / zoom), short smooth
cross-dissolves, a seamless loop back into scene 1, subtle LED status-light
blinking on the PLC panel (scene 2) and a light film grain. No generative
models are used: nothing in the source pictures (robots, people, screens) is
deformed or re-animated; only the virtual camera moves.

Frames are rendered with Pillow/NumPy and piped to FFmpeg, which writes a
lossless intermediate and then the delivery encodes.

Usage:
  python3 build/render.py                 # 854x480 sample (default)
  python3 build/render.py --width 1920 --height 1080 --out dist-1080
"""
import argparse
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

DURATION = 18.0          # seconds
XFADE = 0.8              # cross-dissolve length (s)

# Scene table. Each scene is visible from start to end; neighbours overlap by
# XFADE centred on the cut. Scene 1 additionally fades in from the end of the
# video (t = 18 - XFADE .. 18) so the loop point is invisible.
#   z0/z1  : zoom at start/end of the scene window (1.0 = full frame)
#   k*     : framing bias in [-1, 1]; 0 = centred, +1 = hard right / bottom
SCENES = [
    dict(name="01 plant",   file="scene01-plant.webp",   start=0.0,  end=3.0,
         z0=1.12, z1=1.12, kx0=-1.0, kx1=1.0,  ky0=0.0,  ky1=0.0),
    dict(name="02 PLC",     file="scene02-plc.webp",     start=3.0,  end=7.0,
         z0=1.04, z1=1.15, kx0=0.45, kx1=0.70, ky0=-0.15, ky1=-0.30, leds=True),
    dict(name="03 line",    file="scene03-line.webp",    start=7.0,  end=11.0,
         z0=1.12, z1=1.12, kx0=0.95, kx1=-0.95, ky0=0.10, ky1=0.10),
    dict(name="04 control", file="scene04-control.webp", start=11.0, end=15.0,
         z0=1.06, z1=1.11, kx0=-0.30, kx1=0.45, ky0=0.15, ky1=0.0),
    dict(name="05 factory", file="scene05-factory.webp", start=15.0, end=18.0,
         z0=1.16, z1=1.04, kx0=0.40, kx1=0.0,  ky0=0.0,  ky1=0.0),
]


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


# --------------------------------------------------------------------------
# Colour grade: calm blue-grey / teal, slightly reduced saturation, gentle
# contrast. Applied identically to every scene so they read as one shoot.
# --------------------------------------------------------------------------
def grade(img: np.ndarray) -> np.ndarray:
    x = img.astype(np.float32) / 255.0
    luma = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # 12 % desaturation
    x = luma[..., None] + (x - luma[..., None]) * 0.88
    # cool split-tone: teal in shadows, neutral-cool highlights
    shadow = (1.0 - luma)[..., None] ** 2
    x = x + shadow * np.array([-0.018, 0.004, 0.016], np.float32)
    x = x * np.array([0.985, 1.0, 1.012], np.float32)
    # soft S-curve
    x = np.clip(x, 0, 1)
    x = x + 0.06 * (x - 0.5) * (1 - np.abs(2 * x - 1))
    return np.clip(x * 255.0 + 0.5, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
# LED status lights for the PLC panel. Detect the small green/yellow lit
# indicators on the modules, build a per-LED soft mask and an "off" plate
# (local background with the bright spot removed). Each frame some LEDs
# blink like RUN / COMM indicators; most stay steady.
# --------------------------------------------------------------------------
class LedBlinker:
    def __init__(self, img: np.ndarray, seed=7):
        f = img.astype(np.float32)
        r, g, b = f[..., 0], f[..., 1], f[..., 2]
        m = (g > 150) & (g > b * 1.35) & (g > r * 0.95)
        h, w = m.shape
        roi = np.zeros_like(m)
        roi[int(h * 0.18):int(h * 0.42), int(w * 0.5):] = True
        m &= roi
        lab, n = ndi.label(ndi.binary_dilation(m, iterations=2))
        # "off" plate: grey opening removes small bright spots
        off = np.stack([ndi.grey_opening(f[..., c], size=(9, 9)) for c in range(3)], -1)
        off = off * 0.92
        self.base = f
        self.off = off
        rng = np.random.default_rng(seed)
        self.leds = []
        for i in range(1, n + 1):
            core = (lab == i) & m
            if core.sum() < 3:
                continue
            soft = ndi.gaussian_filter(ndi.binary_dilation(core, iterations=2).astype(np.float32), 1.2)
            soft = np.clip(soft * 1.6, 0, 1)
            ys, xs = np.nonzero(soft > 0.01)
            box = (ys.min(), ys.max() + 1, xs.min(), xs.max() + 1)
            kind = rng.choice(["steady", "steady", "run", "comm"], p=[0.35, 0.25, 0.2, 0.2])
            self.leds.append(dict(box=box, mask=soft[box[0]:box[1], box[2]:box[3]],
                                  kind=kind, phase=rng.uniform(0, 1),
                                  rate=rng.uniform(0.8, 1.3), seed=int(rng.integers(1e9))))

    @staticmethod
    def level(led, t):
        k = led["kind"]
        if k == "steady":
            return 1.0
        if k == "run":                       # ~1 Hz RUN heartbeat, 50 % duty
            p = (t * led["rate"] + led["phase"]) % 1.0
            return 1.0 if p < 0.5 else 0.12
        # comm: irregular short flickers, re-sampled every ~100 ms
        slot = int(t * 10 * led["rate"] + led["phase"] * 10)
        v = np.random.default_rng(led["seed"] + slot).random()
        return 0.15 if v < 0.35 else 1.0

    def frame(self, t) -> np.ndarray:
        out = self.base.copy()
        for led in self.leds:
            lv = self.level(led, t)
            if lv >= 0.999:
                continue
            y0, y1, x0, x1 = led["box"]
            a = led["mask"][..., None] * (1 - lv)
            out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - a) + self.off[y0:y1, x0:x1] * a
        return np.clip(out + 0.5, 0, 255).astype(np.uint8)


# --------------------------------------------------------------------------
def camera_crop(sc, u, W, H):
    """Return (x0, y0, cw, ch) of the virtual-camera crop in source pixels."""
    z = math.exp(math.log(sc["z0"]) + (math.log(sc["z1"]) - math.log(sc["z0"])) * u)
    kx = sc["kx0"] + (sc["kx1"] - sc["kx0"]) * u
    ky = sc["ky0"] + (sc["ky1"] - sc["ky0"]) * u
    cw, ch = W / z, H / z
    cx = W / 2 + kx * (W - cw) / 2
    cy = H / 2 + ky * (H - ch) / 2
    return cx - cw / 2, cy - ch / 2, cw, ch


def render_scene(sc, t, rw, rh):
    img = sc["led"].frame(t - sc["start"]) if sc.get("led") else sc["img"]
    H, W = img.shape[:2]
    t0 = sc["start"] - (XFADE if sc is SCENES[0] else XFADE / 2)
    t1 = sc["end"] + (0 if sc is SCENES[-1] else XFADE / 2)
    u = (t - t0) / (t1 - t0)
    x0, y0, cw, ch = camera_crop(sc, u, W, H)
    sx, sy = cw / rw, ch / rh
    pil = Image.fromarray(img)
    out = pil.transform((rw, rh), Image.Transform.AFFINE,
                        (sx, 0, x0, 0, sy, y0), resample=Image.Resampling.BICUBIC)
    return np.asarray(out).astype(np.float32)


def weights(t):
    """List of (scene, weight, scene_time) contributing to time t."""
    res = []
    h = XFADE / 2
    for i, sc in enumerate(SCENES):
        a, b = sc["start"], sc["end"]
        if i == 0:
            if t < b + h:
                w = 1.0 - smoothstep((t - (b - h)) / XFADE)
                res.append((sc, w, t))
            if t >= DURATION - XFADE:          # loop-in from the end
                w = smoothstep((t - (DURATION - XFADE)) / XFADE)
                res.append((sc, w, t - DURATION))
            continue
        if t < a - h or (i < len(SCENES) - 1 and t > b + h):
            continue
        w_in = smoothstep((t - (a - h)) / XFADE)
        if i == len(SCENES) - 1:
            w_out = 1.0 - smoothstep((t - (DURATION - XFADE)) / XFADE)
        else:
            w_out = 1.0 - smoothstep((t - (b - h)) / XFADE)
        res.append((sc, min(w_in, w_out), t))
    return [r for r in res if r[1] > 1e-4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=854)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--grain", type=float, default=1.4, help="grain sigma in 8-bit levels (0 = off)")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    OW, OH, FPS = args.width, args.height, args.fps
    SS = 2 if OW <= 1000 else 1               # supersample small outputs
    RW, RH = OW * SS, OH * SS
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_master_lossless.mkv"

    for sc in SCENES:
        sc["img"] = grade(np.asarray(Image.open(SRC / sc["file"]).convert("RGB")))
        if sc.get("leds"):
            sc["led"] = LedBlinker(sc["img"])
            print(f"scene {sc['name']}: {len(sc['led'].leds)} LEDs detected")

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
        "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", str(tmp)], stdin=subprocess.PIPE)

    rng = np.random.default_rng(1234)
    n = int(round(DURATION * FPS))
    for fi in range(n):
        t = fi / FPS
        acc = np.zeros((RH, RW, 3), np.float32)
        wsum = 0.0
        for sc, w, st in weights(t):
            acc += render_scene(sc, st, RW, RH) * w
            wsum += w
        acc /= wsum
        if SS > 1:
            acc = np.asarray(Image.fromarray(np.clip(acc + 0.5, 0, 255).astype(np.uint8))
                             .resize((OW, OH), Image.Resampling.LANCZOS)).astype(np.float32)
        if args.grain > 0:
            acc += rng.normal(0, args.grain, (OH, OW, 1)).astype(np.float32)
        ff.stdin.write(np.clip(acc + 0.5, 0, 255).astype(np.uint8).tobytes())
        if fi % 60 == 0:
            print(f"frame {fi}/{n}")
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg (lossless) failed")

    color = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    vf = ["-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=lanczos,format=yuv420p"]
    gop = ["-g", str(FPS * 2), "-keyint_min", str(FPS)]

    def run(cmd):
        print(" ".join(cmd[:12]), "...")
        subprocess.run(cmd, check=True)

    # 1) master H.264 (high quality)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, "-c:v", "libx264",
         "-preset", "slow", "-crf", "18", "-profile:v", "high", "-level", "4.0", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video.mp4")])
    # 2) web-optimised H.264 (smaller, capped bitrate, universal playback)
    cap = "1.2M" if OW <= 1000 else ("2.2M" if OW <= 1300 else "3.5M")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, "-c:v", "libx264",
         "-preset", "veryslow", "-crf", "25", "-maxrate", cap, "-bufsize", cap,
         "-profile:v", "high", "-level", "4.0", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video-web.mp4")])
    # 3) web-optimised VP9 WebM (2-pass constrained quality)
    passlog = str(out_dir / "_vp9pass")
    vp9 = ["-c:v", "libvpx-vp9", "-crf", "38", "-b:v", "0", "-row-mt", "1", "-tile-columns", "1",
           *gop, *color, "-an"]
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, *vp9, "-pass", "1",
         "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "4", "-f", "webm", "/dev/null"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, *vp9, "-pass", "2",
         "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "1",
         str(out_dir / "hero-video-web.webm")])
    # 4) poster = first frame
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-frames:v", "1",
         "-q:v", "3", str(out_dir / "hero-poster.jpg")])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), "-frames:v", "1",
         "-c:v", "libwebp", "-quality", "80", str(out_dir / "hero-poster.webp")])

    for p in out_dir.glob("_vp9pass*"):
        p.unlink()
    tmp.unlink()
    print("done ->", out_dir)


if __name__ == "__main__":
    main()
