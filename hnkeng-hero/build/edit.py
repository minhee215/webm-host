#!/usr/bin/env python3
"""
HNKENG main hero background film — edit & encode (v4, moodboard).

Built from the HNK ENG moodboard (AI · ROBOTICS · AUTOMATION):
  1 AMR            — autonomous mobile robot in a bright automated plant
  2 Data center    — server aisle, infrastructure & data
  3 MCC / PLC      — row of motor control / PLC panels
  4 Monitoring     — plant dashboard with a 3D digital twin
  5 Human control  — engineer seen from behind, tablet in hand, robots ahead
People never show their faces. Cool blue-white industrial light, hard cuts,
~3.6 s per scene, 18 s loop.

Input : clips/NN.mp4 (Kling 3.0, 720p 24 fps) animated from stills/NN.jpg
Output: dist/ — hero-video.mp4, hero-video-web.mp4/.webm, hero-video-mobile.mp4,
        hero-poster.jpg/.webp  (default 854x480 sample)

Usage:  python3 build/edit.py [--width 1280 --height 720]
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "clips"
FPS = 24
SRC_W, SRC_H = 1280, 720

# (clip, first source frame, frames, zoom start, zoom end, x-bias)
# x-bias: 0 = crop anchored left (pushes the subject right, away from the
# hero text), 0.5 = centred, 1 = anchored right.
SHOTS = [
    ("01", 10, 90, 1.00, 1.03, 0.6),   # AMR in a bright automated plant
    ("02", 10, 88, 1.00, 1.03, 0.5),   # data center aisle
    ("03", 10, 87, 1.00, 1.03, 0.6),   # MCC / PLC panel row
    ("04",  0, 79, 1.00, 1.04, 0.6),   # monitoring dashboard, digital twin (cut before model drift)
    ("05", 15, 88, 1.00, 1.03, 0.6),   # engineer from behind, tablet, robots ahead
]


def grade(img: np.ndarray) -> np.ndarray:
    """Moodboard grade: crisp cool blue-white light, navy shadows,
    clean contrast, colour kept natural."""
    x = img.astype(np.float32) / 255.0
    luma = x @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    x = luma[..., None] + (x - luma[..., None]) * 0.96
    sh = (1.0 - luma)[..., None] ** 2.5
    x = x + sh * np.array([-0.014, 0.000, 0.024], np.float32)       # navy shadows
    x = x * np.array([0.980, 0.995, 1.020], np.float32)             # cool whites
    x = np.clip(x, 0, 1)
    x = x + 0.06 * (x - 0.5) * (1 - np.abs(2 * x - 1))             # crisp contrast
    return np.clip(x * 255.0 + 0.5, 0, 255).astype(np.uint8)


def read_frames(path, start, count):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path),
                          "-vf", f"select='gte(n\\,{start})',setpts=N/FRAME_RATE/TB,"
                                 f"scale={SRC_W}:{SRC_H}:flags=lanczos",
                          "-frames:v", str(count), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         stdout=subprocess.PIPE)
    size = SRC_W * SRC_H * 3
    n = 0
    while n < count:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(SRC_H, SRC_W, 3)
        n += 1
    p.stdout.close()
    p.wait()
    if n < count:
        raise SystemExit(f"{path}: only {n} of {count} frames from frame {start}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=854)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--grain", type=float, default=1.2)
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    FW, FH = args.width, args.height     # final size
    OW, OH = SRC_W, SRC_H                # internal master size
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "_master_lossless.mkv"

    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
        "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", str(tmp)], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    t = 0
    for clip, src_in, frames, z0, z1, xb in SHOTS:
        print(f"{t / FPS:6.2f}s  shot {clip}  {frames / FPS:.2f}s")
        for i, fr in enumerate(read_frames(CLIPS / f"{clip}.mp4", src_in, frames)):
            u = i / max(frames - 1, 1)
            u = u * u * (3 - 2 * u) * 0.35 + u * 0.65                 # mostly linear, soft ends
            z = z0 + (z1 - z0) * u
            cw, ch = SRC_W / z, SRC_H / z
            x0 = (SRC_W - cw) * xb
            y0 = (SRC_H - ch) * 0.5
            img = Image.fromarray(grade(fr)).transform(
                (OW, OH), Image.Transform.AFFINE, (cw / OW, 0, x0, 0, ch / OH, y0),
                resample=Image.Resampling.BICUBIC)
            arr = np.asarray(img).astype(np.float32)
            if args.grain > 0:
                arr += rng.normal(0, args.grain, (OH, OW, 1)).astype(np.float32)
            ff.stdin.write(np.clip(arr + 0.5, 0, 255).astype(np.uint8).tobytes())
        t += frames
    ff.stdin.close()
    if ff.wait() != 0:
        raise SystemExit("ffmpeg (lossless) failed")
    print(f"total {t / FPS:.3f}s ({t} frames)")

    color = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    vf = f"scale={FW}:{FH}:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p"
    gop = ["-g", str(FPS * 2), "-keyint_min", str(FPS // 2)]

    def run(cmd):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp), *cmd], check=True)

    run(["-vf", vf, "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-profile:v", "high",
         "-level", "4.0", *gop, *color, "-movflags", "+faststart", "-an", str(out_dir / "hero-video.mp4")])
    run(["-vf", vf, "-c:v", "libx264", "-preset", "veryslow", "-crf", "24", "-maxrate", "1.6M",
         "-bufsize", "2M", "-profile:v", "high", "-level", "4.0", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video-web.mp4")])
    run(["-vf", "scale=640:360:flags=lanczos," + vf, "-c:v", "libx264", "-preset", "veryslow",
         "-crf", "25", "-maxrate", "1M", "-bufsize", "1.2M", "-profile:v", "main", *gop, *color,
         "-movflags", "+faststart", "-an", str(out_dir / "hero-video-mobile.mp4")])
    passlog = str(out_dir / "_vp9pass")
    vp9 = ["-vf", vf, "-c:v", "libvpx-vp9", "-crf", "35", "-b:v", "0", "-row-mt", "1",
           "-tile-columns", "2", "-g", str(FPS * 2), *color, "-an"]
    run([*vp9, "-pass", "1", "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "4",
         "-f", "webm", "/dev/null"])
    run([*vp9, "-pass", "2", "-passlogfile", passlog, "-deadline", "good", "-cpu-used", "1",
         str(out_dir / "hero-video-web.webm")])
    run(["-frames:v", "1", "-vf", f"scale={FW}:{FH}:flags=lanczos", "-q:v", "3", str(out_dir / "hero-poster.jpg")])
    run(["-frames:v", "1", "-vf", f"scale={FW}:{FH}:flags=lanczos", "-c:v", "libwebp", "-quality", "82", str(out_dir / "hero-poster.webp")])
    for p in out_dir.glob("_vp9pass*"):
        p.unlink()
    tmp.unlink()
    print("done ->", out_dir)


if __name__ == "__main__":
    main()
