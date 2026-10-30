"""AXCORE promo film - soundtrack v6: supplied BGM + narration (with pauses) + soft scene-change whooshes.

The picture is unchanged (v4, 120.0 s). This builds the audio track only:

- Narration: the supplied read with the v4 pauses spliced into its silences (same as the film).
- BGM: the supplied track (104.0 BPM, F major, 154.8 s) shortened by exactly 14 bars (32.31 s) with
  one bar-aligned seam at 39.35 s (chosen by chroma/level similarity, under the voice). With that
  edit the track's quiet build lands on "더 빠른 판단…", its drop hits as the AX is revealed and its
  final hit lands on "AXCORE" (logo).
- Mix: sidechain ducking under the voice (music swells back up in the pauses) and a soft whoosh on
  each scene change only (match cuts quieter than line-particle cuts). No other effects.

v7 (--narration, --no-fx): the narration is a supplied read already timed to the film (no splicing), no scene-
change whooshes at all, and the music sits lower (--music LUFS before ducking, --duck depth) so the voice is
never buried.

Usage: python3 audio_bgm.py /path/to/AXCORE_BGM.mp3 [out.mp3] [--narration timed.mp3] [--no-fx]
                                                              [--music -23] [--duck 0.72]
"""
import os
import subprocess
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

import audio as A
import scenes as S

SR = A.SR
BPM = 104.005
BEAT = 60.0 / BPM
PHASE = 0.125                 # first beat of the BGM (s)
CUT = PHASE + 68 * BEAT       # 39.354 s: bar-aligned seam
SKIP = 56 * BEAT              # 14 bars = 32.307 s
XF = 0.06                     # equal-power crossfade at the seam
LEAD = 0.16                   # start the track this far in so its final hit lands on the spoken "AXCORE"

def sec(t):
    return int(round(t * SR))


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)


def lp(x, fc):
    return sosfilt(butter(2, fc, "low", fs=SR, output="sos"), x).astype(np.float32)


# ---------------------------------------------------------------- BGM edit
def load_bgm(path, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)[sec(LEAD):]
    c, s, xf = sec(CUT - LEAD), sec(SKIP), sec(XF)   # seam on the BGM's bar line
    res = np.zeros((total, 2), np.float32)
    res[:c - xf] = x[:c - xf]
    w = np.linspace(0, np.pi / 2, 2 * xf)[:, None]
    res[c - xf:c + xf] = x[c - xf:c + xf] * np.cos(w) + x[c - xf + s:c + xf + s] * np.sin(w)   # equal power
    rest = x[c + xf + s:]
    n = min(len(rest), total - (c + xf))
    res[c + xf:c + xf + n] = rest[:n]
    # tail: the track's own ending decays from ~118.4 s; finish cleanly at 120.0
    tl = np.arange(total) / SR
    fade = np.clip((120.0 - tl) / 1.1, 0, 1) ** 1.5
    return res * fade[:, None].astype(np.float32)


# ---------------------------------------------------------------- effects (synthesized, short, quiet)
class Bus:
    def __init__(self, total):
        self.x = np.zeros((total, 2), np.float32)
        self.total = total

    def add(self, t, sig, gain=1.0, pan=0.0):
        i0 = sec(t)
        if i0 < 0 or i0 >= self.total:
            return
        if sig.ndim == 1:
            sig = np.stack([sig * (1 - pan), sig * (1 + pan)], 1)
        n = min(len(sig), self.total - i0)
        self.x[i0:i0 + n] += sig[:n] * gain


RNG = np.random.default_rng(21)


def room(x, mix=0.22):
    n = sec(1.1)
    tt = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = (RNG.standard_normal(n) * np.exp(-tt * 5.5)).astype(np.float32)
        ir[:sec(0.01)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = fftconvolve(x[:, ch], ir)[:len(x)]
    return x * (1 - mix) + out * mix * 1.4


def whoosh(dur, pan_dir=1.0, soft=1.0):
    """Gentle air whoosh peaking at its centre: noise through a sweeping band, panned with the move."""
    n = sec(dur)
    tt = np.arange(n) / SR
    u = tt / dur
    nz = RNG.standard_normal(n).astype(np.float32)
    y = np.zeros(n, np.float32)
    blocks = 40
    for k in range(blocks):
        a, z = k * n // blocks, (k + 1) * n // blocks
        q = (k + 0.5) / blocks
        fc = 350 + 2600 * np.sin(np.pi * q) ** 1.5
        y[a:z] = bp(nz[a:z], fc * 0.6, min(fc * 1.6, SR * 0.45))
    y = lp(y, 6000)
    e = (np.sin(np.pi * u) ** 2.2).astype(np.float32)
    pan = (u - 0.5) * 1.2 * pan_dir
    sig = y * e * soft
    return np.stack([sig * (1 - pan), sig * (1 + pan)], 1)


def transitions(total):
    """Soft whooshes on the scene changes only (line-particle cuts a little fuller than match cuts)."""
    bus = Bus(total)
    for name, s0, s1, fn in S.SCENES[1:]:
        if name not in S.TRANS:
            continue
        typ, d, kw = S.TRANS[name]
        if typ == "lines":
            dur = d + 0.35
            ang = kw.get("angle", 0) if isinstance(kw, dict) else 0
            bus.add(s0 - dur / 2, whoosh(dur, 1.0 if abs(ang) < 90 else -1.0, 1.0))
        else:
            bus.add(s0 - 0.22, whoosh(0.44, 1.0, 0.45))
    return room(bus.x, 0.2)


# ---------------------------------------------------------------- mix
def lufs(x):
    """Integrated loudness via ffmpeg ebur128 (stereo float32)."""
    p = subprocess.run(["ffmpeg", "-loglevel", "info", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                        "-af", "ebur128=framelog=quiet", "-f", "null", "-"], input=x.astype(np.float32).tobytes(),
                       capture_output=True)
    for ln in p.stderr.decode(errors="ignore").splitlines()[::-1]:
        if ln.strip().startswith("I:"):
            return float(ln.split()[1])
    return None


def load_timed(path, total):
    """A narration file that is already laid out on the film's timeline: decode, pad / trim to the film."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    out = np.zeros(total, np.float32)
    n = min(len(x), total)
    out[:n] = x[:n]
    return out


def build(bgm_path, out_mp3, narration=None, fx=True, music_lufs=-20.0, duck_depth=0.65):
    total = int(S.DURATION * SR)
    narr = load_timed(narration, total) if narration else A.load_narration(total)
    narr = np.stack([narr, narr], 1)
    music = load_bgm(bgm_path, total)
    tr = transitions(total) if fx else np.zeros_like(music)
    # level targets: voice -16 LUFS, music -20 LUFS before ducking (~14 dB under the voice while it speaks), effects sit just under the voice
    narr *= A.db(-16.0 - lufs(narr))
    music *= A.db(music_lufs - lufs(music))
    # sidechain: fast attack, slow release -> the music dips ~9 dB under the voice and swells in the pauses
    e = A.rms_env(narr[:, 0])
    e /= e.max() + 1e-9
    duck = (1 - duck_depth * np.clip(e * 3.0, 0, 1))[:, None]
    tr_duck = (1 - 0.4 * np.clip(e * 3.0, 0, 1))[:, None]
    if fx:
        tr *= np.abs(narr).max() * A.db(-15.0) / (np.abs(tr).max() + 1e-9)     # quiet: well under the voice
    mix = narr + music * duck + tr * tr_duck
    # loudness normalise for web (-14 LUFS) with a -1 dBFS ceiling (soft limiter)
    mix *= A.db(-14.0 - lufs(mix))
    ceil = A.db(-1.0)
    mix = np.where(np.abs(mix) > ceil * 0.8, np.sign(mix) * (ceil * 0.8 + (ceil * 0.2) *
                                                            np.tanh((np.abs(mix) - ceil * 0.8) / (ceil * 0.2))), mix)
    wav = out_mp3.replace(".mp3", ".wav")
    import wave
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "320k", out_mp3])
    print("final loudness %.1f LUFS, peak %.2f dBFS" % (lufs(mix), 20 * np.log10(np.abs(mix).max())))
    return out_mp3


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("bgm")
    ap.add_argument("out", nargs="?", default=os.path.join(A.HERE, "out", "axcore_audio_v6.mp3"))
    ap.add_argument("--narration", default=None, help="narration already timed to the film")
    ap.add_argument("--no-fx", action="store_true", help="no scene-change whooshes")
    ap.add_argument("--music", type=float, default=-20.0, help="music loudness (LUFS) before ducking")
    ap.add_argument("--duck", type=float, default=0.65, help="ducking depth under the voice (0..1)")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    print(build(a.bgm, a.out, a.narration, not a.no_fx, a.music, a.duck))
