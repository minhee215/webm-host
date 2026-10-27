"""Subtle UI / motion sound effects, synthesised. Each returns a stereo array."""
import numpy as np

from .synth import SR, env_exp, env_adsr, sine, noise, fft_band, pan, midi


def _tone(freqs, dur, tau, amp=0.3, attack=0.002):
    n = int(dur * SR)
    s = sum(sine(f, n) / (k + 1) for k, f in enumerate(freqs))
    e = env_exp(n, tau) * np.minimum(1, np.arange(n) / (attack * SR + 1))
    return s * e * amp


def _sweep_noise(dur, lo0, hi0, lo1, hi1, amp=0.2, seed=0, shape="swell"):
    n = int(dur * SR)
    x = noise(n, seed)
    seg = 8
    out = np.zeros(n)
    for k in range(seg):
        a, b = k * n // seg, (k + 1) * n // seg
        u = (k + 0.5) / seg
        out[a:b] = fft_band(x, lo0 + (lo1 - lo0) * u, hi0 + (hi1 - hi0) * u)[a:b]
    if shape == "swell":
        e = np.sin(np.linspace(0, np.pi, n)) ** 2
    elif shape == "rise":
        e = np.linspace(0, 1, n) ** 2 * np.minimum(1, (n - np.arange(n)) / (0.05 * SR))
    else:
        e = env_exp(n, dur / 4)
    return out * e * amp


def _click(amp=0.25, seed=0):
    n = int(0.012 * SR)
    return fft_band(noise(n, seed), 2000, 9000) * env_exp(n, 0.002) * amp


def make(name, seed=0):
    rng = np.random.default_rng(seed)
    p = rng.uniform(-0.25, 0.25)
    if name == "node_soft":
        m = _tone([1320, 2640], 0.25, 0.06, 0.18)
    elif name == "node":
        m = _tone([880, 1760, 2640], 0.45, 0.12, 0.22)
    elif name in ("ui_tick", "type", "chip_land"):
        amp = {"ui_tick": 0.22, "type": 0.12, "chip_land": 0.16}[name]
        m = _click(amp, seed)
        if name == "ui_tick":
            t_ = _tone([3000], 0.045, 0.01, 0.06)
            m = np.pad(m, (0, len(t_) - len(m))) + t_
        if name == "chip_land":
            t = _tone([520, 1040], 0.12, 0.03, 0.12)
            m = np.pad(m, (0, len(t) - len(m))) + t
    elif name == "select":
        t = _tone([1500, 2250], 0.18, 0.05, 0.2)
        m = t + np.pad(_click(0.25, seed), (0, len(t) - int(0.012 * SR)))
    elif name == "ui_open":
        a = _tone([990], 0.16, 0.05, 0.14)
        b = _tone([1485], 0.2, 0.06, 0.14)
        m = np.concatenate([a[:int(0.07 * SR)], b])
    elif name == "line":
        m = _sweep_noise(0.55, 400, 1500, 1500, 6000, 0.08, seed, "swell")
    elif name == "line_rev":
        m = _sweep_noise(0.55, 1500, 6000, 400, 1500, 0.08, seed, "swell")
    elif name in ("scan", "scan_long"):
        d = 0.5 if name == "scan" else 1.0
        m = _sweep_noise(d, 2000, 4000, 5000, 9000, 0.05, seed, "swell") + _tone([2400], d, d / 2, 0.025)
    elif name == "data_rise":
        n = int(0.9 * SR)
        m = np.zeros(n)
        for k in range(14):
            t0 = int(rng.uniform(0, 0.75) * SR)
            b = _tone([rng.uniform(1800, 4200)], 0.12, 0.03, 0.05)
            m[t0:t0 + len(b)] += b[: n - t0]
    elif name in ("push", "pull", "push_rev", "air"):
        if name == "push":
            m = _sweep_noise(0.6, 150, 600, 600, 3000, 0.10, seed, "swell")
        elif name == "air":
            m = _sweep_noise(0.45, 300, 1200, 800, 2500, 0.05, seed, "swell")
        else:
            m = _sweep_noise(0.6, 600, 3000, 150, 600, 0.10, seed, "swell")
    elif name == "swell":
        m = _sweep_noise(1.0, 200, 800, 900, 4000, 0.09, seed, "rise") + _tone([midi(62), midi(69)], 1.0, 0.6, 0.03)
    elif name == "connector":
        t = _tone([2000, 2650], 0.22, 0.05, 0.13)
        m = t + np.pad(_click(0.2, seed), (0, len(t) - int(0.012 * SR)))
    elif name == "count":
        n = int(1.0 * SR)
        m = np.zeros(n)
        for k in range(10):
            c_ = _click(0.08, seed + k)
            i = int(k * 0.095 * SR)
            m[i:i + len(c_)] += c_
    elif name == "alert":
        a = _tone([660, 1320], 0.18, 0.06, 0.14)
        b = _tone([880, 1760], 0.3, 0.09, 0.14)
        m = np.concatenate([a[:int(0.11 * SR)], b])
    elif name == "merge":
        n = int(0.6 * SR)
        f = np.linspace(700, 1100, n)
        m = (sine(f, n) + sine(f * 1.5, n) * 0.5) * env_adsr(n, 0.05, 0.2, 0.5, 0.3) * 0.08
    elif name == "shuffle":
        n = int(0.5 * SR)
        m = np.zeros(n)
        for k in range(4):
            c_ = _tone([1200 + 200 * k], 0.08, 0.02, 0.08)
            i = int(k * 0.09 * SR)
            m[i:i + len(c_)] += c_
    elif name == "resolve":
        m = _tone([midi(65), midi(69), midi(72), midi(76)], 1.6, 0.6, 0.06, attack=0.03)
    elif name == "converge":
        m = _sweep_noise(1.3, 900, 4000, 200, 800, 0.07, seed, "swell")
    elif name == "logo":
        n = int(3.0 * SR)
        boom = sine(np.linspace(70, 48, n), n) * env_exp(n, 0.5) * 0.22
        bell = _tone([midi(77), midi(84), midi(89)], 3.0, 1.1, 0.07, attack=0.004)
        m = boom + bell
    else:
        raise KeyError(name)
    return pan(m, p)
