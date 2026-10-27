#!/usr/bin/env python3
"""AXCORE intro 8-second sample — editorial build.

Four separately generated shots are cut together with hard cuts only. Each cut
is chosen on a real action (spatial continuity, match on action, shape match);
the only per-shot adjustments are trim, gentle scale/position for the match,
and a shared colour match. No transitions, graphics or text.

  python intro8/build_intro8.py            # -> intro8/renders/AXCORE_intro_8sec_preview_v01.mp4
  python intro8/build_intro8.py --sheet    # contact sheets of the source shots for picking cut points
"""
import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from src.audio.synth import SR, sine, noise, fft_band, env_exp, env_adsr, midi, pan, place, reverb  # noqa: E402

FPS = 30
W, H = 854, 480
OUT = HERE / "renders" / "AXCORE_intro_8sec_preview_v01.mp4"

# Edit decision list. Each shot: source segments (in, out, speed) and transform
# keyframes over the shot's own 0..1 progress: (p, scale, (dx, dy) in output px),
# applied around the frame centre. Cuts are hard cuts on real action.
EDL = [
    dict(file="S1_engineer_walk.mp4", segs=[(2.45, 4.55, 1.0)], tf=[(0, 1.0, (0, 0))],
         note="walks right, camera follows; ends with him on the left and the glass control room on the right"),
    dict(file="S2_control_room.mp4", segs=[(2.40, 4.30, 1.0)], tf=[(0, 1.0, (0, 0))],
         note="spatial continuity into the control room; cut while the right hand is coming down"),
    dict(file="S3_robot_cell.mp4", segs=[(0.60, 1.25, 1.3), (1.25, 3.10, 2.3), (3.10, 3.80, 1.0)],
         tf=[(0, 1.0, (0, 0)), (0.6, 1.0, (0, 0)), (1.0, 1.25, (85, -58))],
         note="match on action: tool head continues the hand's downward motion; settles on the ring"),
    dict(file="S4_quality_engineer.mp4", segs=[(2.50, 4.50, 1.0)],
         tf=[(0, 1.45, (-139, 18)), (1.0, 1.0, (0, 0))],
         note="shape match on the ring (position/size aligned), then a gentle pull-back"),
]


def ease(p):
    return 1 - (1 - p) ** 3 if p < 1 else 1.0


def tf_at(keys, p):
    if p <= keys[0][0]:
        return keys[0][1], keys[0][2]
    for (p0, s0, o0), (p1, s1, o1) in zip(keys, keys[1:]):
        if p <= p1:
            u = (p - p0) / max(1e-6, p1 - p0)
            u = u * u * (3 - 2 * u)            # smooth in/out
            return s0 + (s1 - s0) * u, (o0[0] + (o1[0] - o0[0]) * u, o0[1] + (o1[1] - o0[1]) * u)
    return keys[-1][1], keys[-1][2]


def retime(frames, segs):
    """Source segments at given speeds -> list of output frames (nearest source frame)."""
    out = []
    for a, b, sp in segs:
        n = int(round((b - a) / sp * FPS))
        for k in range(n):
            t = a + k / FPS * sp
            out.append(frames[min(len(frames) - 1, int(round(t * FPS)))])
    return out


def decode(path):
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"fps={FPS},scale=1280:720:flags=lanczos",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 720, 1280, 3)


# --- colour: one shared, bright, neutral, slightly cool look ---------------------------
def lab_stats(frames):
    s = np.ascontiguousarray(frames[:: max(1, len(frames) // 10)]).reshape(-1, frames.shape[2], 3)
    lab = cv2.cvtColor(s, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    return lab.mean(0), lab.std(0) + 1e-3


def grade(frame, mean, std, target_mean, target_std):
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB).astype(np.float32)
    strength = np.array([0.6, 0.85, 0.85])          # exposure gently, white balance firmly
    tm = mean + (target_mean - mean) * strength
    ts = std + (target_std - std) * np.array([0.4, 0.5, 0.5])
    lab = (lab - mean) / std * ts + tm
    L = lab[..., 0] / 255.0
    L = np.where(L > 0.9, 0.9 + (L - 0.9) * 0.6, L)  # soft highlight roll-off
    lab[..., 0] = np.clip(L, 0, 1) * 255
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def transform(frame, scale, off):
    if scale == 1.0 and off == (0, 0):
        return frame
    h, w = frame.shape[:2]
    k = w / W
    M = np.array([[scale, 0, (1 - scale) * w / 2 + off[0] * k],
                  [0, scale, (1 - scale) * h / 2 + off[1] * k]], np.float32)
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)


# --- sound: room tone + light machine detail + very light music ------------------------
def build_audio(cuts, total, path):
    n = int(total * SR)
    bus = np.zeros((n, 2))
    # factory room tone (continuous across cuts so the space feels shared)
    tone = fft_band(noise(n, 11), 60, 900) * 0.010 + fft_band(noise(n, 12), 2000, 6000) * 0.0025
    hum = sine(100, n) * 0.0025 + sine(200, n) * 0.0012
    bus += pan(tone + hum, 0.0)
    s1, s2, s3, s4 = cuts
    # shot 1: soft footsteps under the walk
    for k in range(5):
        t = s1 + 0.15 + k * 0.48
        m = int(0.09 * SR)
        step = fft_band(noise(m, 30 + k), 80, 1500) * env_exp(m, 0.02) * 0.05
        place(bus, pan(step, -0.15 + 0.08 * k), t)
    # shot 2: one mouse click as the hand lands (just after the cut it carries over)
    # shot 3: servo descent + contact tick + small lift
    d = int(1.1 * SR)
    servo = (sine(np.linspace(260, 340, d), d) * 0.010 + fft_band(noise(d, 40), 900, 3000) * 0.004) \
        * env_adsr(d, 0.08, 0.2, 0.9, 0.2)
    place(bus, pan(servo, 0.1), s3)
    m = int(0.25 * SR)
    tick = (sine(2900, m) * 0.02 + sine(4100, m) * 0.01) * env_exp(m, 0.04)
    place(bus, pan(tick, 0.0), s3 + 1.05)
    lift = (sine(np.linspace(340, 300, int(0.6 * SR)), int(0.6 * SR)) * 0.008) * env_adsr(int(0.6 * SR), 0.05, 0.1, 0.9, 0.2)
    place(bus, pan(lift, 0.1), s3 + 1.35)
    # shot 4: faint metal handling
    m = int(0.18 * SR)
    place(bus, pan((sine(1800, m) * 0.006 + sine(2650, m) * 0.004) * env_exp(m, 0.05), 0.2), s4 + 0.4)
    # very light music: soft pad, slow swell (narration-friendly)
    mus = np.zeros(n)
    for chord, t0 in (([62, 65, 69, 72, 76], 0.0), ([62, 65, 69, 70, 74], total / 2)):
        m = int((total / 2 + 1.0) * SR)
        sig = sum(np.sin(2 * np.pi * midi(x) * np.arange(m) / SR) for x in chord)
        sig = fft_band(sig, 100, 2500) * env_adsr(m, 1.2, 0.5, 0.8, 1.2) * 0.010
        place(mus, sig, t0)
    bus += pan(mus, 0.0)
    bus = reverb(bus, 1.6, 0.2)
    fi, fo = int(0.4 * SR), int(0.6 * SR)
    bus[:fi] *= np.linspace(0, 1, fi)[:, None]
    bus[-fo:] *= np.linspace(1, 0, fo)[:, None]
    bus *= 10 ** (-3 / 20) / max(1e-6, np.abs(bus).max()) * 0.35      # quiet: leaves room for narration
    pcm = (np.clip(bus, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def build():
    gen = HERE / "generated"
    shots = [decode(gen / e["file"]) for e in EDL]
    stats = [lab_stats(s) for s in shots]
    target_mean = np.mean([m for m, _ in stats], axis=0)
    target_mean[0] = max(target_mean[0], 150.0)      # bright corporate exposure
    target_mean[1], target_mean[2] = 127.5, 125.5      # neutral, slightly cool
    target_std = np.mean([s for _, s in stats], axis=0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    silent = OUT.with_name("video_only.mp4")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16",
                            "-preset", "slow", "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    cuts, t = [], 0.0
    for e, frames, (mean, std) in zip(EDL, shots, stats):
        cuts.append(t)
        seq = retime(frames, e["segs"])
        for k, fr in enumerate(seq):
            scale, off = tf_at(e["tf"], k / max(1, len(seq) - 1))
            g = grade(transform(fr, scale, off), mean, std, target_mean, target_std)
            enc.stdin.write(cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA).tobytes())
        t += len(seq) / FPS
    enc.stdin.close()
    enc.wait()
    wav = OUT.with_name("audio_mix.wav")
    build_audio(cuts, t, wav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(silent), "-i", str(wav), "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(OUT)], check=True)
    silent.unlink()
    print(f"wrote {OUT}  ({t:.2f}s, cuts at {[round(c, 2) for c in cuts]})")


def sheets():
    gen = HERE / "generated"
    for e in EDL:
        p = gen / e["file"]
        if p.exists():
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-vf",
                            "fps=6,scale=240:-1,drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow,tile=6x5",
                            "-frames:v", "1", str(HERE / "renders" / (p.stem + "_sheet.jpg"))], check=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true")
    args = ap.parse_args()
    (HERE / "renders").mkdir(exist_ok=True)
    sheets() if args.sheet else build()
