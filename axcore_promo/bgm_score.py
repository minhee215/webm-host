"""AXCORE promo - original score, composed to the cut (the client's 118.66 s edit with narration).

The music is synthesised here note by note on a tempo map built from the picture, so it is written to the film's
length (no stock track cut to fit):
  - free-time intro on the live-action cuts (2 / 4 / 6 s), the pulse starts with the tile grid (8.68 s)
  - each section has its own constant tempo (110-124 BPM) whose bar lines land on that section's main motion
    beats: 16.60 navy map, 29.40 AXpoint, 43.96 ceiling, 57.97 OCR, 64.06 ontology (70.55 title punch on a
    downbeat), 85.88 white flash, 91.97 robot cut, 96.55 "실행" snap, 106.56 flash into the finale, 115.20 logo
  - risers / reverse swells lead into the big transitions (always in narration gaps), soft impacts land on them
  - the energy follows the film: ambient intro -> light pulse -> groove under the product UI -> deeper ontology
    -> driving montage -> broad, lifted finale -> resolved logo chord
The narration is never covered: the music ducks under the voice (look-ahead, the voice band more than the lows)
and comes back up in the pauses.

Usage: python3 bgm_score.py <narration/video file> <out dir>
Writes AXCORE_BGM.wav (the ducked bed as mixed), AXCORE_BGM_full.wav (no ducking), AXCORE_mix.wav (+ mp3s).
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
from pedalboard import (Chorus, Compressor, Delay, Distortion, Gain, HighpassFilter, LadderFilter, Limiter,
                        LowpassFilter, Pedalboard, Reverb)
from scipy.signal import butter, sosfilt

SR = 48000
MUSIC_LUFS = -23.5
DUR = 118.66
N = int(round((DUR + 0.0) * SR))
RNG = np.random.default_rng(7)


def S(t):
    return int(round(t * SR))


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


# ---------------------------------------------------------------- tempo map
# (start, end, beats): constant tempo inside a section, the section's first beat on its start
SECTIONS = [(8.68, 16.60, 16), (16.60, 29.40, 26), (29.40, 43.96, 28), (43.96, 57.97, 28), (57.97, 64.06, 12),
            (64.06, 85.88, 44), (85.88, 96.55, 21), (96.55, 106.56, 20), (106.56, 115.20, 16)]


def beats(i):
    a, b, n = SECTIONS[i]
    p = (b - a) / n
    return [a + k * p for k in range(n)], p


# ---------------------------------------------------------------- oscillators
TAB = 4096


def _tables():
    """Band-limited saw / square tables per octave (harmonics kept under 18 kHz)."""
    out = {}
    ph = np.arange(TAB) / TAB
    for octv in range(0, 12):
        f0 = 16.35 * 2 ** octv
        kmax = max(1, int(18000 / (f0 * 2)))
        saw = np.zeros(TAB)
        sq = np.zeros(TAB)
        for k in range(1, min(kmax, 400) + 1):
            saw += np.sin(2 * np.pi * k * ph) / k
            if k % 2:
                sq += np.sin(2 * np.pi * k * ph) / k
        out[("saw", octv)] = (saw / np.abs(saw).max()).astype(np.float32)
        out[("sq", octv)] = (sq / np.abs(sq).max()).astype(np.float32)
    return out


TABLES = _tables()


def osc(kind, f, n, phase0=None):
    """f: scalar or per-sample array (Hz)."""
    f = np.broadcast_to(np.asarray(f, np.float64), (n,))
    ph0 = RNG.random() if phase0 is None else phase0
    ph = (ph0 + np.cumsum(f) / SR) % 1.0
    if kind == "sine":
        return np.sin(2 * np.pi * ph).astype(np.float32)
    if kind == "tri":
        return (2 * np.abs(2 * ph - 1) - 1).astype(np.float32)
    octv = int(np.clip(np.log2(max(float(f.max()), 17) / 16.35), 0, 11))
    tab = TABLES[(kind, octv)]
    idx = ph * TAB
    i0 = idx.astype(np.int64) % TAB
    fr = (idx - np.floor(idx)).astype(np.float32)
    return tab[i0] * (1 - fr) + tab[(i0 + 1) % TAB] * fr


def env_adsr(n, a, d, s, r, hold):
    """Attack/decay/sustain for `hold` s, then release r (n covers hold + r)."""
    t = np.arange(n) / SR
    e = np.where(t < a, t / max(a, 1e-4), s + (1 - s) * np.exp(-(t - a) / max(d, 1e-4)))
    rel = np.clip((t - hold) / max(r, 1e-4), 0, None)
    e = e * np.where(t > hold, np.exp(-rel * 5.0), 1.0)
    return e.astype(np.float32)


def add(buf, x, t, pan=0.0, g=1.0):
    """Add mono x (or stereo (n,2)) at time t with constant-power pan."""
    i = S(t)
    if i >= len(buf):
        return
    if x.ndim == 1:
        l, r = math.cos((pan + 1) * math.pi / 4), math.sin((pan + 1) * math.pi / 4)
        x = np.stack([x * l, x * r], 1)
    j = min(len(buf), i + len(x))
    if i < 0:
        x, i = x[-i:], 0
        j = min(len(buf), len(x))
    buf[i:j] += g * x[:j - i]


def stereo_buf():
    return np.zeros((N + S(4), 2), np.float32)


def bandpass(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)


def highpass(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x).astype(np.float32)


def lowpass(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x).astype(np.float32)


def fx(buf, board):
    return board(buf.T.copy(), SR).T.astype(np.float32)


def automate_lpf(buf, curve, res=0.15, drive=1.0, block=1024):
    """Ladder low-pass with its cutoff following curve(t) (Hz), processed in blocks with state kept."""
    lf = LadderFilter(mode=LadderFilter.Mode.LPF24, cutoff_hz=1000, resonance=res, drive=drive)
    board = Pedalboard([lf])
    out = np.zeros_like(buf)
    for i in range(0, len(buf), block):
        lf.cutoff_hz = float(np.clip(curve((i + block / 2) / SR), 60, 19000))
        out[i:i + block] = board(buf[i:i + block].T.copy(), SR, reset=False).T
    return out


def smooth_curve(points):
    """Piecewise (cosine-eased) curve through (t, value) points."""
    pts = sorted(points)

    def f(t):
        if t <= pts[0][0]:
            return pts[0][1]
        for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
            if t <= t1:
                q = (t - t0) / max(t1 - t0, 1e-6)
                q = 0.5 - 0.5 * math.cos(math.pi * q)
                return v0 + (v1 - v0) * q
        return pts[-1][1]
    return f


# ---------------------------------------------------------------- harmony
CH = {
    "Dm9": (38, [50, 53, 57, 60, 64]), "Bbmaj9": (34, [46, 53, 57, 60, 62]), "Fmaj9": (41, [53, 57, 60, 64, 67]),
    "Cadd9": (36, [48, 55, 62, 64, 67]), "Gm9": (43, [55, 58, 62, 65, 69]), "Asus": (45, [57, 62, 64, 67, 69]),
    "C69": (36, [48, 55, 57, 62, 64]), "Am7": (45, [57, 60, 64, 67, 71]),
}
# (time, chord) - chord changes, written on the sections' bar lines
CHORDS = []


def bar_times(i, beats_per_bar=4):
    b, p = beats(i)
    return [b[k] for k in range(0, len(b), beats_per_bar)], p


def plan_harmony():
    C = [(0.0, "Dm9")]
    seq = {0: ["Dm9", "Bbmaj9", "Fmaj9", "Cadd9"],
           1: ["Dm9", "Bbmaj9", "Fmaj9", "Cadd9", "Dm9", "Bbmaj9", "Cadd9"],
           2: ["Fmaj9", "Cadd9", "Dm9", "Bbmaj9", "Fmaj9", "Cadd9", "Dm9"],
           3: ["Gm9", "Bbmaj9", "Dm9", "Cadd9", "Gm9", "Bbmaj9", "Cadd9"],
           4: ["Dm9", "Bbmaj9", "Cadd9"],
           5: ["Dm9", "Dm9", "Bbmaj9", "Fmaj9", "Fmaj9", "Gm9", "Bbmaj9", "Dm9", "Bbmaj9", "Cadd9", "Asus"],
           6: ["Dm9", "Bbmaj9", "Fmaj9", "Cadd9", "Dm9", "Bbmaj9"],
           7: ["Bbmaj9", "Cadd9", "Dm9", "Fmaj9", "Asus"],
           8: ["Bbmaj9", "C69", "Dm9", "Cadd9"]}
    for i in range(len(SECTIONS)):
        bt, p = bar_times(i)
        for k, t in enumerate(bt):
            C.append((t, seq[i][min(k, len(seq[i]) - 1)]))
    C.append((95.30, "Asus"))            # the break before "실행"
    C.append((115.20, "Fmaj9"))          # the logo: resolved, lifted
    C.sort()
    return C


def chord_at(t):
    c = CHORDS[0][1]
    for tt, name in CHORDS:
        if tt <= t + 1e-6:
            c = name
    return c


# ---------------------------------------------------------------- instruments
def pad_layer():
    buf = stereo_buf()
    for (t0, name), (t1, _) in zip(CHORDS, CHORDS[1:] + [(DUR + 2, None)]):
        root, notes = CH[name]
        hold = t1 - t0
        n = S(hold + 2.2)
        e = env_adsr(n, 0.9, 1.5, 0.85, 2.0, hold)
        for m in notes:
            for det, pan in ((-9, -0.7), (0, 0.0), (9, 0.7)):
                x = osc("saw", hz(m) * 2 ** (det / 1200), n) * e
                add(buf, x, t0, pan, 0.045)
        add(buf, osc("sine", hz(root + 12), n) * e, t0, 0, 0.10)
    cut = smooth_curve([(0, 380), (6.0, 700), (8.6, 1100), (16.6, 1500), (29.4, 1900), (43.9, 1500), (50.4, 2300),
                        (64.0, 1300), (70.5, 2800), (75.5, 1200), (85.8, 2400), (95.3, 700), (96.6, 2600),
                        (106.5, 4200), (115.2, 3200), (118.66, 1800)])
    buf = automate_lpf(buf, cut, res=0.12)
    return fx(buf, Pedalboard([Chorus(rate_hz=0.25, depth=0.25, mix=0.35),
                               Reverb(room_size=0.9, damping=0.5, wet_level=0.45, dry_level=0.7, width=1.0)]))


def pluck(m, dur=0.45, bright=1.0):
    n = S(dur)
    t = np.arange(n) / SR
    f = hz(m)
    x = np.zeros(n, np.float32)
    for k in range(1, 18):
        if f * k > 16000:
            break
        x += (np.sin(2 * np.pi * f * k * t + RNG.random()) / k * np.exp(-t * (4 + k * 2.4 / bright))).astype(np.float32)
    att = np.clip(t / 0.003, 0, 1)
    return (x * att).astype(np.float32)


def bell(m, dur=2.0):
    n = S(dur)
    t = np.arange(n) / SR
    f = hz(m)
    idx = 2.2 * np.exp(-t * 3.0)
    x = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * 3.5 * t)) * np.exp(-t * 1.6)
    x += 0.3 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 2.5)
    return (x * np.clip(t / 0.002, 0, 1)).astype(np.float32)


ARP_PATTERNS = {8: [0, 2, 1, 3, 2, 4, 3, 1], 16: [0, 2, 4, 2, 1, 3, 4, 3, 0, 2, 4, 2, 1, 3, 2, 4]}


def arp_layer():
    """Plucked arpeggios on the grid: 8ths where the narration is dense, 16ths in the drives."""
    buf = stereo_buf()
    plan = {0: (8, 0.55, 1.0), 1: (8, 0.65, 1.1), 2: (8, 0.5, 1.4), 3: (8, 0.6, 1.2), 4: (16, 0.55, 1.2),
            5: (8, 0.6, 1.0), 6: (16, 0.6, 1.3), 7: (16, 0.75, 1.5), 8: (8, 0.7, 1.6)}
    for i in range(len(SECTIONS)):
        sub, g, bright = plan[i]
        b, p = beats(i)
        step = p * 4 / sub
        a, e, _ = SECTIONS[i]
        k = 0
        t = a
        while t < e - 1e-6:
            if i == 6 and 95.30 <= t < 96.55:                 # the break before the snap
                t += step
                k += 1
                continue
            name = chord_at(t)
            notes = CH[name][1]
            m = notes[ARP_PATTERNS[sub][k % sub] % len(notes)] + 12
            acc = 1.0 if k % (sub // 4) == 0 else 0.7
            # the first bar of a section eases in
            fade = min(1.0, 0.35 + (t - a) / (4 * p) * 0.65)
            add(buf, pluck(m, 0.5, bright), t, 0.35 * math.sin(k * 1.3), g * acc * fade * 0.16)
            t += step
            k += 1
    # the intro: a few soft plucks on the live-action cuts
    for t, m in ((2.0, 69), (4.0, 72), (6.0, 76)):
        add(buf, pluck(m, 1.2, 0.8), t, 0.0, 0.10)
    return fx(buf, Pedalboard([HighpassFilter(180), Delay(delay_seconds=0.375 * 0.5, feedback=0.35, mix=0.25),
                               Reverb(room_size=0.7, wet_level=0.3, dry_level=0.8, width=1.0)]))


def bell_layer():
    """Glassy accents: the product UI (AXpoint) and the finale; a motif on the logo."""
    buf = stereo_buf()
    marks = [(29.40, 76), (37.20, 79), (39.87, 81), (70.55, 81), (108.05, 74), (109.75, 76), (112.10, 79),
             (115.20, 81), (115.20 + 0.27, 84), (115.20 + 0.54, 88)]
    for t, m in marks:
        add(buf, bell(m, 2.5), t, 0.2 * math.sin(t), 0.11)
    b, p = beats(2)                                   # a light bell figure under the bright UI section
    for k in range(0, len(b), 2):
        name = chord_at(b[k])
        add(buf, bell(CH[name][1][(k // 2) % 5] + 24, 1.2), b[k] + p, 0.5 * math.sin(k), 0.035)
    return fx(buf, Pedalboard([Delay(delay_seconds=0.26, feedback=0.3, mix=0.25),
                               Reverb(room_size=0.95, wet_level=0.5, dry_level=0.6, width=1.0)]))


def bass_layer():
    buf = stereo_buf()
    plan = {0: None, 1: "8", 2: "long", 3: "8", 4: "8s", 5: "8", 6: "8s", 7: "16", 8: "long"}
    for i in range(len(SECTIONS)):
        kind = plan[i]
        if kind is None:
            continue
        b, p = beats(i)
        a, e, _ = SECTIONS[i]
        if kind == "long":
            for t in b[::4]:
                root = CH[chord_at(t)][0]
                n = S(p * 4 + 0.3)
                x = (osc("sine", hz(root), n) + 0.25 * osc("tri", hz(root + 12), n)) * env_adsr(n, 0.02, 0.6, 0.8, 0.3, p * 4)
                add(buf, x, t, 0, 0.30)
            continue
        sub = {"8": 2, "8s": 2, "16": 4}[kind]
        step = p / sub
        t, k = a, 0
        while t < e - 1e-6:
            if i == 6 and 95.30 <= t < 96.55:
                t += step
                k += 1
                continue
            if kind == "8s" and k % 8 in (3, 6):                # syncopation
                t += step
                k += 1
                continue
            root = CH[chord_at(t)][0]
            n = S(step * 0.95)
            x = (osc("sine", hz(root), n) + 0.3 * osc("saw", hz(root), n)) * env_adsr(n, 0.004, 0.12, 0.55, 0.03, step * 0.85)
            add(buf, x, t, 0, 0.22 * (1.0 if k % sub == 0 else 0.75))
            t += step
            k += 1
    buf = fx(buf, Pedalboard([LowpassFilter(900), Distortion(drive_db=6), Gain(-6)]))
    return buf


def kick(g=1.0):
    n = S(0.5)
    t = np.arange(n) / SR
    f = 45 + 90 * np.exp(-t * 32)
    ph = np.cumsum(f) / SR
    x = np.sin(2 * np.pi * ph) * np.exp(-t * 7.0)
    click = highpass(RNG.standard_normal(n).astype(np.float32), 2500) * np.exp(-t * 300) * 0.25
    return ((x + click) * g).astype(np.float32)


def hat(open_=False):
    n = S(0.25 if open_ else 0.06)
    t = np.arange(n) / SR
    x = highpass(RNG.standard_normal(n).astype(np.float32), 7500, 4) * np.exp(-t * (14 if open_ else 70))
    return x.astype(np.float32)


def clap():
    n = S(0.4)
    t = np.arange(n) / SR
    noise = bandpass(RNG.standard_normal(n).astype(np.float32), 900, 4000)
    e = np.zeros(n)
    for o in (0.0, 0.011, 0.022):
        e += np.where(t >= o, np.exp(-(t - o) * 90), 0)
    e += np.exp(-t * 12) * 0.35
    return (noise * e).astype(np.float32)


def drums_layer():
    """Soft, never in the way: half-time kicks in the narration-heavy parts, four-on-the-floor in the drives."""
    kb, hb, cb = stereo_buf(), stereo_buf(), stereo_buf()
    plan = {0: (None, "16s", None), 1: ("half", "off", "3x2"), 2: ("half", "off", None), 3: ("half", "off8", "3x2"),
            4: ("four", "16", "24"), 5: ("half", "off", None), 6: ("four", "16", "24"), 7: ("four", "16", "24"),
            8: ("one", "off", "3x2")}
    sidechain = []
    for i in range(len(SECTIONS)):
        kp, hp, cp = plan[i]
        b, p = beats(i)
        for k, t in enumerate(b):
            if i == 6 and 95.30 <= t < 96.55:
                continue
            if i == 5 and 70.55 <= t < 72.6:                  # the ontology title breathes
                continue
            pos = k % 4
            if kp == "four" or (kp == "half" and pos in (0, 2)) or (kp == "one" and pos == 0):
                add(kb, kick(), t, 0, 0.55 if pos == 0 else 0.45)
                sidechain.append(t)
            if cp == "24" and pos in (1, 3):
                add(cb, clap(), t, 0.05, 0.16)
            if cp == "3x2" and pos == 2 and (k // 4) % 2 == 1:
                add(cb, clap(), t, 0.05, 0.12)
            if hp in ("16", "16s"):
                for s_ in range(4):
                    g = (0.10 if s_ == 2 else 0.05) * (0.6 if hp == "16s" else 1.0)
                    add(hb, hat(), t + s_ * p / 4, 0.3 if s_ % 2 else -0.3, g)
            elif hp == "off":
                add(hb, hat(), t + p / 2, 0.25, 0.09)
            elif hp == "off8":
                add(hb, hat(open_=pos == 3), t + p / 2, 0.25, 0.08)
    kb = fx(kb, Pedalboard([LowpassFilter(6000), Compressor(threshold_db=-14, ratio=3)]))
    hb = fx(hb, Pedalboard([Reverb(room_size=0.4, wet_level=0.15, dry_level=0.9)]))
    cb = fx(cb, Pedalboard([Reverb(room_size=0.75, wet_level=0.35, dry_level=0.7)]))
    return kb, hb, cb, sidechain


def riser(dur, peak):
    """Noise through a low-pass sweeping up (filter state kept, no block clicks) plus a rising tone."""
    n = S(dur)
    t = np.arange(n) / SR
    q = t / dur
    noise = highpass(RNG.standard_normal(n).astype(np.float32), 250)
    st = np.stack([noise, np.roll(noise, 997)], 1)
    swept = automate_lpf(st, lambda tt: 300 * 40 ** min(tt / dur, 1.0), res=0.35)
    tone = (np.sin(2 * np.pi * np.cumsum(220 * 2 ** (2 * q)) / SR) * 0.22).astype(np.float32)
    e = (q ** 2.2).astype(np.float32)
    return ((swept * 0.9 + tone[:, None]) * e[:, None] * peak).astype(np.float32)


def impact(size=1.0):
    n = S(3.0)
    t = np.arange(n) / SR
    f = 34 + 40 * np.exp(-t * 9)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    thump = lowpass(RNG.standard_normal(n).astype(np.float32), 400) * np.exp(-t * 18) * 0.8
    air = highpass(RNG.standard_normal(n).astype(np.float32), 3000) * np.exp(-t * 5) * 0.12
    return ((sub + thump + air) * size).astype(np.float32)


def reverse_swell(dur, g):
    n = S(dur)
    t = np.arange(n) / SR
    x = bandpass(RNG.standard_normal(n).astype(np.float32), 500, 9000) * np.exp(-t * 3.0)
    x = fx(np.stack([x, x], 1), Pedalboard([Reverb(room_size=0.95, wet_level=0.8, dry_level=0.2, width=1.0)]))
    return (x[::-1] * g).astype(np.float32)


def fx_layer():
    """Risers / swells into the big transitions (all in narration gaps), impacts on them."""
    buf = stereo_buf()
    for t, d, g in ((8.68, 1.6, 0.18), (16.60, 3.0, 0.22), (29.40, 1.6, 0.16), (50.38, 2.6, 0.22),
                    (64.06, 1.6, 0.20), (85.88, 2.4, 0.26), (106.56, 3.0, 0.30), (115.20, 2.2, 0.20)):
        r = riser(d, g)
        add(buf, r, t - d, 0, 1.0)
    for t, d, g in ((16.60, 1.4, 0.35), (96.55, 1.15, 0.45), (106.56, 1.2, 0.35), (50.38, 1.0, 0.25)):
        x = reverse_swell(d, g)
        add(buf, x, t - len(x) / SR, 0, 1.0)
    for t, g in ((2.0, 0.22), (4.0, 0.22), (6.0, 0.26), (8.68, 0.32), (16.60, 0.48), (29.40, 0.30), (43.96, 0.22),
                 (50.38, 0.40), (57.97, 0.26), (64.06, 0.40), (70.55, 0.40), (85.88, 0.50), (91.97, 0.30),
                 (96.55, 0.62), (106.56, 0.62), (108.05, 0.20), (109.75, 0.22), (112.10, 0.26), (115.20, 0.62)):
        add(buf, impact(1.0), t, 0, g)
    return fx(buf, Pedalboard([Reverb(room_size=0.85, wet_level=0.3, dry_level=0.85, width=1.0)]))


# ---------------------------------------------------------------- arrangement levels
SECTION_GAIN = smooth_curve([(0, 0.75), (8.6, 0.85), (16.6, 0.95), (29.4, 0.88), (43.9, 0.9), (50.4, 1.0),
                             (64.0, 0.95), (70.5, 1.0), (75.5, 0.85), (85.8, 1.05), (95.3, 0.8), (96.6, 1.08),
                             (106.5, 1.12), (115.2, 1.0), (117.2, 0.85), (118.66, 0.0)])


def pump(sidechain, depth=0.35, rel=0.18):
    """Gentle kick sidechain envelope for pads/bass."""
    g = np.ones(N + S(4), np.float32)
    t = np.arange(S(rel * 3)) / SR
    shape = 1 - depth * np.exp(-t / rel * 2.0) * np.clip(t / 0.008, 0, 1)
    for k in sidechain:
        i = S(k)
        j = min(len(g), i + len(shape))
        g[i:j] = np.minimum(g[i:j], shape[:j - i])
    return g


# ---------------------------------------------------------------- narration ducking
def voice_env(v):
    """Speech presence 0..1 from the narration (look-ahead 120 ms, attack 40 ms, release 450 ms)."""
    mono = v.mean(1)
    bp = bandpass(mono, 150, 4000)
    hop = S(0.01)
    fr = np.sqrt(np.convolve(bp ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(fr + 1e-9)
    gate = np.clip((db - (db.max() - 42)) / 12, 0, 1)
    out = np.zeros_like(gate)
    a_up, a_dn = math.exp(-0.01 / 0.04), math.exp(-0.01 / 0.45)
    s = 0.0
    for i, x in enumerate(gate):
        s = x + (s - x) * (a_up if x > s else a_dn)
        out[i] = s
    la = 12
    out = np.concatenate([out[la:], np.zeros(la)])
    out = np.maximum(out, np.convolve(out, np.ones(30) / 30, "same"))     # hold through short syllable gaps
    t = np.arange(len(out)) * 0.01
    return np.interp(np.arange(N + S(4)) / SR, t, np.clip(out, 0, 1)).astype(np.float32)


def duck(music, env, low_db=-8.0, mid_db=-15.0):
    lo = np.stack([lowpass(music[:, c], 250, 4) for c in range(2)], 1)
    mid = music - lo
    gl = 10 ** (low_db * env / 20)
    gm = 10 ** (mid_db * env / 20)
    return (lo * gl[:, None] + mid * gm[:, None]).astype(np.float32)


# ---------------------------------------------------------------- main
def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "2", "-ar", str(SR),
                          "-"], check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)
    out = np.zeros((N + S(4), 2), np.float32)
    out[:min(len(x), len(out))] = x[:len(out)]
    return out


def limit(x, ceiling_db=-1.5, look=0.005, rel=0.12):
    """Look-ahead peak limiter (no make-up gain)."""
    c = 10 ** (ceiling_db / 20)
    pk = np.abs(x).max(1)
    need = np.minimum(1.0, c / np.maximum(pk, 1e-9))
    la = S(look)
    # minimum over the look-ahead window, then release smoothing
    from scipy.ndimage import minimum_filter1d
    g = minimum_filter1d(need, size=2 * la + 1, origin=0)
    g = np.concatenate([g[la:], np.ones(la)])
    a_rel = math.exp(-1 / (rel * SR))
    out = np.empty_like(g)
    s = 1.0
    for i0 in range(0, len(g), 4096):                  # vectorised enough: per-block running min with release
        blk = g[i0:i0 + 4096]
        for j, v_ in enumerate(blk):
            s = v_ if v_ < s else v_ + (s - v_) * a_rel
            out[i0 + j] = s
    return (x * out[:, None]).astype(np.float32)


def write(path, x):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                    "-c:a", "pcm_s24le", path], input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)


def lufs(x):
    return pyln.Meter(SR).integrated_loudness(x.astype(np.float64))


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    global CHORDS
    CHORDS = plan_harmony()
    print("layers ...", flush=True)
    pad = pad_layer()
    arp = arp_layer()
    bel = bell_layer()
    bas = bass_layer()
    kb, hb, cb, sc = drums_layer()
    fxl = fx_layer()
    pm = pump(sc)[:, None]
    music = (pad * 0.9 * pm + arp * 0.9 + bel * 0.8 + bas * 0.9 * pm + kb * 0.85 + hb * 0.8 + cb * 0.8 + fxl * 0.9)
    t = np.arange(len(music)) / SR
    music *= np.array([SECTION_GAIN(x) for x in t[::480]]).repeat(480)[:len(music), None].astype(np.float32)
    music[:S(0.05)] *= np.linspace(0, 1, S(0.05))[:, None]
    music = music[:N]
    music = fx(music, Pedalboard([HighpassFilter(28), Compressor(threshold_db=-18, ratio=2.0, attack_ms=30,
                                                                  release_ms=250)]))
    # level: the full bed at MUSIC_LUFS before ducking (the narration is about -17 LUFS)
    music *= 10 ** ((MUSIC_LUFS - lufs(music)) / 20)
    v = load(src)[:N]
    env = voice_env(v)[:N]
    bed = duck(music, env)
    mix = v + bed
    # the narration keeps its own level (about -17 LUFS, peaks -1.2 dBTP): no gain, a safety limiter only
    g = 1.0
    mix = limit(mix * g, -1.0)
    bed = bed * g
    music = music * g
    bed_l = limit(bed, -1.0)
    os.makedirs(out_dir, exist_ok=True)
    write(os.path.join(out_dir, "AXCORE_BGM_full.wav"), limit(music))
    write(os.path.join(out_dir, "AXCORE_BGM.wav"), bed_l)
    write(os.path.join(out_dir, "AXCORE_mix.wav"), mix)
    # report: voice-to-music ratio in speech, music level in the gaps
    v = v * g
    speech = env > 0.8
    gaps = env < 0.05
    m_sp = 10 * np.log10(np.mean(bed[speech] ** 2) + 1e-12)
    v_sp = 10 * np.log10(np.mean(v[speech] ** 2) + 1e-12)
    m_gp = 10 * np.log10(np.mean(bed[gaps] ** 2) + 1e-12)
    win = S(3.0)
    rows = []
    for i in range(0, N - win, S(1.0)):
        sl = slice(i, i + win)
        e = float(env[sl].mean())
        rows.append((i / SR, e, 10 * np.log10(np.mean(v[sl] ** 2) + 1e-12), 10 * np.log10(np.mean(bed[sl] ** 2) + 1e-12)))
    np.save(os.path.join(out_dir, "levels.npy"), np.array(rows))
    print(json.dumps({"music_full_lufs": round(float(lufs(music)), 1), "mix_lufs": round(float(lufs(mix)), 1),
                      "narration_lufs": round(float(lufs(v)), 1), "voice_over_music_in_speech_db": round(float(v_sp - m_sp), 1),
                      "music_in_gaps_vs_speech_db": round(float(m_gp - m_sp), 1), "mix_peak": round(float(np.abs(mix).max()), 3)}))


if __name__ == "__main__":
    main()
