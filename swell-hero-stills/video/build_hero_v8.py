"""S-WELL hero v8: draft-storyboard scenes, straight cuts, no fades, centred logo over the final crane-up.

1 clips/c1.mp4    train run (Han river viaduct)
2 clips/v8_a.mp4  rail-level coordinates
3 clips/v8_b.mp4  aerial track-circuit lights
4 clips/v8_c.mp4  viaduct data network          \\ continuous (shared keyframe)
5 clips/v8_d.mp4  network -> digital twin        |
6 clips/v8_e.mp4  twin crane-up + logo draw-on  /
Env: RES=480 for a sample (default 1080).
"""
import os, subprocess, json
import numpy as np
from PIL import Image
import composite_v6 as v6     # logo lockup (centred) + look

W, H, FPS = 1920, 1080, 24
RES = int(os.environ.get("RES", "1080"))
os.makedirs("tmp", exist_ok=True); os.makedirs("out", exist_ok=True)

# (clip, start, length)  -- native speed only
SEG = [("clips/c1.mp4", 0.3, 2.4), ("clips/v8_a.mp4", 0.9, 3.0), ("clips/v8_b.mp4", 1.4, 3.4),
       ("clips/v8_c.mp4", 0.6, 4.2), ("clips/v8_d.mp4", 0.0, 4.6), ("clips/v8_e.mp4", 0.0, 4.9)]
COOL = {3, 4}     # remove warm/red train lights (keep amber piers lower in frame)


def cool_lights(a):
    a = a.astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = (r > g + 35) & (r > b + 35) & (r > 120)
    m[int(H * 0.68):] = False
    v = np.maximum(r, np.maximum(g, b))
    a[..., 0] = np.where(m, v * 0.85, r); a[..., 1] = np.where(m, v * 0.95, g); a[..., 2] = np.where(m, v, b)
    return np.clip(a, 0, 255).astype(np.uint8)
LOGO_SEG = 5
LOGO_T0 = 1.3     # logo starts this many seconds into the last segment


def run(c): subprocess.run(list(map(str, c)), check=True)


def dur(p):
    return float(json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                     "-of", "json", p]))["format"]["duration"])


parts = []
for i, (src, ss, ln) in enumerate(SEG):
    o = f"tmp/v8_p{i}.mp4"
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
    if i != LOGO_SEG and i not in COOL:
        run(["ffmpeg", "-y", "-v", "error", "-ss", ss, "-t", ln, "-i", src, "-vf", vf, "-an",
             "-c:v", "libx264", "-crf", 14, o])
    else:   # draw the logo frame-by-frame over the crane-up
        n = int(round(ln * FPS))
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-t", str(ln + 0.2), "-i", src, "-vf", vf.replace(",format=yuv420p", ""),
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                                "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", o],
                               stdin=subprocess.PIPE)
        last = None
        for k in range(n):
            b = dec.stdout.read(W * H * 3)
            if len(b) < W * H * 3: b = last
            last = b
            arr = np.frombuffer(b, np.uint8).reshape(H, W, 3)
            if i in COOL:
                img = Image.fromarray(cool_lights(arr))
            else:
                img = v6.logo(Image.fromarray(arr), 10.4 + (k / FPS - LOGO_T0))   # v6.logo timeline starts at 10.4 s
            enc.stdin.write(np.asarray(img).tobytes())
        enc.stdin.close(); enc.wait(); dec.kill()
    parts.append(o)

ins = sum([["-i", p] for p in parts], [])
fc = "".join(f"[{i}:v]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1[v]"
run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-an",
     "-c:v", "libx264", "-crf", 12, "-preset", "slow", "tmp/v8_master.mp4"])
tag = "_480p" if RES == 480 else ""
scale = ["-vf", "scale=-2:480:flags=lanczos"] if RES == 480 else []
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v8_master.mp4", *scale, "-an", "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuv420p", "-crf", 22 if RES == 480 else 23, "-preset", "slow", "-movflags", "+faststart",
     f"out/swell_hero_v8{tag}.mp4"])
if RES != 480:
    run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v8_master.mp4", "-an", "-c:v", "libvpx-vp9", "-b:v", 0, "-crf", 34,
         "-row-mt", 1, "-deadline", "good", "-cpu-used", 2, "out/swell_hero_v8.webm"])
    run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v8_master.mp4", "-frames:v", 1, "-q:v", 3, "out/swell_hero_v8_poster.jpg"])
print("TOTAL", round(dur(f"out/swell_hero_v8{tag}.mp4"), 2))
