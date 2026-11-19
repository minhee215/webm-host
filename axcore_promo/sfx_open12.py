"""AXCORE promo - sound effects for the client's new 00:00:00:00-00:00:12:00 (the reordered facade -> performance
scene, seg_where2, 240 frames, then the hand-over into "업무 분석", seg_insight frames 0-47; 289 frames). The same
sound files and levels as sfx_v3 (assets/sfx, KINDS), timed to this cut: the client's cut was matched frame by frame
against the renders (offset 0), so the cue times are the scenes' own beat times.
Usage: python3 sfx_open12.py <out dir> [preview video] [narration]
Writes AXCORE_SFX_000000-001200.wav (the effects alone, 48 kHz stereo, 289 frames long) and, with a preview video,
AXCORE_SFX_000000-001200_preview.mp4 (the video with the narration + the effects).
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import seg_where2 as W2
import sfx_v3 as V

FPS = V.FPS
NFR = 289
V.DUR = NFR / FPS
V.N = N = int(round(V.DUR * V.SR))
SR = V.SR
HO = W2.NF_DEF / FPS                 # the hand-over's first frame (seg_insight f = 0)
PRESS = HO + 44.6 / FPS              # "업무 분석" pressed (seg_insight A_PRESS - A_C0, the pill lights)


def cues():
    c = []
    a = c.append
    a((0.55, "air", -4, 0.0))                    # the footage flies into the facade windows
    for (n, t0), pan in zip(W2.HOPS, (-0.4, 0.4, 0.0, 0.1)):
        a((t0 + 0.02, "click", -6, pan))          # the brackets hop window to window
    a((W2.SCAN_IN + 0.05, "pling", -6, -0.2))     # the crosshair comes up
    a((W2.SCAN_MOVE + 0.45, "air", -8, 0.0))      # it glides to the target
    a((W2.SCAN_LOCK + 0.02, "pling", -2, 0.0))    # locked
    a((W2.SWEEP_T + 0.35, "air", -5, 0.0))        # the camera closes in, the scan beam runs down
    a((6.50, "whoosh", -1, 0.0))                  # the facade opens into the constellation
    a((W2.PERF_T + 0.75, "rise", -2, 0.0))        # the KPI climbs
    a((W2.END_LOCK + 0.03, "click", -2, 0.2))     # the brackets close on the inspection panel
    a((HO + 0.34, "whoosh", -2, 0.2))             # in on the panel -> the hand
    a((PRESS, "click", 0, 0.0))                   # "업무 분석" pressed
    return c


def main():
    outd = sys.argv[1]
    os.makedirs(outd, exist_ok=True)
    fx = np.zeros((N, 2), np.float32)
    cl = cues()
    for cue in cl:
        t, kind, g, pan = cue[:4]
        V.place(fx, t, kind, g, pan, cue[4] if len(cue) > 4 else None)
    pk = np.abs(fx).max()
    if pk > 0.89:
        fx *= 0.89 / pk
    wav = os.path.join(outd, "AXCORE_SFX_000000-001200.wav")
    sf.write(wav, fx, SR, subtype="PCM_24")
    if len(sys.argv) > 2:
        vid = sys.argv[2]
        narr = sys.argv[3] if len(sys.argv) > 3 else None
        ins = ["-i", vid, "-i", wav] + (["-i", narr] if narr else [])
        af = "[1:a][2:a]amix=inputs=2:normalize=0:duration=first[a]" if narr else "[1:a]anull[a]"
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y"] + ins +
                              ["-filter_complex", "[0:v]scale=854:-2[v];" + af, "-map", "[v]", "-map", "[a]",
                               "-c:v", "libx264", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest",
                               os.path.join(outd, "AXCORE_SFX_000000-001200_preview.mp4")])
    print(len(cl), "cues; peak %.2f" % pk, ["%.2f %s" % (q[0], q[1]) for q in cl])


if __name__ == "__main__":
    main()
