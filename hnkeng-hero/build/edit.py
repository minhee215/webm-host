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

Camera jitter in the generated clips is removed with a sub-pixel stabiliser;
the dashboard shot is rendered from its still so the numbers stay crisp.

Usage:  python3 build/edit.py [--width 1280 --height 720]
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

import dashboard
from stabilize import stabilize, jitter

ROOT = Path(__file__).resolve().parent.parent
CLIPS = ROOT / "clips"
FPS = 24
SRC_W, SRC_H = 1280, 720

# (source, first source frame, frames, extra camera move)
# source "dash" = scene 4 rendered from the still (crisp digits, see dashboard.py);
# every generated clip is stabilised (see stabilize.py) before trimming.
# extra camera move = (start zoom, end zoom, end pan x, end pan y), constant speed,
# added in the direction each clip already travels so the camera reads ~30 %
# faster without speeding up the machines themselves.
SHOTS = [
    ("01",   10, 92, (1.09, 1.00, -0.60, 0.0)),   # AMR — camera pulls back & left, a bit faster
    ("02",   10, 91, (1.00, 1.12,  0.00, 0.0)),   # data center — dolly forward, faster
    ("03",   10, 93, (1.03, 1.03, -0.42, 0.0)),   # MCC row — camera trucks left, faster
    ("dash",  0, 79, None),                        # dashboard — digital push (dashboard.py)
    ("05",    0, 77, (1.00, 1.025, 0.08, 0.04)),  # engineer — push in over the shoulder
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
    ap.add_argument("--grain", type=float, default=0.8)
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
    for clip, src_in, frames, move in SHOTS:
        if clip == "dash":
            seq = dashboard.render(frames, OW, OH)
            note = "rendered from still"
        else:
            raw = list(read_frames(CLIPS / f"{clip}.mp4", 0, 121))
            j0 = jitter(raw)
            plain, _, _ = stabilize(raw, start=src_in, count=frames)
            j1 = jitter(plain)
            seq, _, _ = stabilize(raw, start=src_in, count=frames, move=move)
            note = f"jitter {j0[0]:.2f}px -> {j1[0]:.2f}px RMS"
        print(f"{t / FPS:6.2f}s  shot {clip}  {frames / FPS:.2f}s  ({note})")
        for fr in seq:
            arr = grade(fr).astype(np.float32)
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
