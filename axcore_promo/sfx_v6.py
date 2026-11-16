"""AXCORE promo - the motion sound effects on the client's edit of 2026-11-16 (103.896 s, 2491 frames: the new 10 s
facade -> performance opening and its hand-over, then the rest with passages sped up / re-timed and the AXpoint
pages re-ordered). The same sound files, levels and choices as sfx_v3 / sfx_v4 (the client's notes still hold: sparse
effects, no rise on "더 정확하게", nothing in the outro), each cue placed again on this cut's own motion: the cut was
stepped through and every cue's event found by its frame (a click on the frame its ripple / highlight appears, a pop
on the frame its element comes in, a whoosh / air landing on its move's peak). 00:00-12:00 is sfx_open12 as
delivered (the cut matches it frame for frame).
Usage: python3 sfx_v6.py <cut video> <out dir> [bgm.wav]
Writes AXCORE_SFX_v6.wav (the effects alone, 48 kHz stereo, the cut's length) and AXCORE_SFX_v6_preview.mp4 (a small
copy of the cut with its narration, the effects and - given the fitted music - the music under them).
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

import sfx_open12 as O
import sfx_v3 as V

FPS = V.FPS
NFR = 2491
V.DUR = NFR / FPS
V.N = N = int(round(V.DUR * V.SR))
SR = V.SR
END_FX = 93.55                        # the white flash into the outro: no effects from here (client)


def fr(f):
    return f / FPS


def cues():
    c = list(O.cues())                                   # 00:00-12:00 (seg_where2 + the hand-over)
    a = c.append
    # ---- SC05
    a((12.10, "air", 0, 0.0))                            # zoom-through into the navy map
    a((fr(297), "pling", 0, 0.0))                        # the core
    a((fr(401), "pop", 0, -0.3))                         # DX
    a((fr(415), "pop", 0, 0.3))                          # AX
    a((19.20, "air", -2, 0.0))                           # into the flow
    a((22.80, "air", 0, 0.4))                            # the line runs right
    a((23.80, "whoosh", -1, 0.0))                        # the line blooms into the search bar
    # ---- AXpoint
    a((fr(585), "type", 0, 0.0))                         # the company name
    a((fr(604), "click", 0, 0.1))                        # 기업 찾기
    a((fr(646), "pop", 0, 0.0))                          # the files dropped
    a((27.25, "type_long", -2, 0.0, 0.85))               # the request typed
    a((fr(683), "click", 0, 0.2))                        # sent
    a((fr(747), "click", -1, 0.3))                       # 진단 결과 보기
    a((31.60, "whoosh", -3, 0.0))                        # into the diagnosis
    a((33.00, "rise", 0, 0.0))                           # the AX index polygon blooms
    a((34.35, "air", -2, 0.0))                           # the page becomes the browser over the man
    # ---- ceiling (AXunion toggles, frames where each switches on)
    for k, f in enumerate((866, 874, 884, 888, 895)):
        a((fr(f), "click", -3, -0.4 + 0.2 * k))
    a((37.75, "whoosh", -4, 0.0))                        # the chosen ones become the workspace
    a((38.30, "air", -2, 0.0))                           # the workspace page
    # ---- workspace -> connect
    a((fr(940), "whoosh", -3, 0.0))                      # the app goes up and out of frame
    a((fr(942), "pop", -2, 0.0))                         # the AXCORE node pops
    a((fr(950), "pop", 0, -0.4))                         # 사내 시스템
    a((fr(1055), "pop", 0, 0.4))                         # 외부 SaaS
    a((46.90, "chime", 0, 0.3))                          # all connected
    # ---- OCR
    a((48.00, "whoosh", -2, 0.0))
    a((48.40, "pop", 0, 0.0))                            # the folder
    a((fr(1185), "air", 0, 0.0))                         # the files burst out
    a((fr(1219), "pop", -1, 0.0))                        # the table and the handwritten card
    a((fr(1250), "pling", -3, 0.2))                      # the record lands in the table
    # ---- ontology
    a((fr(1289), "whoosh", -2, 0.0))                     # the zoom-out cut
    a((60.20, "whoosh", 0, 0.0))                         # the camera turns frontal
    a((60.85, "chime", 0, 0.0))                          # AXCORE Ontology
    # ---- AI question
    a((64.60, "air", -2, 0.0))
    a((fr(1589), "whoosh", -3, 0.0))                     # they gather behind the search card
    a((67.45, "type", 0, 0.0))                           # the question typed
    a((fr(1641), "enter", 0, 0.0))                       # ENTER
    a((68.75, "air", -2, 0.0))                           # the question flies to the top
    a((70.85, "pling", -2, 0.3))                         # the answer
    a((fr(1788), "click", 0, -0.3))                      # 실행
    # ---- ops
    a((fr(1826), "pop", -2, -0.4))                       # 영업
    a((fr(1858), "pling", -2, -0.2))                     # the forecast
    a((fr(1914), "pop", 0, 0.4))                         # anomaly detected
    a((81.80, "pling", -4, -0.4))                        # the steps checked
    a((fr(1996), "chime_b", -4, 0.4))                    # the robot cell connected
    # ---- exec
    a((fr(2069.6), "click", 2, 0.0))                     # 분석 -> 실행 flips
    a((86.65, "whoosh", -1, 0.0))                        # the shot snaps open
    # ---- sphere
    a((89.15, "click", 0, 0.1))                          # clicked
    a((89.20, "pling", 0, 0.0))                          # the sphere opens
    a((90.65, "whoosh", 0, 0.0))                         # the network bursts out
    a((93.20, "whoosh", 1, 0.0))                         # the rush into the white
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
    wav = os.path.join(outd, "AXCORE_SFX_v6.wav")
    sf.write(wav, fx, SR, subtype="PCM_24")
    # preview: the cut's narration + the effects (+ the music, lower, ducked a little under the voice)
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
                           "-b:a", "192k", "-shortest", os.path.join(outd, "AXCORE_SFX_v6_preview.mp4")])
    os.remove(tmp)
    for q in cl:
        f = int(round(q[0] * FPS))
        print("%7.2f  00:%02d:%02d:%02d  %s" % (q[0], f // 1440, f // 24 % 60, f % 24, q[1]))
    print(len(cl), "cues")


if __name__ == "__main__":
    main()
