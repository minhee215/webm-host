"""AXCORE promo film - soundtrack (v4).

Narration: the supplied read, with silence spliced in at scenes.PAUSES (each split falls inside a
pause of the original read), so the film breathes before the emphasised lines.

Score: a synthesized cinematic cue in D minor (Dm - Bb - F - C, 90 BPM) that resolves to D major on the
logo - string ensemble, low brass swells, a driving cello ostinato, taiko drums, bell motif - shaped to
the story (intro, build, ontology breakdown, second build, finale), with a room reverb and sidechain
ducking under the voice so the narration always sits on top. No transition sound effects.
"""
import os
import subprocess
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

import scenes as S

SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
NARRATION = os.path.join(HERE, "assets", "narration.mp3")
BPM = 90.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT

#            voicing (MIDI)                 bass
CHORDS = {"Dm": ([50, 57, 62, 65, 69], 38), "Bb": ([46, 53, 58, 62, 65], 34), "F": ([53, 60, 65, 69, 72], 41),
          "C": ([48, 55, 60, 64, 67], 36), "D": ([50, 57, 62, 66, 69, 74], 38)}
SEQ = ["Dm", "Bb", "F", "C"]


def C(name):
    return CHORDS[name]


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def sec(t):
    return int(round(t * SR))


# ---------------------------------------------------------------- timeline of the score (film time)
def T(key):
    return S.CUEN[key]


LOGO = T("L32") - 0.05            # final hit
FIN_LINES = [T("L28"), T("L29"), T("L30")]  # 더 빠른 판단 / 효율적인 실행 / 생산성


def chord_at(t):
    if t >= LOGO - 0.15:
        return "D"
    return SEQ[int(t / BAR) % 4]


def intensity(t):
    """0..1.3 arrangement curve: intro, build, ontology breakdown, second build, finale."""
    pts = [(0, 0.25), (6, 0.42), (14.1, 0.55), (28, 0.65), (37, 0.72), (57.8, 0.78), (63.3, 0.5), (69.5, 0.62),
           (71.2, 0.95), (74.3, 0.72), (86.5, 0.85), (99.9, 1.0), (107.0, 1.12), (112.2, 1.2), (113.2, 0.55),
           (LOGO, 0.6), (LOGO + 0.05, 1.3), (118.0, 0.8), (120.0, 0.0)]
    xs, ys = zip(*pts)
    return np.interp(t, xs, ys)


# ---------------------------------------------------------------- instruments
def saw(freq, n, phase=0.0):
    ph = (phase + np.cumsum(np.broadcast_to(freq, (n,)) / SR)) % 1.0
    return (2 * ph - 1).astype(np.float32)


def lp(x, fc, order=2):
    sos = butter(order, min(fc, SR * 0.45), "low", fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def hp(x, fc, order=2):
    sos = butter(order, fc, "high", fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def env(n, a, r, sustain=1.0):
    e = np.full(n, sustain, np.float32)
    na, nr = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if na:
        e[:na] = np.linspace(0, sustain, na) ** 1.6
    if nr:
        e[-nr:] *= np.linspace(1, 0, nr) ** 1.4
    return e


def strings(total, rng):
    """String ensemble: per bar, every chord tone as 5 detuned saws with slow vibrato, warm low-pass."""
    out = np.zeros((total, 2), np.float32)
    nbar = int(np.ceil(total / SR / BAR))
    for b in range(nbar):
        t0 = b * BAR
        name = chord_at(t0 + 0.01)
        if t0 < LOGO - 0.15 < t0 + BAR:   # split the bar at the logo: minor -> major
            spans = [(t0, LOGO - 0.15, chord_at(t0)), (LOGO - 0.15, total / SR, "D")]
        elif t0 >= LOGO - 0.15:
            continue
        else:
            spans = [(t0, t0 + BAR, name)]
        for (a, z, nm) in spans:
            i0 = sec(max(0.0, a - 0.35))
            n = min(sec(z - a + 0.9), total - i0)
            if n <= 0:
                continue
            notes, _ = C(nm)
            sig = np.zeros((n, 2), np.float32)
            tt = np.arange(n) / SR
            for j, m in enumerate(notes):
                for v, det in enumerate((-9, -4, 0, 5, 10)):
                    f = mtof(m) * 2 ** (det / 1200) * (1 + 0.0016 * np.sin(2 * np.pi * (4.6 + v * 0.3) * tt + v))
                    w = saw(f, n, rng.uniform())
                    pan = ((v - 2) / 2) * 0.55 + (j - 2) * 0.06
                    sig[:, 0] += w * (1 - pan) * 0.5
                    sig[:, 1] += w * (1 + pan) * 0.5
            sig *= (env(n, 0.55, 0.9) / (len(notes) * 5))[:, None]
            fc = 900 + 2600 * float(intensity(a + 0.5))
            for ch in range(2):
                sig[:, ch] = lp(sig[:, ch], fc, 2)
            out[i0:i0 + n] += sig
    return out


def high_strings(total, rng, t_on, t_off):
    """Octave-up violins doubling the top voices in the big sections."""
    out = np.zeros((total, 2), np.float32)
    for b in range(int(total / SR / BAR) + 1):
        t0 = b * BAR
        if not (t_on <= t0 < t_off) or t0 >= LOGO - 0.2:
            continue
        notes, _ = C(chord_at(t0 + 0.01))
        i0 = sec(t0 - 0.3)
        n = min(sec(BAR + 0.8), total - i0)
        tt = np.arange(n) / SR
        sig = np.zeros((n, 2), np.float32)
        for m in notes[-2:]:
            for v, det in enumerate((-7, 0, 7)):
                f = mtof(m + 12) * 2 ** (det / 1200) * (1 + 0.0025 * np.sin(2 * np.pi * 5.2 * tt + v))
                w = saw(f, n, rng.uniform())
                sig[:, 0] += w * (0.7 - 0.2 * v)
                sig[:, 1] += w * (0.3 + 0.2 * v)
        sig *= (env(n, 0.7, 0.9) / 6)[:, None]
        for ch in range(2):
            sig[:, ch] = lp(hp(sig[:, ch], 500), 5200)
        out[i0:i0 + n] += sig
    return out


def ostinato(total, spans):
    """Driving cello/bass 8th notes on the chord root (octave/fifth figure)."""
    out = np.zeros(total, np.float32)
    fig = [0, 0, 12, 0, 0, 7, 0, 12]
    step = BEAT / 2
    for s in range(int(total / SR / step)):
        t = s * step
        if not any(a <= t < b for a, b in spans) or t >= LOGO - 0.2:
            continue
        _, root = C(chord_at(t))
        m = root + 12 + fig[s % 8]
        n = sec(0.34)
        i0 = sec(t)
        if i0 + n > total:
            break
        tt = np.arange(n) / SR
        w = saw(mtof(m), n) * 0.6 + saw(mtof(m) * 1.003, n) * 0.4
        e = (1 - np.exp(-tt * 300)) * np.exp(-tt * 9.0)
        acc = 1.0 if s % 4 == 0 else 0.72
        out[i0:i0 + n] += w * e * acc
    out = lp(out, 950, 2)
    return np.stack([out * 0.9, out], 1)


def sub_bass(total):
    out = np.zeros(total, np.float32)
    for b in range(int(total / SR / BAR) + 1):
        t0 = b * BAR
        if t0 < 14.0 or (63.3 <= t0 < 69.5) or t0 >= LOGO - 0.2:
            continue
        _, root = C(chord_at(t0 + 0.01))
        i0, n = sec(t0), min(sec(BAR), total - sec(t0))
        if n <= 0:
            break
        tt = np.arange(n) / SR
        out[i0:i0 + n] += np.sin(2 * np.pi * mtof(root) * tt) * env(n, 0.08, 0.5)
    return np.stack([out, out], 1)


def brass(total, swells):
    """Low horns/trombones: root-fifth-octave saws with a filter swell (crescendo into the downbeat)."""
    out = np.zeros((total, 2), np.float32)
    for (t0, dur, nm, gain) in swells:
        notes, root = C(nm)
        i0 = sec(t0)
        n = min(sec(dur), total - i0)
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        sig = np.zeros(n, np.float32)
        for m in (root + 12, root + 19, root + 24, notes[2]):
            for det in (-6, 0, 6):
                sig += saw(mtof(m) * 2 ** (det / 1200), n)
        sig /= 12
        sw = np.clip(tt / (dur * 0.55), 0, 1) ** 1.5
        # block-wise filter sweep
        y = np.zeros(n, np.float32)
        blocks = 32
        for k in range(blocks):
            a, z = k * n // blocks, (k + 1) * n // blocks
            fc = 260 + 2100 * sw[min(a, n - 1)]
            bb, aa = butter(2, fc, "low", fs=SR)
            y[a:z] = lfilter(bb, aa, sig[a:z])
        e = env(n, dur * 0.45, dur * 0.4) * (0.35 + 0.65 * sw)
        y *= e * gain
        out[i0:i0 + n, 0] += y
        out[i0:i0 + n, 1] += y * 0.92
    return out


def taiko(total, hits, rng):
    out = np.zeros((total, 2), np.float32)
    for (t, g, pan) in hits:
        i0 = sec(t)
        n = min(sec(1.6), total - i0)
        if n <= 0 or i0 < 0:
            continue
        tt = np.arange(n) / SR
        f = 48 + 75 * np.exp(-tt * 28)
        body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5.5)
        skin = lp(rng.standard_normal(n).astype(np.float32), 1400) * np.exp(-tt * 40) * 0.8
        w = (body + skin) * g
        out[i0:i0 + n, 0] += w * (1 - pan)
        out[i0:i0 + n, 1] += w * (1 + pan)
    return out


def bells(total, notes_at):
    out = np.zeros((total, 2), np.float32)
    for (t, m, g) in notes_at:
        i0 = sec(t)
        n = min(sec(2.4), total - i0)
        if n <= 0:
            continue
        tt = np.arange(n) / SR
        f = mtof(m)
        w = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 3) +
             0.18 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt * 6)) * np.exp(-tt * 1.6) * g
        pan = ((m % 7) / 6 - 0.5) * 0.8
        out[i0:i0 + n, 0] += w * (1 - pan)
        out[i0:i0 + n, 1] += w * (1 + pan)
    return out


def swell_noise(total, t_end, dur, rng, gain=1.0):
    """Reverse-cymbal style swell that lands on a downbeat (musical, not a transition effect)."""
    out = np.zeros((total, 2), np.float32)
    i0 = sec(t_end - dur)
    n = sec(dur)
    if i0 < 0 or i0 + n > total:
        return out
    nz = hp(rng.standard_normal(n).astype(np.float32), 3500)
    e = (np.linspace(0, 1, n) ** 3.2).astype(np.float32)
    out[i0:i0 + n, 0] = nz * e * gain
    out[i0:i0 + n, 1] = hp(rng.standard_normal(n).astype(np.float32), 3500) * e * gain
    return out


def reverb(x, seconds=2.2, mix=0.28, rng=None):
    n = sec(seconds)
    tt = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(x.shape[1]):
        ir = rng.standard_normal(n).astype(np.float32) * np.exp(-tt * 3.1).astype(np.float32)
        ir = lp(ir, 5200)
        ir[:sec(0.012)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = fftconvolve(x[:, ch], ir)[:len(x)].astype(np.float32)
    return x * (1 - mix) + out * mix * 1.6


# ---------------------------------------------------------------- narration with pauses
def load_narration(total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", NARRATION, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    out = np.zeros(total, np.float32)
    cuts = [sec(p - S.AUDIO_OFFSET) for p, _ in S.PAUSES]
    bounds = [0] + cuts + [len(x)]
    dst = sec(S.AUDIO_OFFSET)
    for j in range(len(bounds) - 1):
        a, z = bounds[j], bounds[j + 1]
        seg = x[a:z]
        n = min(len(seg), total - dst)
        if n > 0:
            out[dst:dst + n] = seg[:n]
        dst += len(seg) + (sec(S.PAUSES[j][1]) if j < len(S.PAUSES) else 0)
    return out


def rms_env(x, win=0.06):
    n = sec(win)
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, mode="same"))
    att = np.exp(-1 / (0.02 * SR))
    rel = np.exp(-1 / (0.45 * SR))
    # peak-hold style follower: fast attack, slow release (so the bed does not pump between words)
    from scipy.signal import lfilter as lf
    fast = lf([1 - att], [1, -att], e)
    slow = lf([1 - rel], [1, -rel], e)
    return np.maximum(fast, slow).astype(np.float32)


def db(x):
    return 10 ** (x / 20)


def score(total):
    rng = np.random.default_rng(5)
    tl = np.arange(total) / SR
    m = strings(total, rng) * db(-4)
    m += high_strings(total, rng, 99.9, 113.0) * db(-11)
    m += high_strings(total, rng, 69.5, 74.3) * db(-14)
    m += ostinato(total, [(14.1, 63.3), (69.6, 113.0)]) * db(-12)
    m += sub_bass(total) * db(-13)
    # brass swells into the structural downbeats
    swells = [(10.5, 3.6, "Dm", 0.55), (24.5, 3.5, "F", 0.5), (34.0, 3.0, "Dm", 0.5), (54.0, 3.8, "Bb", 0.6),
              (68.6, 2.7, "Dm", 0.7), (83.0, 3.5, "Bb", 0.65), (96.5, 3.4, "F", 0.75), (104.0, 3.0, "C", 0.85)]
    for i, t in enumerate(FIN_LINES):
        swells.append((t - 0.9, 1.6, ["Dm", "Bb", "F"][i], 0.9))
    swells.append((LOGO - 0.02, 4.6, "D", 1.15))
    m += brass(total, swells) * db(-7)
    # taiko: groove in the build sections, accents on the finale lines and the logo
    hits = []
    for b in range(int(total / SR / BAR) + 1):
        t0 = b * BAR
        sect = (18.2 <= t0 < 63.3) or (78.8 <= t0 < 112.5)
        if not sect:
            continue
        big = t0 >= 99.9
        for (bt, g, pan) in ((0, 1.0, 0.0), (1.5, 0.45, -0.3), (2, 0.75, 0.2), (3.5, 0.4, 0.3)):
            hits.append((t0 + bt * BEAT, g * (1.15 if big else 0.85), pan))
        if (b % 4) == 3:
            for k in range(4):
                hits.append((t0 + (3 + k * 0.25) * BEAT, 0.35 + 0.12 * k, (k - 1.5) * 0.25))
    for t in FIN_LINES:
        hits.append((t - 0.04, 1.5, 0.0))
    hits += [(71.2, 1.3, 0.0), (107.0, 1.4, 0.0), (LOGO, 2.2, 0.0), (LOGO + 0.33, 0.9, -0.2)]
    m += taiko(total, hits, rng) * db(-9)
    # bell motif: intro and ontology (sparkle), last echo after the logo
    motif = [62, 65, 69, 72, 69, 65]
    notes = []
    for k in range(int(13.6 / (BEAT * 1.5))):
        notes.append((0.6 + k * BEAT * 1.5, motif[k % 6] + 12, 0.5 if k % 6 == 0 else 0.32))
    for k in range(int(6.0 / (BEAT * 0.75))):
        notes.append((63.4 + k * BEAT * 0.75, motif[k % 6] + 12, 0.3))
    for k, mm in enumerate((74, 78, 81, 86)):
        notes.append((LOGO + 0.6 + k * 0.28, mm, 0.35))
    m += bells(total, notes) * db(-17)
    m += swell_noise(total, 71.2, 2.4, rng, 0.6) * db(-24)
    m += swell_noise(total, 107.0, 2.2, rng, 0.7) * db(-24)
    m += swell_noise(total, LOGO, 2.6, rng, 1.0) * db(-21)
    m = reverb(m, 2.4, 0.3, rng)
    m *= intensity(tl)[:, None].astype(np.float32)
    # gentle bus glue (soft clip)
    m = np.tanh(m * 1.4) / 1.4
    return m


def build_mix(path):
    total = int(S.DURATION * SR)
    narr = load_narration(total)
    narr *= db(-2.5) / (np.abs(narr).max() + 1e-9)
    music = score(total)
    music *= db(-3.0) / (np.abs(music).max() + 1e-9)
    # sidechain: the bed dips ~9 dB under the voice (voice stays ~12 dB above the music) and recovers between sentences
    e = rms_env(narr)
    e /= e.max() + 1e-9
    duck = (1 - 0.66 * np.clip(e * 3.2, 0, 1))[:, None]
    bed = music * duck * db(-7.0)
    mix = bed + narr[:, None]
    mix *= db(-1.0) / np.abs(mix).max()
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
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
