"""AXCORE promo film - live-action media layer.

Every Nano Banana Pro plate can have a Kling image-to-video clip generated from it
(the plate is the clip's first frame, so plate-normalized coordinates stay valid).
This module plays those clips frame-accurately inside the skia compositor:

- ClipReader: sequential ffmpeg decoder (normalized 1920x1080 / 24 fps clips)
- proxies:    small memory-mapped frame stacks for photo tiles and the AX mosaic
- tracks:     per-frame homographies (planar surfaces / camera drift), optical-flow
              points and MediaPipe hand landmarks, produced by track.py
"""
import json
import os
import subprocess

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP_DIR = os.environ.get("AXP_CLIPS", os.path.join(HERE, "clips"))
FPS = 24
CW, CH = 1920, 1080
PW, PH = 480, 270

_MANIFEST = None


def manifest():
    global _MANIFEST
    if _MANIFEST is None:
        path = os.path.join(HERE, "assets", "clips.json")
        _MANIFEST = json.load(open(path)) if os.path.exists(path) else {"clips": {}}
    return _MANIFEST


_INFO = {}


def clip_info(name):
    """Manifest entry merged with the measured duration, or None when the clip is absent."""
    if name in _INFO:
        return _INFO[name]
    info = manifest()["clips"].get(name)
    meta = os.path.join(CLIP_DIR, name + ".json")
    if info and os.path.exists(meta) and os.path.exists(os.path.join(CLIP_DIR, name + ".mp4")):
        info = dict(info, **json.load(open(meta)))
    else:
        info = None
    _INFO[name] = info
    return info


def clip_time(name, t):
    """Scene-local time -> clip time. 'pre' seconds of footage are reserved for the
    incoming transition; 'speed' retimes the take; the last frame holds at the end."""
    info = clip_info(name)
    ct = (t + info.get("pre", 0.5)) * info.get("speed", 1.0)
    return min(max(ct, 0.0), info["dur"] - 1.0 / FPS)


def clip_index(name, t):
    return int(round(clip_time(name, t) * FPS))


class ClipReader:
    def __init__(self, name):
        self.path = os.path.join(CLIP_DIR, name + ".mp4")
        self.proc = None
        self.cur = -1
        self.img = None

    def _open(self, fi):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-threads", "2", "-ss", "%.4f" % (fi / FPS), "-i", self.path, "-f", "rawvideo",
             "-pix_fmt", "rgba", "-"], stdout=subprocess.PIPE, bufsize=CW * CH * 4 * 2)
        self.cur = fi - 1

    def _read(self):
        buf = self.proc.stdout.read(CW * CH * 4)
        if len(buf) < CW * CH * 4:
            return False
        arr = np.frombuffer(buf, np.uint8).reshape(CH, CW, 4)
        self.img = skia.Image.fromarray(arr.copy(), colorType=skia.ColorType.kRGBA_8888_ColorType)
        self.cur += 1
        return True

    def close(self):
        if self.proc:
            self.proc.kill()
            self.proc.wait()
            self.proc = None
        self.img = None

    def get(self, fi):
        if self.img is not None and fi == self.cur:
            return self.img
        if self.proc is None or fi < self.cur or fi > self.cur + 36:
            self._open(fi)
        while self.cur < fi:
            if not self._read():
                break
        return self.img


_READERS = {}
MAX_READERS = 2  # each 1080p decoder holds ~0.6 GB; keep only the clips in use (cut / transition)


def frame(name, t):
    """skia.Image of the clip at scene-local time t (and the clip frame index)."""
    fi = clip_index(name, t)
    if name not in _READERS:
        while len(_READERS) >= MAX_READERS:
            old = next(iter(_READERS))
            _READERS.pop(old).close()
        _READERS[name] = ClipReader(name)
    else:
        _READERS[name] = _READERS.pop(name)  # most recently used goes last
    return _READERS[name].get(fi), fi


_PROXIES = {}


def proxy_frame(name, t, loop=True):
    """Small RGBA frame for tiles/mosaics (memory-mapped .npy made by prep_clips.py)."""
    path = os.path.join(CLIP_DIR, name + "_proxy.npy")
    if not os.path.exists(path):
        return None
    if name not in _PROXIES:
        _PROXIES[name] = np.load(path, mmap_mode="r")
    a = _PROXIES[name]
    n = a.shape[0]
    fi = int(t * FPS)
    fi = fi % n if loop else min(max(fi, 0), n - 1)
    rgb = np.asarray(a[fi])
    rgba = np.dstack([rgb, np.full(rgb.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(rgba), colorType=skia.ColorType.kRGBA_8888_ColorType)


class Track:
    """Tracking data for one clip (normalized frame coordinates)."""

    def __init__(self, data):
        self.d = data
        self.n = data.get("n", 1)

    def _i(self, fi):
        return min(max(int(fi), 0), self.n - 1)

    def H(self, region, fi):
        hs = self.d.get("H", {}).get(region) or self.d.get("H", {}).get("global")
        if not hs:
            return None
        return np.array(hs[self._i(fi)], np.float64).reshape(3, 3)

    def apply(self, region, fi, u, v):
        h = self.H(region, fi)
        if h is None:
            return u, v
        p = h @ np.array([u, v, 1.0])
        return p[0] / p[2], p[1] / p[2]

    def point(self, name, fi):
        pts = self.d.get("points", {}).get(name)
        if not pts:
            return None
        return tuple(pts[self._i(fi)])

    def hand(self, fi, lm=8):
        """Landmark lm (8 = index tip, 4 = thumb tip, 9 = middle MCP) and pinch strength 0..1."""
        h = self.d.get("hand")
        if not h:
            return None
        rec = h[self._i(fi)]
        if rec is None:
            return None
        x, y = rec["lm"][lm]
        return x, y, rec.get("pinch", 0.0)


_TRACKS = {}


def track(name):
    if name not in _TRACKS:
        path = os.path.join(CLIP_DIR, name + "_track.json")
        _TRACKS[name] = Track(json.load(open(path))) if os.path.exists(path) else None
    return _TRACKS[name]
