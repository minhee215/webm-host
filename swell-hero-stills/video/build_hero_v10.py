"""S-WELL hero v9: draft-storyboard scenes, trains moving, camera moves, blue-hour grade, straight cuts.
Env RES=480 for a sample."""
import os, subprocess, json
import numpy as np
from PIL import Image
import composite_v6 as v6
from grade import grade

W, H, FPS = 1920, 1080, 24
RES = int(os.environ.get("RES", "1080"))
os.makedirs("tmp", exist_ok=True); os.makedirs("out", exist_ok=True)

# (clip, start, length, grade strength)
# (clip, src start, src length, grade, setpts)  -- native speed, fast-moving source clips
SEG = [("clips/c1.mp4", 0.3, 2.2, 0.45, "T"),
       ("clips/v10_a.mp4", 0.0, 1.3, 1.0, "T"),      # nose rushes toward camera
       ("clips/v10_a.mp4", 3.6, 1.4, 1.0, "T"),      # just passed: light shoots along the rails
       ("clips/v10_b.mp4", 0.5, 3.8, 1.0, "T"),      # aerial track-circuit lights
       ("clips/v10_c.mp4", 0.4, 3.2, 1.0, "T"),      # viaduct data network (ends on the twin clip's start frame)
       ("clips/v10_d.mp4", 0.0, 8.0, 1.0, "T")]      # digital twin -> crane-up, logo
LOGO_SEG, LOGO_T0 = 5, float(__import__('os').environ.get('LOGO_T0', '5.0'))


def tame_cyan(a, w):
    """pull back an over-bright cyan flash by weight w (0..1)"""
    x = a.astype(np.float32)
    m = np.clip((x[..., 2] - x[..., 0] - 90) / 80, 0, 1) * np.clip((x[..., 1] - 170) / 60, 0, 1)
    x = x * (1 - 0.45 * w * m[..., None])
    return np.clip(x, 0, 255).astype(np.uint8)


def dur(p):
    return float(json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                     "-of", "json", p]))["format"]["duration"])


parts = []
def out_len(expr, ln):
    T = ln
    return eval(expr.replace("if(lt(T,2.7),T/1.8,1.5+(T-2.7))", "(T/1.8 if T < 2.7 else 1.5 + (T - 2.7))"))


for i, (src, ss, ln, k, pts) in enumerate(SEG):
    o = f"tmp/v10_p{i}.mp4"
    n = int(round(out_len(pts, ln) * FPS)) - 1
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(ss), "-t", str(ln), "-i", src, "-vf",
                            f"setpts='({pts})/TB',scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", o],
                           stdin=subprocess.PIPE)
    last = None
    for f in range(n):
        b = dec.stdout.read(W * H * 3)
        if len(b) < W * H * 3: b = last
        last = b
        a = np.frombuffer(b, np.uint8).reshape(H, W, 3)
        t = f / FPS
        a = grade(a, k)
        img = Image.fromarray(a)
        if i == LOGO_SEG:
            img = v6.logo(img, 10.4 + (t - LOGO_T0))
        enc.stdin.write(np.asarray(img).tobytes())
    enc.stdin.close(); enc.wait(); dec.kill()
    parts.append(o); print("seg", i, "done", flush=True)

ins = sum([["-i", p] for p in parts], [])
fc = "".join(f"[{i}:v]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1[v]"
subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-an",
                "-c:v", "libx264", "-crf", "12", "-preset", "slow", "tmp/v10_master.mp4"], check=True)
tag = "_480p" if RES == 480 else ""
scale = ["-vf", "scale=-2:480:flags=lanczos"] if RES == 480 else []
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v10_master.mp4", *scale, "-an", "-c:v", "libx264",
                "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "22" if RES == 480 else "23", "-preset", "slow",
                "-movflags", "+faststart", f"out/swell_hero_v10{tag}.mp4"], check=True)
if RES != 480:
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v10_master.mp4", "-an", "-c:v", "libvpx-vp9", "-b:v", "0",
                    "-crf", "34", "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", "out/swell_hero_v10.webm"], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v10_master.mp4", "-frames:v", "1", "-q:v", "3",
                    "out/swell_hero_v10_poster.jpg"], check=True)
print("TOTAL", round(dur(f"out/swell_hero_v10{tag}.mp4"), 2))
