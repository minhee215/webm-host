"""Download the Nano Banana Pro scene plates listed in assets/plates.json.

Plates are cached as 2304x1296 JPEGs (1.2x the 1080p frame, headroom for camera moves).
Usage: python3 fetch_plates.py [out_dir]
"""
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "plates")
PLATE_SIZE = (2304, 1296)


def fetch(item):
    name, fname = item
    dst = os.path.join(OUT, name + ".jpg")
    if os.path.exists(dst):
        return name, "cached"
    with urllib.request.urlopen(MANIFEST["base"] + fname, timeout=120) as r:
        im = Image.open(BytesIO(r.read())).convert("RGB")
    im.resize(PLATE_SIZE, Image.LANCZOS).save(dst, quality=95)
    return name, "ok"


if __name__ == "__main__":
    MANIFEST = json.load(open(os.path.join(HERE, "assets", "plates.json")))
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        for name, status in ex.map(fetch, MANIFEST["plates"].items()):
            print(f"{name}: {status}")
