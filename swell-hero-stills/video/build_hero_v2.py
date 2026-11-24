"""S-WELL hero video v2: 3 beats, < 10 s, silent, 1920x1080 @24fps.

1) train run            clips/c1.mp4
2) one continuous take  clips/l1.mp4 (coords -> TC -> data -> TCPS) + clips/l2.mp4 (digital twin + AI)
3) ending               clips/e1.mp4 (neon rail -> S symbol) + hold with custom wordmark

Outputs: out/swell_hero_v2.mp4, out/swell_hero_v2.webm, out/swell_hero_v2_poster.jpg
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
os.makedirs("out", exist_ok=True)
os.makedirs("tmp", exist_ok=True)
W, H, FPS = 1920, 1080, 24
XF = 0.3
HOLD = 1.6
FONT_DIR = "/usr/share/fonts/opentype/inter/"


def run(cmd):
    print(" ".join(map(str, cmd)))
    subprocess.run(list(map(str, cmd)), check=True)


def dur(p):
    return float(json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", p]))["format"]["duration"])


def seg(src, ss, out_len, speed, out):
    vf = (f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,"
          f"crop={W}:{H},fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-ss", ss, "-t", out_len * speed, "-i", src,
         "-vf", vf, "-an", "-c:v", "libx264", "-crf", 14, "-preset", "medium", out])


# 1) segments
seg("clips/c1.mp4", 0.3, 1.8, 1.0, "tmp/v2_a.mp4")
seg("clips/l1.mp4", 0.0, 2.5, 2.0, "tmp/v2_b1.mp4")
seg("clips/l2.mp4", 0.0, 2.2, 2.3, "tmp/v2_b2.mp4")
seg("clips/e1.mp4", 0.0, 2.3, 2.2, "tmp/v2_c1.mp4")

# continuous take: hard join (l1 end frame == l2 start frame)
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v2_b1.mp4", "-i", "tmp/v2_b2.mp4", "-filter_complex",
     "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-crf", 14, "tmp/v2_b.mp4"])

# 2) ending: last frame of morph -> measure symbol -> build wordmark overlay
run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.05", "-i", "tmp/v2_c1.mp4", "-frames:v", 1, "tmp/v2_last.png"])
last = np.asarray(Image.open("tmp/v2_last.png").convert("RGB")).astype(int)
r, g, b = last[..., 0], last[..., 1], last[..., 2]
mask = (b > 200) & (g > 130) & (r < 180)
mask[int(H * 0.55):, :] = False          # ignore the rail on the ground
mask[:, int(W * 0.6):] = False
ys, xs = np.nonzero(mask)
x0, y0, x1, y1 = np.percentile(xs, 1), np.percentile(ys, 1), np.percentile(xs, 99), np.percentile(ys, 99)
print("symbol bbox", int(x0), int(y0), int(x1), int(y1))
sym_h = y1 - y0
cy = (y0 + y1) / 2

ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
word_size = int(sym_h * 0.50)
f_word = ImageFont.truetype(FONT_DIR + "InterDisplay-ExtraBoldItalic.otf", word_size)
f_tag = ImageFont.truetype(FONT_DIR + "Inter-Medium.otf", int(word_size * 0.30))
f_tag_b = ImageFont.truetype(FONT_DIR + "Inter-SemiBold.otf", int(word_size * 0.30))
tx = int(x1 + sym_h * 0.12)
word = "S-WELL"
wb = d.textbbox((0, 0), word, font=f_word)
word_h = wb[3] - wb[1]
ty = int(cy - word_h * 0.78) - wb[1]
# soft glow behind wordmark
glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(glow).text((tx, ty), word, font=f_word, fill=(90, 170, 255, 170))
ov = Image.alpha_composite(ov, glow.filter(ImageFilter.GaussianBlur(14)))
d = ImageDraw.Draw(ov)
d.text((tx, ty), word, font=f_word, fill=(245, 250, 255, 255))
# tagline = the required closing line, read with the wordmark: "S-WELL / TCPS makes Rail AI possible."
line_y = ty + wb[3] + int(word_size * 0.22)
x = tx + 4
for t, f, c in [("TCPS ", f_tag_b, (120, 200, 255, 255)), ("makes Rail AI possible.", f_tag, (225, 235, 248, 255))]:
    d.text((x, line_y), t, font=f, fill=c)
    x += d.textlength(t, font=f)
ov.save("tmp/v2_wordmark.png")

# hold = frozen last frame + wordmark fading/sliding in
run(["ffmpeg", "-y", "-v", "error", "-loop", 1, "-t", HOLD, "-i", "tmp/v2_last.png",
     "-loop", 1, "-t", HOLD, "-i", "tmp/v2_wordmark.png", "-filter_complex",
     f"[0:v]fps={FPS},format=yuv420p[bg];"
     f"[1:v]fps={FPS},format=rgba,fade=t=in:st=0:d=0.5:alpha=1[wm];"
     f"[bg][wm]overlay=x='-40*max(0,1-t/0.6)':y=0,format=yuv420p[v]",
     "-map", "[v]", "-c:v", "libx264", "-crf", 14, "tmp/v2_c2.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v2_c1.mp4", "-i", "tmp/v2_c2.mp4", "-filter_complex",
     "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-crf", 14, "tmp/v2_c.mp4"])

# 3) assemble with crossfades between the three beats
parts = ["tmp/v2_a.mp4", "tmp/v2_b.mp4", "tmp/v2_c.mp4"]
lens = [dur(p) for p in parts]
fc, prev, t = [], "[0:v]", lens[0]
for k in range(1, len(parts)):
    off = t - XF
    fc.append(f"{prev}[{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}]")
    prev, t = f"[x{k}]", off + lens[k]
fc.append(f"{prev}format=yuv420p[vout]")
print("TOTAL", round(t, 2))
if t >= 9.9:
    sys.exit("too long")
ins = sum([["-i", p] for p in parts], [])
run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", ";".join(fc), "-map", "[vout]",
     "-an", "-c:v", "libx264", "-crf", 12, "-preset", "slow", "tmp/v2_master.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v2_master.mp4", "-an", "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuv420p", "-crf", 23, "-preset", "slow", "-movflags", "+faststart", "out/swell_hero_v2.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v2_master.mp4", "-an", "-c:v", "libvpx-vp9", "-b:v", 0, "-crf", 34,
     "-row-mt", 1, "-deadline", "good", "-cpu-used", 2, "out/swell_hero_v2.webm"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v2_master.mp4", "-frames:v", 1, "-q:v", 3, "out/swell_hero_v2_poster.jpg"])
for f in ["out/swell_hero_v2.mp4", "out/swell_hero_v2.webm"]:
    print(f, round(dur(f), 2), "s", round(os.path.getsize(f) / 1e6, 2), "MB")
