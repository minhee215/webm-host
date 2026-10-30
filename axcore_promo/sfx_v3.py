"""AXCORE promo - motion sound effects on the client's re-edited cut (AXCORE_수정본, 119.79 s), after the client's
reference 4: the client's own sound files (assets/sfx: click, pling, pop, whoosh, air, typing, chimes, rise) placed
on the motions, kept sparse (the big moves, the clicks / typing / toggles, a few pop-ins and the logo).

Cue times are the scenes' own beat times (the segment scripts' constants, film time = timeline frame / 24) moved to
the edit: each delivered segment file was matched frame by frame against the cut, which gave how many frames the
client moved it (OFF below); the parts made before (opening, SC05) were placed from the cut's own motion.
Edit time = (film time * 24 + offset frames) / 23.976.

Usage: python3 sfx_v3.py <edit video or its audio> <out dir>
Writes AXCORE_SFX_v3.wav (the effects alone, 48 kHz stereo, the cut's length) and AXCORE_SFX_v3_preview_mix.wav
(the cut's own audio - narration + temporary music - with the effects).
"""
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
SR = 48000
DUR = 119.786
N = int(round(DUR * SR))
FPS = 24000 / 1001

# the sound files: (file, anchor = where in the file the motion lands, level dB, keep seconds)
KINDS = {
    "click": ("click.wav", 0.080, -9.0, 0.45),
    "pling": ("pling.wav", 0.010, -12.0, 0.50),
    "pop": ("pop.wav", 0.012, -9.0, 0.46),
    "whoosh": ("whoosh.wav", 0.64, -13.0, 1.90),
    "air": ("air.wav", 0.81, -9.0, 1.60),
    "chime": ("chime_a.wav", 0.300, -13.0, 1.28),
    "chime_b": ("chime_b.wav", 1.050, -14.0, 1.00),
    "rise": ("rise.wav", 0.230, -17.0, 2.40),
    "type": ("type_short.wav", 0.134, -6.0, 1.00),       # the typing run (without its enter)
    "enter": ("type_short.wav", 1.252, -6.0, 0.20),      # its closing (enter) key
    "type_long": ("type_long.wav", 0.07, -8.0, 4.00),
}


def E(film, off):
    """Edit time of a scene beat (film time) in a segment the client moved by `off` frames."""
    return (film * 24 + off) / FPS


def cues():
    c = []
    a = c.append
    # ---- opening -> SC05 (placed from the cut's own motion)
    a((8.62, "whoosh", 0, -0.3))         # live action into the floating panels
    a((10.75, "air", -2, 0.3))           # into the footage grid
    a((14.75, "whoosh", -2, 0.2))        # in on the hand
    a((16.32, "click", 0, 0.0))          # "업무 분석" pressed
    a((16.55, "air", 0, 0.0))            # zoom-through
    a((17.15, "pling", 0, 0.0))          # the core
    a((21.85, "pop", 0, -0.3))           # DX
    a((22.55, "pop", 0, 0.3))            # AX
    a((23.70, "air", -2, 0.0))           # into the flow
    a((27.60, "air", 0, 0.4))            # the line runs right
    a((29.20, "whoosh", -1, 0.0))        # the line blooms into the search bar
    # ---- AXpoint / M-AI Works (moved +1 frame)
    o = 1
    a((E(30.00, o), "type", 0, 0.0))     # the company name
    a((E(30.85, o), "click", 0, 0.1))    # 기업 찾기
    a((E(32.60, o), "pop", 0, 0.0))      # the files dropped
    a((E(33.05, o), "type_long", -2, 0.0, 0.85))   # the request typed
    a((E(34.05, o), "click", 0, 0.2))    # sent
    a((E(36.55, o), "click", -1, 0.3))   # 진단하기
    a((E(36.95, o), "whoosh", -3, 0.0))  # into the diagnosis
    a((E(38.35, o), "rise", 0, 0.0))     # the AX index polygon blooms
    a((E(39.55, o), "air", -2, 0.0))     # to M-AI Works
    for k in range(5):                   # the five toggles switched on
        a((E(44.60 + 0.45 * k, o), "click", -3, -0.4 + 0.2 * k))
    a((E(46.85, o), "whoosh", -4, 0.0))  # the chosen ones become the workspace
    # ---- workspace -> connect (+1)
    a((E(47.45, o), "air", -2, 0.0))     # the UI comes down to face the lens
    a((E(50.10, o), "pop", 0, -0.4))     # 사내 시스템
    a((E(53.30, o), "pop", 0, 0.4))      # 외부 SaaS
    a((E(56.15, o), "chime", 0, 0.3))    # all connected
    # ---- OCR (placed from the cut)
    a((57.85, "whoosh", -2, 0.0))
    a((59.25, "pop", 0, 0.0))            # the folder
    a((60.00, "air", 0, 0.0))            # the files burst out
    a((61.55, "pop", -1, 0.0))           # the table and the handwritten card
    a((63.10, "pling", -3, 0.2))         # the record lands in the table
    # ---- ontology (+2)
    o = 2
    a((E(63.90, o), "whoosh", -2, 0.0))  # the zoom-out cut
    a((E(70.40, o), "whoosh", 0, 0.0))   # the camera turns frontal ("쫜")
    a((E(71.45, o), "chime", 0, 0.0))    # AXCORE Ontology
    # ---- AI question (+2)
    a((E(74.50, o), "air", -2, 0.0))
    a((E(76.45, o), "whoosh", -3, 0.0))  # they gather behind the search card
    a((E(78.05, o), "type", 0, 0.0))     # the question typed
    a((E(78.92, o), "enter", 0, 0.0))    # ENTER
    a((E(79.05, o), "air", -2, 0.0))     # the question flies to the top
    a((E(80.97, o), "pling", -2, 0.3))   # the answer
    a((E(84.85, o), "click", 0, -0.3))   # 실행
    # ---- ops (+2)
    a((E(85.90, o), "whoosh", 0, 0.0))   # the button's light fills the frame
    a((E(86.45, o), "pop", -2, -0.4))    # 영업팀
    a((E(87.93, o), "pling", -2, -0.2))  # +12.4%
    a((E(88.80, o), "air", -2, 0.4))     # the card travels to the production shot
    a((E(90.36, o), "pop", 0, 0.4))      # anomaly detected
    a((E(91.92, o), "air", -3, -0.3))    # to the robot cell
    a((E(93.16, o), "pling", -4, -0.4))  # the steps checked
    a((E(92.85, o), "chime_b", -4, 0.4))  # the robot cell connected
    # ---- exec (+2)
    a((E(96.85, o), "air", -1, 0.0))     # the shot goes soft, the switch rises
    a((E(98.14, o), "click", 2, 0.0))    # 실행 (the flip lands a little before the narration beat)
    a((E(98.30, o), "whoosh", -1, 0.0))  # the shot snaps open
    # ---- sphere (+3)
    o = 3
    t0 = 100.917
    a((E(t0 + 0.25, o), "air", -2, 0.0))   # the AXCORE logo comes in
    a((E(t0 + 1.55, o), "click", 0, 0.1))  # clicked
    a((E(t0 + 1.60, o), "pling", 0, 0.0))  # the sphere opens
    a((E(t0 + 3.10, o), "whoosh", 0, 0.0))  # the network bursts out
    a((E(t0 + 6.10, o), "rise", 2, 0.0))   # the build into the rush
    a((E(t0 + 7.75, o), "whoosh", 1, 0.0))  # the rush into the core
    # ---- outro (+4)
    o = 4
    t0 = 109.042
    a((E(t0 + 0.30, o), "air", -2, 0.0))   # the white clears onto the presenter
    for j, s_ in enumerate((0.90, 2.00, 2.95, 4.25, 5.45)):   # the collage splits (some of them)
        a((E(t0 + s_, o), "pop", -4 - (j % 2), (-0.5, 0.5)[j % 2]))
    a((E(t0 + 3.50, o), "pling", 0, 0.0))  # the logo builds
    a((E(t0 + 3.98, o), "pop", -2, 0.2))   # its diamond
    a((E(t0 + 8.00, o), "air", -2, 0.0))   # all fades to white
    a((E(t0 + 8.90, o), "chime", 1, 0.0))  # "AXCORE": the light runs over the logo
    return c


_CACHE = {}


def sample(kind):
    if kind not in _CACHE:
        f, anchor, db, keep = KINDS[kind]
        x, sr = sf.read(os.path.join(HERE, "assets", "sfx", f), always_2d=True)
        assert sr == SR
        x = x / (np.abs(x).max() + 1e-9)
        if kind == "enter":
            x = x[int(1.18 * SR):]
            anchor -= 1.18
        _CACHE[kind] = (x.astype(np.float32), anchor, db, keep)
    return _CACHE[kind]


def place(out, t, kind, gain_db, pan, keep=None):
    x, anchor, db, k = sample(kind)
    keep = keep or k
    s0 = int(round((t - anchor) * SR))
    pre = 0
    if s0 < 0:
        pre, s0 = -s0, 0
    x = x[pre:int(keep * SR) + int(anchor * SR) if kind != "type" else int(keep * SR)]
    n = len(x)
    fade = np.ones(n, np.float32)
    fl = min(n // 3, int(0.08 * SR))
    fade[-fl:] = np.linspace(1, 0, fl) ** 2
    g = 10 ** ((db + gain_db) / 20)
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    y = x * fade[:, None] * g
    y = np.stack([y[:, 0] * l * 1.414, y[:, 1] * r * 1.414], 1)
    e = min(N, s0 + n)
    out[s0:e] += y[:e - s0]


def main():
    src, outd = sys.argv[1], sys.argv[2]
    os.makedirs(outd, exist_ok=True)
    fx = np.zeros((N, 2), np.float32)
    cl = cues()
    for cue in cl:
        t, kind, g, pan = cue[:4]
        place(fx, t, kind, g, pan, cue[4] if len(cue) > 4 else None)
    pk = np.abs(fx).max()
    if pk > 0.89:
        fx *= 0.89 / pk
    sf.write(os.path.join(outd, "AXCORE_SFX_v3.wav"), fx, SR, subtype="PCM_24")
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    base = np.frombuffer(raw, np.float32).reshape(-1, 2)
    base = np.pad(base, ((0, max(0, N - len(base))), (0, 0)))[:N]
    mix = base + fx
    pk = np.abs(mix).max()
    if pk > 0.97:
        mix *= 0.97 / pk
    sf.write(os.path.join(outd, "AXCORE_SFX_v3_preview_mix.wav"), mix, SR, subtype="PCM_24")
    print(len(cl), "cues; fx peak %.2f" % pk)


if __name__ == "__main__":
    main()
