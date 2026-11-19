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
(v7b, client: the music must start quiet and build as before, not start mid-way) The track plays from its start
again. Its intro (bars 0-7) runs in 2-bar patterns (bars 2/3 and 4 nearly the same, chroma 0.87-0.91): bars 2-3 are
played twice, which adds 2 bars inside the quiet intro; then at the intro's end (bar 8, 19.44 s, a phrase start) it
goes on from bar 32 (74.83 s), the same material (0.89 / 0.95), so 24 bars (3 phrases) come out. The body kicks in at
24.06 s, as the new transition's white page opens; the final hit lands at 92.66 s in the white flash's rise.
(v7c, client: the 2-bar repeat inside the intro is heard - a phrase coming back at 10 s) No repeat: the track plays
from its start to the end of its intro (bar 8), then on from bar 32 (24 bars out, one phrase-aligned join at the
intro's end); the 2 bars that the repeat used to add come instead from starting the track 4.40 s into the film (its
first seconds are a fade-in from silence anyway). The body kicks in at 23.84 s, as the new transition's white page
opens; the final hit lands at 92.45 s in the white flash's rise.
(v7d, client: music from the very start, the intro not slowed, and the stretch from ~01:05 is too calm) From the
start; at the intro's end (bar 8, 19.44 s, under SC05's move into the flow) on from bar 16 (8 bars out, chroma
0.89 / 0.97); then the calm part goes: from bar 41 (77.14 s in the film) on from bar 55 (14 bars out, 0.79 / 0.88,
level within 1.8 dB), the louder part, the breakdown and the hit as before. 22 bars out in all: the hit at 92.66 s.
(v7e, client: from 01:17 it suddenly goes calm) Bars 55-58 belong to the same calm part as 48-54 (same chords, sparse),
so the whole calm part (bars 48-58) goes: the loud body runs to the end of its phrase (bar 47) and drops straight
into the breakdown (bar 59) before the hit, at 86.37 s, where it was before. 8 bars at the intro's end (bar 8 -> 16) +
11 calm bars = 19; the other 3 come off the track's start (it opens 6.92 s in, inside the quiet intro, faded in
over 1 s), so the music still sounds from the first second, the body starts at 12.52 s and the hit stays at 92.66 s.
(v7f, client: keep the whole quiet intro) The intro plays from the track's start, untouched; the 3 bars that came
off the start come out of the body instead: it drops into the breakdown 3 bars earlier in the music (from bar 45 into
bar 59), at the same moment in the film (86.37 s). 8 + 14 = 22 bars out; the hit at 92.66 s.
  --edl a:b,c:d,...  play these spans of the track (s) one after another, crossfaded (xfade s) at sample-aligned joins
  --delay s          the track starts this far into the film
Usage: python3 bgm_fit.py <AXCORE_BGM.mp3/wav> <out.wav> [length s] [splice_at s] [removed s] [start s] [xfade s]
       python3 bgm_fit.py <AXCORE_BGM.mp3/wav> <out.wav> <length s> --edl a:b,c:d,... [xfade s]
"""
import subprocess
import sys

import numpy as np
import soundfile as sf

SR = 48000
DUR = 119.786
A, R = 39.40, 34.61


def edl_join(x, spans, xfs):
    """The track's spans one after another, each join an equal-power crossfade between the old span running on
    past its end and the new one already running before its start (aligned to the sample by correlation)."""
    xf, s, w = int(xfs * SR), int(0.015 * SR), int(0.08 * SR)
    h = xf // 2
    pe = int(spans[0][1] * SR)
    parts = [x[int(spans[0][0] * SR):pe - h]]
    for a, b in spans[1:]:
        ia, ib = int(a * SR), int(b * SR)
        ref = x[pe - w // 2:pe + w // 2].mean(1)
        ia += max(range(-s, s + 1, 4), key=lambda d: np.dot(ref, x[ia + d - w // 2:ia + d + w // 2].mean(1)))
        g = np.linspace(0, 1, 2 * h)
        parts.append(x[pe - h:pe + h] * np.cos(g * np.pi / 2)[:, None] + x[ia - h:ia + h] * np.sin(g * np.pi / 2)[:, None])
        parts.append(x[ia + h:min(ib, len(x)) - h] if ib < len(x) else x[ia + h:])
        pe = ib
    return np.concatenate(parts)


def main():
    src, out = sys.argv[1], sys.argv[2]
    if "--edl" in sys.argv:
        k = sys.argv.index("--edl")
        spans = [tuple(float(v) for v in q.split(":")) for q in sys.argv[k + 1].split(",")]
        xfs = float(sys.argv[k + 2]) if len(sys.argv) > k + 2 and not sys.argv[k + 2].startswith("--") else 0.2
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le",
                              "-"], capture_output=True, check=True).stdout
        x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
        spans = [(a, min(b, len(x) / SR)) for a, b in spans]
        y = edl_join(x, spans, xfs)
        if spans[0][0] > 0:                      # opening inside the track: faded in
            fi = int(1.0 * SR)
            y[:fi] *= np.sin(np.linspace(0, np.pi / 2, fi))[:, None] ** 2
        if "--delay" in sys.argv:
            y = np.concatenate([np.zeros((int(float(sys.argv[sys.argv.index("--delay") + 1]) * SR), 2)), y])
        n = int(round(float(sys.argv[3]) * SR))
        y = np.pad(y, ((0, max(0, n - len(y))), (0, 0)))[:n]
        fo = int(0.5 * SR)
        y[-fo:] *= np.linspace(1, 0, fo)[:, None] ** 2
        sf.write(out, y, SR, subtype="PCM_24")
        return
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
