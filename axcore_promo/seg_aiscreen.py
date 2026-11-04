"""Opening, shot 3 (client's reference S2, second half): the AI inspection screen - an industrial touch monitor at the
inspection station showing the board the camera module just looked at; a cyan scan line runs down the board, the
components it passes are marked, one is found faulty (red box, REJECT), the result panel counts it. Light UI (white /
blue, as the film's other screens), the station softly out of focus round the monitor, a slow push in.
  0.00  scan line starts at the top; boxes mark the parts behind it
  0.95  the defect: red box pops, "REJECT", the panel turns red; 1.20 a red frame flashes round the board
Usage: python3 seg_aiscreen.py <board.png|-> <backdrop.png> <out.mp4> [height=480] [frames=48]
  board: "-" draws a top-down board (default); backdrop.png: the station (a frame of the inspection shot)
"""
import subprocess
import sys

import numpy as np
import skia

import engine as E
from engine import (W, H, R, WHITE, BLUE, lerp, prog, clamp, e_io_sine, e_out_cubic, e_io_cubic, paint_fill,
                    paint_stroke, rrect, rrect_stroke, text, icon)

BAR = 138
INK = "#14203A"
STEEL = "#6A7891"
RED = "#F0384B"
CYAN = "#19C8FF"
GREEN = "#1FC98A"
MON = R(150, 150, 1500, 780)                    # the monitor (bezel), filling most of the band
SCR = R(MON.left() + 22, MON.top() + 22, MON.width() - 44, MON.height() - 44)
HEAD = 56
IMG = R(SCR.left() + 20, SCR.top() + HEAD + 16, SCR.width() * 0.68, SCR.height() - HEAD - 36)
PAN = R(IMG.right() + 20, IMG.top(), SCR.right() - IMG.right() - 40, IMG.height())
SCAN0, SCAN_D = 0.05, 1.45
DEF_T = 0.95
# parts the scan marks (fractions of the board image), the faulty one last
PARTS = [(0.16, 0.14, 0.10, 0.12), (0.40, 0.10, 0.14, 0.10), (0.70, 0.18, 0.12, 0.14), (0.24, 0.40, 0.16, 0.12),
         (0.58, 0.44, 0.10, 0.10), (0.82, 0.48, 0.10, 0.16), (0.12, 0.70, 0.12, 0.12), (0.44, 0.74, 0.14, 0.12),
         (0.74, 0.76, 0.12, 0.10)]
DEFECT = (0.56, 0.58, 0.09, 0.09)


def pcb(w=1600, h=1000, seed=11):
    """A top-down circuit board (drawn, so it stays sharp at 2K): green solder mask, copper traces, pads and vias,
    ICs with pins, small passives, white silkscreen."""
    rng = np.random.default_rng(seed)
    sf = skia.Surface.MakeRaster(skia.ImageInfo.Make(w, h, skia.ColorType.kRGBA_8888_ColorType,
                                                     skia.AlphaType.kPremul_AlphaType))
    c = sf.getCanvas()
    c.clear(E.col("#0E5B3C"))
    sh = skia.GradientShader.MakeRadial(skia.Point(w * 0.45, h * 0.4), w * 0.8,
                                        [E.colint("#1C8A5C", 0.55), E.colint("#0A4029", 0.0)])
    c.drawRect(R(0, 0, w, h), skia.Paint(Shader=sh))
    cu = paint_stroke("#C9A15A", 0.85, 3.0)
    cu.setStrokeCap(skia.Paint.kRound_Cap)
    for _ in range(140):                          # traces: right-angle and 45-degree runs
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        pth = skia.Path()
        pth.moveTo(x, y)
        for _ in range(rng.integers(2, 5)):
            d = rng.choice(4)
            L = rng.uniform(40, 220)
            x += (L, -L, 0, 0)[d] if d < 2 else 0
            y += (0, 0, L, -L)[d] if d >= 2 else 0
            if rng.random() < 0.3:
                x += L * 0.4
                y += L * 0.4
            pth.lineTo(x, y)
        cu.setStrokeWidth(float(rng.choice([2.0, 3.0, 4.5])))
        c.drawPath(pth, cu)
        c.drawCircle(x, y, 6, paint_fill("#D8B26A", 0.9))
        c.drawCircle(x, y, 2.5, paint_fill("#0B2E20"))
    for _ in range(90):                           # vias
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        c.drawCircle(x, y, 5, paint_fill("#D8B26A", 0.9))
        c.drawCircle(x, y, 2, paint_fill("#0B2E20"))
    for (fx, fy, fw, fh) in PARTS + [DEFECT]:     # the parts the scan marks
        r = R(w * fx, h * fy, w * fw, h * fh).makeInset(w * fw * 0.12, h * fh * 0.12)
        rrect(c, r, 6, "#15181D")
        rrect_stroke(c, r, 6, "#3A4048", 1.0, 2.0)
        n = int(r.width() // 16)
        for j in range(n):
            x = r.left() + 8 + j * (r.width() - 16) / max(1, n - 1)
            c.drawRect(R(x - 3, r.top() - 10, 6, 10), paint_fill("#D9DDE3"))
            c.drawRect(R(x - 3, r.bottom(), 6, 10), paint_fill("#D9DDE3"))
        c.drawCircle(r.left() + 14, r.top() + 14, 5, paint_fill("#2A2F37"))
    for _ in range(160):                          # passives
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        vert = rng.random() < 0.5
        r = R(x, y, 14, 26) if vert else R(x, y, 26, 14)
        c.drawRect(r, paint_fill(rng.choice(["#C9B79A", "#2B2F35", "#8C6A3E"])))
        c.drawRect(R(r.left(), r.top(), r.width(), 5) if vert else R(r.left(), r.top(), 5, r.height()),
                   paint_fill("#E3E6EA"))
    for _ in range(40):                           # silkscreen
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        text(c, "%s%d" % (rng.choice(["R", "C", "U", "Q", "D"]), rng.integers(1, 99)), x, y, 18, "SemiBold",
             "#E8F2EC", 0.75)
    return sf.makeImageSnapshot()


def load(path):
    a = np.asarray(__import__("PIL.Image", fromlist=["Image"]).open(path).convert("RGBA"))
    return skia.Image.fromarray(a.copy(), colorType=skia.ColorType.kRGBA_8888_ColorType)


def cover(c, img, rect, k=1.0, cx=0.5, cy=0.5, paint=None):
    s = max(rect.width() / img.width(), rect.height() / img.height()) * k
    iw, ih = img.width() * s, img.height() * s
    x = rect.left() + (rect.width() - iw) * cx
    y = rect.top() + (rect.height() - ih) * cy
    c.save()
    c.clipRect(rect, doAntiAlias=True)
    c.drawImageRect(img, R(x, y, iw, ih), skia.SamplingOptions(skia.CubicResampler.Mitchell()), paint or skia.Paint())
    c.restore()


def render(c, s, board, back):
    # the station round the monitor, out of focus and bright
    bp = skia.Paint(ImageFilter=skia.ImageFilters.Blur(18, 18))
    bp.setColorFilter(E.grade_filter(bright=1.18, contrast=0.92, sat=0.75, tint=(-0.01, 0.0, 0.02)))
    cover(c, back, R(-60, -40, W + 120, H + 80), paint=bp)
    c.drawRect(R(0, 0, W, H), paint_fill("#EAF2FF", 0.30))
    # the monitor: graphite bezel, a soft shadow, the machine panel with the e-stop on its right
    rrect(c, MON.makeOffset(0, 18), 26, "#0B1220", 0.35, blur=26)
    rrect(c, MON, 26, "#252C38")
    rrect_stroke(c, MON, 26, "#4A5466", 1.0, 2.0)
    side = R(MON.right() + 46, MON.top() + 120, 190, 380)
    rrect(c, side, 18, "#E9EDF3")
    rrect_stroke(c, side, 18, "#C9D1DD", 1.0, 2.0)
    c.drawCircle(side.centerX(), side.top() + 120, 46, paint_fill("#C9CFD8"))
    c.drawCircle(side.centerX(), side.top() + 120, 36, paint_fill("#E0313F"))
    c.drawCircle(side.centerX() - 10, side.top() + 108, 12, paint_fill("#FF8A92", 0.6))
    for j in range(3):
        rrect(c, R(side.left() + 40, side.top() + 220 + j * 46, side.width() - 80, 26), 8, "#CBD3DF")
    # the screen
    rrect(c, SCR, 8, "#F5F8FC")
    c.save()
    c.clipRRect(skia.RRect.MakeRectXY(SCR, 8, 8), doAntiAlias=True)
    c.drawRect(R(SCR.left(), SCR.top(), SCR.width(), HEAD), paint_fill(WHITE))
    c.drawRect(R(SCR.left(), SCR.top() + HEAD - 1, SCR.width(), 1), paint_fill("#DCE3EE"))
    icon(c, "scan", SCR.left() + 34, SCR.top() + HEAD / 2, 24, BLUE)
    text(c, "AI 비전 검사", SCR.left() + 58, SCR.top() + 36, 22, "Bold", INK)
    text(c, "LINE 03 · PCB-A21", SCR.left() + 196, SCR.top() + 36, 17, "Medium", STEEL)
    live = 0.55 + 0.45 * np.sin(s * 7)
    c.drawCircle(SCR.right() - 124, SCR.top() + HEAD / 2, 6, paint_fill(GREEN, live))
    text(c, "실시간", SCR.right() - 110, SCR.top() + 35, 17, "SemiBold", INK)
    # the board image under the scan
    rrect(c, IMG, 10, "#0C1626")
    cover(c, board, IMG, k=1.04 + 0.02 * prog(s, 0, 2.0))
    rp = R(IMG.left(), IMG.top(), IMG.width(), IMG.height())
    c.save()
    c.clipRect(rp)
    g = paint_stroke("#9FE6FF", 0.10, 1.0)
    for i in range(1, 12):
        x = rp.left() + rp.width() * i / 12
        c.drawLine(x, rp.top(), x, rp.bottom(), g)
    for i in range(1, 8):
        y = rp.top() + rp.height() * i / 8
        c.drawLine(rp.left(), y, rp.right(), y, g)
    q = e_io_sine(prog(s, SCAN0, SCAN_D))
    sy = rp.top() + rp.height() * q
    if 0 < q < 1:                                 # the scan line and its trail
        sh = skia.GradientShader.MakeLinear([skia.Point(0, sy - 120), skia.Point(0, sy)],
                                            [E.colint(CYAN, 0.0), E.colint(CYAN, 0.28)])
        c.drawRect(R(rp.left(), sy - 120, rp.width(), 120), skia.Paint(Shader=sh))
        c.drawRect(R(rp.left(), sy - 2, rp.width(), 4), paint_fill("#BFF3FF", 0.95))
        c.drawRect(R(rp.left(), sy - 9, rp.width(), 18), paint_fill(CYAN, 0.35, blur=8))
    for (fx, fy, fw, fh) in PARTS:                # parts behind the line: marked OK
        y0 = rp.top() + rp.height() * (fy + fh)
        a = e_out_cubic(clamp((sy - y0) / 40 + 0.2)) if q > 0 else 0
        if a > 0:
            r = R(rp.left() + rp.width() * fx, rp.top() + rp.height() * fy, rp.width() * fw, rp.height() * fh)
            c.drawRect(r, paint_stroke(GREEN, 0.85 * a, 2.0))
            c.drawRect(R(r.left(), r.top() - 18, 34, 18), paint_fill(GREEN, 0.85 * a))
            text(c, "OK", r.left() + 6, r.top() - 4, 13, "Bold", WHITE, a)
    d = prog(s, DEF_T, 0.25)
    if d > 0:                                     # the defect
        fx, fy, fw, fh = DEFECT
        r = R(rp.left() + rp.width() * fx, rp.top() + rp.height() * fy, rp.width() * fw, rp.height() * fh)
        k = 1 + 0.5 * (1 - e_out_cubic(d))
        rr = R(r.centerX() - r.width() * k / 2, r.centerY() - r.height() * k / 2, r.width() * k, r.height() * k)
        pulse = 0.75 + 0.25 * np.sin((s - DEF_T) * 10)
        c.drawRect(rr, paint_fill(RED, 0.16 * d))
        c.drawRect(rr, paint_stroke(RED, d * pulse, 3.0))
        tag = R(rr.right() + 8, rr.top(), 118, 30)
        rrect(c, tag, 6, RED, d)
        text(c, "REJECT", tag.left() + 14, tag.top() + 21, 16, "Bold", WHITE, d)
    f = prog(s, DEF_T + 0.25, 0.5)
    if 0 < f < 1:                                 # the red frame flash round the board
        c.drawRect(rp.makeInset(3, 3), paint_stroke(RED, 0.9 * (1 - f) * min(1, f * 6), 6.0))
    c.restore()
    rrect_stroke(c, IMG, 10, "#C7D2E2", 1.0, 1.5)
    # the result panel
    rrect(c, PAN, 12, WHITE)
    rrect_stroke(c, PAN, 12, "#DCE3EE", 1.0, 1.5)
    text(c, "검사 결과", PAN.left() + 22, PAN.top() + 40, 20, "Bold", INK)
    pill = R(PAN.left() + 22, PAN.top() + 62, PAN.width() - 44, 52)
    if d > 0:
        rrect(c, pill, 12, RED, d)
        icon(c, "alert", pill.left() + 30, pill.centerY(), 22, WHITE, d)
        text(c, "불량 감지", pill.left() + 52, pill.centerY() + 7, 20, "Bold", WHITE, d)
    if d < 1:
        rrect(c, pill, 12, "#E8F1FF", 1 - d)
        icon(c, "scan", pill.left() + 30, pill.centerY(), 22, BLUE, 1 - d)
        text(c, "검사 중 %d%%" % int(99 * q), pill.left() + 52, pill.centerY() + 7, 20, "Bold", BLUE, 1 - d)
    n_ok = 1284 + int(12 * q)
    rows = [("검사 수량", "{:,}".format(n_ok)), ("양품률", "99.2%"), ("불량", "3" if d > 0.5 else "2"),
            ("판정 시간", "0.08 s")]
    for j, (k_, v) in enumerate(rows):
        y = pill.bottom() + 46 + j * 44
        text(c, k_, PAN.left() + 22, y, 17, "Medium", STEEL)
        text(c, v, PAN.right() - 22, y, 19, "Bold", RED if (k_ == "불량" and d > 0.5) else INK, 1.0, "right")
        c.drawRect(R(PAN.left() + 22, y + 14, PAN.width() - 44, 1), paint_fill("#EEF2F7"))
    ch = R(PAN.left() + 22, PAN.bottom() - 150, PAN.width() - 44, 120)
    rrect(c, ch, 10, "#F4F8FD")
    vals = [0.55, 0.62, 0.58, 0.66, 0.64, 0.70, 0.68, 0.74, 0.71, 0.78]
    pts = [(ch.left() + 14 + i * (ch.width() - 28) / 9, ch.bottom() - 18 - v * (ch.height() - 40)) for i, v in
           enumerate(vals)]
    E.line(c, E.poly(pts), BLUE, 1.0, 2.6, (0, e_io_sine(prog(s, 0.0, 1.4))))
    text(c, "AI 판정 신뢰도", ch.left() + 12, ch.top() + 22, 14, "SemiBold", STEEL)
    c.restore()


if __name__ == "__main__":
    board_p, back_p, out = sys.argv[1], sys.argv[2], sys.argv[3]
    height = int(sys.argv[4]) if len(sys.argv) > 4 else 480
    NF = int(sys.argv[5]) if len(sys.argv) > 5 else 48
    E.configure(E.SEED, E.CHAOS)
    SCV = max(1.0, height / H)
    SW, SH = int(round(W * SCV)), int(round(H * SCV))
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(SW, SH, skia.ColorType.kRGBA_8888_ColorType,
                                                       skia.AlphaType.kPremul_AlphaType))
    finish = E.Finish(size=(SW, SH))
    board = pcb() if board_p == "-" else load(board_p)
    back = load(back_p)
    width = int(round(height * 16 / 9 / 2)) * 2
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", "%dx%d" % (SW, SH), "-r", "24000/1001", "-i", "-",
                            "-vf", "scale=%d:%d:flags=lanczos" % (width, height),
                            "-c:v", "libx264", "-preset", "medium", "-crf", "18" if height <= 1080 else "14",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    bar = int(round(BAR * SCV))
    for f in range(NF):
        s = f / 24.0
        c = surf.getCanvas()
        c.clear(skia.Color4f(0, 0, 0, 1))
        c.save()
        c.scale(SCV, SCV)
        # push in leaving the cut at the inspection shot's speed (ease-out), drifting right and speeding up to
        # the right into the next cut (the logistics shot trucks right at ~0.4 % of the width per frame)
        z = 1.0 + 0.06 * e_out_cubic(prog(s, 0.0, NF / 24.0 * 1.4))
        dx = 18 * prog(s, 0, NF / 24.0) + 0.013 * W * np.exp((f - NF) / 3.5)
        c.translate(W / 2 - dx, H / 2)
        c.scale(z, z)
        c.translate(-W / 2, -H / 2)
        render(c, s, board, back)
        c.restore()
        fr = finish.apply(surf, 100 + f)
        fr[:bar] = 0
        fr[-bar:] = 0
        enc.stdin.write(np.ascontiguousarray(fr).tobytes())
    enc.stdin.close()
    enc.wait()
    print(out)
