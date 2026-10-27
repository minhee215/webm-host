"""Instrumental BGM: minimal, progressive enterprise tech (no trailer drums).

100 BPM, D-minor/F-major colour. Energy rises by layering per scene and
resolves on the logo. Kept low (narration will sit on top).
"""
import numpy as np

from .synth import SR, t_axis, env_adsr, env_exp, saw, sine, noise, fft_band, midi, pan, place, reverb
from ..utils.config import DURATION

BPM = 100
BEAT = 60 / BPM
BAR = BEAT * 4
CHORDS = [  # (bass, voicing) — Dm9, Bbmaj7, Fmaj7, C(add9)
    (38, [62, 65, 69, 72, 76]), (34, [62, 65, 69, 70, 74]),
    (41, [60, 65, 69, 72, 76]), (36, [60, 64, 67, 72, 74]),
]


def energy(t):
    """0..1 arrangement energy by film time."""
    keys = [(0, 0.15), (15, 0.3), (31, 0.45), (50, 0.55), (73, 0.65), (89, 0.8), (106, 0.9), (115.5, 1.0),
            (117.4, 0.35), (DURATION, 0.25)]
    xs, ys = zip(*keys)
    return np.interp(t, xs, ys)


def _pad(total_n):
    out = np.zeros((total_n, 2))
    n_ch = int(BAR * 2 * SR)          # one chord per 2 bars
    k = 0
    t0 = 0.0
    while t0 < DURATION:
        bass, notes = CHORDS[k % len(CHORDS)]
        if t0 >= 117.2:
            bass, notes = 41, [60, 65, 69, 72, 76, 79]   # resolve: Fmaj9
            n = total_n - int(t0 * SR)
        else:
            n = n_ch + int(0.6 * SR)
        sig = np.zeros(n)
        for j, m in enumerate(notes):
            for det in (-0.07, 0.07):
                sig += saw(midi(m) * (1 + det / 100), n, phase=j * 0.13 + det) * 0.5
        sig = fft_band(sig, 80, 1400 + 1800 * energy(t0)) * env_adsr(n, 0.8, 0.5, 0.85, 1.0)
        pad_l = sig * 0.05
        st = np.stack([pad_l * 0.95, pad_l * 1.05], 1)
        place(out, st, t0)
        if t0 >= 117.2:
            break
        k += 1
        t0 += BAR * 2
    return out


def _bass(total_n):
    out = np.zeros(total_n)
    t = 31.0 - (31.0 % (BEAT / 2))
    while t < 116.0:
        chord = CHORDS[int(t // (BAR * 2)) % len(CHORDS)]
        n = int(BEAT / 2 * SR)
        f = midi(chord[0] + 12)
        s = sine(f, n) + 0.3 * sine(f * 2, n)
        s = np.tanh(s * 1.5) * env_exp(n, 0.12)
        place(out, s * 0.09 * energy(t), t)
        t += BEAT / 2
    return pan(out, 0.0)


def _arp(total_n):
    out = np.zeros(total_n)
    rng = np.random.default_rng(5)
    step = BEAT / 4
    t = 15.0
    i = 0
    while t < 116.5:
        e = energy(t)
        dens = 0.35 + 0.6 * e
        if rng.uniform() < dens:
            chord = CHORDS[int(t // (BAR * 2)) % len(CHORDS)][1]
            m = chord[[0, 2, 1, 3, 4, 2, 3, 1][i % 8]] + 12
            n = int(0.35 * SR)
            s = (sine(midi(m), n) + 0.25 * sine(midi(m) * 2, n) + 0.08 * sine(midi(m) * 3, n)) * env_exp(n, 0.09)
            place(out, s * 0.035 * (0.6 + 0.4 * e), t)
        i += 1
        t += step
    return pan(out, 0.15)


def _drums(total_n):
    out = np.zeros(total_n)
    t = 73.0
    while t < 115.5:
        e = energy(t)
        n = int(0.4 * SR)
        f = np.linspace(110, 45, n)
        kick = sine(f, n) * env_exp(n, 0.09)
        place(out, kick * 0.16 * e, t)
        if t >= 89.0:
            hn = int(0.06 * SR)
            hat = fft_band(noise(hn, int(t * 10)), 6000, 14000) * env_exp(hn, 0.012)
            place(out, hat * 0.05 * e, t + BEAT / 2)
        t += BEAT
    # riser into the logo
    rn = int(3.0 * SR)
    riser = fft_band(noise(rn, 9), 800, 6000) * np.linspace(0, 1, rn) ** 2.5 * 0.05
    place(out, riser, 113.0)
    return pan(out, 0.0)


def build():
    total_n = int(DURATION * SR) + SR
    mix = _pad(total_n) + _bass(total_n) + _arp(total_n) + _drums(total_n)
    mix = reverb(mix, 2.4, 0.28)
    # fade in / out
    fi = int(1.5 * SR)
    mix[:fi] *= np.linspace(0, 1, fi)[:, None]
    end = int(DURATION * SR)
    fo = int(2.2 * SR)
    mix[end - fo:end] *= np.linspace(1, 0, fo)[:, None] ** 1.5
    return mix[:end]
