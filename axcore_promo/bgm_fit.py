"""Fit the client's AXCORE_BGM (154.8 s) to the final cut (119.786 s) with one musical splice.

The music's repeating middle is shortened by 34.61 s (a whole number of its phrases, found as the shift where the
music best matches itself, 2 s either side): it jumps from 39.40 s to 74.01 s, under the cut's cross-blur into
M-AI Works, with a 120 ms equal-power crossfade, sample-aligned by waveform correlation. That lands the music's final
hit (143.43 s) at 108.82 s, on the rush into the white flash before the outro, and its own ending at the cut's end.
The client's final cut (2869 frames, 119.66 s) runs 3 frames shorter from the OCR scene on; the splice stays (a
shift of a fraction of a beat would break the rhythm), so the hit falls 3 frames later in the same white rush, and
the music is cut to the new length (pass it as the third argument).
The client's edit of 2026-11-16 (103.896 s, 2491 frames; the new 10 s facade -> performance opening, sped-up
passages): 22 bars (50.77 s) out in one splice at 30.98 s -> 81.75 s (a bar line, the best-matching 22-bar shift in
the first half, under the narration on the AXpoint flow page), so the final hit lands at 92.66 s, as the logo
network starts its rush into the white flash before the outro.
The client's edit of 2026-11-19 (103.52 s, 2482 frames; the landing page cut out): the 22-bar cut fell mid-phrase
(audible at 00:31). The track runs in 8-bar phrases (bar b and b+8 match far better than b+4 or b+2), so now the
cut is 16 bars (36.92 s), from the start of a phrase (bar 16, 37.905 s) to the same place in the phrase 16 bars on
(bar 32, 74.83 s), where both sides are the same material (chroma similarity 0.82 / 0.95, level within 2 dB), with a
200 ms crossfade; it falls under the new transition's white opening (23.80 s). The rest of the length comes off the
start: the track begins 14.107 s in (inside its intro), faded in over 1.2 s. The final hit lands at 92.40 s, as the
white flash before the outro builds (the same place against it as before), and the music's own ending at the end.
Usage: python3 bgm_fit.py <AXCORE_BGM.mp3/wav> <out.wav> [length s] [splice_at s] [removed s] [start s] [xfade s]
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
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    a_, r_ = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (A, R)
    s0 = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
    xfs = float(sys.argv[7]) if len(sys.argv) > 7 else 0.12
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    ia, ib = int(a_ * SR), int((a_ + r_) * SR)
    w, s = int(0.08 * SR), int(0.015 * SR)
    ref = x[ia - w // 2:ia + w // 2].mean(1)
    ib += max(range(-s, s + 1, 4), key=lambda d: np.dot(ref, x[ib + d - w // 2:ib + d + w // 2].mean(1)))
    xf = int(xfs * SR)
    g = np.linspace(0, 1, xf)
    y = np.concatenate([x[:ia - xf // 2],
                        x[ia - xf // 2:ia + xf // 2] * np.cos(g * np.pi / 2)[:, None]
                        + x[ib - xf // 2:ib + xf // 2] * np.sin(g * np.pi / 2)[:, None],
                        x[ib + xf // 2:]])
    if s0 > 0:                                   # start inside the track, faded in
        y = y[int(s0 * SR):]
        fi = int(1.2 * SR)
        y[:fi] *= np.sin(np.linspace(0, np.pi / 2, fi))[:, None] ** 2
    n = int(round(dur * SR))
    y = np.pad(y, ((0, max(0, n - len(y))), (0, 0)))[:n]
    fo = int(0.5 * SR)
    y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
    sf.write(out, y, SR, subtype="PCM_24")


if __name__ == "__main__":
    main()
