"""S-WELL hero video v4: 3 beats joined by straight cuts. No zoom, no fades.

beat A  clips/c1.mp4                 train run
beat B  clips/l1.mp4 + clips/l2.mp4  one continuous take (coords -> TC -> data/TCPS -> digital twin + AI)
beat C  clips/e1.mp4 + hold          neon rail -> S symbol, then wordmark appears on a cut

Silent, 1920x1080, 24 fps, < 10 s.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
os.makedirs("out", exist_ok=True); os.makedirs("tmp", exist_ok=True)
W, H, FPS = 1920, 1080, 24
HOLD_SYMBOL = 0.3   # symbol alone after the morph
HOLD_LOGO = 1.1     # symbol + wordmark
FD = "/usr/share/fonts/opentype/inter/"


def run(cmd):
    print(" ".join(map(str, cmd))); subprocess.run(list(map(str, cmd)), check=True)


def dur(p):
    return float(json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", p]))["format"]["duration"])


def seg(src, ss, out_len, speed, out):
    run(["ffmpeg", "-y", "-v", "error", "-ss", ss, "-t", out_len * speed, "-i", src, "-vf",
         f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
         "-an", "-c:v", "libx264", "-crf", 14, out])


def still(img, length, out):
    run(["ffmpeg", "-y", "-v", "error", "-loop", 1, "-t", length, "-i", img, "-vf",
         f"scale={W}:{H},fps={FPS},format=yuv420p", "-an", "-c:v", "libx264", "-crf", 14, out])


seg("clips/c1.mp4", 0.3, 1.6, 1.0, "tmp/v4_a.mp4")
seg("clips/l1.mp4", 0.0, 2.3, 2.17, "tmp/v4_b1.mp4")
seg("clips/l2.mp4", 0.0, 2.1, 2.38, "tmp/v4_b2.mp4")
seg("clips/e1.mp4", 0.0, 2.2, 2.27, "tmp/v4_c1.mp4")

# last frame of the morph -> symbol position -> wordmark next to it
run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.05", "-i", "tmp/v4_c1.mp4", "-frames:v", 1, "tmp/v4_last.png"])
last_img = Image.open("tmp/v4_last.png").convert("RGB")
a = np.asarray(last_img).astype(int)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
m = (b > 200) & (g > 130) & (r < 180); m[int(H * 0.55):, :] = False; m[:, int(W * 0.6):] = False
ys, xs = np.nonzero(m)
x0, y0, x1, y1 = np.percentile(xs, 1), np.percentile(ys, 1), np.percentile(xs, 99), np.percentile(ys, 99)
print("symbol bbox", int(x0), int(y0), int(x1), int(y1))
sym_h, cy = y1 - y0, (y0 + y1) / 2
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
ws = int(sym_h * 0.50)
fw = ImageFont.truetype(FD + "InterDisplay-ExtraBoldItalic.otf", ws)
ft = ImageFont.truetype(FD + "Inter-Medium.otf", int(ws * 0.30))
ftb = ImageFont.truetype(FD + "Inter-SemiBold.otf", int(ws * 0.30))
tx = int(x1 + sym_h * 0.12); wb = d.textbbox((0, 0), "S-WELL", font=fw)
ty = int(cy - (wb[3] - wb[1]) * 0.78) - wb[1]
gl = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(gl).text((tx, ty), "S-WELL", font=fw, fill=(90, 170, 255, 170))
ov = Image.alpha_composite(ov, gl.filter(ImageFilter.GaussianBlur(14))); d = ImageDraw.Draw(ov)
d.text((tx, ty), "S-WELL", font=fw, fill=(245, 250, 255, 255))
ly = ty + wb[3] + int(ws * 0.22); x = tx + 4
for t_, f_, c_ in [("TCPS ", ftb, (120, 200, 255, 255)), ("makes Rail AI possible.", ft, (225, 235, 248, 255))]:
    d.text((x, ly), t_, font=f_, fill=c_); x += d.textlength(t_, font=f_)
logo = last_img.convert("RGBA"); logo.alpha_composite(ov); logo.convert("RGB").save("tmp/v4_logo.png")

still("tmp/v4_last.png", HOLD_SYMBOL, "tmp/v4_c2.mp4")
still("tmp/v4_logo.png", HOLD_LOGO, "tmp/v4_c3.mp4")

parts = ["tmp/v4_a.mp4", "tmp/v4_b1.mp4", "tmp/v4_b2.mp4", "tmp/v4_c1.mp4", "tmp/v4_c2.mp4", "tmp/v4_c3.mp4"]
ins = sum([["-i", p] for p in parts], [])
fc = "".join(f"[{i}:v]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1[v]"
run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-an",
     "-c:v", "libx264", "-crf", 12, "-preset", "slow", "tmp/v4_master.mp4"])
total = dur("tmp/v4_master.mp4"); print("TOTAL", round(total, 2))
if total >= 10:
    sys.exit("too long")
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v4_master.mp4", "-an", "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuv420p", "-crf", 23, "-preset", "slow", "-movflags", "+faststart", "out/swell_hero_v4.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v4_master.mp4", "-an", "-c:v", "libvpx-vp9", "-b:v", 0, "-crf", 34,
     "-row-mt", 1, "-deadline", "good", "-cpu-used", 2, "out/swell_hero_v4.webm"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v4_master.mp4", "-frames:v", 1, "-q:v", 3, "out/swell_hero_v4_poster.jpg"])
for f in ["out/swell_hero_v4.mp4", "out/swell_hero_v4.webm"]:
    print(f, round(dur(f), 2), "s", round(os.path.getsize(f) / 1e6, 2), "MB")
