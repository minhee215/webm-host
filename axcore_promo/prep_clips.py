"""Download the Kling clips listed in assets/clips.json and normalize them.

For each clip: 1920x1080 (or its 'res', e.g. native 4K) / 24 fps CFR H.264 (frame-accurate seeking), a 480x270
proxy frame stack (.npy) for tiles and mosaics, and <name>.json with the duration.
Usage: python3 prep_clips.py [clip_dir]
"""
import json
import os
import subprocess
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "clips")
PW, PH = 480, 270


def prep(item):
    name, info = item
    dst = os.path.join(OUT, name + ".mp4")
    meta = os.path.join(OUT, name + ".json")
    if os.path.exists(dst) and os.path.exists(meta):
        return name, "cached"
    raw = os.path.join(OUT, name + "_src.mp4")
    urllib.request.urlretrieve(info["file"] if info["file"].startswith("http") else MANIFEST["base"] + info["file"], raw)
    w, h = info.get("res", (1920, 1080))
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-an", "-vf",
                           "scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d,fps=24" % (w, h, w, h),
                           "-c:v", "libx264", "-preset", "veryfast", "-crf", "12" if w > 1920 else "14", "-g", "12",
                           "-pix_fmt", "yuv420p", dst])
    raw_px = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", dst, "-vf", "scale=%d:%d" % (PW, PH),
                             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    frames = np.frombuffer(raw_px, np.uint8).reshape(-1, PH, PW, 3)
    np.save(os.path.join(OUT, name + "_proxy.npy"), frames)
    json.dump({"dur": len(frames) / 24.0, "frames": len(frames)}, open(meta, "w"))
    os.remove(raw)
    return name, "ok %.2fs" % (len(frames) / 24.0)


if __name__ == "__main__":
    MANIFEST = json.load(open(os.path.join(HERE, "assets", "clips.json")))
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for name, status in ex.map(prep, MANIFEST["clips"].items()):
            print(name, status, flush=True)
