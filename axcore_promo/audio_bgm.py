"""AXCORE promo film - soundtrack v5: supplied BGM + narration (with pauses) + light UI/emphasis effects.

The picture is unchanged (v4, 120.0 s). This builds the audio track only:

- Narration: the supplied read with the v4 pauses spliced into its silences (same as the film).
- BGM: the supplied track (104.0 BPM, F major, 154.8 s) shortened by exactly 14 bars (32.31 s) with
  one bar-aligned seam at 39.35 s (chosen by chroma/level similarity, under the voice). With that
  edit the track's quiet build lands on "더 빠른 판단…", its drop hits as the AX is revealed and its
  final hit lands on "AXCORE" (logo).
- Mix: sidechain ducking under the voice (music swells back up in the pauses), effects tuned to
  F major pentatonic: taps/pops on tablet touches, chimes on completion, pings on the ontology
  entities, scan ticks for OCR, typing on the question, an alert on the anomaly, three emphasis hits
  on the closing lines, a swell into the ontology title, a shimmer on the logo. No transition effects.

Usage: python3 audio_bgm.py /path/to/AXCORE_BGM.mp3 [out.mp3]
"""
import os
import subprocess
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

import audio as A
import scenes as S

SR = A.SR
BPM = 104.005
BEAT = 60.0 / BPM
PHASE = 0.125                 # first beat of the BGM (s)
CUT = PHASE + 68 * BEAT       # 39.354 s: bar-aligned seam
SKIP = 56 * BEAT              # 14 bars = 32.307 s
XF = 0.06                     # equal-power crossfade at the seam
LEAD = 0.16                   # start the track this far in so its final hit lands on the spoken "AXCORE"

F_PENTA = [77, 79, 81, 84, 86, 89, 91, 93]   # F G A C D (F major pentatonic, octave 5-6)

# scene clock -> film time
OFF = {n: s0 - t0 for (n, t0, _), (_, s0, _, _) in zip(S._TIMELINE, S.SCENES)}


def film(scene, t):
    return t + OFF[scene]


def sec(t):
    return int(round(t * SR))


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x).astype(np.float32)


def hp(x, fc):
    return sosfilt(butter(2, fc, "high", fs=SR, output="sos"), x).astype(np.float32)


def lp(x, fc):
    return sosfilt(butter(2, fc, "low", fs=SR, output="sos"), x).astype(np.float32)


# ---------------------------------------------------------------- BGM edit
def load_bgm(path, total):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32).reshape(-1, 2)[sec(LEAD):]
    c, s, xf = sec(CUT - LEAD), sec(SKIP), sec(XF)   # seam on the BGM's bar line
    res = np.zeros((total, 2), np.float32)
    res[:c - xf] = x[:c - xf]
    w = np.linspace(0, np.pi / 2, 2 * xf)[:, None]
    res[c - xf:c + xf] = x[c - xf:c + xf] * np.cos(w) + x[c - xf + s:c + xf + s] * np.sin(w)   # equal power
    rest = x[c + xf + s:]
    n = min(len(rest), total - (c + xf))
    res[c + xf:c + xf + n] = rest[:n]
    # tail: the track's own ending decays from ~118.4 s; finish cleanly at 120.0
    tl = np.arange(total) / SR
    fade = np.clip((120.0 - tl) / 1.1, 0, 1) ** 1.5
    return res * fade[:, None].astype(np.float32)


# ---------------------------------------------------------------- effects (synthesized, short, quiet)
class Bus:
    def __init__(self, total):
        self.x = np.zeros((total, 2), np.float32)
        self.total = total

    def add(self, t, sig, gain=1.0, pan=0.0):
        i0 = sec(t)
        if i0 < 0 or i0 >= self.total:
            return
        if sig.ndim == 1:
            sig = np.stack([sig * (1 - pan), sig * (1 + pan)], 1)
        n = min(len(sig), self.total - i0)
        self.x[i0:i0 + n] += sig[:n] * gain


RNG = np.random.default_rng(21)


def tap():
    """Glass tap: tiny filtered click + short high blip."""
    n = sec(0.06)
    tt = np.arange(n) / SR
    click = bp(RNG.standard_normal(n).astype(np.float32), 2500, 9000) * np.exp(-tt * 260)
    blip = np.sin(2 * np.pi * 3150 * tt) * np.exp(-tt * 90) * 0.5
    return (click * 0.8 + blip).astype(np.float32)


def pop(m, up=True, dur=0.16):
    """Soft UI pop: a quick pitch glide into a pentatonic note."""
    n = sec(dur)
    tt = np.arange(n) / SR
    f1 = mtof(m)
    f = f1 * (0.82 + 0.18 * (1 - np.exp(-tt * 60))) if up else f1 * (1.15 - 0.3 * (1 - np.exp(-tt * 40)))
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = (1 - np.exp(-tt * 900)) * np.exp(-tt * 22)
    return ((np.sin(ph) + 0.25 * np.sin(2 * ph)) * e).astype(np.float32)


def chime(notes, spread=0.07, dur=1.4):
    n = sec(dur + spread * len(notes))
    out = np.zeros(n, np.float32)
    for k, m in enumerate(notes):
        i0 = sec(k * spread)
        tt = np.arange(n - i0) / SR
        f = mtof(m)
        w = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.0 * tt) * np.exp(-tt * 4) +
             0.12 * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt * 7)) * np.exp(-tt * 3.2) * (1 - np.exp(-tt * 600))
        out[i0:] += w.astype(np.float32)
    return out / len(notes) ** 0.5


def ping(m):
    """Data ping for the ontology entities: bell with a soft shimmer."""
    n = sec(1.6)
    tt = np.arange(n) / SR
    f = mtof(m)
    w = (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 2.6) + 0.35 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt * 6) +
         0.15 * np.sin(2 * np.pi * (f * 4.07) * tt) * np.exp(-tt * 9)) * (1 - np.exp(-tt * 500))
    return w.astype(np.float32)


def scan(dur=0.45):
    n = sec(dur)
    tt = np.arange(n) / SR
    nz = RNG.standard_normal(n).astype(np.float32)
    y = np.zeros(n, np.float32)
    blocks = 12
    for k in range(blocks):
        a, z = k * n // blocks, (k + 1) * n // blocks
        fc = 3000 + 5000 * k / blocks
        y[a:z] = bp(nz[a:z], fc * 0.8, min(fc * 1.25, SR * 0.45))
    e = np.sin(np.pi * tt / dur) ** 2
    return (y * e * 0.5).astype(np.float32)


def key_click():
    n = sec(0.035)
    tt = np.arange(n) / SR
    return (bp(RNG.standard_normal(n).astype(np.float32), 1800, 7000) * np.exp(-tt * 180) +
            np.sin(2 * np.pi * 1200 * tt) * np.exp(-tt * 300) * 0.3).astype(np.float32)


def alert():
    n = sec(0.62)
    tt = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k, m in enumerate((84, 81)):
        i0 = sec(k * 0.2)
        t2 = tt[:n - i0]
        out[i0:] += (np.sin(2 * np.pi * mtof(m) * t2) * np.exp(-t2 * 9) * (1 - np.exp(-t2 * 800))).astype(np.float32)
    return out


def impact(size=1.0):
    """Cinematic emphasis hit: sub drop + body + air, short room tail."""
    n = sec(2.4)
    tt = np.arange(n) / SR
    f = 42 + 60 * np.exp(-tt * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 3.0)
    body = lp(RNG.standard_normal(n).astype(np.float32), 900) * np.exp(-tt * 22) * 0.7
    air = hp(RNG.standard_normal(n).astype(np.float32), 5000) * np.exp(-tt * 9) * 0.12
    return ((sub + body + air) * size).astype(np.float32)


def swell(dur=1.8):
    """Reverse swell that lands exactly on its end time (emphasis, not a transition)."""
    n = sec(dur)
    tt = np.arange(n) / SR
    nz = RNG.standard_normal(n).astype(np.float32)
    y = bp(nz, 1500, 9000) * 0.5 + np.sin(2 * np.pi * mtof(65) * tt) * 0.25 + np.sin(2 * np.pi * mtof(72) * tt) * 0.18
    e = (tt / dur) ** 3.0
    return (y * e).astype(np.float32)


def shimmer(dur=2.6):
    n = sec(dur)
    tt = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for k, m in enumerate((89, 93, 96, 101)):
        i0 = sec(k * 0.09)
        t2 = tt[:n - i0]
        out[i0:] += (np.sin(2 * np.pi * mtof(m) * t2) * np.exp(-t2 * 2.2) * (1 - np.exp(-t2 * 400)) * 0.5).astype(np.float32)
    return out


def hologram(dur=0.8):
    n = sec(dur)
    tt = np.arange(n) / SR
    f = mtof(72) * (1 + 1.0 * (tt / dur) ** 1.5)
    w = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur) ** 2
    nz = bp(RNG.standard_normal(n).astype(np.float32), 4000, 10000) * np.sin(np.pi * tt / dur) ** 2 * 0.25
    return ((w * 0.6 + nz) * 0.6).astype(np.float32)


def room(x, mix=0.22):
    n = sec(1.1)
    tt = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = (RNG.standard_normal(n) * np.exp(-tt * 5.5)).astype(np.float32)
        ir[:sec(0.01)] = 0
        ir /= np.sqrt((ir ** 2).sum())
        out[:, ch] = fftconvolve(x[:, ch], ir)[:len(x)]
    return x * (1 - mix) + out * mix * 1.4


def effects(total):
    ui = Bus(total)       # interface sounds (taps, pops, chimes, pings)
    fx = Bus(total)       # emphasis (impacts, swells, shimmer)
    CUE = S.CUE
    # AXpoint: files arrive, checks, level ring, hero task
    for i in range(6):
        ui.add(film("sc07", S.AP_A + 0.25 + i * 0.14), tap(), 0.35, -0.2 + i * 0.08)
        ui.add(film("sc07", S.AP_A + 1.2 + i * 0.12), pop(F_PENTA[i % 5] + 12, dur=0.1), 0.12)
    ui.add(film("sc07", S.AP_A + 2.5), chime([81, 84, 89]), 0.22)
    for i in range(6):
        ui.add(film("sc07", S.AP_B + 0.15 + i * 0.18), tap(), 0.22, -0.3 + i * 0.12)
    ui.add(film("sc07", S.AP_C + 0.3 + 2 * 0.32 + 0.45), chime([84, 89, 93]), 0.28)
    # enterprise: panel projects up, each tap sends a module, one removed, workspace complete
    ui.add(film("sc09", 33.95), hologram(), 0.32)
    for i in range(8):
        t = film("sc09", S.ENT_ADD0 + i * S.ENT_ADDS - 0.05)
        ui.add(t, tap(), 0.5, 0.25)
        ui.add(t + 0.03, pop(F_PENTA[i % 8]), 0.26, -0.3 + i * 0.08)
        ui.add(film("sc09", S.ENT_ADD0 + i * S.ENT_ADDS + 0.45), key_click(), 0.18)
    ui.add(film("sc09", S.ENT_RM_T + 0.15), tap(), 0.5, 0.25)
    ui.add(film("sc09", S.ENT_RM_T + 0.2), pop(79, up=False, dur=0.22), 0.3)
    ui.add(film("sc09", S.ENT_DONE), chime([77, 81, 84, 89]), 0.3)
    # personal: tap lifts each app, it docks and connects
    for i, (_, _, cue, _) in enumerate(S.SC12_APPS):
        c = CUE[cue]
        ui.add(film("sc12", c - 0.25), tap(), 0.5, 0.2)
        ui.add(film("sc12", c - 0.2), pop([84, 86, 89][i], dur=0.22), 0.3)
        ui.add(film("sc12", c + 0.75 + 0.55), key_click(), 0.25)
        ui.add(film("sc12", c + 0.75 + 0.55 + 0.05), chime([[89], [91], [93]][i], dur=0.9), 0.2)
    for j in range(3):
        ui.add(film("sc12", 51.75 + j * 0.14), pop(F_PENTA[j + 2] + 12, dur=0.1), 0.12)
    # OCR: files -> data, each handwritten row underlined
    for i in range(4):
        ui.add(film("sc13", CUE["FILES"] + i * 0.18), tap(), 0.3, -0.4 + i * 0.1)
    ui.add(film("sc13", CUE["FILES"] + 0.6), pop(84), 0.2)
    for i in range(4):
        t0 = CUE["OCR"] + 0.3 + i * 0.34
        ui.add(film("sc13", t0), scan(0.5), 0.3, -0.1)
        ui.add(film("sc13", t0 + 0.75), pop(F_PENTA[i + 1] + 12, dur=0.1), 0.12, 0.4)
    # ontology: an ascending ping for each entity, the flow pulse, the AI core, the title
    for i, key in enumerate(("EQUIP", "MATER", "PROC", "PROD", "PEOPLE", "TASK")):
        ui.add(film("sc14", CUE[key] - 0.08), ping(F_PENTA[i] + 0), 0.24, -0.5 + i * 0.2)
    ui.add(film("sc14", S.ON_PULSE0), hologram(S.ON_PULSE1), 0.18)
    ui.add(film("sc14", 64.2), chime([77, 84, 89, 93]), 0.26)
    title = film("sc14", CUE["ONTO"] - 0.1)
    fx.add(title - 1.6, swell(1.6), 0.22)
    fx.add(title, impact(0.8), 0.5)
    fx.add(title, shimmer(), 0.12)
    # Q&A: typing the question, the answer and the context tags
    q = S.SC16_Q
    for k in range(len(q)):
        if q[k] != " ":
            ui.add(film("sc16", 72.25 + 0.8 * k / len(q)) + RNG.uniform(-0.01, 0.01), key_click(), 0.22, RNG.uniform(-0.2, 0.2))
    ui.add(film("sc16", CUE["L20b"] - 0.05), pop(84), 0.22)
    for key in ("L21", "CAUSE", "CTX"):
        ui.add(film("sc16", CUE[key] - 0.05), pop({"L21": 81, "CAUSE": 84, "CTX": 89}[key], dur=0.12), 0.16)
    # use cases
    ui.add(film("sc17", 79.7), pop(89), 0.18)
    ui.add(film("sc18", 82.5), alert(), 0.2)
    for i in range(4):
        ui.add(film("sc19", CUE["L24"] + i * 0.25 + 1.1), pop(F_PENTA[i + 1] + 12, dur=0.1), 0.13)
    ui.add(film("sc19", CUE["L24b"] + 0.6), chime([84, 89]), 0.2)
    ui.add(film("sc20", 89.9), tap(), 0.4)
    # finale: vertex ticks of the three video shapes, emphasis hit on each closing line, logo
    for name, poly_ax, src, t_on, tgt in S.AX_PIECES[:3]:
        for j in range(len(poly_ax)):
            ui.add(t_on + j * 0.06, key_click(), 0.16, -0.3 + j * 0.15)
    fx.add(S.CUEN["L28"] - 1.5, swell(1.5), 0.16)
    for t in (S.CUEN["L28"], S.CUEN["L29"], S.CUEN["L30"]):
        fx.add(t - 0.03, impact(0.9), 0.55)
    for name, poly_ax, src, t_on, tgt in S.AX_PIECES[3:]:
        ui.add(t_on, key_click(), 0.1)
    fx.add(S.CUEN["L32"] - 0.02, shimmer(3.0), 0.16)
    fx.add(S.CUEN["L32"] - 0.02, impact(0.6), 0.3)
    return room(ui.x, 0.25), room(fx.x, 0.18)


# ---------------------------------------------------------------- mix
def lufs(x):
    """Integrated loudness via ffmpeg ebur128 (stereo float32)."""
    p = subprocess.run(["ffmpeg", "-loglevel", "info", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-i", "-",
                        "-af", "ebur128=framelog=quiet", "-f", "null", "-"], input=x.astype(np.float32).tobytes(),
                       capture_output=True)
    for ln in p.stderr.decode(errors="ignore").splitlines()[::-1]:
        if ln.strip().startswith("I:"):
            return float(ln.split()[1])
    return None


def build(bgm_path, out_mp3):
    total = int(S.DURATION * SR)
    narr = A.load_narration(total)
    narr = np.stack([narr, narr], 1)
    music = load_bgm(bgm_path, total)
    ui, fx = effects(total)
    # level targets: voice -16 LUFS, music -20 LUFS before ducking (~14 dB under the voice while it speaks), effects sit just under the voice
    narr *= A.db(-16.0 - lufs(narr))
    music *= A.db(-20.0 - lufs(music))
    # sidechain: fast attack, slow release -> the music dips ~9 dB under the voice and swells in the pauses
    e = A.rms_env(narr[:, 0])
    e /= e.max() + 1e-9
    duck = (1 - 0.65 * np.clip(e * 3.0, 0, 1))[:, None]
    ui_duck = (1 - 0.35 * np.clip(e * 3.0, 0, 1))[:, None]
    ui *= A.db(-14.0) / (np.abs(ui).max() + 1e-9) * 2.2
    fx *= A.db(-9.0) / (np.abs(fx).max() + 1e-9)
    mix = narr + music * duck + ui * ui_duck + fx * (1 - 0.25 * np.clip(e * 3, 0, 1))[:, None]
    # loudness normalise for web (-14 LUFS) with a -1 dBFS ceiling (soft limiter)
    mix *= A.db(-14.0 - lufs(mix))
    ceil = A.db(-1.0)
    mix = np.where(np.abs(mix) > ceil * 0.8, np.sign(mix) * (ceil * 0.8 + (ceil * 0.2) *
                                                            np.tanh((np.abs(mix) - ceil * 0.8) / (ceil * 0.2))), mix)
    wav = out_mp3.replace(".mp3", ".wav")
    import wave
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libmp3lame", "-b:a", "320k", out_mp3])
    print("final loudness %.1f LUFS, peak %.2f dBFS" % (lufs(mix), 20 * np.log10(np.abs(mix).max())))
    return out_mp3


if __name__ == "__main__":
    bgm = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(A.HERE, "out", "axcore_audio_v5.mp3")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print(build(bgm, out))
