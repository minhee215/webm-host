"""The landing page (search, 기업 찾기) taken out (client: 00:00:23:04-00:00:26:07 deleted); the navy stage's line and
diamond now lead straight into the upload page: the line draws back into the diamond, the diamond glides to the
middle and turns into the stepper's "파일 업로드" dot, the white page opens from it with the camera close on the
stepper, then the camera pulls back onto the whole upload page ("우리 회사 자료를 올려 주세요").
Starts after seg_axpoint frame 1 (the line, as the edit has it at 23:03) and ends on seg_axpoint frame 88 exactly
(the upload page settled, the file stack coming in), so the edit carries on with seg_axpoint frame 89.
Usage: python3 trans_axp.py <out.mp4> [height=480] [first last]
"""
import math
import subprocess
import sys

import numpy as np
import skia

import engine as E
import scenes as S
import seg_axpoint as A
from engine import W, H, R, lerp, prog, clamp, e_io_cubic, e_io_sine, e_out_cubic, paint_fill, paint_stroke

N = 36                     # frames (1.5 s)
F_START, F_END = 1, 88     # seg_axpoint frames this hands over from / lands on
LINE_X0, LINE_X1, LINE_Y = S.BAR_LINE[1], S.BAR_LINE[0], S.BAR_LINE[2]
Z0 = 3.0                   # camera zoom on the stepper when the page opens
MID = (960.0, 470.0)       # where the diamond / dot goes (screen)


def page_t(k):
    return A.ft(F_END) - (N - 1 - k) / 24.0


def dot_page():
    """The '파일 업로드' dot in page coordinates (seg_axpoint.nav, step 0)."""
    x = 960 - 2 * 128
    return x - A.text_w(A.STEPS[0], 13, "SemiBold") / 2 - 12, 181.0


def render(c, k):
    u = k / (N - 1)
    t_nav = A.ft(F_START) + (k + 1) / 24.0
    tp = page_t(k)
    # timeline of the move
    g = e_io_cubic(prog(k, 0, 12))                      # line draws back, diamond glides to the middle
    m = e_io_cubic(prog(k, 6, 8))                       # diamond -> dot
    rev = e_io_cubic(prog(k, 10, 9))                    # white page opens from the dot
    pull = e_io_cubic(prog(k, 17, N - 1 - 17))          # camera pulls back onto the page
    # the dot on screen at the end (page camera at tp) and the zoom anchor now
    dpx, dpy = dot_page()
    dsx, dsy = A.to_screen(A.CAM_DOCS, tp, dpx, dpy)
    ax_, ay_ = lerp(MID[0], dsx, pull), lerp(MID[1], dsy, pull)
    z = lerp(Z0, 1.0, pull)
    # 1) the navy stage (the previous segment's, line left out) until the page has covered it
    if rev < 1:
        S.S5_FRONT, S.S5_FRONT_END, S.S5_LINE_HIDE = True, "line", True
        T = t_nav - 1.0
        S.sc05(c, T, T - S.SC05_T0, 10.0)
        S.S5_LINE_HIDE = False
        # the line drawing back into the diamond
        bx, by = lerp(LINE_X1, MID[0], g), lerp(LINE_Y, MID[1], g)
        la = 1 - e_io_sine(prog(k, 4, 8))
        if la > 0:
            x0 = lerp(LINE_X0, bx, e_io_cubic(prog(k, 0, 10)))
            for wdt, al, bl in ((7, 0.5, 8), (2.2, 1.0, 0)):
                c.drawLine(x0, by, bx, by, paint_stroke(A.LINE_BLUE, al * la, wdt, blur=bl))
    # 2) the page, opening from the dot inside a growing circle, seen through the zoom about the dot
    if rev > 0:
        rad = lerp(0, 2600, rev ** 1.6)
        c.save()
        if rev < 1:
            path = skia.Path()
            path.addCircle(ax_, ay_, rad)
            c.clipPath(path, skia.ClipOp.kIntersect, True)
        c.translate(ax_, ay_)
        c.scale(z, z)
        c.translate(-dsx, -dsy)
        A.docs(c, tp)
        c.restore()
        if rev < 1:
            c.drawCircle(ax_, ay_, rad, paint_stroke("#9DB8FF", 0.7 * (1 - rev), 3, blur=6))
    # 3) the diamond turning into the dot (until the page's own dot is under it)
    da = 1 - e_io_sine(prog(k, 15, 4))
    if da > 0:
        bx, by = lerp(LINE_X1, MID[0], g), lerp(LINE_Y, MID[1], g)
        size = lerp(15.6, 15.0 * Z0, m)
        col_ = A.LINE_BLUE if m < 0.5 else A.BLUE
        c.save()
        c.translate(bx, by)
        c.rotate(45 * (1 - m))
        rr_ = R(-size / 2, -size / 2, size, size)
        rad_ = lerp(1.5, size / 2, m)
        c.drawRRect(skia.RRect.MakeRectXY(rr_, 11, 11), paint_fill(A.LINE_BLUE, 0.5 * (1 - m) * da, blur=8))
        c.drawRRect(skia.RRect.MakeRectXY(rr_, rad_, rad_), paint_fill(col_, da))
        if m < 0.5:
            c.drawRRect(skia.RRect.MakeRectXY(rr_, rad_, rad_), paint_stroke(A.WHITE, (1 - 2 * m) * da, 1.2))
        c.restore()


if __name__ == "__main__":
    out = sys.argv[1]
    height = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    F0, F1 = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, N)
    width = int(round(height * 16 / 9 / 2)) * 2
    surf, finish, SWD, SHD = A.setup(height)
    bar = int(round(A.BAR * A.SCV))
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SWD, SHD), "-r", "%d/%d" % (A.FPS_NUM, A.FPS_DEN), "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    for k in range(F0, F1):
        fe = F_START + (k + 1) * (F_END - F_START) / N          # the film finish eases in as in seg_axpoint
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(A.SCV, A.SCV)
        render(c, k)
        c.restore()
        raw = surf.makeImageSnapshot().toarray()[..., :3].astype(np.float32)
        fin = finish.apply(surf, A.F_TL + int(round(fe))).astype(np.float32)
        w = e_io_sine(clamp(fe / 30))
        img = raw * (1 - w) + fin * w
        img[:bar] = 0
        img[-bar:] = 0
        enc.stdin.write(np.clip(img + 0.5, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out, F1 - F0)
