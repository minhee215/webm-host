#!/usr/bin/env python3
"""AXCORE promo film - renderer.

  python3 render.py                       # full film -> out/axcore_promo.mp4
  python3 render.py --stills 10,30.5      # preview stills -> out/stills/
  python3 render.py --range 58 68         # render a time range (no audio)
  python3 render.py --seed new --chaos 0.5

Same seed + chaos always reproduces the identical frame (the seed is printed and
written next to the output so a good take can be kept).
"""
import argparse
import os
import subprocess
import sys
import time
from multiprocessing import Pool

import numpy as np
import skia

import engine as E
import scenes as S

OUT = os.path.join(E.HERE, "out")


def make_surface():
    info = skia.ImageInfo.Make(E.W, E.H, skia.ColorType.kRGBA_8888_ColorType, skia.AlphaType.kPremul_AlphaType)
    return skia.Surface.MakeRaster(info)


class Renderer:
    def __init__(self):
        self.main = make_surface()
        self.sa = make_surface()
        self.sb = make_surface()
        self.finish = E.Finish()

    def _draw(self, i, T, surf):
        name, t0, t1, fn = S.SCENES[i]
        c = surf.getCanvas()
        c.save()
        c.clear(skia.Color4f(0, 0, 0, 1))
        fn(c, T, T - t0, t1 - t0)
        c.restore()

    def _transition(self, T, i):
        name, t0, t1, _ = S.SCENES[i]
        if i > 0 and name in S.TRANS:
            typ, dur, kw = S.TRANS[name]
            if T < t0 + dur / 2:
                return i - 1, i, typ, dur, kw, t0
        if i + 1 < len(S.SCENES):
            nxt = S.SCENES[i + 1][0]
            if nxt in S.TRANS:
                typ, dur, kw = S.TRANS[nxt]
                if T >= t1 - dur / 2:
                    return i, i + 1, typ, dur, kw, t1
        return None

    def frame(self, f):
        T = f / E.FPS
        i = max(k for k, sc in enumerate(S.SCENES) if sc[1] <= T + 1e-9)
        tr = self._transition(T, i)
        c = self.main.getCanvas()
        if tr is None:
            self._draw(i, T, self.main)
        else:
            a, b, typ, dur, kw, bd = tr
            p = E.clamp((T - (bd - dur / 2)) / dur)
            self._draw(a, T, self.sa)
            self._draw(b, T, self.sb)
            A = self.sa.makeImageSnapshot()
            B = self.sb.makeImageSnapshot()
            if callable(kw):
                kw = kw(T)
            c.save()
            c.clear(skia.Color4f(0, 0, 0, 1))
            E.TRANSITIONS[typ](c, A, B, p, **kw)
            c.restore()
        return self.finish.apply(self.main, f)


_R = None


def _init(seed, chaos, plates):
    global _R
    if plates:
        E.PLATE_DIR = plates
    E.configure(seed, chaos)
    _R = Renderer()


def _render_chunk(job):
    k, f0, f1, path = job
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (E.W, E.H),
           "-r", str(E.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
           "-g", "48", "-bf", "2", "-movflags", "+faststart", path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t = time.time()
    for f in range(f0, f1):
        proc.stdin.write(_R.frame(f).tobytes())
    proc.stdin.close()
    proc.wait()
    return k, f1 - f0, time.time() - t


def _render_still(T):
    from PIL import Image
    f = int(round(T * E.FPS))
    img = Image.fromarray(_R.frame(f))
    path = os.path.join(OUT, "stills", "f%06.2f.jpg" % T)
    img.save(path, quality=90)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default=str(E.SEED), help="int, or 'new' for a fresh seed")
    ap.add_argument("--chaos", type=float, default=E.CHAOS)
    ap.add_argument("--plates", default=None)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--stills", default=None, help="comma separated times (s)")
    ap.add_argument("--range", nargs=2, type=float, default=None)
    ap.add_argument("--out", default=os.path.join(OUT, "axcore_promo.mp4"))
    ap.add_argument("--no-audio", action="store_true")
    ap.add_argument("--webm", action="store_true", help="also export a VP9 webm")
    args = ap.parse_args()

    seed = int(np.random.SeedSequence().entropy % 2 ** 31) if args.seed == "new" else int(args.seed)
    print("seed=%d chaos=%.2f" % (seed, args.chaos), flush=True)
    os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
    initargs = (seed, args.chaos, args.plates)

    if args.stills:
        times = [float(x) for x in args.stills.split(",")]
        with Pool(min(args.workers, len(times)), _init, initargs) as pool:
            for p in pool.imap(_render_still, times):
                print(p, flush=True)
        return

    t0, t1 = (0.0, S.DURATION) if args.range is None else args.range
    f0, f1 = int(round(t0 * E.FPS)), int(round(t1 * E.FPS))
    n = f1 - f0
    nchunks = max(1, min(n // 12, args.workers * 3))
    bounds = np.linspace(f0, f1, nchunks + 1).astype(int)
    cdir = os.path.join(OUT, "chunks")
    os.makedirs(cdir, exist_ok=True)
    jobs = [(k, bounds[k], bounds[k + 1], os.path.join(cdir, "c%03d.mp4" % k)) for k in range(nchunks)]
    start = time.time()
    done = 0
    with Pool(args.workers, _init, initargs) as pool:
        for k, nf, dt in pool.imap_unordered(_render_chunk, jobs):
            done += nf
            print("chunk %03d  %4d frames  %.1fs  [%d/%d  %.0fs]" % (k, nf, dt, done, n, time.time() - start),
                  flush=True)
    lst = os.path.join(cdir, "list.txt")
    with open(lst, "w") as fh:
        for j in jobs:
            fh.write("file '%s'\n" % j[3])
    video = args.out.replace(".mp4", "_video.mp4")
    subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                           "-c", "copy", video])
    if args.no_audio or args.range is not None:
        os.replace(video, args.out)
    else:
        import audio
        wav = os.path.join(OUT, "mix.wav")
        audio.build_mix(wav)
        subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map",
                               "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest",
                               "-movflags", "+faststart", args.out])
        os.remove(video)
        if args.webm:
            webm = args.out.replace(".mp4", ".webm")
            subprocess.check_call(["ffmpeg", "-loglevel", "error", "-y", "-i", args.out, "-c:v", "libvpx-vp9",
                                   "-b:v", "0", "-crf", "30", "-row-mt", "1", "-deadline", "good", "-cpu-used", "4",
                                   "-c:a", "libopus", "-b:a", "160k", webm])
    with open(args.out + ".seed.txt", "w") as fh:
        fh.write("seed=%d chaos=%.2f\n" % (seed, args.chaos))
    print("done in %.0fs -> %s" % (time.time() - start, args.out), flush=True)


if __name__ == "__main__":
    sys.exit(main())
