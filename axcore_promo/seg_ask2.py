"""Patch 00:01:14:11-00:01:20:01 (135 frames) of seg_ask: the highlight and the cursor hop one time fewer and slower;
the systems are not swept away into the search card - they shrink a little, go soft and stay behind it as its
background, fading out as the answer cards come in; no flash where they used to meet (01:16:23); the search card
has less room under its input. Everything else is seg_ask's own render, so the first and the last frame join the
delivered file.
Usage: python3 seg_ask2.py <out.mp4> [height=480]
"""
import subprocess
import sys

from engine import R
import seg_ask as Q

F0, F1 = 1, 136                  # seg_ask frames = timeline 01:14:11 .. 01:20:01

if __name__ == "__main__":
    Q.V2 = True
    Q.SEARCH = R(530, 396, 860, 248)        # bottom padding 108 -> 56 (the card stays centred in the band)
    Q.PILL0 = R(574, 496, 772, 92)
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    a, b = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (F0, F1)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = Q.setup(height)
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (Q.FPS_NUM, Q.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for f in range(a, b):
        enc.stdin.write(Q.frame(f, surf, finish).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
