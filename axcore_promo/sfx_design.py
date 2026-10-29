"""AXCORE promo - motion sound effects only (no music), designed to the client's 118.66 s cut.

Every sound is synthesised here (no library samples): whooshes and swishes for camera moves and transitions,
glassy pops for UI cards, ticks for small items, mouse clicks, typing, toggles, a scan sweep, data sparkles,
swirls, risers, soft impacts and light flashes. The cue list was built from the edit itself: frame differences
(and where in the frame they happen) located each motion, the scene scripts said what it is.
The narration stays on top: the effects dip a little under the voice, the big transitions sit in its pauses.

Usage: python3 sfx_design.py <narration/video file> <out dir>
Writes AXCORE_SFX.wav (as mixed), AXCORE_SFX_unducked.wav, AXCORE_narration_SFX_mix.wav.
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
import pyloudnorm as pyln
from pedalboard import Delay, HighpassFilter, LadderFilter, Pedalboard, Reverb
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 118.66
N = int(round(DUR * SR))
RNG = np.random.default_rng(11)


def S(t):
    return int(round(t * SR))


def tt(n):
    return np.arange(n) / SR


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [max(lo, 20), min(hi, 23000)], "band", fs=SR, output="sos"), x).astype(np.float32)


def hpf(x, fc, order=2):
    return sosfilt(butter(order, fc, "high", fs=SR, output="sos"), x).astype(np.float32)


def lpf(x, fc, order=2):
    return sosfilt(butter(order, fc, "low", fs=SR, output="sos"), x).astype(np.float32)


def noise(n):
    return RNG.standard_normal(n).astype(np.float32)


def pink(n):
    w = np.fft.rfft(noise(n))
    f = np.arange(len(w)) + 1.0
    return (np.fft.irfft(w / np.sqrt(f), n) * 30).astype(np.float32)


def board(x, *plugins):
    st = x if x.ndim == 2 else np.stack([x, x], 1)
    return Pedalboard(list(plugins))(st.T.copy(), SR).T.astype(np.float32)


def sweep_filter(x, curve, mode="BPF24", res=0.4, block=512):
    """Ladder filter whose cutoff follows curve(q), q = 0..1 over the sound (state kept between blocks)."""
    lf = LadderFilter(mode=getattr(LadderFilter.Mode, mode), cutoff_hz=1000, resonance=res, drive=1.0)
    b = Pedalboard([lf])
    st = x if x.ndim == 2 else np.stack([x, x], 1)
    out = np.zeros_like(st)
    n = len(st)
    for i in range(0, n, block):
        lf.cutoff_hz = float(np.clip(curve((i + block / 2) / n), 40, 19000))
        out[i:i + block] = b(st[i:i + block].T.copy(), SR, reset=False).T
    return out


def pan_st(x, p):
    """Mono x -> stereo with per-sample pan p (-1..1, scalar or array), constant power."""
    p = np.broadcast_to(np.asarray(p, np.float32), x.shape)
    a = (p + 1) * math.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)], 1).astype(np.float32)


# ---------------------------------------------------------------- the sounds
def whoosh(dur=0.9, size=1.0, pan0=-0.5, pan1=0.5, peak=0.6, lo=250, hi=5000, tone=True):
    """Air past the lens: noise through a band sweeping up to the peak and back down, moving across."""
    n = S(dur)
    q = tt(n) / dur
    env = np.where(q < peak, (q / peak) ** 2.2, np.exp(-(q - peak) / (1 - peak) * 3.2)).astype(np.float32)
    src = pink(n) * 0.7 + noise(n) * 0.3

    def cut(u):
        k = u / peak if u < peak else 1 - (u - peak) / (1 - peak) * 0.7
        return lo * (hi / lo) ** max(0.0, min(1.0, k))
    st = sweep_filter(src * env, cut, "BPF12", res=0.25)
    st = st[:, 0] * 0.7 + st[:, 1] * 0.3
    out = pan_st(st, np.linspace(pan0, pan1, n))
    if tone:                                            # a faint doppler tone gives it body
        f = 140 * size * (1 + 0.6 * np.sin(np.pi * np.clip(q / peak, 0, 1) / 2)) * np.where(q > peak, 1 - 0.35 * (q - peak), 1)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32) * env * 0.18
        out += pan_st(x, np.linspace(pan0, pan1, n))
    return out * size


def swish(dur=0.32, pan0=-0.4, pan1=0.4, hi=9000, g=1.0):
    return whoosh(dur, 0.6 * g, pan0, pan1, peak=0.45, lo=1200, hi=hi, tone=False)


def pop(f=1800, g=1.0, dur=0.35):
    """Glassy UI pop: a pitched blip dropping into a short FM shimmer, a tiny transient on top."""
    n = S(dur)
    t = tt(n)
    pitch = f * (1 + 0.35 * np.exp(-t * 60))
    body = np.sin(2 * np.pi * np.cumsum(pitch) / SR) * np.exp(-t * 26)
    shim = np.sin(2 * np.pi * f * 2.0 * t + 1.4 * np.exp(-t * 18) * np.sin(2 * np.pi * f * 3.01 * t)) * np.exp(-t * 14) * 0.35
    tr = hpf(noise(n), 4000) * np.exp(-t * 700) * 0.25
    x = (body * 0.8 + shim + tr) * np.clip(t / 0.0015, 0, 1)
    return (x * g).astype(np.float32)


def tick(f=4200, g=1.0):
    n = S(0.05)
    t = tt(n)
    x = np.sin(2 * np.pi * f * t) * np.exp(-t * 160) + bp(noise(n), 3000, 9000) * np.exp(-t * 400) * 0.5
    return (x * g).astype(np.float32)


def click(g=1.0):
    """Mouse click: press and release."""
    n = S(0.12)
    t = tt(n)
    out = np.zeros(n, np.float32)
    for o, a, f in ((0.0, 1.0, 2600), (0.055, 0.55, 3300)):
        i = S(o)
        m = n - i
        s = tt(m)
        out[i:] += (bp(noise(m), f * 0.6, f * 1.6, 2) * np.exp(-s * 520) * 1.6 + np.sin(2 * np.pi * f * 0.5 * s) *
                    np.exp(-s * 300) * 0.4) * a
    return out * g


def typing(dur, rate=14, g=1.0):
    n = S(dur + 0.1)
    out = np.zeros(n, np.float32)
    t = 0.0
    while t < dur:
        k = tick(RNG.uniform(1800, 3200), RNG.uniform(0.5, 1.0)) * 0.8
        k += click(0.25)[:len(k)] if RNG.random() < 0.3 else 0
        i = S(t)
        out[i:i + len(k)] += k[:max(0, min(len(k), n - i))]
        t += 1 / rate * RNG.uniform(0.7, 1.35)
    return out * g


def toggle(g=1.0):
    n = S(0.3)
    t = tt(n)
    x = click(0.8)
    out = np.zeros(n, np.float32)
    out[:len(x)] += x
    f = 900 + 700 * np.clip(t / 0.08, 0, 1)
    out += (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 18) * 0.35).astype(np.float32)
    return out * g


def success(g=1.0):
    n = S(0.9)
    out = np.zeros(n, np.float32)
    for o, f in ((0.0, 1318.5), (0.09, 1975.5)):
        x = pop(f, 0.7, 0.7)
        i = S(o)
        out[i:i + len(x)] += x[:n - i]
    return out * g


def scan(dur, g=1.0):
    """A scan line passing: a filtered hum sweeping down with a soft tremolo and a high glint."""
    n = S(dur)
    t = tt(n)
    q = t / dur
    hum = (np.sin(2 * np.pi * np.cumsum(600 - 220 * q) / SR) + 0.4 * np.sin(2 * np.pi * np.cumsum(1200 - 440 * q) / SR))
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 14 * t)
    air = bp(noise(n), 3000, 9000) * 0.25
    env = np.clip(q / 0.08, 0, 1) * np.clip((1 - q) / 0.15, 0, 1)
    return ((hum * 0.3 * trem + air) * env * g).astype(np.float32)


def sparkle(dur, density=18, g=1.0, rise=True):
    """Data flowing: tiny glassy ticks scattered in time and space, getting denser."""
    n = S(dur + 0.3)
    out = np.zeros((n, 2), np.float32)
    k = int(density * dur)
    for j in range(k):
        u = RNG.random() ** (0.6 if rise else 1.0)
        t0 = u * dur
        x = pop(RNG.uniform(2600, 5200), RNG.uniform(0.15, 0.4), 0.12)
        i = S(t0)
        out[i:i + len(x)] += pan_st(x, RNG.uniform(-0.8, 0.8))[:n - i]
    return out * g


def riser(dur, g=1.0):
    n = S(dur)
    q = tt(n) / dur
    st = sweep_filter(noise(n) * (q ** 2.0), lambda u: 300 * 30 ** u, "LPF24", res=0.3)
    f = 300 * 2 ** (2.5 * q)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32) * q ** 2.5 * 0.15
    return (st * 0.8 + np.stack([tone, tone], 1)) * g


def impact(g=1.0, low=1.0):
    n = S(1.6)
    t = tt(n)
    f = 48 + 60 * np.exp(-t * 14)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5) * low
    body = lpf(noise(n), 900) * np.exp(-t * 22) * 0.6
    air = hpf(noise(n), 2500) * np.exp(-t * 9) * 0.15
    return ((sub + body + air) * g).astype(np.float32)


def shimmer(dur=1.2, g=1.0, base=1760):
    n = S(dur)
    t = tt(n)
    x = np.zeros(n)
    for k, r in enumerate((1.0, 1.5, 2.0, 2.52, 3.0)):
        x += np.sin(2 * np.pi * base * r * t + RNG.random() * 6) * np.exp(-t * (2.2 + k)) / (k + 1)
    x *= np.clip(t / 0.01, 0, 1) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * t))
    return (x * g * 0.5).astype(np.float32)


def reverse_swell(dur, g=1.0):
    n = S(dur)
    t = tt(n)
    x = bp(noise(n), 600, 10000) * np.exp(-t * 3.5)
    st = board(x, Reverb(room_size=0.9, wet_level=0.8, dry_level=0.3, width=1.0))
    return st[::-1] * g


def swirl(dur, g=1.0, turns=1.6):
    """Long whoosh circling the listener (vortex)."""
    n = S(dur)
    q = tt(n) / dur
    env = (np.sin(np.pi * q) ** 1.2).astype(np.float32)
    st = sweep_filter(pink(n) * env, lambda u: 400 * (1 + 6 * math.sin(math.pi * u) ** 2), "BPF12", res=0.35)
    mono = st[:, 0]
    pan = np.sin(2 * np.pi * turns * q) * 0.85
    return pan_st(mono, pan) * g


def glitch(g=1.0, dur=0.35):
    n = S(dur)
    t = tt(n)
    x = np.sign(np.sin(2 * np.pi * 880 * t)) * 0.3
    gate = (np.floor(t * 40) % 3 != 1).astype(np.float32)
    x = x * gate * np.exp(-t * 7) + bp(noise(n), 2000, 6000) * gate * np.exp(-t * 12) * 0.4
    return (x * g).astype(np.float32)


# ---------------------------------------------------------------- the cue list (edit time, s)
def cues():
    C = []

    def a(t, kind, **kw):
        C.append((t, kind, kw))
    # intro: live action cuts, tile grid
    for t in (2.0, 4.0, 6.0):
        a(t - 0.18, "swish", g=0.45)
    a(8.25, "whoosh", dur=0.75, g=0.65, pan0=-0.3, pan1=0.6)
    a(9.8, "swish", g=0.4)
    a(10.45, "whoosh", dur=0.6, g=0.45)
    a(12.47, "pop", f=1500, g=0.5)
    a(14.05, "swish", g=0.4, pan0=0.4, pan1=-0.4)
    a(15.10, "click", g=0.55)
    a(15.12, "pop", f=1250, g=0.55)
    a(15.95, "reverse", dur=0.65, g=0.30)
    a(16.0, "whoosh", dur=1.0, g=0.85, peak=0.6, pan0=-0.6, pan1=0.6)
    a(16.60, "impact", g=0.32)
    # the navy map: tiles land one by one, links light
    for i, t in enumerate((17.43, 17.60, 17.93, 18.23, 18.48, 18.73, 19.23, 19.81)):
        a(t, "pop", f=1400 + 90 * i, g=0.32, pan=-0.6 + 0.17 * i)
    a(20.9, "sparkle", dur=1.5, g=0.45)
    a(23.0, "whoosh", dur=0.7, g=0.45)
    a(24.11, "swish", g=0.4)
    for i, t in enumerate((24.69, 25.28, 25.78)):
        a(t, "pop", f=1700 + 150 * i, g=0.4)
    a(26.95, "swish", g=0.35, dur=0.45)
    a(27.4, "sparkle", dur=1.1, g=0.3)
    a(28.6, "whoosh", dur=0.75, g=0.6, peak=0.7, pan0=-0.5, pan1=0.0)
    a(29.25, "shimmer", g=0.35, base=2093)
    # AXpoint: landing, search, upload, flow graph, diagnosis, candidates
    a(30.13, "typing", dur=0.55, g=0.45)
    a(30.98, "click", g=0.6)
    a(31.0, "whoosh", dur=0.7, g=0.5, pan0=0.5, pan1=-0.5)
    a(31.88, "swish", g=0.35, dur=0.8, pan0=0.6, pan1=0.1)
    a(32.73, "pop", f=900, g=0.55)
    for i in range(4):
        a(32.80 + 0.12 * i, "tick", f=3600 + 200 * i, g=0.35, pan=-0.5 + 0.3 * i)
    a(33.18, "typing", dur=0.80, g=0.40)
    a(34.18, "click", g=0.6)
    a(34.22, "swish", g=0.45, pan0=0.0, pan1=0.0)
    for i in range(10):
        a(34.45 + 0.11 * i, "tick", f=3000 + 120 * i, g=0.3, pan=-0.7 + 0.15 * i)
    a(34.6, "sparkle", dur=1.6, g=0.35)
    a(36.68, "click", g=0.55)
    a(36.72, "whoosh", dur=0.6, g=0.55)
    a(37.88, "shimmer", g=0.35, base=1568)
    a(38.48, "pop", f=1050, g=0.6)
    a(39.45, "whoosh", dur=0.55, g=0.45, pan0=0.0, pan1=0.0)
    for i in range(6):
        a(40.08 + 0.12 * i, "pop", f=1600 + 80 * i, g=0.28, pan=-0.5 + 0.2 * i)
    a(41.85, "whoosh", dur=0.8, g=0.4, pan0=0.3, pan1=-0.2)
    a(43.5, "whoosh", dur=0.75, g=0.5, pan0=-0.2, pan1=0.3)
    for i, t in enumerate((44.89, 45.34, 45.80, 46.25, 46.71)):
        a(t, "toggle", g=0.5, pan=-0.6 + 0.3 * i)
    a(46.92, "shimmer", g=0.35, base=1760)
    a(46.95, "swish", g=0.35)
    # connect: push into the UI, light, datacenter, panels and SaaS cards
    a(49.10, "whoosh", dur=0.9, g=0.55, peak=0.75, pan0=0.0, pan1=0.0)
    a(49.45, "reverse", dur=0.75, g=0.35)
    a(50.18, "impact", g=0.25, low=0.6)
    a(50.20, "shimmer", g=0.45, base=2349)
    for i, t in enumerate((50.32, 51.17)):
        a(t, "swish", g=0.4, pan0=-0.8, pan1=-0.4)
    for i in range(6):
        a(50.70 + 0.08 * i, "tick", f=3400 + 150 * i, g=0.25, pan=-0.6)
        a(51.55 + 0.08 * i, "tick", f=3400 + 150 * i, g=0.25, pan=-0.6)
    for i in range(5):
        t = 53.70 + 0.42 * i
        a(t, "pop", f=1500 + 120 * i, g=0.38, pan=0.6)
        a(t + 0.8, "tick", f=4800, g=0.3, pan=0.6)
    # OCR: work files, data table, handwriting scanned
    a(57.85, "whoosh", dur=0.7, g=0.4, peak=0.3, lo=200, hi=2500)
    a(58.0, "swish", g=0.4, dur=0.5, pan0=0.0, pan1=0.0)
    a(58.68, "click", g=0.6)
    a(58.75, "pop", f=1100, g=0.5)
    a(58.80, "whoosh", dur=0.8, g=0.55, peak=0.25, pan0=0.0, pan1=0.0)
    a(58.85, "sparkle", dur=0.7, density=30, g=0.4, rise=False)
    a(59.40, "swirl", dur=1.0, g=0.55, turns=1.0)
    a(59.83, "pop", f=1300, g=0.5)
    for i in range(12):
        a(60.03 + 0.035 * i, "tick", f=3000 + 90 * i, g=0.25, pan=0.2 * math.sin(i))
    a(60.35, "swish", g=0.4, pan0=0.3, pan1=-0.4)
    a(60.50, "swish", g=0.35, pan0=0.5, pan1=0.5)
    a(60.88, "scan", dur=0.70, g=0.45, pan=0.4)
    a(61.55, "success", g=0.40, pan=0.4)
    a(61.55, "swish", g=0.4, dur=0.8, pan0=0.4, pan1=-0.4)
    a(62.35, "pop", f=1600, g=0.4, pan=-0.4)
    # ontology: zoom-out match cut, entities, flow pulse, AI core, title
    a(63.45, "whoosh", dur=0.55, g=0.6, peak=0.85, lo=300, hi=6000)
    a(63.96, "whoosh", dur=0.9, g=0.5, peak=0.1, lo=200, hi=4000)
    for i in range(8):
        a(64.30 + 0.16 * i, "tick", f=2600 + 150 * i, g=0.3, pan=-0.8 + 0.22 * i)
    for i, t in enumerate((64.53, 65.28, 66.02, 66.71, 67.44, 67.93)):
        a(t, "pop", f=1100 + 110 * i, g=0.45, pan=-0.6 + 0.24 * i)
    a(68.18, "sparkle", dur=1.8, g=0.35)
    a(68.2, "swish", g=0.3, dur=1.8, pan0=-0.8, pan1=0.8)
    a(69.43, "shimmer", g=0.35, base=1318)
    a(70.40, "whoosh", dur=0.9, g=0.55, peak=0.4, pan0=-0.4, pan1=0.3)
    a(71.28, "impact", g=0.20, low=0.5)
    a(71.30, "shimmer", g=0.45, base=1760)
    # AI question: systems scatter and merge, the question, reasoning, answer, actions
    a(74.55, "whoosh", dur=0.8, g=0.4, peak=0.3, lo=200, hi=2500)
    for i in range(10):
        a(74.85 + 0.07 * i, "tick", f=2200 + 100 * i, g=0.18, pan=-0.8 + 0.17 * i)
    for i in range(5):
        a(75.58 + 0.22 * i, "tick", f=3800, g=0.28, pan=-0.5 + 0.25 * i)
    a(76.10, "reverse", dur=0.6, g=0.35)
    a(76.62, "whoosh", dur=0.5, g=0.45, peak=0.8, pan0=0.0, pan1=0.0)
    a(77.05, "pop", f=1250, g=0.5)
    a(78.18, "typing", dur=0.75, g=0.42)
    a(79.05, "click", g=0.6)
    a(79.12, "swish", g=0.45, pan0=0.0, pan1=0.0)
    a(79.35, "swish", g=0.35, pan0=-0.4, pan1=0.4)
    for i, t in enumerate((79.53, 79.71, 80.25, 80.61)):
        a(t, "tick", f=3200 + 300 * i, g=0.32, pan=-0.5)
    for i, t in enumerate((81.10, 81.68)):
        a(t, "swish", g=0.35, dur=0.7, pan0=0.0, pan1=0.7, hi=11000)
    a(81.68, "sparkle", dur=1.0, g=0.25)
    a(82.20, "pop", f=1700, g=0.45, pan=0.3)
    for i in range(3):
        a(82.58 + 0.25 * i, "tick", f=3600 + 200 * i, g=0.3, pan=0.3 + 0.2 * i)
    a(83.43, "swish", g=0.4, pan0=-0.5, pan1=-0.5, dur=0.5)
    for i, t in enumerate((83.98, 84.20)):
        a(t, "tick", f=4200, g=0.35, pan=-0.5)
    a(85.00, "click", g=0.6, pan=-0.5)
    a(85.02, "success", g=0.3, pan=-0.5)
    # sales / production / automation
    a(85.55, "reverse", dur=0.45, g=0.4)
    a(85.62, "whoosh", dur=0.9, g=0.55, peak=0.35, lo=500, hi=9000)
    a(86.6, "swish", g=0.35, pan0=-0.7, pan1=-0.4)
    a(87.3, "sparkle", dur=0.9, g=0.25, rise=False)
    a(88.30, "pop", f=1500, g=0.4, pan=-0.4)
    a(87.95, "whoosh", dur=0.8, g=0.55, pan0=-0.6, pan1=0.6)
    a(89.0, "swish", g=0.35, pan0=0.7, pan1=0.4)
    a(90.40, "glitch", g=0.35, pan=0.5)
    a(90.42, "pop", f=1100, g=0.4, pan=0.5)
    a(91.75, "whoosh", dur=0.6, g=0.4, pan0=0.3, pan1=-0.3)
    a(91.95, "swish", g=0.35, pan0=-0.7, pan1=-0.4)
    for i in range(4):
        a(92.32 + 0.28 * i, "tick", f=3600 + 250 * i, g=0.35, pan=-0.6)
    a(93.45, "swish", g=0.4, pan0=-0.6, pan1=-0.6, dur=0.5)
    for i in range(4):
        a(93.70 + 0.16 * i, "pop", f=1400 + 100 * i, g=0.3, pan=-0.6 + 0.1 * i)
    a(94.05, "sparkle", dur=0.8, g=0.3)
    a(94.9, "whoosh", dur=0.7, g=0.4, peak=0.3, lo=200, hi=2200)
    a(95.25, "swish", g=0.45, dur=0.55, pan0=0.0, pan1=0.0, hi=7000)
    # analysis -> execution
    a(96.20, "toggle", g=0.7)
    a(96.24, "impact", g=0.28, low=0.7)
    a(96.26, "whoosh", dur=0.9, g=0.6, peak=0.15, lo=300, hi=7000)
    a(96.5, "sparkle", dur=1.5, g=0.3, rise=False)
    # the vortex, the structure, the rush into the core
    a(99.35, "swirl", dur=2.2, g=0.65, turns=1.4)
    a(101.3, "swirl", dur=2.6, g=0.35, turns=1.8)
    a(103.5, "shimmer", g=0.3, base=2093, dur=1.5)
    a(104.4, "riser", dur=2.1, g=0.45)
    a(106.0, "reverse", dur=0.55, g=0.45)
    a(106.52, "impact", g=0.3, low=0.6)
    a(106.55, "shimmer", g=0.5, base=2637)
    # finale: AX pieces, logo
    a(106.95, "swish", g=0.4, pan0=0.5, pan1=-0.2)
    a(107.55, "whoosh", dur=0.7, g=0.45, pan0=-0.5, pan1=0.4)
    a(108.53, "pop", f=1300, g=0.35)
    a(109.30, "whoosh", dur=0.7, g=0.45, pan0=0.5, pan1=-0.4)
    a(111.30, "whoosh", dur=0.8, g=0.5, pan0=-0.4, pan1=0.4)
    a(113.20, "pop", f=1600, g=0.4, pan=0.3)
    a(114.20, "swish", g=0.4, dur=0.5)
    a(114.55, "reverse", dur=0.5, g=0.35)
    a(115.03, "impact", g=0.32, low=0.8)
    a(115.05, "shimmer", g=0.55, base=1760, dur=2.2)
    return C


def render_cue(kind, kw):
    g = kw.get("g", 1.0)
    pan = kw.get("pan", 0.0)
    if kind == "whoosh":
        return whoosh(kw.get("dur", 0.8), g, kw.get("pan0", -0.5), kw.get("pan1", 0.5), kw.get("peak", 0.6),
                      kw.get("lo", 250), kw.get("hi", 5000))
    if kind == "swish":
        return swish(kw.get("dur", 0.32), kw.get("pan0", -0.4), kw.get("pan1", 0.4), kw.get("hi", 9000), g)
    if kind == "pop":
        return pan_st(pop(kw.get("f", 1800), g), pan)
    if kind == "tick":
        return pan_st(tick(kw.get("f", 4200), g), pan)
    if kind == "click":
        return pan_st(click(g), pan)
    if kind == "typing":
        return pan_st(typing(kw["dur"], g=g), pan)
    if kind == "toggle":
        return pan_st(toggle(g), pan)
    if kind == "success":
        return pan_st(success(g), pan)
    if kind == "scan":
        return pan_st(scan(kw["dur"], g), pan)
    if kind == "sparkle":
        return sparkle(kw["dur"], kw.get("density", 18), g, kw.get("rise", True))
    if kind == "riser":
        return riser(kw["dur"], g)
    if kind == "impact":
        return pan_st(impact(g, kw.get("low", 1.0)), 0.0)
    if kind == "shimmer":
        return pan_st(shimmer(kw.get("dur", 1.2), g, kw.get("base", 1760)), pan)
    if kind == "reverse":
        return reverse_swell(kw["dur"], g)
    if kind == "swirl":
        return swirl(kw["dur"], g, kw.get("turns", 1.6))
    if kind == "glitch":
        return pan_st(glitch(g), pan)
    raise ValueError(kind)


# ---------------------------------------------------------------- mix
def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-vn", "-f", "f32le", "-ac", "2", "-ar", str(SR),
                          "-"], check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)
    out = np.zeros((N, 2), np.float32)
    out[:min(len(x), N)] = x[:N]
    return out


def write(path, x):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                    "-c:a", "pcm_s24le", path], input=np.ascontiguousarray(x, np.float32).tobytes(), check=True)


def voice_env(v):
    mono = bp(v.mean(1), 150, 4000)
    hop = S(0.01)
    fr = np.sqrt(np.convolve(mono ** 2, np.ones(hop) / hop, "same")[::hop] + 1e-12)
    db = 20 * np.log10(fr + 1e-9)
    gate = np.clip((db - (db.max() - 42)) / 12, 0, 1)
    out = np.zeros_like(gate)
    s = 0.0
    for i, x in enumerate(gate):
        s = x + (s - x) * (math.exp(-0.01 / 0.03) if x > s else math.exp(-0.01 / 0.35))
        out[i] = s
    out = np.concatenate([out[8:], np.zeros(8)])
    return np.interp(np.arange(N) / SR, np.arange(len(out)) * 0.01, out).astype(np.float32)


def lufs(x):
    return pyln.Meter(SR).integrated_loudness(x.astype(np.float64))


def main():
    src, out_dir = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    fx = np.zeros((N + S(4), 2), np.float32)
    C = cues()
    meter = pyln.Meter(SR, block_size=0.1)
    for t, kind, kw in C:
        x = render_cue(kind, kw)
        # level by kind (short-term loudness of the sound itself), g nudges it around that (0.45 = nominal)
        pad = np.zeros((max(len(x), S(0.4)), 2), np.float32)
        pad[:len(x)] = x
        l0 = meter.integrated_loudness(pad.astype(np.float64))
        if np.isfinite(l0):
            target = LEVEL[kind] + TRIM + 20 * math.log10(max(kw.get("g", 0.45), 0.05) / 0.45) * 0.6
            x = x * 10 ** ((target - l0) / 20)
        pk = float(np.abs(x).max())
        if pk > PEAK_CAP:                         # very short sounds: keep the click, not a spike
            x = x * (PEAK_CAP / pk)
        i = S(t)
        j = min(len(fx), i + len(x))
        fx[i:j] += x[:j - i]
    fx = fx[:N]
    # a common small room so the sounds sit together, a high-pass to keep the low end clean
    fx = Pedalboard([HighpassFilter(45), Reverb(room_size=0.45, damping=0.6, wet_level=0.14, dry_level=0.92,
                                                width=1.0)])(fx.T.copy(), SR).T.astype(np.float32)
    v = load(src)
    env = voice_env(v)
    hi = fx - np.stack([sosfilt(butter(2, 300, "low", fs=SR, output="sos"), fx[:, c]) for c in range(2)], 1)
    duck = 10 ** (-5.0 * env / 20)                 # the effects step back a little while someone speaks
    fxd = (fx - hi + hi * (10 ** (-7.0 * env / 20))[:, None]) * duck[:, None]
    mix = v + fxd
    # where a sound lands on a voice peak, pull the sound (never the voice) under 0.89
    over = np.abs(mix).max(1)
    need = np.where(over > 0.89, np.clip((0.89 - np.abs(v).max(1)) / (np.abs(fxd).max(1) + 1e-9), 0, 1), 1.0)
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    g = uniform_filter1d(minimum_filter1d(need, S(0.01)), S(0.01))
    fxd = fxd * g[:, None]
    mix = v + fxd
    write(os.path.join(out_dir, "AXCORE_SFX_unducked.wav"), fx)
    write(os.path.join(out_dir, "AXCORE_SFX.wav"), fxd)
    write(os.path.join(out_dir, "AXCORE_narration_SFX_mix.wav"), mix)
    speech = env > 0.8
    print(json.dumps({"cues": len(C), "sfx_lufs": round(float(lufs(fxd)), 1), "mix_lufs": round(float(lufs(mix)), 1),
                      "narration_lufs": round(float(lufs(v)), 1), "sfx_peak": round(float(np.abs(fxd).max()), 3),
                      "voice_over_sfx_in_speech_db": round(float(10 * np.log10(np.mean(v[speech] ** 2) /
                                                                              (np.mean(fxd[speech] ** 2) + 1e-12))), 1)}))


PEAK_CAP = 0.30
TRIM = -3.0                      # overall effects level (dB)
# short-term loudness of each kind of sound (LUFS), against the narration's -18 or so
LEVEL = {"whoosh": -25.0, "swish": -29.0, "pop": -28.0, "tick": -32.0, "click": -27.0, "typing": -30.0,
         "toggle": -27.0, "success": -29.0, "scan": -29.0, "sparkle": -32.0, "shimmer": -29.0, "impact": -24.0,
         "reverse": -27.0, "swirl": -25.0, "riser": -27.0, "glitch": -29.0}

if __name__ == "__main__":
    main()
