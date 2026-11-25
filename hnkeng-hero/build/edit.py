#!/usr/bin/env python3
"""
HNKENG hero background video: match-cut edit.

Input : five 5-second image-to-video clips (clips/s1..s5.mp4) generated with
        Kling 3.0 (Higgsfield) from the five supplied photos.
Output: an 18 s, 24 fps, hard-cut edit. At every cut a virtual-camera reframe
        (sub-pixel crop/zoom, eased) lines up a shared shape or colour across
        the cut so the eye carries straight through it (graphic match cut).

  cut 1  plant -> PLC       : vertical steel column  -> vertical cabinet frame,
                              forward push continues into the next shot
  cut 2  PLC -> line        : green PLC status LEDs  -> green tower light
                              (same screen position, push-in carries through)
  cut 3  line -> control    : passing foreground post -> window mullion
                              (same x position, rightward travel continues)
  cut 4  control -> factory : tank symbol on the P&ID screen -> real tank,
                              push into the screen, pull back out in the plant
  loop   factory -> plant   : open left wall / sky, vessels on the right

Usage:
  python3 build/edit.py                              # 854x480 sample
  python3 build/edit.py --width 1920 --height 1080 --out dist-1080
"""
import argparse
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "clips"
FPS = 24
SRC_W, SRC_H = 1280, 720

# Each segment: clip, first source frame, length in frames, and reframe keys.
# A key is (t_seconds_in_segment, zoom, cx, cy, ease_into_this_key).
# cx/cy are the crop centre in normalised source coordinates.
SEGMENTS = [
    dict(name="01 plant", clip="s1.mp4", src_in=0, frames=82, keys=[
        (0.0, 1.00, 0.500, 0.50, None),
        (2.3, 1.00, 0.500, 0.50, "linear"),
        (82 / FPS, 1.15, 0.580, 0.50, "in"),        # column x0.58 -> ~0.52
    ]),
    dict(name="02 PLC", clip="s2.mp4", src_in=19, frames=86, keys=[
        (0.0, 1.00, 0.500, 0.50, None),
        (2.3, 1.04, 0.510, 0.51, "linear"),
        (86 / FPS, 1.50, 0.577, 0.557, "in"),       # LEDs (0.625,0.29) -> (0.57,0.10)
    ]),
    dict(name="03 line", clip="s3.mp4", src_in=17, frames=82, keys=[
        (0.0, 1.00, 0.500, 0.50, None),
    ]),
    dict(name="04 control", clip="s4.mp4", src_in=14, frames=91, keys=[
        (0.0, 1.30, 0.385, 0.50, None),             # mullion x0.51 -> ~0.66
        (2.5, 1.38, 0.360, 0.50, "linear"),
        (91 / FPS, 2.00, 0.250, 0.51, "in"),        # P&ID tank (0.22,0.51) -> (0.44,0.50)
    ]),
    dict(name="05 factory", clip="s5.mp4", src_in=29, frames=91, keys=[
        (0.0, 2.00, 0.531, 0.41, None),             # real tank (0.50,0.41) -> (0.44,0.50)
        (1.7, 1.00, 0.500, 0.50, "out"),
    ]),
]

EASE = {
    "linear": lambda u: u,
    "in": lambda u: u * u * u,
    "out": lambda u: 1 - (1 - u) ** 3,
    "inout": lambda u: u * u * (3 - 2 * u),
}


def reframe_at(keys, t):
    if t <= keys[0][0] or len(keys) == 1:
        return keys[0][1:4]
    for (t0, z0, x0, y0, _), (t1, z1, x1, y1, ease) in zip(keys, keys[1:]):
        if t <= t1:
            u = EASE[ease]((t - t0) / (t1 - t0))
            z = math.exp(math.log(z0) + (math.log(z1) - math.log(z0)) * u)
            return z, x0 + (x1 - x0) * u, y0 + (y1 - y0) * u
    return keys[-1][1:4]


def grade(img: np.ndarray) -> np.ndarray:
    """Calm blue-grey / teal grade shared by every shot."""
    x = img.astype(np.float32) / 255.0
    luma = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x = luma[..., None] + (x - luma[..., None]) * 0.90
    shadow = (1.0 - luma)[..., None] ** 2
    x = x + shadow * np.array([-0.016, 0.004, 0.014], np.float32)
    x = x * np.array([0.985, 1.0, 1.010], np.float32)
    x = np.clip(x, 0, 1)
    x = x + 0.05 * (x - 0.5) * (1 - np.abs(2 * x - 1))
    return np.clip(x * 255.0 + 0.5, 0, 255).astype(np.uint8)


def read_frames(path, start, count):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path),
                          "-vf", f"select='gte(n\\,{start})',setpts=N/FRAME_RATE/TB",
                          "-frames:v", str(count), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = SRC_W * SRC_H * 3
    for _ in range(count):
        buf = p.stdout.read(size)
        if len(buf) < size:
            raise SystemExit(f"{path}: ran out of frames")
        yield np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
    p.stdout.close()
    p.wait()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=854)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--grain", type=float, default=1.4)
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    OW, OH = args.width, args.height
    SS = 2 if OW <= 1000 else 1
    RW, RH = OW * SS, OH * SS
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_master_lossless.mkv"

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
        "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", str(tmp)], stdin=subprocess.PIPE)
    rng = np.random.default_rng(1234)
    t_global = 0.0
    for seg in SEGMENTS:
        print(f"{t_global:6.2f}s  {seg['name']}  ({seg['frames'] / FPS:.2f}s)")
        for i, frame in enumerate(read_frames(CLIPS / seg["clip"], seg["src_in"], seg["frames"])):
            z, cx, cy = reframe_at(seg["keys"], i / FPS)
            cw, ch = SRC_W / z, SRC_H / z
            x0 = min(max(cx * SRC_W - cw / 2, 0), SRC_W - cw)
            y0 = min(max(cy * SRC_H - ch / 2, 0), SRC_H - ch)
            img = Image.fromarray(grade(frame)).transform(
                (RW, RH), Image.Transform.AFFINE, (cw / RW, 0, x0, 0, ch / RH, y0),
                resample=Image.Resampling.BICUBIC)
            if SS > 1:
                img = img.resize((OW, OH), Image.Resampling.LANCZOS)
            arr = np.asarray(img).astype(np.float32)
            if args.grain > 0:
                arr += rng.normal(0, args.grain, (OH, OW, 1)).astype(np.float32)
            ff.stdin.write(np.clip(arr + 0.5, 0, 255).astype(np.uint8).tobytes())
        t_global += seg["frames"] / FPS
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg (lossless) failed")
    print(f"total {t_global:.3f}s")

    color = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    vf = ["-vf", "scale=out_color_matrix=bt709:out_range=tv:flags=lanczos,format=yuv420p"]
    gop = ["-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "40"]

    def run(cmd):
        subprocess.run(cmd, check=True)

    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, "-c:v", "libx264",
         "-preset", "slow", "-crf", "18", "-profile:v", "high", "-level", "4.0", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video.mp4")])
    cap = "1.4M" if OW <= 1000 else ("2.5M" if OW <= 1300 else "4M")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, "-c:v", "libx264",
         "-preset", "veryslow", "-crf", "25", "-maxrate", cap, "-bufsize", cap,
         "-profile:v", "high", "-level", "4.0", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video-web.mp4")])
    passlog = str(out_dir / "_vp9pass")
    vp9 = ["-c:v", "libvpx-vp9", "-crf", "38", "-b:v", "0", "-row-mt", "1", "-tile-columns", "1",
           "-g", str(FPS * 2), *color, "-an"]
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, *vp9, "-pass", "1",
         "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "4", "-f", "webm", "/dev/null"])
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *vf, *vp9, "-pass", "2",
         "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "1",
         str(out_dir / "hero-video-web.webm")])
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
