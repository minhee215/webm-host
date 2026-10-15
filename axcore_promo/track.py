"""Track the live-action clips so graphics stay attached to what moves.

For every clip in assets/clips.json with a "track" block:
  regions: {name: [u0, v0, u1, v1]}  per-frame homography of that surface (frame 0 -> frame i),
           estimated from Lucas-Kanade feature tracks with RANSAC ("global" = whole frame)
  points:  {name: [u, v]}            single optical-flow point tracks (e.g. a robot gripper)
  hand:    true                      MediaPipe hand landmarks (21 points) + pinch strength
Output: clips/<name>_track.json (normalized frame coordinates).
Needs: opencv-python-headless, mediapipe (hand model fetched on first use).
Usage: python3 track.py [clip_dir] [name ...]
"""
import json
import os
import sys
import urllib.request

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CLIP_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "clips")
ONLY = set(sys.argv[2:])
TW, TH = 960, 540
HAND_MODEL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"


def read_frames(path):
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        out.append(f)
    return out


def to_gray(f):
    return cv2.cvtColor(cv2.resize(f, (TW, TH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def region_mask(box):
    m = np.zeros((TH, TW), np.uint8)
    u0, v0, u1, v1 = box
    m[int(v0 * TH):int(v1 * TH), int(u0 * TW):int(u1 * TW)] = 255
    return m


LK = dict(winSize=(25, 25), maxLevel=4, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
NORM = np.array([[1 / TW, 0, 0], [0, 1 / TH, 0], [0, 0, 1]])
DENORM = np.linalg.inv(NORM)


def track_region(grays, box):
    """Homographies (normalized coords) mapping frame-0 points to frame i."""
    mask = region_mask(box)
    ref = cv2.goodFeaturesToTrack(grays[0], 400, 0.01, 8, mask=mask)
    Hs = [np.eye(3)]
    if ref is None or len(ref) < 8:
        return [np.eye(3).ravel().tolist() for _ in grays]
    cur = ref.copy()
    H_prev = np.eye(3)
    for i in range(1, len(grays)):
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(grays[i - 1], grays[i], cur, None, **LK)
        back, st2, _ = cv2.calcOpticalFlowPyrLK(grays[i], grays[i - 1], nxt, None, **LK)
        good = (st.ravel() == 1) & (st2.ravel() == 1) & (np.linalg.norm(back - cur, axis=2).ravel() < 1.0)
        ref, cur = ref[good], nxt[good]
        H = H_prev
        if len(ref) >= 8:
            Hp, inl = cv2.findHomography(ref, cur, cv2.RANSAC, 2.5)
            if Hp is not None:
                H = Hp
        if len(ref) < 60:  # reseed inside the region as tracked so far
            m = cv2.warpPerspective(mask, H, (TW, TH))
            new = cv2.goodFeaturesToTrack(grays[i], 400, 0.01, 8, mask=m)
            if new is not None:
                back_ref = cv2.perspectiveTransform(new, np.linalg.inv(H))
                ref = np.concatenate([ref, back_ref.astype(np.float32)])
                cur = np.concatenate([cur, new])
        H_prev = H
        Hs.append(H)
    # temporal smoothing of the homography entries (removes RANSAC jitter)
    arr = np.array([NORM @ h @ DENORM for h in Hs])
    arr /= arr[:, 2:3, 2:3]
    k = np.array([1, 2, 3, 2, 1], float)
    k /= k.sum()
    pad = np.concatenate([arr[:1].repeat(2, 0), arr, arr[-1:].repeat(2, 0)])
    sm = np.stack([np.tensordot(k, pad[i:i + 5], axes=1) for i in range(len(arr))])
    return [h.ravel().tolist() for h in sm]


def track_point(grays, uv):
    p = np.array([[[uv[0] * TW, uv[1] * TH]]], np.float32)
    out = [list(uv)]
    for i in range(1, len(grays)):
        nxt, st, _ = cv2.calcOpticalFlowPyrLK(grays[i - 1], grays[i], p, None, **LK)
        if st[0][0] == 1:
            p = nxt
        out.append([float(p[0, 0, 0]) / TW, float(p[0, 0, 1]) / TH])
    a = np.array(out)
    for _ in range(2):
        a[1:-1] = (a[:-2] + 2 * a[1:-1] + a[2:]) / 4
    return a.tolist()


def track_hand(frames, near=None):
    import mediapipe as mp
    from mediapipe.tasks import python as mpt
    from mediapipe.tasks.python import vision
    model = os.path.join(CLIP_DIR, "hand_landmarker.task")
    if not os.path.exists(model):
        urllib.request.urlretrieve(HAND_MODEL, model)
    opts = vision.HandLandmarkerOptions(base_options=mpt.BaseOptions(model_asset_path=model),
                                        running_mode=vision.RunningMode.VIDEO, num_hands=2 if near else 1,
                                        min_hand_detection_confidence=0.3, min_hand_presence_confidence=0.3,
                                        min_tracking_confidence=0.3)
    det = vision.HandLandmarker.create_from_options(opts)
    raw = []
    for i, f in enumerate(frames):
        rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        res = det.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), int(i * 1000 / 24))
        if res.hand_landmarks:
            hands = [np.array([[p.x, p.y] for p in h]) for h in res.hand_landmarks]
            if near is not None:  # several hands: keep the one whose index fingertip is nearest the hint
                prev = raw[-1][8] if raw and raw[-1] is not None else np.array(near)
                hands.sort(key=lambda h: np.linalg.norm(h[8] - prev))
            raw.append(hands[0])
        else:
            raw.append(None)
    det.close()
    # fill gaps by linear interpolation, then smooth
    idx = [i for i, r in enumerate(raw) if r is not None]
    if not idx:
        return None
    arr = np.zeros((len(raw), 21, 2))
    for i in range(len(raw)):
        if raw[i] is not None:
            arr[i] = raw[i]
        else:
            a = max([j for j in idx if j < i], default=None)
            b = min([j for j in idx if j > i], default=None)
            if a is None:
                arr[i] = raw[b]
            elif b is None:
                arr[i] = raw[a]
            else:
                w = (i - a) / (b - a)
                arr[i] = raw[a] * (1 - w) + raw[b] * w
    sm = arr.copy()
    for _ in range(2):
        sm[1:-1] = (sm[:-2] + 2 * sm[1:-1] + sm[2:]) / 4
    out = []
    for i in range(len(sm)):
        lm = sm[i]
        size = np.linalg.norm((lm[0] - lm[9]) * [16, 9]) + 1e-6
        d = np.linalg.norm((lm[4] - lm[8]) * [16, 9]) / size
        pinch = float(np.clip((0.55 - d) / 0.35, 0, 1))
        out.append({"lm": lm.tolist(), "pinch": pinch, "seen": raw[i] is not None})
    return out


def track_screen(frames, box):
    """Corners (TL, TR, BR, BL; normalized) of the bright blank device screen inside box, per frame.
    Thresholds the bright low-saturation blob, takes its convex hull (fingers over the edge are
    bridged) and reduces it to a quadrilateral; smoothed over time."""
    u0, v0, u1, v1 = box
    out, last = [], None
    for f in frames:
        h, w = f.shape[:2]
        x0, y0, x1, y1 = int(u0 * w), int(v0 * h), int(u1 * w), int(v1 * h)
        hsv = cv2.cvtColor(f[y0:y1, x0:x1], cv2.COLOR_BGR2HSV)
        m = ((hsv[..., 2] > 185) & (hsv[..., 1] < 90)).astype(np.uint8) * 255
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        quad = None
        if cs:
            cnt = max(cs, key=cv2.contourArea)
            hull = cv2.convexHull(cnt)
            peri = cv2.arcLength(hull, True)
            for eps in np.linspace(0.01, 0.12, 23):
                ap = cv2.approxPolyDP(hull, eps * peri, True)
                if len(ap) == 4:
                    quad = ap.reshape(4, 2).astype(float)
                    break
        if quad is None:
            out.append(last)
            continue
        quad[:, 0] = (quad[:, 0] + x0) / w
        quad[:, 1] = (quad[:, 1] + y0) / h
        sm, df = quad.sum(1), quad[:, 0] - quad[:, 1]
        tl, br = quad[np.argmin(sm)], quad[np.argmax(sm)]
        tr, bl = quad[np.argmax(df)], quad[np.argmin(df)]
        last = np.array([tl, tr, br, bl])
        out.append(last)
    first = next((q for q in out if q is not None), None)
    if first is None:
        return None
    arr = np.array([q if q is not None else first for q in out])
    for _ in range(3):
        arr[1:-1] = (arr[:-2] + 2 * arr[1:-1] + arr[2:]) / 4
    return arr.tolist()


def main():
    manifest = json.load(open(os.path.join(HERE, "assets", "clips.json")))
    for name, info in manifest["clips"].items():
        cfg = info.get("track")
        if cfg is None or (ONLY and name not in ONLY):
            continue
        path = os.path.join(CLIP_DIR, name + ".mp4")
        frames = read_frames(path)
        grays = [to_gray(f) for f in frames]
        data = {"n": len(frames), "H": {}, "points": {}}
        regions = dict(cfg.get("regions", {}))
        regions.setdefault("global", [0.02, 0.02, 0.98, 0.98])
        for rname, box in regions.items():
            data["H"][rname] = track_region(grays, box)
        for pname, uv in cfg.get("points", {}).items():
            data["points"][pname] = track_point(grays, uv)
        if cfg.get("hand"):
            data["hand"] = track_hand(frames, cfg.get("hand_near"))
        if cfg.get("screens"):
            data["screens"] = {k: track_screen(frames, b) for k, b in cfg["screens"].items()}
        json.dump(data, open(os.path.join(CLIP_DIR, name + "_track.json"), "w"))
        hs = data["H"]["global"][-1]
        print(name, len(frames), "frames; global H end", [round(v, 3) for v in hs[:6]],
              "hand" if data.get("hand") else "", flush=True)


if __name__ == "__main__":
    main()
