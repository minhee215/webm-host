#!/usr/bin/env python3
"""AXCORE film — build pipeline.

  python build_video.py --prepare              # decode/grade plates + tracking
  python build_video.py --still 3.0 47.5        # review stills -> renders/stills/
  python build_video.py --scenes s03 s04        # re-render only these scenes
  python build_video.py                         # render all missing scenes, audio, mux
  python build_video.py --force                 # re-render everything

Each scene is rendered to renders/cache/segments/<scene>.mp4 (near-lossless),
so a single scene can be revised and the film re-assembled in seconds.
Final encode / audio mix / mux are done by FFmpeg.
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.utils.config import FPS, OUT_W, OUT_H, SCENES, CACHE, RENDERS, OUTPUT_NAME  # noqa: E402

SEG_DIR = CACHE / "segments"
AUDIO_DIR = RENDERS / "audio"


def _render_chunk(args):
    scene, f0, f1, part_path = args
    from src.render import render_frame
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
           "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "10", "-pix_fmt", "yuv420p",
           str(part_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(f0, f1):
        proc.stdin.write(render_frame(f).tobytes())
    proc.stdin.close()
    proc.wait()
    return part_path


def render_scene(name, workers):
    a, b = next((s, e) for n, s, e in SCENES if n == name)
    f0, f1 = round(a * FPS), round(b * FPS)
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    n = max(1, min(workers, (f1 - f0) // 30))
    step = (f1 - f0 + n - 1) // n
    jobs = [(name, f0 + i * step, min(f1, f0 + (i + 1) * step), SEG_DIR / f"{name}_p{i}.mp4")
            for i in range(n)]
    t0 = time.time()
    with Pool(n) as pool:
        parts = pool.map(_render_chunk, jobs)
    lst = SEG_DIR / f"{name}.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    out = SEG_DIR / f"{name}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out)], check=True)
    for p in parts:
        p.unlink()
    lst.unlink()
    print(f"  {name}: {f1 - f0} frames in {time.time() - t0:.1f}s")
    return out


def stills(times):
    from src.render import render_frame
    d = RENDERS / "stills"
    d.mkdir(parents=True, exist_ok=True)
    for t in times:
        img = render_frame(int(round(t * FPS)), grain=False)
        p = d / f"still_{t:06.2f}.png"
        cv2.imwrite(str(p), img)
        print(p)


def assemble():
    from src.audio.mix import build_audio
    lst = SEG_DIR / "all.txt"
    lst.write_text("".join(f"file '{n}.mp4'\n" for n, _, _ in SCENES))
    video = SEG_DIR / "video_only.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(video)], check=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    stems = build_audio(AUDIO_DIR)
    out = RENDERS / OUTPUT_NAME
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(stems["master"]),
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-profile:v", "high",
                    "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", "-shortest", str(out)], check=True)
    print("wrote", out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--still", nargs="*", type=float)
    ap.add_argument("--scenes", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-assemble", action="store_true")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    args = ap.parse_args()

    if args.prepare:
        from src.compositing import plates, tracks
        for k in plates.PLATES:
            plates.prepare(k)
        tracks.prepare_all()
        return
    if args.still is not None:
        stills(args.still)
        return
    todo = args.scenes or [n for n, _, _ in SCENES
                           if args.force or not (SEG_DIR / f"{n}.mp4").exists()]
    for name in todo:
        render_scene(name, args.workers)
    if not args.no_assemble and all((SEG_DIR / f"{n}.mp4").exists() for n, _, _ in SCENES):
        assemble()


if __name__ == "__main__":
    main()
