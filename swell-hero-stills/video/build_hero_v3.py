"""S-WELL hero video v3: 3 beats joined by match cuts on the neon rail light.

beat A  clips/c1.mp4                 train run           -> push into neon streak  (P_A)
beat B  clips/l1.mp4 + clips/l2.mp4  one continuous take: pull out of neon rail (P_B) ... push into twin rail (P_C)
beat C  clips/e1.mp4 + hold          pull out of S-curve neon rail (P_D) -> S symbol -> wordmark

Match cut = at the cut both shots show their light point centred, at the same zoom, with motion blur
and a short light bloom, so the neon line carries over. Silent, 1920x1080, 24 fps, < 10 s.
"""
import json, os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
os.makedirs("out", exist_ok=True); os.makedirs("tmp", exist_ok=True)
W, H, FPS = 1920, 1080, 24
T = 0.42      # match-cut zoom time on each side
ZM = 2.4      # zoom at the cut
HOLD = 1.5
FD = "/usr/share/fonts/opentype/inter/"

P_A = (1350, 770)   # c1 end: neon streak under the train
P_B = (560, 800)    # l1 start: neon rail
P_C = tuple(map(int, os.environ.get("P_C", "520,820").split(",")))  # l2 end: twin rail
P_D = (880, 760)    # e1 start: S-curve neon rail


def run(cmd):
    print(" ".join(map(str, cmd))); subprocess.run(list(map(str, cmd)), check=True)


def dur(p):
    return float(json.loads(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", p]))["format"]["duration"])


def base(src, ss, out_len, speed, out):
    run(["ffmpeg", "-y", "-v", "error", "-ss", ss, "-t", out_len * speed, "-i", src, "-vf",
         f"setpts=PTS/{speed},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},format=yuv420p",
         "-an", "-c:v", "libx264", "-crf", 14, out])


def matchcut(src, out, D, pin=None, pout=None):
    """pin: pull out of point at start; pout: push into point at end."""
    def ease(tv):
        terms = []
        if pin:
            terms.append(f"pow(max(0,1-{tv}/{T}),2)")
        if pout:
            terms.append(f"pow(max(0,({tv}-{D - T})/{T}),2)")
        return "+".join(terms) if terms else "0"

    def pt(i, tv):
        a = pin[i] if pin else (W / 2, H / 2)[i]
        b = pout[i] if pout else (W / 2, H / 2)[i]
        return f"if(lt({tv},{D/2}),{a},{b})"

    S2 = 2  # zoompan on a 2x upscaled source to avoid sub-pixel jitter
    e = ease("it")
    px, py = pt(0, "it"), pt(1, "it")
    cx = f"({px}+({W/2}-{px})*({e}))"   # screen position of the point (moves to centre at the cut)
    cy = f"({py}+({H/2}-{py})*({e}))"
    z = f"(1+{ZM - 1}*({e}))"
    xexpr = f"max(0,min(iw-iw/zoom,{S2}*{px}-{S2}*{cx}/zoom))"
    yexpr = f"max(0,min(ih-ih/zoom,{S2}*{py}-{S2}*{cy}/zoom))"
    et = ease("t")
    vf = (f"scale={W*S2}:{H*S2}:flags=lanczos,"
          f"zoompan=z='{z}':x='{xexpr}':y='{yexpr}':d=1:s={W}x{H}:fps={FPS},"
          f"eq=brightness='0.12*({et})':saturation='1+0.3*({et})':eval=frame,setsar=1,format=yuv420p")
    run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vf", vf, "-an", "-c:v", "libx264", "-crf", 14, out])


# beat A
base("clips/c1.mp4", 0.3, 1.6, 1.0, "tmp/v3_a0.mp4")
matchcut("tmp/v3_a0.mp4", "tmp/v3_a.mp4", 1.6, pout=P_A)

# beat B (continuous take)
base("clips/l1.mp4", 0.0, 2.3, 2.17, "tmp/v3_b1.mp4")
base("clips/l2.mp4", 0.0, 2.1, 2.38, "tmp/v3_b2.mp4")
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v3_b1.mp4", "-i", "tmp/v3_b2.mp4", "-filter_complex",
     "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-c:v", "libx264", "-crf", 14, "tmp/v3_b0.mp4"])
matchcut("tmp/v3_b0.mp4", "tmp/v3_b.mp4", dur("tmp/v3_b0.mp4"), pin=P_B, pout=P_C)

# beat C: morph + hold with wordmark
base("clips/e1.mp4", 0.0, 2.1, 2.38, "tmp/v3_c0.mp4")
matchcut("tmp/v3_c0.mp4", "tmp/v3_c1.mp4", 2.1, pin=P_D)
run(["ffmpeg", "-y", "-v", "error", "-sseof", "-0.05", "-i", "tmp/v3_c0.mp4", "-frames:v", 1, "tmp/v3_last.png"])
last = np.asarray(Image.open("tmp/v3_last.png").convert("RGB")).astype(int)
r, g, b = last[..., 0], last[..., 1], last[..., 2]
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
ov.save("tmp/v3_wordmark.png")
run(["ffmpeg", "-y", "-v", "error", "-loop", 1, "-t", HOLD, "-i", "tmp/v3_last.png", "-loop", 1, "-t", HOLD,
     "-i", "tmp/v3_wordmark.png", "-filter_complex",
     f"[0:v]fps={FPS},format=yuv420p[bg];[1:v]fps={FPS},format=rgba,fade=t=in:st=0:d=0.5:alpha=1[wm];"
     f"[bg][wm]overlay=x='-40*max(0,1-t/0.6)':y=0,format=yuv420p[v]", "-map", "[v]", "-c:v", "libx264", "-crf", 14,
     "tmp/v3_c2.mp4"])

# hard-cut assembly (match cuts carry the transition)
parts = ["tmp/v3_a.mp4", "tmp/v3_b.mp4", "tmp/v3_c1.mp4", "tmp/v3_c2.mp4"]
ins = sum([["-i", p] for p in parts], [])
fc = "".join(f"[{i}:v]" for i in range(len(parts))) + f"concat=n={len(parts)}:v=1[v]"
run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", fc, "-map", "[v]", "-an",
     "-c:v", "libx264", "-crf", 12, "-preset", "slow", "tmp/v3_master.mp4"])
total = dur("tmp/v3_master.mp4"); print("TOTAL", round(total, 2))
if total >= 10:
    sys.exit("too long")
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v3_master.mp4", "-an", "-c:v", "libx264", "-profile:v", "high",
     "-pix_fmt", "yuv420p", "-crf", 23, "-preset", "slow", "-movflags", "+faststart", "out/swell_hero_v3.mp4"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v3_master.mp4", "-an", "-c:v", "libvpx-vp9", "-b:v", 0, "-crf", 34,
     "-row-mt", 1, "-deadline", "good", "-cpu-used", 2, "out/swell_hero_v3.webm"])
run(["ffmpeg", "-y", "-v", "error", "-i", "tmp/v3_master.mp4", "-frames:v", 1, "-q:v", 3, "out/swell_hero_v3_poster.jpg"])
for f in ["out/swell_hero_v3.mp4", "out/swell_hero_v3.webm"]:
    print(f, round(dur(f), 2), "s", round(os.path.getsize(f) / 1e6, 2), "MB")
