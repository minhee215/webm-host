#!/usr/bin/env python3
"""Sub-pixel global-motion stabiliser for the generated clips.

Generated image-to-video clips carry a small high-frequency camera jitter
(0.3-0.6 px RMS at 720p) on top of the intended slow move. This estimates
frame-to-frame translation and zoom with phase correlation (sub-pixel),
smooths the camera path with a wide Gaussian, and re-renders each frame
with the residual removed, so only the intended smooth move remains.

Usage (library): frames = stabilize(frames_uint8_list)  -> list of uint8 frames
"""
import numpy as np
from PIL import Image


def _gray(f, s=2):
    g = f.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    h, w = g.shape
    return g[: h // s * s, : w // s * s].reshape(h // s, s, w // s, s).mean((1, 3))


def _win(shape):
    return np.outer(np.hanning(shape[0]), np.hanning(shape[1])).astype(np.float32)


def _phase(a, b, win):
    A = np.fft.rfft2((a - a.mean()) * win)
    B = np.fft.rfft2((b - b.mean()) * win)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-6
    r = np.fft.irfft2(R, s=a.shape)
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    h, w = r.shape

    def sub(c, m1, p1):
        d = (m1 - p1) / (2 * (m1 - 2 * c + p1) + 1e-9)
        return float(np.clip(d, -0.5, 0.5))
    dy = iy + sub(r[iy, ix], r[(iy - 1) % h, ix], r[(iy + 1) % h, ix])
    dx = ix + sub(r[iy, ix], r[iy, (ix - 1) % w], r[iy, (ix + 1) % w])
    if dy > h / 2: dy -= h
    if dx > w / 2: dx -= w
    return dx, dy


def motion(frames, s=2):
    """Per-frame (dx, dy, log-zoom) relative to previous frame, full-res px.
    Zoom is estimated from the translation of four quadrant patches."""
    g = [_gray(f, s) for f in frames]
    h, w = g[0].shape
    ph, pw = h // 2, w // 2
    win_full, win_q = _win((h, w)), _win((ph, pw))
    out = [(0.0, 0.0, 0.0)]
    quads = [(0, 0), (0, pw), (ph, 0), (ph, pw)]
    centres = np.array([[pw / 2 - w / 2, ph / 2 - h / 2], [pw * 1.5 - w / 2, ph / 2 - h / 2],
                        [pw / 2 - w / 2, ph * 1.5 - h / 2], [pw * 1.5 - w / 2, ph * 1.5 - h / 2]])
    for a, b in zip(g[1:], g[:-1]):
        dx, dy = _phase(a, b, win_full)
        q = np.array([_phase(a[y:y + ph, x:x + pw], b[y:y + ph, x:x + pw], win_q) for y, x in quads])
        # q_i ~ t + k * c_i  -> least squares for zoom k
        rel = q - np.array([dx, dy])
        k = float((rel * centres).sum() / (centres ** 2).sum())
        out.append((dx * s, dy * s, np.log1p(k)))
    return np.array(out)


def _gauss_smooth(x, sigma):
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(x, r, mode="edge"), k, "valid")


def stabilize(frames, sigma=10.0, margin=1.04):
    """Remove high-frequency camera jitter; keep the smooth intended move.
    margin: fixed zoom so corrections never expose the frame edge."""
    m = motion(frames)
    path = np.cumsum(m, axis=0)                     # x, y, log-zoom
    smooth = np.stack([_gauss_smooth(path[:, i], sigma) for i in range(3)], 1)
    corr = smooth - path                             # what to add back
    h, w = frames[0].shape[:2]
    out = []
    for f, (cx, cy, cz) in zip(frames, corr):
        z = margin * np.exp(cz)
        # output pixel (u,v) samples input at centre + (u-centre)/z - shift
        a = 1 / z
        tx = w / 2 - a * w / 2 - cx
        ty = h / 2 - a * h / 2 - cy
        img = Image.fromarray(f).transform((w, h), Image.Transform.AFFINE, (a, 0, tx, 0, a, ty),
                                           resample=Image.Resampling.BICUBIC)
        out.append(np.asarray(img))
    return out, m, corr


def jitter(frames, sigma=3.0):
    """High-frequency camera motion (px RMS, max) — for verification."""
    m = motion(frames)
    p = np.cumsum(m[:, :2], axis=0)
    s = np.stack([_gauss_smooth(p[:, i], sigma) for i in range(2)], 1)
    r = np.hypot(*(p - s).T)
    return float(np.sqrt((r ** 2).mean())), float(r.max())
