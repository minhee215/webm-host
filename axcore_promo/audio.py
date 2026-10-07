"""AXCORE promo film - soundtrack.

Synthesizes a restrained, quietly optimistic music bed (pad, plucked arpeggio,
sub, soft shaker), transition whooshes and a logo impact, then mixes them under
the narration (delayed by the film pre-roll) with sidechain ducking.
"""
import os
import subprocess

import numpy as np

import scenes as S

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
NARRATION = os.path.join(HERE, "assets", "narration.mp3")
BPM = 92.0
BAR = 4 * 60.0 / BPM

# D major: Dmaj9 - Bm11 - Gmaj7(#11) - Asus4 -> A (two bars each)
PROG = [
    [50, 57, 61, 64, 66],   # D A C# E F#
    [47, 54, 57, 61, 64],   # B F# A C# E
    [43, 50, 54, 57, 61],   # G D F# A C#
    [45, 52, 57, 59, 64],   # A E A B E
]


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a, r, sr=SR):
    e = np.ones(n, np.float32)
    na, nr = min(int(a * sr), n // 2), min(int(r * sr), n // 2)
    if na:
        e[:na] = np.linspace(0, 1, na) ** 2
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    from scipy.signal import lfilter
    return lfilter([1 - a], [1, -a], x).astype(np.float32)


def pad(total):
    out = np.zeros((total, 2), np.float32)
    seg = 2 * BAR
    n_seg = int(np.ceil(total / SR / seg)) + 1
    rng = np.random.default_rng(7)
    for k in range(n_seg):
        t0 = k * seg - 0.6
        dur = seg + 1.2
        i0 = int(max(0, t0) * SR)
        n = int(dur * SR)
        if i0 >= total:
            break
        n = min(n, total - i0)
        t = np.arange(n) / SR
        chord = PROG[k % 4]
        sig = np.zeros((n, 2), np.float32)
        for note in chord:
            for v, det in enumerate((-5, 0, 6)):
                f = mtof(note) * 2 ** (det / 1200)
                ph = rng.uniform(0, 2 * np.pi)
                w = np.zeros(n, np.float32)
                for h in range(1, 7):
                    w += (np.sin(2 * np.pi * f * h * t + ph * h) / h * np.exp(-0.35 * h)).astype(np.float32)
                pan = (v - 1) * 0.45
                sig[:, 0] += w * (1 - pan) * 0.5
                sig[:, 1] += w * (1 + pan) * 0.5
        e = env_adsr(n, 0.9, 1.1)
        sig *= e[:, None] / (len(chord) * 3)
        out[i0:i0 + n] += sig
    for ch in range(2):
        out[:, ch] = onepole_lp(out[:, ch], 1800)
    lfo = 1 + 0.08 * np.sin(2 * np.pi * 0.11 * np.arange(total) / SR)
    return out * lfo[:, None].astype(np.float32)


def pluck_arp(total, t_on, t_off_list):
    out = np.zeros((total, 2), np.float32)
    step = 60.0 / BPM / 2
    pattern = [0, 2, 4, 3, 1, 4, 2, 3]
    nsteps = int(total / SR / step)
    dl = int(step * 1.5 * SR)
    for s in range(nsteps):
        t = s * step
        if t < t_on or any(a <= t < b for a, b in t_off_list):
            continue
        chord = PROG[int(t / (2 * BAR)) % 4]
        note = chord[pattern[s % 8]] + 12
        f = mtof(note)
        n = int(0.9 * SR)
        i0 = int(t * SR)
        if i0 + n > total:
            break
        tt = np.arange(n) / SR
        w = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 6.5)
        w *= 0.9 + 0.1 * (s % 2)
        pan = 0.3 * np.sin(s * 0.7)
        out[i0:i0 + n, 0] += w * (1 - pan) * 0.5
        out[i0:i0 + n, 1] += w * (1 + pan) * 0.5
    # ping-pong delay
    d = np.zeros_like(out)
    d[dl:, 0] += out[:-dl, 1] * 0.35
    d[2 * dl:, 1] += out[:-2 * dl, 0] * 0.25
    out += d
    for ch in range(2):
        out[:, ch] = onepole_lp(out[:, ch], 4200)
    return out


def sub(total, t_on, t_off_list):
    out = np.zeros(total, np.float32)
    seg = 2 * BAR
    for k in range(int(total / SR / seg) + 1):
        t0 = k * seg
        if t0 < t_on or any(a <= t0 < b for a, b in t_off_list):
            continue
        f = mtof(PROG[k % 4][0] - 12)
        n = min(int(seg * SR), total - int(t0 * SR))
        if n <= 0:
            break
        tt = np.arange(n) / SR
        out[int(t0 * SR):int(t0 * SR) + n] += (np.sin(2 * np.pi * f * tt) * env_adsr(n, 0.25, 0.6)).astype(np.float32)
    return np.stack([out, out], 1)


def shaker(total, t_on, t_off):
    out = np.zeros((total, 2), np.float32)
    rng = np.random.default_rng(11)
    step = 60.0 / BPM / 4
    for s in range(int(total / SR / step)):
        t = s * step
        if not (t_on <= t < t_off):
            continue
        n = int(0.07 * SR)
        i0 = int(t * SR)
        nz = rng.standard_normal(n).astype(np.float32)
        nz = np.diff(np.concatenate([[0], nz]))  # crude high-pass
        acc = 1.0 if s % 4 == 2 else 0.45
        e = np.exp(-np.arange(n) / SR * 60)
        pan = 0.25 if s % 2 else -0.25
        out[i0:i0 + n, 0] += nz * e * acc * (1 - pan)
        out[i0:i0 + n, 1] += nz * e * acc * (1 + pan)
    return out


def whoosh(total, t_center, dur=0.9, gain=1.0, rng=None):
    out = np.zeros((total, 2), np.float32)
    n = int(dur * SR)
    i0 = int((t_center - dur * 0.6) * SR)
    if i0 < 0 or i0 + n > total:
        return out
    nz = rng.standard_normal(n).astype(np.float32)
    tt = np.linspace(0, 1, n)
    e = (np.sin(np.pi * tt ** 0.8) ** 2).astype(np.float32)
    # sweeping band: filter cutoff rises then falls
    from scipy.signal import lfilter
    y = np.zeros(n, np.float32)
    blocks = 24
    for b in range(blocks):
        a0, a1 = b * n // blocks, (b + 1) * n // blocks
        fc = 400 + 5200 * np.sin(np.pi * (b + 0.5) / blocks)
        a = np.exp(-2 * np.pi * fc / SR)
        y[a0:a1] = lfilter([1 - a], [1, -a], nz[a0:a1])
    y = y - onepole_lp(y, 180)
    pan = np.linspace(-0.6, 0.6, n)
    out[i0:i0 + n, 0] = y * e * (1 - pan) * gain
    out[i0:i0 + n, 1] = y * e * (1 + pan) * gain
    return out


def impact(total, t):
    out = np.zeros((total, 2), np.float32)
    n = int(4.0 * SR)
    i0 = int(t * SR)
    n = min(n, total - i0)
    tt = np.arange(n) / SR
    f = 55 * np.exp(-tt * 1.4) + 38
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 1.6)
    shim = np.zeros(n)
    for m in (86, 90, 93, 97):
        shim += np.sin(2 * np.pi * mtof(m) * tt) * np.exp(-tt * 1.2) * 0.18
    out[i0:i0 + n, 0] = boom * 0.9 + shim * 0.8
    out[i0:i0 + n, 1] = boom * 0.9 + shim * 1.0
    return out


def tick(total, t, gain=0.5):
    out = np.zeros((total, 2), np.float32)
    n = int(0.05 * SR)
    i0 = int(t * SR)
    if i0 + n > total:
        return out
    tt = np.arange(n) / SR
    w = np.sin(2 * np.pi * 2400 * tt) * np.exp(-tt * 120) * gain
    out[i0:i0 + n] += w[:, None]
    return out


def load_narration(total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", NARRATION, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    out = np.zeros(total, np.float32)
    i0 = int(S.AUDIO_OFFSET * SR)
    n = min(len(x), total - i0)
    out[i0:i0 + n] = x[:n]
    return out


def rms_env(x, win=0.08):
    n = int(win * SR)
    k = np.ones(n) / n
    e = np.sqrt(np.convolve(x ** 2, k, mode="same"))
    # smooth release
    from scipy.signal import lfilter
    a = np.exp(-1 / (0.35 * SR))
    return lfilter([1 - a], [1, -a], e).astype(np.float32)


def db(x):
    return 10 ** (x / 20)


def build_mix(path):
    total = int(S.DURATION * SR)
    rng = np.random.default_rng(3)
    narr = load_narration(total)
    narr *= db(-3) / (np.abs(narr).max() + 1e-9)

    tl = np.arange(total) / SR
    music = pad(total) * db(-5)
    arp_off = [(58.0, 62.6), (102.4, 120)]
    music += pluck_arp(total, 13.1, arp_off) * db(-12)
    music += sub(total, 17.2, [(102.4, 120)]) * db(-11)
    music += shaker(total, 40.6, 97.4) * db(-30)
    music += shaker(total, 97.4, 102.4) * db(-25)
    # arrangement dynamics
    dyn = np.interp(tl, [0, 3, 13, 17, 40, 58, 62.6, 68, 91, 97.4, 102.4, 104.6, 107.6, 109.5],
                    [0.0, 0.7, 0.8, 0.9, 1.0, 0.9, 1.1, 1.0, 1.05, 1.15, 0.75, 1.3, 1.1, 0.0])
    music *= dyn[:, None].astype(np.float32)

    sfx = np.zeros((total, 2), np.float32)
    for name, t0, t1, fn in S.SCENES[1:]:
        typ = S.TRANS.get(name, ("cut",))[0]
        g = {"streak": 0.9, "zoom": 0.7, "whip": 1.0, "blocks": 0.6, "expand": 0.6, "shrink": 0.6}.get(typ, 0.35)
        sfx += whoosh(total, t0, 0.7 if typ == "whip" else 1.0, g, rng)
    for cue in ("ERP", "MES", "CRM", "GMAIL", "SLACK", "NOTION", "EQUIP", "MATER", "PROC", "PROD", "PEOPLE", "TASK",
                "L21", "CAUSE", "CTX"):
        sfx += tick(total, S.CUE[cue], 0.35)
    sfx += impact(total, S.CUE["L32"] - 0.12)
    sfx *= db(-17)

    # sidechain duck music + sfx under the voice
    env = rms_env(narr)
    env /= env.max() + 1e-9
    duck = (1 - 0.5 * np.clip(env * 3, 0, 1))[:, None]
    bed = (music + sfx * 0.8) * duck

    mix = bed + narr[:, None] * np.array([1.0, 1.0], np.float32)
    peak = np.abs(mix).max()
    mix *= db(-1.0) / peak
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    out = os.path.join(HERE, "out", "mix.wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(build_mix(out))
