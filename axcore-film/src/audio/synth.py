"""Small numpy synthesis toolkit (no external samples)."""
import numpy as np

SR = 48000


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def env_adsr(n, a=0.01, d=0.1, s=0.7, r=0.2, hold=None):
    a_n, d_n, r_n = int(a * SR), int(d * SR), int(r * SR)
    h_n = max(0, n - a_n - d_n - r_n) if hold is None else int(hold * SR)
    e = np.concatenate([np.linspace(0, 1, max(a_n, 1)), np.linspace(1, s, max(d_n, 1)),
                        np.full(h_n, s), np.linspace(s, 0, max(r_n, 1))])
    return np.pad(e, (0, max(0, n - len(e))))[:n]


def env_exp(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))


def onepole_lp(x, cutoff):
    """Time-varying one-pole low-pass (cutoff: float or array in Hz)."""
    cut = np.broadcast_to(np.asarray(cutoff, dtype=np.float64), x.shape)
    a = np.exp(-2 * np.pi * cut / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):          # small loops only (sfx); pads use fft_lp
        acc = (1 - a[i]) * x[i] + a[i] * acc
        y[i] = acc
    return y


def fft_band(x, lo=20.0, hi=20000.0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def saw(freq, n, phase=0.0):
    ph = (np.cumsum(np.full(n, freq) / SR) + phase) % 1.0
    return 2 * ph - 1


def sine(freq, n, phase=0.0):
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (n,))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)


def noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def reverb(x, seconds=2.2, wet=0.25, seed=1):
    """Convolution with a synthetic exponentially decaying stereo noise IR."""
    n = int(seconds * SR)
    out = []
    for ch in range(2):
        ir = noise(n, seed + ch) * env_exp(n, seconds / 6.5)
        ir = fft_band(ir, 200, 9000)
        ir /= np.sqrt((ir ** 2).sum())
        src = x[:, ch] if x.ndim == 2 else x
        L = len(src) + n
        nfft = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(src, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(src)]
        out.append(y)
    wet_sig = np.stack(out, 1)
    dry = x if x.ndim == 2 else np.stack([x, x], 1)
    return dry * (1 - wet) + wet_sig * wet


def pan(mono, p=0.0):
    l = np.cos((p + 1) * np.pi / 4)
    r = np.sin((p + 1) * np.pi / 4)
    return np.stack([mono * l, mono * r], 1)


def place(bus, sig, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(bus):
        return
    j = min(len(bus), i + len(sig))
    bus[i:j] += sig[: j - i] * gain
