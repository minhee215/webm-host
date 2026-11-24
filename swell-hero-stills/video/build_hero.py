"""Assemble the S-WELL hero video from Kling clips.

Usage: python3 build_hero.py
Inputs : clips/c1.mp4 .. clips/c6.mp4, ../stills_v6/scene6_4_logo_final.png
Outputs: out/swell_hero.mp4 (H.264), out/swell_hero.webm (VP9), out/swell_hero_poster.jpg
Silent (no audio track), 1920x1080, 30fps, total < 10s.
"""
import subprocess, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
os.makedirs("out", exist_ok=True)
os.makedirs("tmp", exist_ok=True)

W, H, FPS = 1920, 1080, 24
XF = 0.3  # crossfade seconds

# (clip, start_sec, length_sec, speed)  speed>1 = faster
SEG = [
    ("clips/c1.mp4", 0.3, 1.7, 1.0),
    ("clips/c2.mp4", 0.4, 1.5, 1.0),
    ("clips/c3.mp4", 0.3, 1.5, 1.0),
    ("clips/c4b.mp4", 0.2, 1.5, 1.0),
    ("clips/c5.mp4", 0.3, 1.5, 1.0),
    ("clips/c6.mp4", 0.4, 2.3, 2.0),   # rail -> symbol morph, 2x speed
]
LOGO_IMG = "../stills_v6/scene6_4_logo_final.png"
LOGO_LEN = 1.5


def run(cmd):
    print(" ".join(cmd))
    subprocess.run(cmd, check=True)


def dur(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])


parts = []
for i, (src, ss, ln, sp) in enumerate(SEG, 1):
    o = f"tmp/p{i}.mp4"
    # take ln*sp seconds of source, speed it to ln seconds
    take = ln * sp
    vf = f"setpts=PTS/{sp},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p"
    run(["ffmpeg", "-y", "-v", "error", "-ss", str(ss), "-t", str(take), "-i", src,
         "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14", "-preset", "medium", o])
    parts.append((o, ln))

# logo hold with a gentle push-in
o = "tmp/p7.mp4"
frames = int(LOGO_LEN * FPS)
run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(LOGO_LEN), "-i", LOGO_IMG,
     "-vf", f"scale=2688:1520,zoompan=z='1+0.03*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},format=yuv420p",
     "-an", "-c:v", "libx264", "-crf", "14", o])
parts.append((o, LOGO_LEN))

# chain crossfades
inputs = []
for p, _ in parts:
    inputs += ["-i", p]
fc = []
prev = "[0:v]"
t = parts[0][1]
for k in range(1, len(parts)):
    off = t - XF
    lab = f"[v{k}]"
    fc.append(f"{prev}[{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}{lab}")
    prev = lab
    t = off + parts[k][1]
fc.append(f"{prev}format=yuv420p[vout]")  # no fade-in: seamless loop
total = t
print("TOTAL", round(total, 2), "s")
if total > 9.8:
    sys.exit("total must be < 10s")

master = "tmp/master.mp4"
run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[vout]",
     "-an", "-c:v", "libx264", "-crf", "12", "-preset", "slow", master])

# web deliverables (silent)
run(["ffmpeg", "-y", "-v", "error", "-i", master, "-an", "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuv420p", "-crf", "23", "-preset", "slow", "-movflags", "+faststart", "out/swell_hero.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", master, "-an", "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "34",
     "-row-mt", "1", "-deadline", "good", "-cpu-used", "2", "out/swell_hero.webm"])
run(["ffmpeg", "-y", "-v", "error", "-i", master, "-frames:v", "1", "-q:v", "3", "out/swell_hero_poster.jpg"])
for f in ["out/swell_hero.mp4", "out/swell_hero.webm"]:
    print(f, round(dur(f), 2), "s", round(os.path.getsize(f) / 1e6, 2), "MB")
