"""Planar / point / screen tracking on the graded plates (OpenCV).

All results are in plate pixels (960x540) and cached as JSON so that a scene
re-render never re-tracks. Every function returns per-source-frame data; use
`sample()` to get a value at plate-local time t.
"""
import json

import cv2
import numpy as np

from .plates import Plate, PLATE_DIR, SRC_FPS

LK = dict(winSize=(25, 25), maxLevel=4,
          criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01))


def _gray(plate, i):
    return cv2.cvtColor(np.asarray(plate.frames[i][..., :3]), cv2.COLOR_BGR2GRAY)


def _cache(name):
    return PLATE_DIR / f"track_{name}.json"


def _load(name):
    p = _cache(name)
    return np.array(json.loads(p.read_text())) if p.exists() else None


def _save(name, arr):
    _cache(name).write_text(json.dumps(np.asarray(arr).tolist()))


def track_plane(key, roi, name=None, force=False):
    """Homographies H_i (frame0 -> frame i) of the plane inside polygon `roi`."""
    name = name or f"{key}_plane"
    if not force and (cached := _load(name)) is not None:
        return cached
    pl = Plate(key)
    Hs = [np.eye(3)]
    prev = _gray(pl, 0)
    roi = np.array(roi, np.float32)
    for i in range(1, pl.n):
        cur = _gray(pl, i)
        cur_roi = cv2.perspectiveTransform(roi[None], Hs[-1])[0]
        mask = np.zeros_like(prev)
        cv2.fillPoly(mask, [cur_roi.astype(np.int32)], 255)
        p0 = cv2.goodFeaturesToTrack(prev, 400, 0.01, 6, mask=mask)
        H_step = np.eye(3)
        if p0 is not None and len(p0) >= 8:
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, p0, None, **LK)
            pb, st2, _ = cv2.calcOpticalFlowPyrLK(cur, prev, p1, None, **LK)
            good = (st[:, 0] == 1) & (st2[:, 0] == 1) & (np.linalg.norm(pb - p0, axis=2)[:, 0] < 1.0)
            if good.sum() >= 8:
                H, _ = cv2.findHomography(p0[good], p1[good], cv2.RANSAC, 2.0)
                if H is not None:
                    H_step = H
        Hs.append(H_step @ Hs[-1])
        prev = cur
    Hs = np.array([H / H[2, 2] for H in Hs])
    _save(name, Hs)
    return Hs


def track_points(key, pts, name, force=False, plane=None):
    """LK tracks for a few anchor points; falls back to `plane` homographies."""
    if not force and (cached := _load(name)) is not None:
        return cached
    pl = Plate(key)
    pts = np.array(pts, np.float32).reshape(-1, 1, 2)
    out = [pts[:, 0].copy()]
    prev = _gray(pl, 0)
    cur_pts = pts.copy()
    for i in range(1, pl.n):
        cur = _gray(pl, i)
        p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, cur, cur_pts, None, **LK)
        pb, st2, _ = cv2.calcOpticalFlowPyrLK(cur, prev, p1, None, **LK)
        ok = (st[:, 0] == 1) & (np.linalg.norm(pb - cur_pts, axis=2)[:, 0] < 1.5)
        if plane is not None:
            pred = cv2.perspectiveTransform(pts, plane[i])
            p1[~ok] = pred[~ok]
        else:
            p1[~ok] = cur_pts[~ok]
        cur_pts = p1
        out.append(p1[:, 0].copy())
        prev = cur
    out = _smooth(np.array(out), 5)
    _save(name, out)
    return out


def track_similarity(key, pts, name, force=False):
    """Per-frame 2x3 similarity (frame0 -> frame i) from a few LK point tracks.

    Used where the anchor plane has no texture of its own (e.g. a conveyor
    with moving parts): rigid neighbours at the same depth carry the motion.
    """
    if not force and (cached := _load(name)) is not None:
        return cached
    pl = Plate(key)
    g0 = _gray(pl, 0)
    snapped = []
    for p in pts:   # snap each anchor to the strongest nearby corner
        x, y = int(p[0]), int(p[1])
        r = 24
        sub = g0[max(0, y - r):y + r, max(0, x - r):x + r]
        c = cv2.goodFeaturesToTrack(sub, 1, 0.01, 5)
        if c is not None:
            snapped.append((c[0, 0, 0] + max(0, x - r), c[0, 0, 1] + max(0, y - r)))
        else:
            snapped.append((x, y))
    tracks = track_points(key, snapped, name + "_pts", force=force)
    src = np.array(snapped, np.float32)
    mats = []
    for i in range(len(tracks)):
        M, _ = cv2.estimateAffinePartial2D(src, tracks[i].astype(np.float32))
        mats.append(M if M is not None else (mats[-1] if mats else np.eye(2, 3)))
    mats = _smooth(np.array(mats), 5)
    _save(name, mats)
    return mats


def track_screen(key, quad0, name=None, force=False, dark=False):
    """Track a display surface (uniform bright — or dark — panel in a bezel).

    Each frame: predict the quad from the previous one, segment the uniform
    region around it, fit 4 corners; fall back to the prediction if the fit is
    implausible. Result is temporally smoothed.
    """
    name = name or f"{key}_screen"
    if not force and (cached := _load(name)) is not None:
        return cached
    pl = Plate(key)
    q = np.array(quad0, np.float32)
    quads = []
    vel = np.zeros_like(q)
    for i in range(pl.n):
        g = _gray(pl, i)
        g = cv2.GaussianBlur(g, (5, 5), 0)
        inner = _shrink(q, 0.25)
        m = np.zeros_like(g)
        cv2.fillPoly(m, [inner.astype(np.int32)], 255)
        ref = np.median(g[m > 0])
        tol = 18 if not dark else 14
        band = ((np.abs(g.astype(np.int16) - ref) < tol) * 255).astype(np.uint8)
        search = np.zeros_like(g)
        cv2.fillPoly(search, [_shrink(q, -0.10).astype(np.int32)], 255)
        band &= search
        band = cv2.morphologyEx(band, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        n, lab, stats, _ = cv2.connectedComponentsWithStats(band)
        c = q.mean(0).astype(int)
        lid = lab[np.clip(c[1], 0, g.shape[0] - 1), np.clip(c[0], 0, g.shape[1] - 1)]
        fitted = None
        if lid > 0:
            comp = ((lab == lid) * 255).astype(np.uint8)
            cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            hull = cv2.convexHull(max(cnts, key=cv2.contourArea))
            approx = cv2.approxPolyN(hull, 4, ensure_convex=True)
            if approx is not None and len(approx.reshape(-1, 2)) == 4:
                cand = _order(approx.reshape(-1, 2).astype(np.float32))
                area_ratio = cv2.contourArea(cand) / max(1.0, cv2.contourArea(q))
                jump = np.abs(cand - (q + vel)).max()
                limit = 60 if i == 0 else 6
                if 0.7 < area_ratio < 1.4 and jump < limit:
                    fitted = cand
        if fitted is not None:
            if i > 0:
                vel = 0.7 * vel + 0.3 * (fitted - q)
            q = fitted
        else:
            q = q + vel          # occluded / implausible: constant-velocity prediction
        quads.append(q.copy())
    quads = _smooth(np.array(quads), 7)
    _save(name, quads)
    return quads


def _shrink(q, f):
    c = q.mean(0)
    return c + (q - c) * (1 - f)


def _order(pts):
    s = pts.sum(1)
    d = np.diff(pts, axis=1)[:, 0]
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    np.float32)


def _smooth(arr, k):
    if k <= 1 or len(arr) < k:
        return arr
    pad = k // 2
    ext = np.concatenate([arr[:1].repeat(pad, 0), arr, arr[-1:].repeat(pad, 0)])
    return np.array([ext[i:i + k].mean(0) for i in range(len(arr))])


def sample(arr, t):
    """Linear interpolation of per-frame tracking data at plate time t."""
    fi = float(np.clip(t * SRC_FPS, 0, len(arr) - 1))
    i0 = int(fi)
    i1 = min(i0 + 1, len(arr) - 1)
    w = fi - i0
    return arr[i0] * (1 - w) + arr[i1] * w


def warp_points(H, pts):
    pts = np.array(pts, np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, np.asarray(H, np.float64))[:, 0]
