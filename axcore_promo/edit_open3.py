"""Opening 00:00:00:00-00:00:08:02, third version (client's new references S1-S3; client: the last one fell short):
  1 factory   a vast autonomous car plant, blue AGVs carrying bodies across a white floor; the camera glides in
  2 inspect   the AI inspection station: vision camera module, the scan light on the board, the arm's probe; a
              holographic PASS badge over the board (prep_up2 --pass)
  3 screen    the AI inspection screen (seg_aiscreen, drawn at full size): the top-down conveyor feed, a board comes
              down under the scan line, REJECT
  4 logistics small robot modules carrying blue totes past the racks; the camera trucks right
40 + 56 + 42 + 57 = 195 frames (client: longer logistics; the inspection's stop / light / PASS), hard cuts. The camera moves differ, matched only across the cuts:
forward -> forward (push in) -> push in, speeding up to the right -> trucking right. White / blue look.
Sources: the generated clips (21:9, 720p) blown up x2 first (prep_up2: Lanczos + unsharp); the screen rendered at the
output size. The edit grammar and look are edit_open's (no shutter blend: sharp frames).
Usage: python3 edit_open3.py <factory_x2> <inspect_x2> <screen_x2> <logistics_x2> <out.mp4> [height=1440]
"""
import subprocess
import sys

import cv2
import numpy as np

import edit_open as EO

EO.PUSH = 0.0
EO.DRIFT = 0.0
SHOTS = [
    dict(key="factory", a=0, n=40, speed=[(0, 1.0), (34, 1.0), (40, 1.2)], push=0.0, drift=0.0, v=0.50,
         b_in=0.0, b_out=0.0),
    # locked off (client): a board comes in and stops, the camera lowers, blue light, PASS; x1.5
    dict(key="inspect", a=8, n=56, speed=[(0, 1.5), (56, 1.5)], push=0.0, drift=0.0, v=0.50,
         b_in=0.0, b_out=0.0),
    # the monitor (prep_monitor2): board in, stop, scan, REJECT; a slow digital push in, speeding right at the end
    dict(key="screen", a=0, n=42, speed=[(0, 1.0), (42, 1.0)], push=-0.0012, drift=0.0, v=0.50,
         b_in=0.0, b_out=-0.012),
    dict(key="logistics", a=0, n=57, speed=[(0, 1.0), (57, 1.0)], push=0.0, drift=0.0, v=0.50,
         b_in=0.0, b_out=0.0),
]
EO.SHOTS = SHOTS


def travel(i, shot, k):
    x = 0.0
    if shot["b_in"]:
        x -= shot["b_in"] * np.exp(-k / EO.TAU)
    if shot["b_out"]:
        x += shot["b_out"] * np.exp((k - shot["n"]) / EO.TAU)
    return x


EO.travel = travel
_cam = EO.cam


def cam(i, shot, k):
    s, x = _cam(i, shot, k)
    z = shot.get("z_out", 0.0) * np.exp((k - shot["n"]) / EO.TAU) + shot.get("z_in", 0.0) * (1 - np.exp(-k / EO.TAU))
    return s * np.exp(z), x


EO.cam = cam


def place(src, s, x, shot, W, Hb):
    h, w = src.shape[:2]
    s = max(W / w, Hb / h) * s
    cx = w / 2 - x * W / s
    cy = min(max(shot["v"] * h, Hb / s / 2), h - Hb / s / 2)
    cx = min(max(cx, W / s / 2), w - W / s / 2)
    M = np.array([[s, 0, W / 2 - s * cx], [0, s, Hb / 2 - s * cy]], np.float32)
    flags = cv2.INTER_AREA if s < 1 else cv2.INTER_LANCZOS4
    return cv2.warpAffine(src, M, (W, Hb), flags=flags, borderMode=cv2.BORDER_REFLECT)


EO.place = place


def frame(clip, i, shot, k, W, Hb):
    s, x = EO.cam(i, shot, k)
    return EO.place(clip.frame(int(round(EO.src_time(shot, k)))), s, x, shot, W, Hb)


def main():
    fact, insp, scr, logi, out = sys.argv[1:6]
    H = int(sys.argv[6]) if len(sys.argv) > 6 else 1440
    W = int(round(H * 16 / 9 / 2)) * 2
    bar = int(round(H * EO.BAR_FRAC / 2)) * 2
    Hb = H - 2 * bar
    work = int(W * 1.35)
    paths = {"factory": fact, "inspect": insp, "screen": scr, "logistics": logi}
    sts = []
    for i, s in enumerate(EO.SHOTS):
        c = EO.Clip(paths[s["key"]], work)
        sts.append(EO.stats([frame(c, i, s, k, W, Hb) for k in range(0, s["n"], 6)]))
    tg = {k: float(np.mean([s[k] for s in sts])) for k in sts[0]}
    tg["am"] = tg["am"] * 0.5 + EO.COOL_A * 0.5
    tg["bm"] = tg["bm"] * 0.5 + EO.COOL_B * 0.5
    tg["Lm"] += EO.LIFT
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", "%dx%d" % (W, H), "-r", "%d/%d" % (EO.FPS_NUM, EO.FPS_DEN), "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "14" if H >= 1080 else "18",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    rng = np.random.default_rng(7)
    t = 0
    for i, (s, st) in enumerate(zip(EO.SHOTS, sts)):
        c = EO.Clip(paths[s["key"]], work)
        for k in range(s["n"]):
            g = EO.grade(frame(c, i, s, k, W, Hb), st, tg)
            g += rng.normal(0, EO.GRAIN, g.shape[:2]).astype(np.float32)[..., None]
            fr = np.zeros((H, W, 3), np.uint8)
            fr[bar:bar + Hb] = np.clip(g * 255 + 0.5, 0, 255).astype(np.uint8)
            enc.stdin.write(fr.tobytes())
            t += 1
    enc.stdin.close()
    enc.wait()
    print(out, t, "frames")


if __name__ == "__main__":
    main()
