"""Collect SFX cues from every scene, render stems, mix with narration headroom.

Deliverables: renders/audio/{bgm_stem.wav, sfx_stem.wav, master_mix.wav}
BGM sits around -26 dBFS RMS and the master peaks at -3 dBFS, leaving room
for a narration track to be added on top later.
"""
import importlib
import wave

import numpy as np

from .synth import SR, place, reverb
from . import bgm, sfx
from ..utils.config import SCENES, DURATION


def collect_cues():
    cues = []
    for name, start, _ in SCENES:
        mod = importlib.import_module(f"src.scenes.{name}")
        for t, kind, gain in getattr(mod, "SFX", []):
            cues.append((start + t, kind, gain))
    return sorted(cues)


def _write(path, x):
    x = np.clip(x, -1, 1)
    pcm = (x * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def _rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


def build_audio(out_dir):
    n = int(DURATION * SR)
    music = bgm.build()
    music *= 10 ** ((-26 - _rms_db(music)) / 20)
    fx = np.zeros((n, 2))
    for k, (t, kind, gain) in enumerate(collect_cues()):
        place(fx, sfx.make(kind, seed=k), t, gain)
    fx = reverb(fx, 1.2, 0.18, seed=3)
    fx *= 0.9
    master = music + fx
    peak = np.abs(master).max()
    if peak > 10 ** (-3 / 20):
        g = 10 ** (-3 / 20) / peak
        master *= g
        music *= g
        fx *= g
    paths = {"bgm": out_dir / "bgm_stem.wav", "sfx": out_dir / "sfx_stem.wav", "master": out_dir / "master_mix.wav"}
    _write(paths["bgm"], music)
    _write(paths["sfx"], fx)
    _write(paths["master"], master)
    print(f"  audio: bgm {_rms_db(music):.1f} dB rms, sfx {_rms_db(fx):.1f} dB rms, "
          f"master peak {20 * np.log10(np.abs(master).max()):.1f} dBFS")
    return paths
