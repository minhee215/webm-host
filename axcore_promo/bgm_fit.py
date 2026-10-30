"""Fit the client's AXCORE_BGM (154.8 s) to the final cut (119.786 s) with one musical splice.

The music's repeating middle is shortened by 34.61 s (a whole number of its phrases, found as the shift where the
music best matches itself, 2 s either side): it jumps from 39.40 s to 74.01 s, under the cut's cross-blur into
M-AI Works, with a 120 ms equal-power crossfade, sample-aligned by waveform correlation. That lands the music's final
hit (143.43 s) at 108.82 s, on the rush into the white flash before the outro, and its own ending at the cut's end.
Usage: python3 bgm_fit.py <AXCORE_BGM.mp3/wav> <out.wav>
"""
import subprocess
import sys

import numpy as np
import soundfile as sf

SR = 48000
DUR = 119.786
A, R = 39.40, 34.61


def main():
    src, out = sys.argv[1], sys.argv[2]
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    ia, ib = int(A * SR), int((A + R) * SR)
    w, s = int(0.08 * SR), int(0.015 * SR)
    ref = x[ia - w // 2:ia + w // 2].mean(1)
    ib += max(range(-s, s + 1, 4), key=lambda d: np.dot(ref, x[ib + d - w // 2:ib + d + w // 2].mean(1)))
    xf = int(0.12 * SR)
    g = np.linspace(0, 1, xf)
    y = np.concatenate([x[:ia - xf // 2],
                        x[ia - xf // 2:ia + xf // 2] * np.cos(g * np.pi / 2)[:, None]
                        + x[ib - xf // 2:ib + xf // 2] * np.sin(g * np.pi / 2)[:, None],
                        x[ib + xf // 2:]])
    n = int(round(DUR * SR))
    y = np.pad(y, ((0, max(0, n - len(y))), (0, 0)))[:n]
    fo = int(0.5 * SR)
    y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    sf.write(out, y, SR, subtype="PCM_24")


if __name__ == "__main__":
    main()
