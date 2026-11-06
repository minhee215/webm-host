"""AXCORE promo - the motion sound effects (sfx_v3) moved onto the client's final cut (119.66 s, 2869 frames).

The final cut was matched frame by frame against the cut sfx_v3 was made on (48x27 grey frames, best match per frame):
  - up to 00:39:21 (frame 957) nothing moved;
  - the diagnosis -> monitor passage (seg_diagmon, 41 frames) sits at frame 948 as delivered; the ceiling / M-AI
    Works toggles after it run 70 frames earlier than before;
  - the workspace -> connect segment (seg_wsapp, 313 frames) sits at frame 1067 (its timeline frame 1137 - 70); its
    cues are new: the app goes up and out, the node pops, 사내 시스템, 외부 SaaS, all connected;
  - from the OCR scene (frame ~1380) to the outro everything runs 3 frames earlier;
  - the outro (seg_outro2) starts at frame 2616: no effects from there (client).
The client's notes from sfx_v3 still hold (no transition swishes 01:25:12-01:43:06 except "실행으로", no rise on
"더 정확하게", nothing in the outro).
Usage: python3 sfx_v4.py <final cut video or its audio> <out dir>
Writes AXCORE_SFX_v5.wav (the effects alone, 48 kHz stereo, the cut's length) and AXCORE_SFX_v5_preview_mix.wav
(the cut's own audio with the effects).
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import sfx_v3 as V

FPS = V.FPS
NFR = 2869
V.DUR = NFR / FPS
V.N = N = int(round(V.DUR * V.SR))
SR = V.SR
END_FX = 2616 / FPS                   # the outro's first frame in the final cut
WS_F0 = 1067                          # seg_wsapp's first frame in the final cut (its timeline frame 1137)


def ws(film):
    """Final-cut time of a seg_wsapp beat (film time)."""
    return (film * 24 - 1137 + WS_F0) / FPS


def remap(t):
    """Final-cut time of an sfx_v3 cue (time in the earlier cut); None where that passage was replaced."""
    f = t * FPS
    if f < 957:
        return t
    if 1050 <= f < 1160:              # the ceiling / M-AI Works toggles, the UI coming down
        return (f - 70) / FPS
    if f >= 1370:                     # OCR -> sphere
        return (f - 3) / FPS
    return None                       # (the old workspace -> connect cues: replaced below)


def cues():
    out = []
    for cue in V.cues():
        t = remap(cue[0])
        if t is not None:
            out.append((t,) + tuple(cue[1:]))
    # the new workspace -> connect (seg_wsapp)
    out += [(1164 / FPS, "whoosh", -3, 0.0),         # the app goes up and out of frame
            (ws(51.90), "pop", -2, 0.0),             # the AXCORE node pops
            (1197 / FPS, "pop", 0, -0.4),            # 사내 시스템 (the panel spreads out of the node)
            (1273 / FPS, "pop", 0, 0.4),             # 외부 SaaS
            (1335 / FPS, "chime", 0, 0.3)]           # all connected (5연결+)
    return sorted(c for c in out if c[0] < END_FX)


def main():
    src, outd = sys.argv[1], sys.argv[2]
    os.makedirs(outd, exist_ok=True)
    fx = np.zeros((N, 2), np.float32)
    cl = cues()
    for cue in cl:
        t, kind, g, pan = cue[:4]
        V.place(fx, t, kind, g, pan, cue[4] if len(cue) > 4 else None)
    cut = int(round(END_FX * SR))                 # nothing runs on into the outro
    fl = int(0.25 * SR)
    fx[cut - fl:cut] *= np.linspace(1, 0, fl)[:, None] ** 2
    fx[cut:] = 0
    pk = np.abs(fx).max()
    if pk > 0.89:
        fx *= 0.89 / pk
    sf.write(os.path.join(outd, "AXCORE_SFX_v5.wav"), fx, SR, subtype="PCM_24")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    base = np.frombuffer(raw, np.float32).reshape(-1, 2)
    base = np.pad(base, ((0, max(0, N - len(base))), (0, 0)))[:N]
    mix = base + fx
    pk = np.abs(mix).max()
    if pk > 0.97:
        mix *= 0.97 / pk
    sf.write(os.path.join(outd, "AXCORE_SFX_v5_preview_mix.wav"), mix, SR, subtype="PCM_24")
    for c in cl:
        fr = int(round(c[0] * FPS))
        print("%7.2f  00:%02d:%02d:%02d  %s" % (c[0], fr // 1440, fr // 24 % 60, fr % 24, c[1]))
    print(len(cl), "cues")


if __name__ == "__main__":
    main()
