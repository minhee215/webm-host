"""AXCORE promo - the sound effects on the client's edit of 2026-11-19 (103.52 s, 2482 frames): the landing page
(search, 기업 찾기) cut out and the new transition (trans_axp: the line draws into the diamond, it becomes the
'파일 업로드' dot, the page opens from it) in its place, 00:00-16:09 and 34:02-41:09 re-timed, a few passages after
41 s lengthened / shortened by the client.
The cues are sfx_v6's (placed on the 2026-11-16 edit by its own motion), carried over through a frame-by-frame match of
the two edits (every frame of this edit matched to the old one's, kept monotone, simplified to the knots below); the
landing page's cues (the bloom into the search bar, the typing, 기업 찾기) go, the new transition gets its own.
Usage: python3 sfx_v7.py <cut video> <out dir> [bgm.wav]
Writes AXCORE_SFX_v7.wav (the effects alone, 48 kHz stereo, the cut's length) and AXCORE_SFX_v7_preview.mp4.
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import sfx_v6 as V6
import sfx_v3 as V

FPS = V.FPS
NFR = 2482
V.DUR = NFR / FPS
V.N = N = int(round(V.DUR * V.SR))
SR = V.SR
# old edit frame -> this edit's frame (frame match, monotone, simplified to 0.75 frame)
KNOTS = [(0, 1.0), (204, 204.0), (206, 205.0), (238, 234.0), (239, 236.0), (260, 259.0), (277, 279.0), (278, 281.0),
         (285, 288.0), (291, 301.0), (321, 331.0), (323, 332.0), (385, 392.0), (393, 393.0), (552, 552.0),
         (641, 602.0), (937, 899.0), (939, 905.0), (940, 906.0), (942, 912.0), (944, 920.0), (945, 922.0),
         (953, 945.0), (962, 953.0), (969, 956.0), (972, 959.0), (1004, 979.0), (1012, 985.0), (1024, 986.0),
         (1077, 1039.0), (1079, 1042.0), (1085, 1047.0), (1477, 1439.0), (1481, 1442.0), (1487, 1449.0),
         (1600, 1562.0), (1608, 1568.0), (1611, 1571.0), (1612, 1577.0), (1619, 1584.0), (1634, 1596.0),
         (1652, 1614.0), (1656, 1619.0), (1659, 1620.0), (1663, 1624.0), (1664, 1626.0), (2055, 2017.0),
         (2061, 2021.0), (2062, 2024.0), (2121, 2083.0), (2129, 2094.0), (2138, 2103.0), (2145, 2112.0),
         (2148, 2117.0), (2159, 2129.0), (2160, 2132.0), (2165, 2137.0), (2174, 2149.0), (2188, 2165.0),
         (2190, 2169.0), (2195, 2174.0), (2215, 2199.0), (2219, 2203.0), (2223, 2209.0), (2227, 2213.0),
         (2237, 2226.0), (2249, 2239.0), (2489, 2479.0), (2490, 2481.0)]
KO = np.array([k[0] for k in KNOTS], float)
KN = np.array([k[1] for k in KNOTS], float)
TR0 = 553                              # the new transition's first frame in this edit (48 frames)
DROP = (23.79, 25.30)                  # old-edit times of the landing page's cues (gone with it)
END_FX = float(np.interp(V6.END_FX * FPS, KO, KN)) / FPS


def to_new(t):
    return float(np.interp(t * FPS, KO, KN)) / FPS


def cues():
    c = []
    for q in V6.cues():
        if DROP[0] <= q[0] <= DROP[1]:
            continue
        c.append((to_new(q[0]),) + tuple(q[1:]))
    # the new transition (trans_axp; its frame k = TR0 + k here)
    c.append(((TR0 + 16) / FPS, "pling", -4, 0.0))     # the diamond has become the '파일 업로드' dot
    c.append(((TR0 + 24) / FPS, "air", -3, 0.0))       # the page opens from it
    return sorted(q for q in c if q[0] < END_FX)


def main():
    src, outd = sys.argv[1], sys.argv[2]
    bgm = sys.argv[3] if len(sys.argv) > 3 else None
    os.makedirs(outd, exist_ok=True)
    fx = np.zeros((N, 2), np.float32)
    cl = cues()
    for cue in cl:
        t, kind, g, pan = cue[:4]
        V.place(fx, t, kind, g, pan, cue[4] if len(cue) > 4 else None)
    cut = int(round(END_FX * SR))
    fl = int(0.25 * SR)
    fx[cut - fl:cut] *= np.linspace(1, 0, fl)[:, None] ** 2
    fx[cut:] = 0
    pk = np.abs(fx).max()
    if pk > 0.89:
        fx *= 0.89 / pk
    sf.write(os.path.join(outd, "AXCORE_SFX_v7.wav"), fx, SR, subtype="PCM_24")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    base = np.frombuffer(raw, np.float32).reshape(-1, 2)
    base = np.pad(base, ((0, max(0, N - len(base))), (0, 0)))[:N].astype(np.float64)
    mix = base + fx
    if bgm:
        m, _ = sf.read(bgm, always_2d=True)
        m = np.pad(m, ((0, max(0, N - len(m))), (0, 0)))[:N]
        env = np.sqrt(np.convolve((base ** 2).mean(1), np.ones(int(0.3 * SR)) / int(0.3 * SR), "same"))
        duck = 1 - 0.45 * np.clip(env / 0.05, 0, 1)
        mix = mix + m * 0.30 * duck[:, None]
    pk = np.abs(mix).max()
    if pk > 0.97:
        mix *= 0.97 / pk
    tmp = os.path.join(outd, "_preview_audio.wav")
    sf.write(tmp, mix, SR, subtype="PCM_16")
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-i", tmp, "-map", "0:v", "-map", "1:a",
                           "-vf", "scale=1280:-2", "-c:v", "libx264", "-crf", "22", "-preset", "fast", "-c:a", "aac",
                           "-b:a", "192k", "-shortest", os.path.join(outd, "AXCORE_SFX_v7_preview.mp4")])
    os.remove(tmp)
    for q in cl:
        f = int(round(q[0] * FPS))
        print("%7.2f  00:%02d:%02d:%02d  %s" % (q[0], f // 1440, f // 24 % 60, f % 24, q[1]))
    print(len(cl), "cues; effects end %.2f" % END_FX)


if __name__ == "__main__":
    main()
